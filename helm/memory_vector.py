"""
helm/memory_vector.py — Optional local semantic (vector) memory layer.

Adds embedding-based recall on top of the existing keyword/FTS5 memory in
``helm/memory.py`` and ``helm/agent/memory.py``.

Design goals
------------
* **Optional & safe.** If ``fastembed`` isn't installed (or the model can't
  load), every function degrades to a no-op and callers fall back to the
  existing keyword/FTS recall — no crashes, no behaviour change, no build
  breakage. This is why it's a separate module rather than a hard dependency.
* **Local & free.** Embeddings run on-device via fastembed (ONNX). No API key,
  no network at query time — consistent with RAPR's no-token-cost model.
* **No new services.** Vectors live in a plain ``memory_vectors`` table inside
  the existing ``helmhq.db`` (created lazily). Similarity is a brute-force
  normalized dot product, which is optimal at the memory cap (~500 rows) and
  needs no native SQLite extension. ``numpy`` is used when present, with a
  pure-Python fallback otherwise.

Namespacing lets one table serve multiple callers:
    "mem"            → shared user memory (helm/memory.py), ref_id = memories.id
    "agent:<id>"     → agent node outputs (helm/agent/memory.py), ref_id = row id

Public API
----------
    is_enabled() -> bool
    upsert(namespace, ref_id, text) -> bool
    delete(namespace, ref_id) -> bool
    search(query, limit=20, namespace="mem", allowed_ids=None) -> list[(ref_id, score)]
    count(namespace=None) -> int
    backfill(namespace, items) -> int          # items: iterable of (ref_id, text)

Environment
-----------
    MEMORY_VECTOR_ENABLED   "1"/"0"   (default "1")
    MEMORY_EMBED_MODEL      fastembed model name (default "BAAI/bge-small-en-v1.5")
"""

from __future__ import annotations

import math
import os
import threading
from array import array
from typing import Iterable, Optional

# Logger: use the app logger when available, fall back to stdlib otherwise so
# this module is importable in isolation (tests / tooling).
try:
    from helm.config import logger
except Exception:  # pragma: no cover
    import logging
    logger = logging.getLogger("memory_vector")

# numpy is optional — only used to speed up the dot products.
try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

_ENABLED_ENV = os.environ.get("MEMORY_VECTOR_ENABLED", "1") not in ("0", "false", "False", "")
_MODEL_NAME = os.environ.get("MEMORY_EMBED_MODEL", "BAAI/bge-small-en-v1.5")

_model = None
_model_failed = False
_model_lock = threading.Lock()
_schema_ready = False


# ---------------------------------------------------------------------------
# Embedding model (lazy, best-effort)
# ---------------------------------------------------------------------------

def _get_model():
    """Lazily construct the fastembed model. Returns None if unavailable."""
    global _model, _model_failed
    if _model is not None:
        return _model
    if _model_failed or not _ENABLED_ENV:
        return None
    with _model_lock:
        if _model is not None:
            return _model
        if _model_failed:
            return None
        try:
            from fastembed import TextEmbedding  # type: ignore
            _model = TextEmbedding(model_name=_MODEL_NAME)
            logger.info("memory_vector: embedding model loaded (%s)", _MODEL_NAME)
        except Exception as exc:
            _model_failed = True
            logger.info(
                "memory_vector: embeddings unavailable (%s) — keyword/FTS recall only",
                exc,
            )
            return None
    return _model


def is_enabled() -> bool:
    """True only if embeddings are turned on AND the model is loadable."""
    return _ENABLED_ENV and _get_model() is not None


def _normalize(vec: list) -> list:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 1e-12:
        return vec
    return [x / norm for x in vec]


