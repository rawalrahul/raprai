"""
helm/model_prefs.py — Persistent per-AI model selection.

Selected models survive session restarts.
Storage: helm/config/selected_models.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path

_PREFS_PATH = Path(__file__).parent / "config" / "selected_models.json"

_DEFAULTS: dict[str, str | None] = {
    "claude": None,
    "gemini": None,
    "codex": None,
    "ollama": None,
}


def _load() -> dict:
    try:
        if _PREFS_PATH.exists():
            return json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return dict(_DEFAULTS)


def _save(prefs: dict) -> None:
    try:
        _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(_PREFS_PATH) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
        os.replace(tmp, str(_PREFS_PATH))
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
