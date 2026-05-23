"""
helm/computer_runners/gemini_native.py — Native Google Gemini API runner.

Gemini lacks a built-in computer-use tool, so we expose every Tier 1 tool
as a function declaration and attach a fresh screenshot after every turn
so the vision model can see the resulting screen.
"""

from __future__ import annotations

import asyncio
import base64
import os

from helm.broadcast import push_message
from helm.config import logger

from .base import _capture_b64, execute_action

MAX_TURNS = 20
DEFAULT_MODEL = "gemini-2.5-flash"

# JSON Schema "type" → google.genai schema enum name.
_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
}


def _schema_to_genai(schema: dict, types_module):
    """Convert a JSON Schema dict from COMPUTER_USE_TOOLS into a genai Schema."""
    Schema = types_module.Schema
    props_in = schema.get("properties", {}) or {}
    props_out = {}
    for key, val in props_in.items():
        t = _TYPE_MAP.get(val.get("type", "string"), "STRING")
        if t == "ARRAY":
            items_t = _TYPE_MAP.get(val.get("items", {}).get("type", "string"), "STRING")
            props_out[key] = Schema(type=t, items=Schema(type=items_t))
        else:
            props_out[key] = Schema(type=t)
    return Schema(
        type="OBJECT",
        properties=props_out,
        required=schema.get("required", []) or [],
    )


def _build_tools(types_module):
    from helm.builtin_tools import COMPUTER_USE_TOOLS
    Tool = types_module.Tool
    FunctionDeclaration = types_module.FunctionDeclaration
    decls = [
        FunctionDeclaration(
            name=t["name"],
            description=t["desc"],
            parameters=_schema_to_genai(t["schema"], types_module),
        )
        for t in COMPUTER_USE_TOOLS
    ]
    return [Tool(function_declarations=decls)]


async def run(prompt: str, cwd: str, session_id: str,
              model: str | None = None) -> str:
    """Run a single user prompt to completion via Gemini function calling."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY/GOOGLE_API_KEY not set")

    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(api_key=key)
    use_model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    tools = _build_tools(genai_types)

    initial_b64 = await asyncio.to_thread(_capture_b64)
    history = [
        genai_types.Content(role="user", parts=[
            genai_types.Part(inline_data=genai_types.Blob(
                mime_type="image/png",
                data=base64.b64decode(initial_b64),
            )),
            genai_types.Part(text=prompt),
        ]),
    ]

    for turn in range(MAX_TURNS):
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=use_model,
            contents=history,
            config=genai_types.GenerateContentConfig(tools=tools),
        )

        candidate = resp.candidates[0] if resp.candidates else None
        parts = list(candidate.content.parts) if candidate and candidate.content else []
        fcalls = [p.function_call for p in parts if getattr(p, "function_call", None)]

        if not fcalls:
            text = getattr(resp, "text", None) or ""
            return text.strip() or "(no response)"

        history.append(candidate.content)

        response_parts = []
        for fc in fcalls:
            args = dict(fc.args) if fc.args else {}
            result = await execute_action(fc.name, args, cwd)
            response_parts.append(genai_types.Part(
                function_response=genai_types.FunctionResponse(
                    name=fc.name,
                    response={"result": result["text"]},
                ),
            ))
            response_parts.append(genai_types.Part(
                inline_data=genai_types.Blob(
                    mime_type="image/png",
                    data=base64.b64decode(result["screenshot_b64"]),
                ),
            ))

        history.append(genai_types.Content(role="user", parts=response_parts))

        try:
            await push_message(
                "system",
                f"Tier 2 (Gemini): turn {turn + 1} executed {len(fcalls)} action(s)",
                source="web", session_id=session_id,
            )
        except Exception:
            logger.debug("push_message failed in gemini_native loop", exc_info=True)

    return "(Tier 2 Gemini: MAX_TURNS reached without completion)"
