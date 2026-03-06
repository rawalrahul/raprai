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

    mgr = get_manager()
    if not mgr or not mgr.has_running_servers():
        return prompt

    tool_docs = mgr.get_text_tool_descriptions()
    if not tool_docs.strip():
        return prompt

    logger.info("inject_mcp_context: injecting MCP context (code_exec=%s)", code_exec)

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

    # Include built-in document tools
    from helm.builtin_tools import BUILTIN_TOOL_DOCS

    block = (
        f"[MCP TOOLS] Use these to access external services. "
        f"Do NOT pip install any packages — use these tools only.\n"
        f"{call_method}\n"
        f"Available:\n{tool_docs}\n"
        f"Built-in document tools (same calling method):\n{BUILTIN_TOOL_DOCS}\n"
        f"[/MCP TOOLS]\n\n"
    )

    return block + prompt
