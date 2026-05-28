"""
helm/learning/playbook.py — Playbook storage, retrieval, and versioning.

Playbooks are markdown files in helm/learning/playbooks/{task_type}/{name}/
Each playbook has versioned files (v1.md, v2.md, ...) and current.md (always = latest version content).
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_PLAYBOOKS_DIR = _HERE / "playbooks"
_ERROR_LOG = _HERE / "telemetry_errors.log"

logging.basicConfig(
    filename=str(_ERROR_LOG),
    level=logging.ERROR,
    format="%(asctime)s [playbook] %(levelname)s: %(message)s",
)
_log = logging.getLogger("playbook")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _playbook_dir(task_type: str, name: str) -> Path:
    return _PLAYBOOKS_DIR / task_type / name


def _atomic_write(path: Path, text: str) -> None:
    """Write text to path atomically via .tmp intermediary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    # On Windows rename over existing file requires explicit removal first
    if path.exists():
        path.unlink()
    tmp.rename(path)


def _atomic_write_json(path: Path, data: dict) -> None:
    _atomic_write(path, json.dumps(data, indent=2))


def _load_meta(meta_path: Path) -> dict | None:
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        _log.error("_load_meta %s: %s", meta_path, exc)
        return None


def _save_meta(meta_path: Path, meta: dict) -> None:
    _atomic_write_json(meta_path, meta)


