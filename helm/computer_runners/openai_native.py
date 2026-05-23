"""
helm/computer_runners/openai_native.py — Native OpenAI / Codex API runner.

Uses GPT-4o vision + function calling. OpenAI's ``role:tool`` content
field is string-only, so screenshots can't ride along inside tool_result
the way Anthropic allows. We send the text result via role:tool and
follow up with a separate role:user message that carries the screenshot
image blocks — GPT-4o vision sees the resulting screen on the next call.
"""

from __future__ import annotations

import asyncio
import json
import os

from helm.broadcast import push_message
from helm.config import logger

from .base import _capture_b64, execute_action

MAX_TURNS = 20
DEFAULT_MODEL = "gpt-4o"


def _build_tools() -> list[dict]:
    from helm.builtin_tools import COMPUTER_USE_TOOLS
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["desc"],
                "parameters": t["schema"],
            },
        }
        for t in COMPUTER_USE_TOOLS
    ]


async def run(prompt: str, cwd: str, session_id: str,
              model: str | None = None) -> str:
    """Run a single user prompt to completion via OpenAI function calling."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=key)
    use_model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    tools = _build_tools()

    initial_b64 = await asyncio.to_thread(_capture_b64)
    messages: list[dict] = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{initial_b64}"},
            },
        ],
    }]

    for turn in range(MAX_TURNS):
        resp = await client.chat.completions.create(
            model=use_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip() or "(no response)"

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        screenshots: list[str] = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await execute_action(tc.function.name, args, cwd)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result["text"],
            })
            screenshots.append(result["screenshot_b64"])

        # Follow-up role:user message carrying screenshots — OpenAI does
        # not accept image blocks inside role:tool content.
        messages.append({
            "role": "user",
            "content": [
                {"type": "text",
                 "text": "Resulting screen state after the tool calls above:"},
                *[{
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                } for b64 in screenshots],
            ],
        })

        try:
            await push_message(
                "system",
                f"Tier 2 (OpenAI): turn {turn + 1} executed {len(msg.tool_calls)} action(s)",
                source="web", session_id=session_id,
            )
        except Exception:
            logger.debug("push_message failed in openai_native loop", exc_info=True)

    return "(Tier 2 OpenAI: MAX_TURNS reached without completion)"
