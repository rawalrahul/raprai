"""
helm/model_prefs.py — Persistent per-AI model selection.

Selected models survive session restarts.
Storage: selected_models.json in the user data folder. Before 2.0.1 it was
helm/config/selected_models.json inside the app, which an update replaces (and
the server image resets), so choices were lost; that file is still read as a
fallback until the first new choice is saved.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_OLD_PREFS_PATH = Path(__file__).parent / "config" / "selected_models.json"


def _prefs_path() -> Path:
    from helm.paths import user_data_dir
    return user_data_dir() / "selected_models.json"

_DEFAULTS: dict[str, str | None] = {
    "claude": None,
    "gemini": None,
    "codex": None,
    "ollama": None,
}


def _load() -> dict:
    for path in (_prefs_path(), _OLD_PREFS_PATH):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(prefs: dict) -> None:
    try:
        path = _prefs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        pass


def get_model_pref(ai: str) -> str | None:
    """Return persisted model for AI, or None if not set."""
    return _load().get(ai)


def set_model_pref(ai: str, model: str | None) -> None:
    """Persist model selection for AI. Pass None to clear."""
    prefs = _load()
    prefs[ai] = model
    _save(prefs)


def get_all_prefs() -> dict[str, str | None]:
    """Return all persisted model selections."""
    base = dict(_DEFAULTS)
    base.update(_load())
    return base
