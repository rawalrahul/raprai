"""
helm/outward.py — Ask before an AI acts outside your computer.

When an AI wants to send an email, post a message, comment on a pull request,
merge, pay, sign or delete something in a connected app, it asks you first,
the same way risky commands do: in the app, on Telegram, WhatsApp and your
phone. Your rules (Settings → Approvals & audit) still decide:
"allow" lets an action through without asking, "deny" refuses it, "ask" asks
even for a tool that only reads.

These routes go through gate():
  - tools RAPR runs for an AI: its text tool loop (ai_runner/agent_loop.py)
    and the /mcp/call endpoint (helm/mcp/call_tool.py)
  - Claude Code's own tool calls, through a PreToolUse hook
    (helm/mcp/tool_gate_hook.py → POST /mcp/gate). That covers RAPR's MCP
    servers, the MCP servers you added to Claude Code and your claude.ai
    connectors.
  - ACP agents already ask through their own permission requests (helm/acp.py).
Codex and Gemini call the MCP servers in their own settings directly (RAPR
copies its servers there too, mcp/manager.py), so those calls follow their own
approval settings.

Settings (.env / Settings → Approvals & audit):
  OUTWARD_ACTIONS       "ask" (default) or "allow" (never ask; your rules still apply)
  OUTWARD_WAIT_MINUTES  how long an AI waits for your answer (default 10). With
                        no answer the action is skipped and the AI is told so.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import helm.state as _st
from helm.config import logger


# Words in a tool's name that mean it changes something outside your computer.
_WRITE_VERBS = frozenset("""
send post reply forward publish share invite comment create update edit patch put
delete remove archive trash destroy purge merge push deploy release close reopen
approve reject assign transfer pay purchase buy order charge refund sign submit
book cancel schedule move rename upload write insert append modify add set
""".split())

# Drafts stay with you until something sends them.
_DRAFT_WORDS = frozenset({"draft", "drafts"})


def enabled() -> bool:
    return os.environ.get("OUTWARD_ACTIONS", "ask").strip().lower() != "allow"


def wait_seconds() -> float:
    try:
        return max(30.0, float(os.environ.get("OUTWARD_WAIT_MINUTES", "10")) * 60)
    except ValueError:
        return 600.0


def split_tool(name: str) -> tuple[str, str]:
    """("app", "tool") for a tool name.

    Claude Code names MCP tools mcp__<server>__<tool>; RAPR prefixes its own
    with the server id ("slack_post_message"), which its MCP manager maps back.
    """
    name = (name or "").strip()
    if name.startswith("mcp__"):
        parts = name[5:].split("__", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return parts[0], parts[0]
    try:
        from helm.mcp import get_manager
        mgr = get_manager()
        found = mgr and mgr._tool_map.get(name)
        if found:
            return found[0], found[1]
    except Exception:
        logger.debug("Couldn't look up the MCP tool %s", name, exc_info=True)
    return "", name


def words(name: str) -> list[str]:
    """Lower-case words of a tool name: sendEmail, send_email, send-email → send, email."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name or "")
    return [w for w in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if w]


def is_outward(tool_name: str) -> bool:
    """True when a tool's name says it changes something in a connected app."""
    app, tool = split_tool(tool_name)
    ws = set(words(tool))
    if ws & _DRAFT_WORDS and "send" not in ws:
        return False
    return bool(ws & _WRITE_VERBS)


_NAMES = {"github": "GitHub", "gitlab": "GitLab", "hubspot": "HubSpot", "linkedin": "LinkedIn",
          "youtube": "YouTube", "clickup": "ClickUp", "quickbooks": "QuickBooks", "docusign": "DocuSign"}


def app_label(app: str) -> str:
    """claude_ai_Gmail → Gmail, github → GitHub, google_workspace → Google workspace."""
    app = re.sub(r"^(claude_ai_|plugin_)", "", app or "")
    if app.lower() in _NAMES:
        return _NAMES[app.lower()]
    return app.replace("_", " ").strip().capitalize() if app.islower() else app.replace("_", " ").strip()


