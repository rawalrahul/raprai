"""
helm/mcp/inject.py — Inject MCP tool context into AI prompts.

Used by non-Ollama AIs (Claude CLI, Gemini, Codex) that need text-based
tool-call instructions rather than native tool definitions.

Usage:
    from helm.mcp.inject import inject_mcp_context
    enriched = inject_mcp_context(prompt)
"""

from __future__ import annotations

import os

from helm.config import logger


def inject_mcp_context(prompt: str, code_exec: bool = False) -> str:
    """Prepend compact MCP tool instructions to a prompt.

    Args:
        prompt: The original user prompt.
        code_exec: True for code-executing AIs (Codex/Gemini) — shows HTTP API.
                   False for text-generating AIs (Claude) — shows <tool_call> tags.
    """
    from .manager import get_manager
    from helm.builtin_tools import (
        BUILTIN_TOOL_DOCS,
        get_computer_use_tool_descriptions,
        is_computer_use_enabled,
    )

    mgr = get_manager()
    mcp_running = bool(mgr and mgr.has_running_servers())
    computer_on = is_computer_use_enabled()

    # Bypass the no-MCP short-circuit when computer use is active,
    # so desktop control tools still reach the prompt.
    if not mcp_running and not computer_on:
        return prompt

    tool_docs = mgr.get_text_tool_descriptions() if mcp_running else ""
    if mcp_running and not tool_docs.strip() and not computer_on:
        return prompt

    logger.info(
        "inject_mcp_context: injecting (code_exec=%s, mcp=%s, computer=%s)",
        code_exec, mcp_running, computer_on,
    )

    port = os.environ.get("WEB_PORT", "8000")

    # Get the bearer token for MCP subprocess auth
    try:
        from helm.web_routes.app import MCP_BEARER_TOKEN
        bearer = MCP_BEARER_TOKEN
    except Exception:
        bearer = ""

    if code_exec:
        # Compact HTTP API instruction for Codex/Gemini
        call_method = (
            "Call tools via HTTP POST:\n"
            "```python\n"
            "import json, urllib.request\n"
            f"req = urllib.request.Request('http://127.0.0.1:{port}/mcp/call',\n"
            '  data=json.dumps({{"name":"TOOL","arguments":{{}}}}).encode(),\n'
            f'  headers={{"Content-Type":"application/json","Authorization":"Bearer {bearer}"}})\n'
            'print(json.loads(urllib.request.urlopen(req,timeout=30).read())["result"])\n'
            "```\n"
        )
    else:
        # Compact <tool_call> instruction for Claude
        call_method = (
            "Call tools using XML tags:\n"
            '<tool_call>{{"name":"TOOL","arguments":{{}}}}</tool_call>\n'
        )

    computer_docs = ""
    if computer_on:
        computer_docs = (
            "Desktop control tools — drive the user's real screen, keyboard, and mouse.\n"
            "Treat these as a peer of scripting, not a last resort.\n"
            "Prefer these when scripts cannot reach the task. Broad classes:\n"
            "  - Any web app the user is already signed into — act inside "
            "their real browser session, no API keys, no OAuth dance, no "
            "bot detection (works the same for social, email, banking, "
            "SaaS dashboards, internal tools, gov portals, etc.).\n"
            "  - Native desktop apps without a public scripting API.\n"
            "  - Anti-bot or captcha-walled flows.\n"
            "  - Cross-app orchestration (drag/drop between windows, OS "
            "dialogs, file pickers, print dialogs, clipboard hand-offs).\n"
            "  - Anything the user is watching live (demos, screencasts, "
            "AFK automation, accessibility, supervised hand-off).\n"
            "  - Visual verification of results that a script can't see.\n"
            "Tactics:\n"
            "  - Prefer computer_click_control / computer_type_in_control "
            "(pywinauto, semantic, no vision needed) over pixel coordinates "
            "for native Windows apps.\n"
            "  - Take a computer_screenshot before clicking by pixel so you "
            "actually see where things are.\n"
            "  - Use computer_get_windows / computer_focus_window before "
            "typing — keystrokes go to the focused window.\n"
            "Tools:\n"
            f"{get_computer_use_tool_descriptions()}"
        )

    block = (
        f"[MCP TOOLS] Use these to access external services. "
        f"Do NOT pip install any packages — use these tools only.\n"
        f"{call_method}\n"
        + (f"Available:\n{tool_docs}\n" if tool_docs.strip() else "")
        + f"Built-in document tools (same calling method):\n{BUILTIN_TOOL_DOCS}\n"
        + (computer_docs if computer_docs else "")
        + "[/MCP TOOLS]\n\n"
    )

    return block + prompt