def _embed(texts: list) -> Optional[list]:
    """Embed and L2-normalize texts. Returns list[list[float]] or None."""
    model = _get_model()
    if model is None:
        return None
    try:
        raw = list(model.embed(list(texts)))
        out = []
        for v in raw:
            try:
                v = v.tolist()  # fastembed yields numpy arrays
            except Exception:
                v = list(v)
            out.append(_normalize([float(x) for x in v]))
        return out
    except Exception as exc:
        logger.warning("memory_vector: embed failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Storage (plain table in helmhq.db; no native extension required)
# ---------------------------------------------------------------------------

def _db():
    from helm.db import get_db
    return get_db()


def _ensure_schema(db) -> bool:
    global _schema_ready
    if _schema_ready:
        return True
    try:
        db.execute(
            "CREATE TABLE IF NOT EXISTS memory_vectors ("
            "  namespace TEXT NOT NULL,"
            "  ref_id    INTEGER NOT NULL,"
            "  dim       INTEGER NOT NULL,"
            "  vec       BLOB NOT NULL,"
            "  updated   REAL,"
            "  PRIMARY KEY (namespace, ref_id)"
            ")"
        )
        db.commit()
        _schema_ready = True
        return True
    except Exception as exc:
        logger.warning("memory_vector: schema init failed: %s", exc)
        return False


def _pack(vec: list) -> bytes:
    return array("f", vec).tobytes()


def _unpack(blob: bytes) -> list:
    a = array("f")
    a.frombytes(blob)
    return a.tolist()


def _dot(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Public operations (all best-effort; never raise)
# ---------------------------------------------------------------------------

def upsert(namespace: str, ref_id: int, text: str) -> bool:
    """Embed `text` and store/replace the vector for (namespace, ref_id)."""
    if not text or not text.strip() or not is_enabled():
        return False
    try:
        embs = _embed([text])
        if not embs:
            return False
        vec = embs[0]
        db = _db()
        if not _ensure_schema(db):
            return False
        db.execute(
            "INSERT OR REPLACE INTO memory_vectors (namespace, ref_id, dim, vec, updated)"
            " VALUES (?, ?, ?, ?, strftime('%s','now'))",
            (namespace, int(ref_id), len(vec), _pack(vec)),
        )
        db.commit()
        return True
    except Exception as exc:
        logger.warning("memory_vector: upsert failed (ns=%s id=%s): %s", namespace, ref_id, exc)
        return False


def delete(namespace: str, ref_id: int) -> bool:
    """Remove the vector for (namespace, ref_id)."""
    try:
        db = _db()
        if not _ensure_schema(db):
            return False
        db.execute(
            "DELETE FROM memory_vectors WHERE namespace = ? AND ref_id = ?",
            (namespace, int(ref_id)),
        )
        db.commit()
        return True
    except Exception as exc:
        logger.warning("memory_vector: delete failed (ns=%s id=%s): %s", namespace, ref_id, exc)
        return False


def search(query: str, limit: int = 20, namespace: str = "mem",
           allowed_ids: Optional[Iterable[int]] = None) -> list:
    """Return [(ref_id, score)] sorted by cosine similarity (score in 0..1).

    `allowed_ids`, if given, restricts results to that id set (e.g. only
    non-archived memories). Empty list on any failure or when disabled.
    """
    if not query or not query.strip() or not is_enabled():
        return []
    try:
        embs = _embed([query])
        if not embs:
            return []
        q = embs[0]
        db = _db()
        if not _ensure_schema(db):
            return []
        rows = db.execute(
            "SELECT ref_id, vec FROM memory_vectors WHERE namespace = ?",
            (namespace,),
        ).fetchall()
        if not rows:
            return []
        allowed = set(allowed_ids) if allowed_ids is not None else None

        scored = []
        if _np is not None:
            qv = _np.asarray(q, dtype=_np.float32)
            for r in rows:
                rid = r["ref_id"]
                if allowed is not None and rid not in allowed:
                    continue
                v = _np.frombuffer(r["vec"], dtype=_np.float32)
                if v.shape[0] != qv.shape[0]:
                    continue
                scored.append((rid, float(qv.dot(v))))
        else:
            for r in rows:
                rid = r["ref_id"]
                if allowed is not None and rid not in allowed:
                    continue
                v = _unpack(r["vec"])
                if len(v) != len(q):
                    continue
                scored.append((rid, _dot(q, v)))

        scored.sort(key=lambda t: -t[1])
        return scored[:limit]
    except Exception as exc:
        logger.warning("memory_vector: search failed: %s", exc)
        return []


def count(namespace: Optional[str] = None) -> int:
    try:
        db = _db()
        if not _ensure_schema(db):
            return 0
        if namespace:
            row = db.execute(
                "SELECT COUNT(*) FROM memory_vectors WHERE namespace = ?",
                (namespace,),
            ).fetchone()
        else:
            row = db.execute("SELECT COUNT(*) FROM memory_vectors").fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


def indexed_ids(namespace: str = "mem") -> set:
    """Return the set of ref_ids that already have a stored vector."""
    try:
        db = _db()
        if not _ensure_schema(db):
            return set()
        rows = db.execute(
            "SELECT ref_id FROM memory_vectors WHERE namespace = ?", (namespace,)
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()


def backfill(namespace: str, items: Iterable) -> int:
    """Index any (ref_id, text) pairs that lack vectors. Returns count indexed."""
    if not is_enabled():
        return 0
    indexed = 0
    for ref_id, text in items:
        if text and upsert(namespace, ref_id, text):
            indexed += 1
    if indexed:
        logger.info("memory_vector: backfilled %d vectors into ns=%s", indexed, namespace)
    return indexed
