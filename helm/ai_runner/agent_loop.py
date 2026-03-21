"""
helm/ai_runner/agent_loop.py — Text-based agent loop fallback for MCP tools.

Activates when an AI CLI can't reach MCP tools natively:
  - Any CLI: when websocket-only servers (Chrome) are running — CLIs can't
    connect to WebSocket, so we inject tool descriptions + parse <tool_call> tags.
  - Custom/unknown CLIs: user-added integrations that don't support native MCP.
  - NemoClaw: sandboxed in WSL, can't read host config files.

Native path (no agent loop) when:
  - Claude: has subprocess MCP servers → --mcp-config flag (same as Claude Code).
  - Gemini: servers synced to ~/.gemini/settings.json → reads them at startup.
  - Codex: servers synced to ~/.codex/config.toml → reads them at startup.
  - Ollama: own native tool calling via API (never uses this loop).
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Awaitable, Callable, Optional

from helm.config import logger
from helm.broadcast import push_message

# Regex to find <tool_call>...</tool_call> blocks
_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(.*?)\s*</tool_call>",
    re.DOTALL,
)

# Safety limits — let the AI work as it would natively
_MAX_ITERATIONS = 10  # generous ceiling; loop detection catches runaways
_TOOL_TIMEOUT = 120   # seconds per tool call — tools like doc gen can be slow
_MAX_RESULT_CHARS = 12000  # enough context for meaningful tool results


def _extract_tool_calls(text: str) -> list[dict]:
    """Extract tool call dicts from AI output text."""
    calls = []
    for match in _TOOL_CALL_RE.finditer(text):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
            name = data.get("name", "")
            args = data.get("arguments") or data.get("args") or {}
            if name:
                calls.append({"name": name, "arguments": args})
        except (json.JSONDecodeError, AttributeError):
            logger.warning("agent_loop: malformed tool_call JSON: %s", raw[:200])
    return calls


def _strip_tool_calls(text: str) -> str:
    """Remove <tool_call> blocks from output text, leaving the rest."""
    return _TOOL_CALL_RE.sub("", text).strip()


def _truncate(text: str, max_chars: int = _MAX_RESULT_CHARS) -> str:
    """Truncate long results to prevent prompt bloat."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (truncated, {len(text)} total chars)"


def _format_tool_results(results: list[dict]) -> str:
    """Format tool execution results for injection back into the prompt."""
    parts = []
    for r in results:
        status = "Success" if not r.get("error") else "Error"
        output = _truncate(r["output"])
        parts.append(f"[{r['name']}] ({status}): {output}")
    return "\n\n".join(parts)


async def _execute_builtin(name: str, arguments: dict, cwd: str) -> dict:
    """Execute a built-in tool (create_presentation, create_pdf, etc.)."""
    from helm.builtin_tools import execute_builtin_tool
    try:
        result = await asyncio.wait_for(
            execute_builtin_tool(name, arguments, cwd),
            timeout=120,  # doc generation can be slower
        )
        return {"name": name, "output": result, "error": False}
    except asyncio.TimeoutError:
        return {"name": name, "output": f"Error: tool '{name}' timed out", "error": True}
    except Exception as exc:
        return {"name": name, "output": f"Error: {exc}", "error": True}


async def _execute_mcp_tool(name: str, arguments: dict) -> dict:
    """Execute a single MCP tool call. Returns {"name", "output", "error"}."""
    from helm.mcp import get_manager

    mgr = get_manager()
    if not mgr:
        return {"name": name, "output": "Error: MCP manager not available", "error": True}

    try:
        result = await asyncio.wait_for(
            mgr.call_tool(name, arguments),
            timeout=_TOOL_TIMEOUT,
        )
        return {"name": name, "output": result, "error": False}
    except asyncio.TimeoutError:
        return {"name": name, "output": f"Error: tool '{name}' timed out after {_TOOL_TIMEOUT}s", "error": True}
    except Exception as exc:
        return {"name": name, "output": f"Error: {exc}", "error": True}


