"""
helm/model_catalog.py — The models offered in the model picker, per AI.

Each list starts with "Default" (no --model: the AI uses its own setting) and
then what the AI's own CLI offers, read live so new models appear without a
RAPR update. For Claude that's Claude Code's own /model list, each name with
the version behind it ("Opus · Opus 5.5"), plus older versions when Anthropic's
model list can be read (see helm/claude_models.py). Lists are cached for a few
minutes; refresh() drops the cache.

Only Claude has a picker in the app so far (PICKER_AIS); the others are added one
at a time once they've been checked on real installs.
"""

from __future__ import annotations

import time

PICKER_AIS = ("claude",)
_TTL = 600
_cache: dict[str, tuple[float, list[dict]]] = {}


def _short(description: str) -> str:
    """'Opus 5.5 · Best for everyday, complex tasks' -> 'Opus 5.5'."""
    return (description or "").split(" · ")[0].strip()


def _claude_options() -> list[dict]:
    from helm import claude_models
    live = claude_models.live_models()
    default = next((m for m in live if m["value"] == "default"), None)
    opts = [{"id": None, "label": "Default",
             "sub": _short(default["description"]) if default else "Claude decides",
             "title": "Whatever Claude Code would use on its own (your Claude setting, if you set one)",
             "efforts": default["efforts"] if default else []}]
    current = set()
    for m in live:
        if m["value"] == "default":
            continue
        opts.append({"id": m["value"], "label": m["name"], "sub": _short(m["description"]),
                     "title": m["description"] or m["name"], "efforts": m["efforts"]})
        current.add(m["value"])
        if m.get("resolved"):
            current.add(m["resolved"])
    if not live:   # couldn't ask Claude Code: the names and effort levels its --help mentions
        from helm.web_routes import helpers as h
        levels = claude_models.help_effort_levels()
        opts[0]["efforts"] = levels
        for alias in h._claude_cli_aliases() or ["opus", "sonnet"]:
            opts.append({"id": alias, "label": alias.capitalize(), "efforts": levels})
            current.add(alias)
        if "haiku" not in current:
            opts.append({"id": "haiku", "label": "Haiku", "efforts": levels})
    for v in claude_models.all_versions():
        if v["id"] not in current and not any(v["id"].startswith(c + "-") for c in current if c.startswith("claude-")):
            # Claude Code doesn't say which effort levels older versions take, so none are offered.
            opts.append({"id": v["id"], "label": v["name"], "sub": v["id"], "group": "Older versions",
                         "efforts": []})
    return opts


def _generic_options(ai: str) -> list[dict]:
    from helm.web_routes import helpers as h
    fn = {"codex": h._fetch_openai_models, "antigravity": h._fetch_antigravity_models,
          "ollama": h._fetch_ollama_models}.get(ai)
    try:
        ids = list(dict.fromkeys(fn())) if fn else []
    except Exception:
        ids = []
    return [{"id": None, "label": "Default"}] + [{"id": m, "label": m} for m in ids]


def options(ai: str) -> list[dict]:
    """[{id, label, sub?, title?, group?, efforts?}] for the picker; id None means the AI's
    default; efforts are the effort levels the CLI reports for that model."""
    now = time.time()
    at, opts = _cache.get(ai, (0.0, []))
    if len(opts) > 1 and now - at < _TTL:
        return opts
    opts = _claude_options() if ai == "claude" else _generic_options(ai)
    if len(opts) > 1:
        _cache[ai] = (now, opts)
    return opts


def efforts_for(ai: str, model: str | None) -> list[str]:
    """The effort levels the AI's CLI reports for this model ([] if none or unknown)."""
    return next((o.get("efforts") or [] for o in options(ai) if o["id"] == model), [])


def model_ids(ai: str) -> list[str]:
    return [o["id"] for o in options(ai) if o["id"]]


def refresh(ai: str) -> list[str]:
    _cache.pop(ai, None)
    return model_ids(ai)


def label(ai: str, model: str | None) -> str:
    """How a model is named to the user: its version when known ("Opus 5.5"), from the
    cached list (call options() first to fill it)."""
    if not model:
        return "Default"
    at, opts = _cache.get(ai, (0.0, []))
    o = next((o for o in opts if o["id"] == model), None)
    if not o:
        return model
    return o["sub"] if o.get("sub") and not o.get("group") else o["label"]