def _load_content(pb_dir: Path) -> str | None:
    current = pb_dir / "current.md"
    try:
        return current.read_text(encoding="utf-8")
    except Exception as exc:
        _log.error("_load_content %s: %s", current, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_playbook(
    task_type: str,
    name: str = None,
    fingerprint: str = None,
) -> dict | None:
    """
    Load a specific active playbook.

    - If name given: load that playbook directly.
    - If fingerprint given: scan task_type dir for matching fingerprint.
    Returns {"name", "task_type", "content": str, "meta": dict} or None.
    Only returns status="active" playbooks.
    """
    try:
        if name:
            pb_dir = _playbook_dir(task_type, name)
            meta_path = pb_dir / "meta.json"
            if not meta_path.exists():
                return None
            meta = _load_meta(meta_path)
            if not meta or meta.get("status") != "active":
                return None
            content = _load_content(pb_dir)
            if content is None:
                return None
            return {"name": name, "task_type": task_type, "content": content, "meta": meta}

        if fingerprint:
            type_dir = _PLAYBOOKS_DIR / task_type
            if not type_dir.exists():
                return None
            for pb_dir in type_dir.iterdir():
                if not pb_dir.is_dir():
                    continue
                meta_path = pb_dir / "meta.json"
                if not meta_path.exists():
                    continue
                meta = _load_meta(meta_path)
                if not meta:
                    continue
                if meta.get("fingerprint") == fingerprint and meta.get("status") == "active":
                    content = _load_content(pb_dir)
                    if content is None:
                        continue
                    return {
                        "name": pb_dir.name,
                        "task_type": task_type,
                        "content": content,
                        "meta": meta,
                    }
            return None

        return None
    except Exception as exc:
        _log.error("get_playbook task_type=%s name=%s fp=%s: %s", task_type, name, fingerprint, exc)
        return None


def list_playbooks(task_type: str = None) -> list[dict]:
    """
    Return list of active playbook metadata dicts.
    If task_type given: filter to that type only.
    """
    results: list[dict] = []
    try:
        if not _PLAYBOOKS_DIR.exists():
            return results

        type_dirs = (
            [_PLAYBOOKS_DIR / task_type]
            if task_type
            else [d for d in _PLAYBOOKS_DIR.iterdir() if d.is_dir()]
        )

        for type_dir in type_dirs:
            if not type_dir.exists() or not type_dir.is_dir():
                continue
            for pb_dir in type_dir.iterdir():
                if not pb_dir.is_dir():
                    continue
                meta_path = pb_dir / "meta.json"
                if not meta_path.exists():
                    continue
                meta = _load_meta(meta_path)
                if meta and meta.get("status") == "active":
                    results.append(meta)
    except Exception as exc:
        _log.error("list_playbooks task_type=%s: %s", task_type, exc)
    return results


def save_playbook(
    name: str,
    task_type: str,
    content: str,
    fingerprint: str,
    source_task_ids: list[str],
    model_version: str = None,
) -> str:
    """
    Create or update a playbook.

    New: creates v1.md + current.md, status="draft", promotions_needed=3.
    Existing: bumps version, writes v{N}.md + current.md,
              resets promotions_needed=3 if content changed.
    Returns: str path to playbook directory.
    """
    try:
        pb_dir = _playbook_dir(task_type, name)
        meta_path = pb_dir / "meta.json"
        now = _now_iso()

        if meta_path.exists():
            # --- Update existing ---
            meta = _load_meta(meta_path)
            if meta is None:
                meta = {}
            old_version = meta.get("version", 1)
            new_version = old_version + 1

            # Detect significant content change: compare with current.md
            old_content = _load_content(pb_dir) or ""
            content_changed = old_content.strip() != content.strip()

            _atomic_write(pb_dir / f"v{new_version}.md", content)
            _atomic_write(pb_dir / "current.md", content)

            meta["version"] = new_version
            meta["last_updated"] = now
            meta["fingerprint"] = fingerprint
            if source_task_ids:
                existing_ids = meta.get("source_task_ids", [])
                meta["source_task_ids"] = list(set(existing_ids + source_task_ids))
            if model_version:
                validated = meta.get("model_versions_validated", [])
                if model_version not in validated:
                    validated.append(model_version)
                meta["model_versions_validated"] = validated
            if content_changed:
                meta["promotions_needed"] = 3
                meta["status"] = "draft"
        else:
            # --- Create new ---
            pb_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(pb_dir / "v1.md", content)
            _atomic_write(pb_dir / "current.md", content)

            meta = {
                "name": name,
                "task_type": task_type,
                "fingerprint": fingerprint,
                "version": 1,
                "status": "draft",
                "success_rate": 0.0,
                "sample_count": 0,
                "promotions_needed": 3,
                "source_task_ids": source_task_ids or [],
                "model_versions_validated": [model_version] if model_version else [],
                "created_at": now,
                "last_success": None,
                "last_updated": now,
            }

        _save_meta(meta_path, meta)
        return str(pb_dir)
    except Exception as exc:
        _log.error("save_playbook name=%s task_type=%s: %s", name, task_type, exc)
        return ""


def promote_playbook(task_type: str, name: str) -> bool:
    """
    Decrement promotions_needed. When <= 0: set status="active".
    Returns True if now active.
    """
    try:
        pb_dir = _playbook_dir(task_type, name)
        meta_path = pb_dir / "meta.json"
        if not meta_path.exists():
            return False
        meta = _load_meta(meta_path)
        if not meta:
            return False

        needed = max(0, meta.get("promotions_needed", 1) - 1)
        meta["promotions_needed"] = needed
        meta["last_updated"] = _now_iso()

        if needed <= 0 and meta.get("status") == "draft":
            meta["status"] = "active"

        _save_meta(meta_path, meta)
        return meta.get("status") == "active"
    except Exception as exc:
        _log.error("promote_playbook task_type=%s name=%s: %s", task_type, name, exc)
        return False


def record_outcome(task_type: str, name: str, success: bool) -> None:
    """
    Update success_rate (rolling window of last 20 outcomes).
    If success_rate drops below 0.5 over last 5 outcomes: set status="deprecated".
    """
    try:
        pb_dir = _playbook_dir(task_type, name)
        meta_path = pb_dir / "meta.json"
        if not meta_path.exists():
            return
        meta = _load_meta(meta_path)
        if not meta:
            return

        now = _now_iso()

        # Rolling window stored as list of 0/1 in meta (last 20)
        history: list[int] = meta.get("_outcome_history", [])
        history.append(1 if success else 0)
        history = history[-20:]  # keep last 20
        meta["_outcome_history"] = history

        # Recompute success_rate from full history
        meta["success_rate"] = round(sum(history) / len(history), 4)
        meta["sample_count"] = meta.get("sample_count", 0) + 1
        meta["last_updated"] = now
        if success:
            meta["last_success"] = now

        # Deprecate if last 5 outcomes are below 0.5
        if len(history) >= 5:
            recent = history[-5:]
            recent_rate = sum(recent) / len(recent)
            if recent_rate < 0.5 and meta.get("status") == "active":
                meta["status"] = "deprecated"

        _save_meta(meta_path, meta)
    except Exception as exc:
        _log.error("record_outcome task_type=%s name=%s: %s", task_type, name, exc)


def get_best_playbook(task_type: str, fingerprint: str = None) -> dict | None:
    """
    Find the active playbook with highest success_rate for task_type.
    If fingerprint given: prefer exact match first.
    """
    try:
        type_dir = _PLAYBOOKS_DIR / task_type
        if not type_dir.exists():
            return None

        candidates: list[dict] = []
        for pb_dir in type_dir.iterdir():
            if not pb_dir.is_dir():
                continue
            meta_path = pb_dir / "meta.json"
            if not meta_path.exists():
                continue
            meta = _load_meta(meta_path)
            if not meta or meta.get("status") != "active":
                continue
            content = _load_content(pb_dir)
            if content is None:
                continue
            candidates.append(
                {
                    "name": pb_dir.name,
                    "task_type": task_type,
                    "content": content,
                    "meta": meta,
                }
            )

        if not candidates:
            return None

        # Prefer exact fingerprint match
        if fingerprint:
            for c in candidates:
                if c["meta"].get("fingerprint") == fingerprint:
                    return c

        # Fall back to highest success_rate
        candidates.sort(key=lambda c: c["meta"].get("success_rate", 0.0), reverse=True)
        return candidates[0]
    except Exception as exc:
        _log.error("get_best_playbook task_type=%s fp=%s: %s", task_type, fingerprint, exc)
        return None
