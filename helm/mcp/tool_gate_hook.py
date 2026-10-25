#!/usr/bin/env python3
"""
helm/mcp/tool_gate_hook.py — Claude Code hook: ask RAPR before acting.

RAPR starts Claude Code with this as a PreToolUse hook on MCP tools (see
helm/outward.py). Claude Code hands it each call on stdin; it asks RAPR
(POST /mcp/gate), which lets reading through and asks you before anything that
acts outside your computer: sending, posting, merging, deleting, paying...

Exit 0 lets the call run. Exit 2 blocks it, and Claude reads why on stderr.

Usage (Claude Code runs it): python tool_gate_hook.py <rapr-url> <session-id> <timeout-seconds>
Standard library only: it runs in its own process, without RAPR's code.
"""

import json
import os
import sys
import urllib.request


def main(argv: list[str]) -> int:
    url = argv[1] if len(argv) > 1 else ""
    session_id = argv[2] if len(argv) > 2 else ""
    try:
        timeout = float(argv[3]) if len(argv) > 3 else 660.0
    except ValueError:
        timeout = 660.0
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0  # nothing to judge; Claude Code's own rules decide
    body = json.dumps({
        "tool_name": event.get("tool_name", ""),
        "tool_input": event.get("tool_input") or {},
        "session_id": session_id,
    }).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/mcp/gate", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ.get('MCP_BEARER_TOKEN', '')}"},
    )
    # RAPR is on this computer: never send this through an HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
            answer = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        sys.stderr.write(f"RAPR AI couldn't be reached to check this with the user ({exc}), "
                         "so it was not done.\n")
        return 2
    if answer.get("allowed"):
        return 0
    sys.stderr.write((answer.get("reason") or "The user did not allow this.") + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
