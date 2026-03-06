#!/usr/bin/env python3
"""
helm/mcp/call_tool.py — Standalone MCP tool caller for code-executing AIs.

This script is designed to be run by Codex, Gemini, or any AI that executes
Python code. It calls the RAPR AI MCP HTTP endpoint to invoke MCP tools.

Usage:
    python helm/mcp/call_tool.py <tool_name> '<json_arguments>'
    python helm/mcp/call_tool.py google_workspace_gmail_users_messages_list '{"userId":"me","maxResults":5}'
    python helm/mcp/call_tool.py google_workspace_list_tools '{}'

Can also be imported:
    from helm.mcp.call_tool import mcp_call
    result = mcp_call("google_workspace_gmail_users_messages_list", {"userId": "me"})
"""

import json
import os
import sys
import urllib.request
import urllib.error


_PORT = os.environ.get("WEB_PORT", "8000")
_HOST = os.environ.get("WEB_HOST", "127.0.0.1")
_BASE = f"http://{_HOST}:{_PORT}"


def mcp_call(tool_name: str, arguments: dict | None = None) -> str:
    """Call an MCP tool via the RAPR AI HTTP API. Returns the result string."""
    url = f"{_BASE}/mcp/call"
    payload = json.dumps({
        "name": tool_name,
        "arguments": arguments or {},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                return data.get("result", "")
            return f"Error: {data.get('error', 'unknown error')}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body)
            return f"Error ({e.code}): {err.get('error', body)}"
        except Exception:
            return f"Error ({e.code}): {body}"
    except urllib.error.URLError as e:
        return f"Error: Cannot reach RAPR AI at {url} — {e.reason}"
    except Exception as e:
        return f"Error: {e}"


def mcp_list_servers() -> str:
    """List available MCP servers and their status."""
    url = f"{_BASE}/mcp/servers"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            servers = data.get("servers", [])
            if not servers:
                return "No MCP servers configured."
            lines = ["Available MCP servers:"]
            for s in servers:
                status = "✅ running" if s.get("running") else "❌ stopped"
                lines.append(f"  {s['id']}: {status} ({s.get('tool_count', 0)} tools) — {s.get('summary', '')}")
            return "\n".join(lines)
    except Exception as e:
        return f"Error listing servers: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m helm.mcp.call_tool <tool_name> [json_arguments]")
        print("       python -m helm.mcp.call_tool --list-servers")
        sys.exit(1)

    if sys.argv[1] == "--list-servers":
        print(mcp_list_servers())
        sys.exit(0)

    tool_name = sys.argv[1]
    args_str = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        arguments = json.loads(args_str)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON arguments: {args_str}")
        sys.exit(1)

    result = mcp_call(tool_name, arguments)
    print(result)
