"""
helm/integrations.py — AI integration plugin loader.

Scans the integrations/ folder and registers every non-underscore .py file
into ``helm.state.integrations``.
"""

import importlib.util
import pathlib

import helm.state as _st
from helm.config import logger


def load_integrations() -> None:
    """Scan integrations/ folder and register every non-underscore .py file."""
    folder = pathlib.Path(__file__).parent.parent / "integrations"
    if not folder.exists():
        logger.info("No integrations/ folder found — skipping plugin load.")
        return
    for path in sorted(folder.glob("*.py")):
        if path.stem.startswith("_"):
            continue                          # skip _template.py and __init__.py
        try:
            spec = importlib.util.spec_from_file_location(f"integrations.{path.stem}", path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            key = getattr(mod, "KEY", path.stem)
            _st.integrations[key] = {
                "name":          getattr(mod, "NAME",       key.title()),
                "emoji":         getattr(mod, "EMOJI",      "🤖"),
                "color":         getattr(mod, "COLOR",      "#6b7280"),
                "build_command": mod.build_command,
                "env_vars":      getattr(mod, "ENV_VARS",   []),
                "setup_hint":    getattr(mod, "SETUP_HINT", ""),
            }
            logger.info("Loaded AI integration: %s (%s)", key, _st.integrations[key]["name"])
        except Exception as exc:
            logger.warning("Failed to load integration %s: %s", path.name, exc)
