"""
helm/learning/namespace.py

Per-user namespace helpers for the learning store.

Multi-user mode is enabled by either:
  - Env var HELM_MULTI_USER=1
  - Sentinel file helm/learning/MULTI_USER exists

When enabled:
  - task_logs/{user_id_hash}/YYYY-MM/  (instead of task_logs/YYYY-MM/)
  - routing_table_{user_id_hash}.json  (per-user routing, falls back to global)

Single-user (default): no subdirs, existing layout unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).parent
_SENTINEL = _HERE / "MULTI_USER"


def is_multi_user() -> bool:
    """True if multi-user mode is active."""
    if os.environ.get("HELM_MULTI_USER", "").strip() == "1":
        return True
    return _SENTINEL.exists()


def enable_multi_user() -> None:
    _SENTINEL.touch(exist_ok=True)


def disable_multi_user() -> None:
    if _SENTINEL.exists():
        _SENTINEL.unlink()


def user_log_dir(base_log_dir: Path, user_id_hash: str) -> Path:
    """
    Return the task_logs directory for this user.
    Multi-user: base_log_dir/{user_id_hash}/
    Single-user: base_log_dir/
    """
    if is_multi_user() and user_id_hash:
        d = base_log_dir / user_id_hash
        d.mkdir(parents=True, exist_ok=True)
        return d
    return base_log_dir


def user_routing_table(base_dir: Path, user_id_hash: str) -> Path:
    """
    Return path for user-specific routing table.
    Multi-user: base_dir/routing_table_{user_id_hash}.json
    Single-user: base_dir/routing_table.json
    """
    if is_multi_user() and user_id_hash:
        return base_dir / f"routing_table_{user_id_hash}.json"
    return base_dir / "routing_table.json"


def all_user_log_dirs(base_log_dir: Path) -> list[Path]:
    """
    Return all task_log directories to scan.
    Multi-user: each user subdirectory.
    Single-user: [base_log_dir].
    """
    if not base_log_dir.exists():
        return []
    if is_multi_user():
        dirs = [d for d in base_log_dir.iterdir() if d.is_dir()
                and not d.name.startswith(".") and len(d.name) == 16]
        return dirs if dirs else [base_log_dir]
    return [base_log_dir]
