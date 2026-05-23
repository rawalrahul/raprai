"""
helm/computer_runners/ — Tier 2 native API runners for computer use.

Each runner (claude_native, gemini_native, openai_native) calls the AI
provider's API directly with vision + function calling, bypassing the
CLI subprocess path used in Tier 1. Screenshots are attached inline
after every action so the model sees the resulting screen state.

Tier 1 (CLI text-tool path) remains the fallback for any AI without
an API key or vision support.

Activation: COMPUTER_USE=true AND COMPUTER_USE_TIER2=true AND the
selected AI's API key env var is present. See ``should_use_tier2``.
"""

from __future__ import annotations

import os


def should_use_tier2(ai: str) -> bool:
    """True when Tier 2 native runner should handle this AI."""
    if os.environ.get("COMPUTER_USE", "false").lower() != "true":
        return False
    if os.environ.get("COMPUTER_USE_TIER2", "false").lower() != "true":
        return False
    if ai == "claude" and os.environ.get("ANTHROPIC_API_KEY"):
        return True
    if ai == "gemini" and (
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    ):
        return True
    if ai in ("codex", "openai") and os.environ.get("OPENAI_API_KEY"):
        return True
    return False
