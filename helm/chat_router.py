"""
helm/chat_router.py — One set of chat commands for every chat app.

WhatsApp, Discord and Slack (and Telegram's text commands, in time) all take
the same messages: plain text goes to the focused session or group, /sessions,
/use, /new, /group, /approvals, /kelvin, /status, /help. This module does the
work once; each chat app only moves messages in and out.
"""

from __future__ import annotations

from typing import Optional

import helm.state as _st

HELP = (
    "🐧 RAPR AI\n"
    "Just type to talk to your focused session.\n"
    "/sessions — list sessions\n"
    "/use <number> — switch session\n"
    "/new <ai> — start a session (claude, gemini, codex, ollama…)\n"
    "/group — group chats with several AIs (/group help)\n"
    "/kelvin — is RAPR on?\n"
    "/approvals — actions waiting for your OK; /approve <id> or /deny <id>\n"
    "/status — what's running\n"
    "/help — this message"
)


def sessions_text() -> str:
    items = sorted(_st.sessions.values(), key=lambda s: s.get("created", 0))
    if not items:
        return "No sessions yet. Start one with /new claude (or gemini, codex, ollama…)."
    lines = ["Sessions:"]
    for i, s in enumerate(items, 1):
        mark = "  ← focused" if s["id"] == _st.focused_id else ""
        busy = " (working…)" if s.get("busy") else ""
        lines.append(f"{i}. {s.get('emoji', '🤖')} {s['name']}{busy}{mark}")
    lines.append("\nSwitch with /use <number>")
    return "\n".join(lines)


def status_text() -> str:
    from helm.kelvin_report import kelvin_report
    try:
        return kelvin_report()
    except Exception:
        return sessions_text()


def approval_command(text: str) -> Optional[str]:
    """Reply for /approve, /deny or /approvals, or None when it isn't one."""
    import helm.approval as appr
    parts = text.split()
    cmd = parts[0].lower() if parts else ""
    if cmd == "/approvals":
        pending = appr.pending()
        if not pending:
            return "Nothing is waiting for approval."
        return "Waiting for approval:\n" + "\n".join(
            f"• {r['id']}: {r.get('description', '')[:120]}" for r in pending)
    if cmd in ("/approve", "/deny"):
        if len(parts) < 2:
            return f"Usage: {cmd} <id>. See /approvals."
        status = "approved" if cmd == "/approve" else "denied"
        if appr.resolve(parts[1], status, source=_CURRENT["channel"]):
            return f"✅ {'Approved' if status == 'approved' else 'Denied'} {parts[1]}."
        return f"No pending approval {parts[1]}. See /approvals."
    return None


_CURRENT = {"channel": "chat"}


async def handle(channel: str, text: str) -> list[str]:
    """Process one message from `channel`. Returns the replies to send back."""
    import helm.groupchat as gc
    import helm.groupchat_channels as gch
    from helm.broadcast import push_state

    _CURRENT["channel"] = channel
    text = (text or "").strip()
    if not text:
        return []
    low = text.lower()

    if low in ("/help", "help", "/start", "menu", "/menu"):
        return [HELP]
    if low.startswith("/group"):
        return [await gch.handle_command(channel, text[6:])]
    if low in ("/kelvin", "kelvin"):
        from helm.kelvin_report import kelvin_report
        return [kelvin_report()]
    approval_reply = approval_command(text)
    if approval_reply:
        return [approval_reply]
    if low in ("/status", "status"):
        return [status_text()]
    if low in ("/sessions", "sessions"):
        return [sessions_text()]
    if low.startswith("/use"):
        arg = text[4:].strip()
        items = sorted(_st.sessions.values(), key=lambda s: s.get("created", 0))
        if not arg.isdigit() or not (0 < int(arg) <= len(items)):
            return [sessions_text()]
        sess = items[int(arg) - 1]
        _st.focused_id = sess["id"]
        await push_state()
        left = ""
        if gc.active_group(channel):
            gc.set_active_group(channel, None)
            left = " (left the group chat)"
        return [f"✅ Now talking to {sess.get('emoji', '🤖')} {sess['name']}{left}. Just type."]
    if low.startswith("/new"):
        from helm.session_mgr import make_session, session_cwd
        ai = text[4:].strip().lower() or "claude"
        if ai != "claude" and ai not in _st.integrations:
            names = ", ".join(["claude", *sorted(_st.integrations)])
            return [f"Unknown AI \"{ai}\". Try one of: {names}"]
        sess = make_session(ai, cwd=session_cwd())
        _st.focused_id = sess["id"]
        await push_state()
        return [f"✨ {sess['name']} created. Just type your task."]

    # In a group chat: the message goes to the whole group; replies are relayed.
    if await gch.send_to_active_group(channel, text):
        return []
    if low in ("/stop", "stop"):
        return ["Nothing to stop here. In a group, /group stop stops the replies."]

    if not _st.focused_id or _st.focused_id not in _st.sessions:
        return ["No session is focused.\n\n" + sessions_text()]
    from helm.ai_runner import process_message
    reply = await process_message(text, source=channel)
    return [reply or "(no output)"]
