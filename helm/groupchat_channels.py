"""
helm/groupchat_channels.py — Group chats from chat apps (Telegram, WhatsApp).

One text command, the same on every chat app:

    /group                  list your group chats (numbered)
    /group 2                enter group 2: your messages now go to that group
    /group new              list your AI sessions, numbered
    /group new 1 3          create a group from AI sessions 1 and 3 and enter it
    /group new Launch: 1 3  ... and name it "Launch"
    /group who              who is in the group you're in
    /group stop             stop the group's current replies
    /group leave            back to talking to a single session

While a chat app is in a group, every message posted there (by you from any
app, or by a member AI) is relayed to it, so the app reads like a group chat.
Telegram adds buttons on top of this (helm/telegram_bot/groups.py).
"""

from __future__ import annotations

import re
from typing import Optional

import helm.state as _st
import helm.groupchat as gc

HELP = (
    "👥 Group chats — several AIs in one chat\n"
    "/group — list your groups\n"
    "/group <number> — enter that group\n"
    "/group new — list AI sessions to add\n"
    "/group new <name>: 1 3 — create a group from sessions 1 and 3\n"
    "/group who — members of your group\n"
    "/group stop — stop the replies in progress\n"
    "/group leave — back to a single session\n"
    "In a group, start with @Name to ask one member, or @all."
)


def ordered_groups() -> list[dict]:
    """Groups in a stable order (oldest first) so their numbers don't shift."""
    gc.load_groups()
    return sorted(gc.groups.values(), key=lambda g: g.get("created_at", 0))


def ai_sessions() -> list[dict]:
    return sorted((s for s in _st.sessions.values() if s.get("ai")),
                  key=lambda s: s.get("created", 0))


def find_group(ref: str) -> Optional[dict]:
    ref = (ref or "").strip()
    items = ordered_groups()
    if ref.isdigit():
        i = int(ref) - 1
        return items[i] if 0 <= i < len(items) else None
    low = ref.lower()
    for g in items:
        if g["name"].lower() == low:
            return g
    hits = [g for g in items if g["name"].lower().startswith(low)]
    return hits[0] if len(hits) == 1 else None


def members_line(group: dict) -> str:
    return ", ".join(f"{m['emoji']} {m['name']}" for m in group["members"])


def list_text(channel: str) -> str:
    items = ordered_groups()
    if not items:
        return "You have no group chats yet.\nCreate one with /group new"
    current = gc.active_groups.get(channel)
    lines = ["👥 Your group chats:"]
    for i, g in enumerate(items, 1):
        mark = "  ← you're here" if g["id"] == current else ""
        busy = " (replying…)" if g.get("status") == "running" else ""
        lines.append(f"{i}. {g['name']}{busy}{mark}\n    {members_line(g)}")
    lines.append("\nEnter one with /group <number>, or create one with /group new")
    return "\n".join(lines)


def sessions_text() -> str:
    sess = ai_sessions()
    if not sess:
        return ("No AI sessions are open. Start some first (e.g. /claude, /gemini, "
                "or from the web UI), then come back to /group new")
    lines = ["Open AI sessions:"]
    for i, s in enumerate(sess, 1):
        lines.append(f"{i}. {s.get('emoji', '🤖')} {s['name']}")
    lines.append("\nCreate a group: /group new <name>: 1 2  (the name is optional)")
    return "\n".join(lines)


def enter_text(group: dict) -> str:
    first = group["members"][0]["name"].split()[0] if group["members"] else "Name"
    return (f"👥 You're in \"{group['name']}\" with {members_line(group)}.\n"
            f"Everything you send now goes to the group. Start with @{first} to ask one member, "
            "or @all. /group leave to go back.")


async def create_group(channel: str, name: str, session_ids: list[str]) -> tuple[Optional[dict], str]:
    sessions = [_st.sessions[sid] for sid in dict.fromkeys(session_ids)
                if sid in _st.sessions and _st.sessions[sid].get("ai")]
    if not sessions:
        return None, "Pick at least one AI session."
    if len(sessions) > gc.MAX_MEMBERS:
        return None, f"A group can have at most {gc.MAX_MEMBERS} members."
    group = gc.make_group(name, "", sessions)
    gc.set_active_group(channel, group["id"])
    await gc.broadcast_group(group)
    return group, enter_text(group)


async def handle_command(channel: str, args: str) -> str:
    """Run a /group command from a chat app. Returns the reply text."""
    args = (args or "").strip()
    low = args.lower()
    current = gc.active_group(channel)

    if low in ("", "list", "ls"):
        return list_text(channel)
    if low in ("help", "?"):
        return HELP
    if low in ("leave", "exit", "off", "quit"):
        if not current:
            return "You're not in a group. /group to see your groups."
        gc.set_active_group(channel, None)
        return f"Left \"{current['name']}\". Your messages go to your focused session again."
    if low in ("who", "members"):
        if not current:
            return "You're not in a group. /group to see your groups."
        return f"👥 {current['name']}: {members_line(current)}"
    if low == "stop":
        if not current:
            return "You're not in a group."
        await gc.stop_group(current)
        return f"⏹ Stopped \"{current['name']}\"."
    if low == "new" or low.startswith("new "):
        rest = args[3:].strip()
        if not rest:
            return sessions_text()
        name, _, nums = rest.rpartition(":")
        if not _:
            name, nums = "", rest
        picks = re.findall(r"\d+", nums)
        sess = ai_sessions()
        chosen = [sess[int(n) - 1]["id"] for n in picks if 0 < int(n) <= len(sess)]
        if not chosen:
            return sessions_text()
        _group, text = await create_group(channel, name.strip(), chosen)
        return text

    group = find_group(args)
    if not group:
        return f"No group matches \"{args}\".\n\n" + list_text(channel)
    gc.set_active_group(channel, group["id"])
    return enter_text(group)


async def send_to_active_group(channel: str, text: str) -> bool:
    """If this chat app is in a group, post text there and return True."""
    group = gc.active_group(channel)
    if not group:
        return False
    await gc.send_user_message(group, text, source=channel)
    return True
