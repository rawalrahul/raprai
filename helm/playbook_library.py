"""
helm/playbook_library.py — See and manage what RAPR has learned.

Playbooks are short how-to notes RAPR writes after solving a task, and reuses
for similar tasks. This module lets you browse all of them (including drafts
and ones you've switched off), read them, and switch one on or off. It edits
only a playbook's status in its meta.json; the learning code is unchanged.

Status: active (used), draft (still being checked), disabled (kept, not used).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from helm.config import logger
from helm.learning import playbook as _pb

STATUSES = ("active", "draft", "disabled")


def _dir() -> Path:
    return _pb._PLAYBOOKS_DIR


def _meta_path(task_type: str, name: str) -> Path:
    if "/" in task_type or "\\" in task_type or ".." in task_type or "/" in name or "\\" in name or ".." in name:
        raise ValueError("bad playbook name")
    return _dir() / task_type / name / "meta.json"


def list_all() -> list[dict]:
    out = []
    if not _dir().exists():
        return out
    for meta_path in sorted(_dir().glob("*/*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("playbook meta unreadable %s: %s", meta_path, exc)
            continue
        out.append({
            "name": meta.get("name", meta_path.parent.name),
            "task_type": meta.get("task_type", meta_path.parent.parent.name),
            "status": meta.get("status", "draft"),
            "version": meta.get("version", 1),
            "success_rate": meta.get("success_rate"),
            "sample_count": meta.get("sample_count", 0),
            "last_updated": meta.get("last_updated"),
            "seeded": "seed" in (meta.get("source_task_ids") or []),
        })
    return out


def read(task_type: str, name: str) -> Optional[str]:
    path = _meta_path(task_type, name).parent / "current.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def set_status(task_type: str, name: str, status: str) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    meta_path = _meta_path(task_type, name)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["status"] = status
    _pb._atomic_write_json(meta_path, meta)
    return meta


def export_bundle() -> dict:
    """Everything you've learned, as one JSON file you can keep or share."""
    items = []
    for item in list_all():
        items.append({**item, "content": read(item["task_type"], item["name"])})
    return {"format": "rapr-playbooks-1", "playbooks": items}
