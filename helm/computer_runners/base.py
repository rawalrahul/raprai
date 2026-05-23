"""
helm/computer_runners/base.py — Shared action executor for Tier 2 runners.

Reuses Tier 1's ``_run_computer_sync`` so action semantics stay identical
across both tiers. After every action, captures a fresh primary-monitor
screenshot and returns it as base64 PNG for inline attachment to the
next model turn.
"""

from __future__ import annotations

import asyncio
import base64

from helm.builtin_tools import _COMPUTER_LOCK, _run_computer_sync


# Anthropic computer_20250124 action names → our Tier 1 tool names.
_ACTION_MAP = {
    "screenshot": "computer_screenshot",
    "left_click": "computer_click",
    "double_click": "computer_double_click",
    "right_click": "computer_right_click",
    "middle_click": "computer_click",
    "mouse_move": "computer_move",
    "type": "computer_type",
    "key": "computer_key",
    "scroll": "computer_scroll",
    "cursor_position": "computer_get_cursor",
}


def _capture_b64() -> str:
    """Grab primary monitor as PNG, return base64-encoded string."""
    import mss
    with mss.mss() as sct:
        mon = sct.monitors[1]
        img = sct.grab(mon)
        png = mss.tools.to_png(img.rgb, img.size)
    return base64.b64encode(png).decode("ascii")


async def execute_action(action: str, args: dict, cwd: str) -> dict:
    """Run one desktop action; return {text, screenshot_b64}.

    Serializes via the same lock Tier 1 uses, so Tier 1 + Tier 2 cannot
    interleave even if both somehow active in the same process.
    """
    tool_name = _ACTION_MAP.get(action, action)
    async with _COMPUTER_LOCK:
        text = await asyncio.to_thread(_run_computer_sync, tool_name, args, cwd)
        b64 = await asyncio.to_thread(_capture_b64)
    return {"text": text, "screenshot_b64": b64}


def coord_to_args(coord) -> dict:
    """Convert Anthropic's [x, y] coordinate array into our tool args."""
    return {"x": int(coord[0]), "y": int(coord[1])}


def primary_display_size() -> tuple[int, int]:
    """Return (width, height) of primary monitor — never hardcode 1920x1080."""
    import mss
    with mss.mss() as sct:
        mon = sct.monitors[1]
        return int(mon["width"]), int(mon["height"])
