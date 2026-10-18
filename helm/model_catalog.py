"""
helm/model_catalog.py — The models offered in the model picker, per AI.

Each list starts with "Default" (no --model: the AI picks, as it would on its own)
and then the models the AI's own CLI reports. Lists are cached for a few minutes;
refresh() drops the cache.

Only Claude has a picker in the app so far (PICKER_AIS); the others are added one
at a time once they've been checked on real installs.
"""

from __future__ import annotations

import time

PICKER_AIS = ("claude",)
_TTL = 600
_cache: dict[str, tuple[float, list[str]]] = {}


def _label(ai: str, model: str) -> str:
    if ai == "claude" and model.isalpha():
        return model.capitalize()          # fable -> Fable, opus -> Opus
    return model


def _fetch(ai: str) -> list[str]:
    from helm.web_routes import helpers as h
    fn = {"claude": h._fetch_claude_models, "codex": h._fetch_openai_models,
          "antigravity": h._fetch_antigravity_models, "ollama": h._fetch_ollama_models}.get(ai)
    try:
        return list(dict.fromkeys(fn())) if fn else []
    except Exception:
        return []


def model_ids(ai: str) -> list[str]:
    now = time.time()
    at, ids = _cache.get(ai, (0.0, []))
    if ids and now - at < _TTL:
        return ids
    ids = _fetch(ai)
    if ids:
        _cache[ai] = (now, ids)
    return ids


def refresh(ai: str) -> list[str]:
    _cache.pop(ai, None)
    return model_ids(ai)


def options(ai: str) -> list[dict]:
    """[{id, label}] for the picker; id None means the AI's default."""
    return ([{"id": None, "label": "Default"}]
            + [{"id": m, "label": _label(ai, m)} for m in model_ids(ai)])


def label(ai: str, model: str | None) -> str:
    return "Default" if not model else _label(ai, model)
