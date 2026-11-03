"""
The fixed text around a member's view of the chat.

Order matters for prompt caching: what changes least comes first.
    header (room, member, role)          — fixed for the group
    earlier conversation (summaries/raw) — grows at the end, rarely rewritten
    recent messages                      — grows at the end
    recalled details                     — only when asked for
    room facts, pins                     — change now and then
    instructions                         — fixed
"""

from __future__ import annotations

from helm.groupchat_context.text import shorten

PIN_CHARS = 1500
RECALL_HINT_EXAMPLE = "(recall b1)"


def header(group: dict, member: dict) -> str:
    others = [m for m in group["members"] if m["id"] != member["id"]]
    roster = ", ".join(f'{m["name"]} ({m["ai"]})' for m in others) or "nobody else"
    about = f'What this group is for: {group["about"]}\n\n' if group.get("about") else ""
    role = f'Your role in this group: {member["role_prompt"]}\n\n' if member.get("role_prompt") else ""
    return (
        f'[Group chat: "{group["name"]}" - with the user, {roster}]\n\n'
        f"You are {member['name']}, one of several AI assistants in a group chat "
        f"with the user. {about}{role}"
    )


def block_text(block: dict) -> str:
    n = len(block.get("msg_ids") or [])
    count = f"{n} messages" if n else "older messages"
    topic = f" · {block['topic']}" if block.get("topic") else ""
    return f"[{block['id']} · summary of {count}{topic}]\n{block.get('summary', '').strip()}"


EARLIER_TITLE = ("Earlier in this chat, summarised (oldest first). Each summary has an id "
                 "such as b1:\n\n")
RECENT_TITLE = "Conversation so far (oldest first):\n\n"
NEWS_MARK = "--- new since your last message ---"


def facts(group: dict) -> str:
    items = group.get("facts") or []
    if not items:
        return ""
    return ("Room facts (kept up to date by RAPR from the whole chat):\n"
            + "\n".join(f"- {f}" for f in items) + "\n\n")


def pins(group: dict) -> str:
    items = group.get("pinned") or []
    if not items:
        return ""
    lines = [f"- {p.get('who') or 'User'}: {shorten(p.get('content', ''), PIN_CHARS)}" for p in items]
    return "Pinned by the user (always keep these in mind):\n" + "\n".join(lines) + "\n\n"


def recalled(text: str) -> str:
    if not text:
        return ""
    return ("Details you asked for, word for word from earlier in the chat:\n\n"
            f"{text}\n\n")


def instructions(group: dict, member: dict, *, can_recall: bool) -> str:
    others = [m for m in group["members"] if m["id"] != member["id"]]
    first = others[0]["name"].split()[0] if others else "User"
    out = (
        f"\n\n---\nWrite your next message to the group as {member['name']}.\n"
        "- Answer the user directly, and build on, correct or agree with the other "
        "assistants instead of repeating them.\n"
        f"- Address someone with @Name (e.g. @{first}) when you want a specific member to respond.\n"
        "- If you have nothing useful to add, reply with exactly: (pass)"
    )
    if can_recall:
        out += (
            "\n- If you need the exact words behind a summary to answer well, reply with only "
            f"{RECALL_HINT_EXAMPLE} (its id; several are fine, e.g. (recall b1, b2)) or "
            "(recall: a few search words). You will be asked again with those messages shown."
            f" With RAPR's MCP tools you can instead call group_recall or group_search "
            f'with group "{group["id"]}".'
        )
    out += "\n- Reply with your message only: no name prefix, no preamble."
    return out
