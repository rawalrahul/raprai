"""
helm/plugins.py — Helm-level plugin system loader and manager.

Scans helm/plugins/ directory for plugin manifests, loads them into a registry,
manages enable/disable state, and injects plugin instructions into AI prompts.

Plugins enabled at the RAPR AI level work seamlessly for ALL AIs — Claude,
Gemini, Codex, Ollama, and any future integration.

Public API:
    load_plugins()                  → None   (called at startup)
    list_plugins()                  → list[dict]
    plugin_enabled(plugin_id)       → bool
    set_plugin_enabled(id, bool)    → None
    inject_plugin_context(prompt)   → str    (enriched prompt)
"""

import json
import os
import pathlib
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_registry: dict[str, dict] = {}        # plugin_id -> {manifest + instructions}
_enabled: set[str] = set()             # set of enabled plugin IDs
_plugins_dir: Optional[pathlib.Path] = None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_plugins() -> None:
    """Scan helm/plugins/ for plugin folders and populate the registry.

    IMPORTANT: We use .clear() + in-place mutation instead of reassigning
    _registry/_enabled so that any module that imported these references
    (e.g. ``from helm.plugins import _registry``) sees the updated data.
    """
    global _plugins_dir

    _registry.clear()

    # Locate plugins directory
    from helm.paths import HELM_DIR
    _plugins_dir = HELM_DIR / "plugins"
    if not _plugins_dir.exists():
        logger.info("Plugins: directory %s not found — skipping", _plugins_dir)
        return

    # Read enabled set from env
    _enabled.clear()
    raw = os.environ.get("ENABLED_PLUGINS", "").strip()
    if raw:
        _enabled.update(p.strip().lower() for p in raw.split(",") if p.strip())

    # Scan subdirectories
    for entry in sorted(_plugins_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(("_", ".")):
            continue
        manifest_file = entry / "manifest.json"
        if not manifest_file.exists():
            continue
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            instructions = ""
            instr_file = entry / "instructions.md"
            if instr_file.exists():
                instructions = instr_file.read_text(encoding="utf-8")

            plugin_id = manifest.get("id", entry.name).lower()
            _registry[plugin_id] = {**manifest, "instructions": instructions}

            status = "enabled" if plugin_id in _enabled else "disabled"
            logger.info("Plugin loaded: %s [%s]", plugin_id, status)
        except Exception as exc:
            logger.warning("Failed to load plugin %s: %s", entry.name, exc)

    logger.info("Plugins: %d loaded, %d enabled", len(_registry), len(_enabled & set(_registry)))


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------

def list_plugins() -> list[dict]:
    """Return summary list for the Settings UI."""
    return [
        {
            "id": info.get("id", pid),
            "name": info.get("name", pid.title()),
            "description": info.get("description", ""),
            "emoji": info.get("emoji", "🔌"),
            "category": info.get("category", "general"),
            "version": info.get("version", "1.0.0"),
            "enabled": pid in _enabled,
            "env_vars": info.get("env_vars", []),
            "keywords": info.get("keywords", []),
        }
        for pid, info in _registry.items()
    ]


def plugin_enabled(plugin_id: str) -> bool:
    return plugin_id.lower() in _enabled


# ---------------------------------------------------------------------------
# Toggle
# ---------------------------------------------------------------------------

def set_plugin_enabled(plugin_id: str, enabled: bool) -> None:
    """Enable or disable a plugin and persist to .env."""
    pid = plugin_id.lower()
    if enabled:
        _enabled.add(pid)
    else:
        _enabled.discard(pid)

    # Persist
    from helm.web_routes.app import update_env
    value = ",".join(sorted(_enabled)) if _enabled else ""
    update_env("ENABLED_PLUGINS", value)
    os.environ["ENABLED_PLUGINS"] = value
    logger.info("Plugin %s: %s", pid, "enabled" if enabled else "disabled")


# ---------------------------------------------------------------------------
# Prompt injection
# ---------------------------------------------------------------------------

def reload_registry() -> None:
    """Convenience wrapper for hot-reload after helmpack install/uninstall."""
    load_plugins()


def inject_plugin_context(prompt: str) -> str:
    """Prepend enabled plugin instructions to the prompt.

    Called after skill injection in the AI dispatch pipeline so that
    every AI (Claude, Gemini, Codex, Ollama) gets plugin context.
    """
    if not _enabled:
        return prompt

    parts: list[str] = []
    for pid in sorted(_enabled):
        info = _registry.get(pid)
        if not info or not info.get("instructions"):
            continue
        # Only include first 200 lines to avoid blowing context
        lines = info["instructions"].splitlines()[:200]
        content = "\n".join(lines)
        parts.append(
            f"[RAPR PLUGIN: {info.get('name', pid)}]\n"
            f"{content}\n"
            f"[END PLUGIN]\n"
        )

    if not parts:
        return prompt

    header = (
        "[RAPR AI — AVAILABLE PLUGINS]\n"
        "The following service plugins are enabled. Use them when the task "
        "involves these services. Write and execute Python code to call their APIs.\n\n"
    )
    return header + "\n".join(parts) + "\n" + prompt
