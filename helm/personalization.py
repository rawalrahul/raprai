"""
helm/personalization.py — User personalization and custom instructions.

Reads user_name, ai_name, and custom_instructions from user_prefs.json
and builds a block that can be prepended to any AI system prompt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from helm.paths import user_data_dir


def _load_prefs() -> dict:
    """Load user preferences from disk (cached per-process)."""
    try:
        p = user_data_dir() / "user_prefs.json"
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_user_name() -> str:
    """Return the user's name, or empty string."""
    return _load_prefs().get("user_name", "").strip()


def get_ai_name() -> str:
    """Return the custom AI assistant name, or 'RAPR AI'."""
    return _load_prefs().get("ai_name", "").strip() or "RAPR AI"


def get_custom_instructions() -> str:
    """Return the user's custom instructions, or empty string."""
    return _load_prefs().get("custom_instructions", "").strip()


def get_personalization_block() -> str:
    """Build a prompt block with personalization + custom instructions.

    Returns an empty string if nothing is configured.
    """
    prefs = _load_prefs()
    parts: list[str] = []

    user_name = prefs.get("user_name", "").strip()
    ai_name = prefs.get("ai_name", "").strip()
    custom_instructions = prefs.get("custom_instructions", "").strip()

    if user_name or ai_name:
        identity_lines = []
        if ai_name:
            identity_lines.append(f"Your name is {ai_name}.")
        if user_name:
            identity_lines.append(
                f"The user's name is {user_name}. Address them by name when appropriate."
            )
        parts.append("[Identity]\n" + " ".join(identity_lines))

    if custom_instructions:
        parts.append(
            "[Custom Instructions — follow these for every response]\n"
            + custom_instructions
        )

    if not parts:
        return ""

    return "\n\n".join(parts) + "\n\n"