async def run_with_tools(
    run_fn: Callable[[str], Awaitable[str]],
    initial_prompt: str,
    cwd: str,
    session_id: str,
    source: str = "web",
    max_iterations: int = _MAX_ITERATIONS,
) -> str:
    """Run an AI with text-based MCP tool calling.

    Key perf optimizations:
    - Parallel tool execution (asyncio.gather)
    - Max 2 iterations (was 5)
    - 30s tool timeout (was 60)
    - Truncated tool results to prevent prompt bloat
    """
    from helm.mcp import get_manager

    mgr = get_manager()
    prompt = initial_prompt
    accumulated_context = ""
    prev_calls: list[tuple[str, str]] = []

    for iteration in range(max_iterations):
        output = await run_fn(prompt)

        if not output:
            return "(no output)"

        tool_calls = _extract_tool_calls(output)

        if not tool_calls:
            return _strip_tool_calls(output)

        # Loop detection
        current_calls = [(tc["name"], json.dumps(tc["arguments"], sort_keys=True)) for tc in tool_calls]
        repeated = sum(1 for cc in current_calls if cc in prev_calls)
        if repeated == len(current_calls) and repeated > 0:
            logger.warning("agent_loop: loop detected, aborting")
            return _strip_tool_calls(output) or "(Tool loop detected)"
        prev_calls = current_calls

        # Execute tool calls IN PARALLEL
        logger.info("agent_loop: iteration %d — executing %d tool call(s) in parallel", iteration + 1, len(tool_calls))

        await push_message(
            "system",
            f"🔧 Calling {len(tool_calls)} tool(s): {', '.join(tc['name'] for tc in tool_calls)}...",
            source=source,
            session_id=session_id,
        )

        # Build coroutines for all valid MCP tool calls
        coros = []
        indices = []
        results = [None] * len(tool_calls)

        from helm.builtin_tools import is_builtin_tool, execute_builtin_tool

        for i, tc in enumerate(tool_calls):
            name = tc["name"]
            args = tc["arguments"]
            if mgr and mgr.is_mcp_tool(name):
                coros.append(_execute_mcp_tool(name, args))
                indices.append(i)
            elif is_builtin_tool(name):
                coros.append(_execute_builtin(name, args, cwd))
                indices.append(i)
            else:
                results[i] = {"name": name, "output": f"Error: Unknown tool '{name}'", "error": True}

        # Run all MCP calls concurrently
        if coros:
            parallel_results = await asyncio.gather(*coros, return_exceptions=True)
            for idx, res in zip(indices, parallel_results):
                if isinstance(res, Exception):
                    results[idx] = {"name": tool_calls[idx]["name"], "output": f"Error: {res}", "error": True}
                else:
                    results[idx] = res

        errors = sum(1 for r in results if r and r.get("error"))
        await push_message(
            "system",
            f"✅ {len(tool_calls) - errors} succeeded, {errors} failed",
            source=source,
            session_id=session_id,
        )

        # Build compact follow-up prompt
        results_text = _format_tool_results([r for r in results if r])
        text_without_tools = _strip_tool_calls(output)

        accumulated_context += f"\n{results_text}\n"

        prompt = (
            f"{initial_prompt}\n\n"
            f"[Tool Results]:\n{accumulated_context}\n"
            f"Answer the user's question using these results. "
            f"Do NOT call any more tools — provide your final answer now."
        )

    # Max iterations reached
    logger.warning("agent_loop: max iterations (%d) reached", max_iterations)
    prompt = (
        f"{initial_prompt}\n\n"
        f"[Tool Results]:\n{accumulated_context}\n"
        f"Provide your FINAL answer using the results above. No more tool calls."
    )
    output = await run_fn(prompt)
    return _strip_tool_calls(output) if output else "(no output after max iterations)"
