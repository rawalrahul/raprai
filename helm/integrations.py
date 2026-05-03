"""
helm/integrations.py — AI integration plugin loader.

Loads integrations from two sources:
  1. File-based: .py files in the integrations/ folder (auto-discovered)
  2. Custom: user-defined via the Settings UI, stored in custom_integrations.json

Both types end up in ``helm.state.integrations`` and appear identically in the UI.
"""

import importlib.util
import json
import pathlib
import re
import shlex
import sys

import helm.state as _st
from helm.config import logger
from helm.paths import resolve, user_data_dir


# ---------------------------------------------------------------------------
# Custom integrations JSON storage
# ---------------------------------------------------------------------------

def _custom_file() -> pathlib.Path:
    return user_data_dir() / "custom_integrations.json"


def _load_custom_json() -> list[dict]:
    """Load the custom integrations list from disk."""
    path = _custom_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("Failed to load custom integrations: %s", e)
        return []


def _save_custom_json(entries: list[dict]) -> None:
    """Persist the custom integrations list to disk."""
    path = _custom_file()
    path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _build_command_fn(command_template: str, stdin_prompt: bool = False):
    """Create a build_command function from a command template string.

    Template supports {python}, {prompt}, and {model} placeholders.
    If stdin_prompt is True, {prompt} is removed from args (piped via stdin).
    """
    def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
        tpl = command_template
        python_token = "__RAPR_PYTHON_EXE__"
        tpl = tpl.replace("{python}", python_token)
        if model:
            tpl = tpl.replace("{model}", model)
        else:
            # Remove --model {model} or similar patterns
            tpl = re.sub(r'\s+--model\s+\{model\}', '', tpl)
            tpl = tpl.replace("{model}", "")
        if not stdin_prompt:
            tpl = tpl.replace("{prompt}", prompt)
        else:
            tpl = tpl.replace("{prompt}", "").strip()
        parts = shlex.split(tpl, posix=(sys.platform != "win32"))
        cleaned = []
        for part in parts:
            part = part.strip()
            if sys.platform == "win32":
                part = part.strip('"')
            if not part:
                continue
            cleaned.append(sys.executable if part == python_token else part)
        return cleaned
    return build_command


# ---------------------------------------------------------------------------
# Public API for managing custom integrations
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def list_custom() -> list[dict]:
    """Return all custom integrations (raw config dicts)."""
    return _load_custom_json()


def add_custom(entry: dict) -> str:
    """Add a custom integration. Returns the key."""
    key = (entry.get("key") or "").strip().lower()
    if not key or not _KEY_RE.match(key):
        raise ValueError(f"Invalid key: must be lowercase alphanumeric, 1-32 chars (got '{key}')")
    _RESERVED = {
        "claude", "ollama", "shell",
        "gemini", "codex", "openrouter", "groq",
        "local_ai", "github_models", "nemoclaw", "openclaw",
    }
    if key in _RESERVED:
        raise ValueError(f"Cannot override built-in AI: {key}")

    required = ["name", "command"]
    for field in required:
        if not entry.get(field, "").strip():
            raise ValueError(f"Missing required field: {field}")

    entries = _load_custom_json()
    # Replace if key exists
    entries = [e for e in entries if e.get("key") != key]
    entries.append({
        "key":           key,
        "name":          entry["name"].strip(),
        "emoji":         entry.get("emoji", "🤖").strip() or "🤖",
        "color":         entry.get("color", "#6b7280").strip() or "#6b7280",
        "command":       entry["command"].strip(),
        "env_vars":      [v.strip() for v in entry.get("env_vars", []) if v.strip()],
        "setup_hint":    entry.get("setup_hint", "").strip(),
        "stdin_prompt":  bool(entry.get("stdin_prompt", False)),
        "custom":        True,
    })
    _save_custom_json(entries)

    # Hot-register into state
    _register_custom(entries[-1])
    logger.info("Custom integration added: %s (%s)", key, entry["name"])
    return key


def update_custom(key: str, updates: dict) -> bool:
    """Update fields on an existing custom integration."""
    entries = _load_custom_json()
    found = False
    for e in entries:
        if e.get("key") == key:
            for field in ("name", "emoji", "color", "command", "env_vars",
                          "setup_hint", "stdin_prompt"):
                if field in updates:
                    e[field] = updates[field]
            found = True
            break
    if not found:
        return False
    _save_custom_json(entries)
    # Hot-update state
    _register_custom(next(e for e in entries if e["key"] == key))
    return True


def remove_custom(key: str) -> bool:
    """Remove a custom integration."""
    entries = _load_custom_json()
    before = len(entries)
    entries = [e for e in entries if e.get("key") != key]
    if len(entries) == before:
        return False
    _save_custom_json(entries)
    # Remove from state
    _st.integrations.pop(key, None)
    logger.info("Custom integration removed: %s", key)
    return True


def get_telegram_bot():
    """Return the configured Telegram bot instance, if available."""
    app = getattr(_st, "telegram_app", None)
    return getattr(app, "bot", None) if app else None


def _register_custom(entry: dict) -> None:
    """Register a single custom integration into helm.state."""
    key = entry["key"]
    _st.integrations[key] = {
        "name":          entry["name"],
        "emoji":         entry.get("emoji", "🤖"),
        "color":         entry.get("color", "#6b7280"),
        "build_command": _build_command_fn(entry["command"], entry.get("stdin_prompt", False)),
        "env_vars":      entry.get("env_vars", []),
        "setup_hint":    entry.get("setup_hint", ""),
        "stdin_prompt":  entry.get("stdin_prompt", False),
        "custom":        True,
    }


# ---------------------------------------------------------------------------
# Main loader (called at startup)
# ---------------------------------------------------------------------------

def load_integrations() -> None:
    """Load all integrations: file-based first, then custom overlays."""

    # 1. File-based integrations (integrations/*.py)
    folder = resolve("integrations")
    if folder.exists():
        for path in sorted(folder.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"integrations.{path.stem}", path
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                key = getattr(mod, "KEY", path.stem)
                _st.integrations[key] = {
                    "name":          getattr(mod, "NAME",        key.title()),
                    "emoji":         getattr(mod, "EMOJI",       "🤖"),
                    "color":         getattr(mod, "COLOR",       "#6b7280"),
                    "build_command": mod.build_command,
                    "env_vars":      getattr(mod, "ENV_VARS",    []),
                    "setup_hint":    getattr(mod, "SETUP_HINT",  ""),
                    "stdin_prompt":  getattr(mod, "STDIN_PROMPT", False),
                    "process_env":   getattr(mod, "PROCESS_ENV",  {}),
                }
                logger.info("Loaded AI integration: %s (%s)",
                            key, _st.integrations[key]["name"])
            except Exception as exc:
                logger.warning("Failed to load integration %s: %s", path.name, exc)
    else:
        logger.info("No integrations/ folder found — skipping file-based load.")

    # 2. Custom integrations (user-defined via Settings UI)
    customs = _load_custom_json()
    for entry in customs:
        try:
            _register_custom(entry)
            logger.info("Loaded custom AI integration: %s (%s)",
                        entry["key"], entry["name"])
        except Exception as exc:
            logger.warning("Failed to load custom integration %s: %s",
                           entry.get("key", "?"), exc)