def describe(tool_name: str, arguments: Optional[dict], ai: Optional[str] = None) -> tuple[str, list[str]]:
    """The approval's one-line description and its detail lines."""
    app, tool = split_tool(tool_name)
    who = _ai_label(ai)
    where = f" in {app_label(app)}" if app else ""
    description = f"{who} wants to {tool.replace('_', ' ')}{where}"
    details = [f"tool: {tool_name}"]
    for key, value in list((arguments or {}).items())[:6]:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        details.append(f"{key}: {' '.join(text.split())[:160]}")
    return description, details


def _ai_label(ai: Optional[str]) -> str:
    if not ai:
        return "An AI"
    if ai == "claude":
        return "Claude"
    info = _st.integrations.get(ai) if isinstance(getattr(_st, "integrations", None), dict) else None
    return (info or {}).get("name") or ai.capitalize()


def _hook_python() -> str:
    """The Python that runs the hook: python.exe rather than pythonw.exe (no stdin)."""
    import sys
    exe = sys.executable or "python"
    if exe.lower().endswith("pythonw.exe"):
        console = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.isfile(console):
            return console
    return exe


def claude_hook_settings(session_id: str) -> Optional[str]:
    """The --settings JSON that sends Claude Code's MCP tool calls through gate().

    None when RAPR's web server isn't serving (nothing could answer the hook), or
    when nothing would ever ask: OUTWARD_ACTIONS=allow and no rules of your own.
    """
    import sys
    from helm import approval_rules
    if not getattr(_st, "gate_url", "") or getattr(sys, "frozen", False):
        return None
    if not enabled() and not approval_rules.load_rules():
        return None
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp", "tool_gate_hook.py")
    if not os.path.isfile(script):
        return None
    wait = int(wait_seconds())
    # Forward slashes work in both bash and cmd; Claude Code runs hooks in a shell.
    command = '"{}" "{}" {} {} {}'.format(
        _hook_python().replace("\\", "/"), script.replace("\\", "/"),
        _st.gate_url, re.sub(r"[^A-Za-z0-9_-]", "", session_id or "") or "-", wait + 60)
    return json.dumps({"hooks": {"PreToolUse": [{
        "matcher": "mcp__.*",
        "hooks": [{"type": "command", "command": command, "timeout": wait + 120}],
    }]}})


def _session(session_id: Optional[str]) -> Optional[dict]:
    return _st.sessions.get(session_id) if session_id else None


async def gate(tool_name: str, arguments: Optional[dict] = None,
               session_id: Optional[str] = None, ai: Optional[str] = None) -> tuple[bool, str]:
    """Decide whether a tool call may run. Returns (allowed, reason for the AI).

    Reading never asks unless one of your rules says so. An outward action asks
    you, waits up to OUTWARD_WAIT_MINUTES, and is skipped when you don't answer.
    In a read-only run (the morning brief) outward actions are refused outright.
    """
    from helm import approval as appr
    from helm import approval_rules

    sess = _session(session_id)
    ai = ai or (sess or {}).get("ai")
    outward = is_outward(tool_name)
    description, details = describe(tool_name, arguments, ai)

    if outward and sess and sess.get("read_only"):
        logger.info("outward: refused %s in read-only session %s", tool_name, session_id)
        return False, ("This run only looks; it doesn't act. Don't do this now: list it in "
                       "your answer as a suggested action for the user instead.")

    rule = approval_rules.evaluate(f"{description} {' '.join(details)}")
    if not rule and not (outward and enabled()):
        return True, ""

    req = appr.create_request(session_id or "", "outward_action", description, details=details)
    if req["status"] == "pending":
        await appr.broadcast_approval(req)
        outcome = await appr.wait(req["id"], timeout=wait_seconds())
        await appr.broadcast_resolution(req)
    else:
        outcome = req["status"]

    if outcome == "approved":
        return True, ""
    if outcome == "timeout":
        return False, ("The user hasn't answered this request yet, so it was not done. Carry on "
                       "with the rest, and say in your answer that it's waiting for their OK.")
    return False, "The user declined this action. Don't try it another way; say it was declined."
