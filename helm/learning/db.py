"""
helm/learning/db.py

SQLite-backed similarity index for task fingerprints.

Public API:
  upsert(fingerprint, task_type, keywords, tools_used)
  find_similar(fingerprint, task_type, keywords, tools_used, limit) -> list[dict]
  merge_fingerprints(src, canonical)
  resolve(fingerprint) -> str           # canonical fingerprint (follows merges)
  rebuild_from_logs()                   # populate from task_logs/ JSON files
  get_stats() -> dict

Similarity tiers (per spec):
  1.0  exact or merged match
  0.8  same task_type + >=2 of top-3 keywords overlap
  0.6  same task_type + same tools_used set
  0.3  same task_type only
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_DB_PATH = _HERE / "similarity.db"
_LOG_DIR = _HERE / "task_logs"
_ERROR_LOG = _HERE / "telemetry_errors.log"

# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _log(msg: str) -> None:
    try:
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} db: {msg}\n")
    except Exception:
        pass


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            fingerprint  TEXT PRIMARY KEY,
            task_type    TEXT NOT NULL,
            keywords     TEXT NOT NULL DEFAULT '[]',
            tools_used   TEXT NOT NULL DEFAULT '[]',
            sample_count INTEGER NOT NULL DEFAULT 1,
            last_seen    TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_fp_task_type ON fingerprints(task_type);

        CREATE TABLE IF NOT EXISTS merged_fingerprints (
            src       TEXT PRIMARY KEY,
            canonical TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_merge_canonical ON merged_fingerprints(canonical);
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Keyword extraction (no external deps)
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    "a an the this that my your we i it is are was be been have has "
    "do does did will would could should may might to of in on at for "
    "with by from and or not no but so if then when how what where who".split()
)


def _extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """Return top_n frequent non-stopword tokens from text."""
    tokens = re.findall(r"[a-z][a-z0-9_]{2,}", text.lower())
    freq: dict[str, int] = {}
    for t in tokens:
        if t not in _STOPWORDS:
            freq[t] = freq.get(t, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])][:top_n]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def upsert(
    fingerprint: str,
    task_type: str,
    keywords: list[str],
    tools_used: list[str],
) -> None:
    """Insert or update a fingerprint entry."""
    try:
        with _lock:
            conn = _get_conn()
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO fingerprints(fingerprint, task_type, keywords, tools_used, sample_count, last_seen)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    sample_count = sample_count + 1,
                    last_seen    = excluded.last_seen,
                    keywords     = CASE WHEN excluded.keywords != '[]' THEN excluded.keywords
                                        ELSE keywords END,
                    tools_used   = CASE WHEN excluded.tools_used != '[]' THEN excluded.tools_used
                                        ELSE tools_used END
                """,
                (
                    fingerprint,
                    task_type,
                    json.dumps(keywords),
                    json.dumps(sorted(set(tools_used))),
                    now,
                ),
            )
            conn.commit()
    except Exception as e:
        _log(f"upsert error: {e}")


def resolve(fingerprint: str) -> str:
    """Follow merge chain to canonical fingerprint."""
    try:
        with _lock:
            conn = _get_conn()
            seen: set[str] = set()
            current = fingerprint
            while current not in seen:
                seen.add(current)
                row = conn.execute(
                    "SELECT canonical FROM merged_fingerprints WHERE src = ?", (current,)
                ).fetchone()
                if row is None:
                    break
                current = row["canonical"]
            return current
    except Exception as e:
        _log(f"resolve error: {e}")
        return fingerprint


