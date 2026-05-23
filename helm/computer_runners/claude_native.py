"""
helm/computer_runners/claude_native.py — Native Anthropic API runner.

Uses Claude's native ``computer_20250124`` tool alongside custom function
tools for window management. Loops up to MAX_TURNS, attaching a fresh
screenshot inside every ``tool_result`` so Claude sees the new screen.
"""

from __future__ import annotations

import os

from helm.broadcast import push_message
from helm.config import logger

from .base import coord_to_args, execute_action

MAX_TURNS = 20
DEFAULT_MODEL = "claude-opus-4-7"


# Tools the native computer_20250124 already covers — skip these in custom list
# to avoid duplicate-tool errors from the Anthropic API.
_NATIVE_COVERED = {
    "computer_screenshot", "computer_click", "computer_double_click",
    "computer_right_click", "computer_move", "computer_type",
    "computer_key", "computer_scroll", "computer_get_cursor",
}


def _custom_function_tools():
    """Derive custom tool list from COMPUTER_USE_TOOLS minus native-covered set.

    Picks up Tier 3 (pywinauto) + OmniParser + window/app tools automatically.
    """
    from helm.builtin_tools import COMPUTER_USE_TOOLS
    return [
        {
            "name": t["name"],
            "description": t["desc"],
            "input_schema": t["schema"],
        }
        for t in COMPUTER_USE_TOOLS
        if t["name"] not in _NATIVE_COVERED
    ]


async def run(prompt: str, cwd: str, session_id: str,
              display_w: int, display_h: int,
              model: str | None = None) -> str:
    """Run a single user prompt to completion via native Claude computer use."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set — Tier 2 Claude requires an API key"
        )

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=key)
    use_model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL

    tools = [
        {
            "type": "computer_20250124",
            "name": "computer",
            "display_width_px": display_w,
            "display_height_px": display_h,
            "display_number": 1,
        },
        *_custom_function_tools(),
    ]

    messages: list[dict] = [{"role": "user", "content": prompt}]

    for turn in range(MAX_TURNS):
        resp = await client.beta.messages.create(
            model=use_model,
            max_tokens=4096,
            tools=tools,
            messages=messages,
            betas=["computer-use-2025-01-24"],
        )

        tool_uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
        text_blocks = [b.text for b in resp.content if getattr(b, "type", "") == "text"]

        if not tool_uses:
            return "\n".join(text_blocks).strip() or "(no response)"

        # Append assistant content verbatim (Anthropic requires the raw blocks).
        messages.append({"role": "assistant", "content": resp.content})

        results_content = []
        for tu in tool_uses:
            tu_input = tu.input or {}
            if tu.name == "computer":
                action = tu_input.get("action", "screenshot")
                args: dict = {}
                if "coordinate" in tu_input:
                    args.update(coord_to_args(tu_input["coordinate"]))
                if "text" in tu_input:
                    args["text"] = tu_input["text"]
                if "amount" in tu_input:
                    args["amount"] = tu_input["amount"]
                if "scroll_amount" in tu_input:
                    args["amount"] = tu_input["scroll_amount"]
                result = await execute_action(action, args, cwd)
            else:
                # Custom function tool — name already matches our Tier 1 tool.
                result = await execute_action(tu.name, dict(tu_input), cwd)

            results_content.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": [
                    {"type": "text", "text": result["text"]},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": result["screenshot_b64"],
                        },
                    },
                ],
            })

        messages.append({"role": "user", "content": results_content})

        try:
            await push_message(
                "system",
                f"Tier 2 (Claude): turn {turn + 1} executed {len(tool_uses)} action(s)",
                source="web", session_id=session_id,
            )
        except Exception:
            logger.debug("push_message failed in claude_native loop", exc_info=True)

    return "(Tier 2 Claude: MAX_TURNS reached without completion)"