def find_similar(
    fingerprint: str,
    task_type: str,
    keywords: list[str],
    tools_used: list[str],
    limit: int = 5,
) -> list[dict]:
    """
    Return up to `limit` similar fingerprint entries with similarity scores.

    Each result: {"fingerprint": str, "task_type": str, "score": float,
                  "sample_count": int, "source": str}
    """
    try:
        canonical = resolve(fingerprint)
        kw_set = set(keywords[:3])  # top-3 only per spec
        tools_set = set(tools_used)
        results: list[dict] = []

        with _lock:
            conn = _get_conn()

            # 1. Exact / merged match
            rows = conn.execute(
                """
                SELECT f.fingerprint, f.task_type, f.keywords, f.tools_used, f.sample_count
                FROM fingerprints f
                WHERE f.fingerprint = ?
                   OR f.fingerprint IN (
                       SELECT src FROM merged_fingerprints WHERE canonical = ?
                   )
                   OR f.fingerprint IN (
                       SELECT canonical FROM merged_fingerprints WHERE src = ?
                   )
                """,
                (canonical, canonical, canonical),
            ).fetchall()

            exact_fps: set[str] = set()
            for row in rows:
                exact_fps.add(row["fingerprint"])
                results.append({
                    "fingerprint": row["fingerprint"],
                    "task_type": row["task_type"],
                    "score": 1.0,
                    "sample_count": row["sample_count"],
                    "source": "exact",
                })

            # 2-4. Fuzzy: same task_type candidates
            candidates = conn.execute(
                "SELECT fingerprint, task_type, keywords, tools_used, sample_count "
                "FROM fingerprints WHERE task_type = ? AND fingerprint != ?",
                (task_type, canonical),
            ).fetchall()

            for row in candidates:
                fp = row["fingerprint"]
                if fp in exact_fps:
                    continue

                row_kws = set(json.loads(row["keywords"])[:3])
                row_tools = set(json.loads(row["tools_used"]))

                kw_overlap = len(kw_set & row_kws) if kw_set and row_kws else 0
                tools_match = (tools_set == row_tools) if tools_set and row_tools else False

                if kw_overlap >= 2:
                    score = 0.8
                    source = "kw_overlap"
                elif tools_match:
                    score = 0.6
                    source = "tools_match"
                else:
                    score = 0.3
                    source = "task_type"

                results.append({
                    "fingerprint": fp,
                    "task_type": row["task_type"],
                    "score": score,
                    "sample_count": row["sample_count"],
                    "source": source,
                })

        # Sort: score desc, sample_count desc
        results.sort(key=lambda x: (-x["score"], -x["sample_count"]))
        return results[:limit]

    except Exception as e:
        _log(f"find_similar error: {e}")
        return []


def merge_fingerprints(src: str, canonical: str) -> None:
    """Mark `src` as equivalent to `canonical` (user-defined equivalence)."""
    try:
        if src == canonical:
            return
        # Resolve canonical chain first to avoid cycles
        canonical = resolve(canonical)
        with _lock:
            conn = _get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO merged_fingerprints(src, canonical) VALUES (?, ?)",
                (src, canonical),
            )
            conn.commit()
    except Exception as e:
        _log(f"merge_fingerprints error: {e}")


def rebuild_from_logs() -> dict:
    """
    Scan all task_logs/ JSON files and (re)populate the index.
    Sync — run in a thread. Returns {"indexed": N, "errors": M}.
    """
    indexed = 0
    errors = 0
    try:
        if not _LOG_DIR.exists():
            return {"indexed": 0, "errors": 0}

        for month_dir in sorted(_LOG_DIR.iterdir()):
            if not month_dir.is_dir():
                continue
            for log_file in month_dir.glob("task_*.json"):
                try:
                    data = json.loads(log_file.read_text(encoding="utf-8"))
                    fp = data.get("task_fingerprint")
                    tt = data.get("task_type")
                    if not fp or not tt:
                        continue

                    summary = data.get("task_summary", "") or ""
                    kws = _extract_keywords(summary) if summary else []
                    tools = data.get("tools_used") or []
                    if isinstance(tools, str):
                        tools = [tools]

                    upsert(fp, tt, kws, tools)
                    indexed += 1
                except Exception:
                    errors += 1
    except Exception as e:
        _log(f"rebuild_from_logs error: {e}")
        errors += 1

    return {"indexed": indexed, "errors": errors}


def get_stats() -> dict:
    """Return index statistics."""
    try:
        with _lock:
            conn = _get_conn()
            total = conn.execute("SELECT COUNT(*) FROM fingerprints").fetchone()[0]
            merged = conn.execute("SELECT COUNT(*) FROM merged_fingerprints").fetchone()[0]
            by_type = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT task_type, COUNT(*) FROM fingerprints GROUP BY task_type"
                ).fetchall()
            }
        return {"total_fingerprints": total, "merged": merged, "by_task_type": by_type}
    except Exception as e:
        _log(f"get_stats error: {e}")
        return {"total_fingerprints": 0, "merged": 0, "by_task_type": {}}
