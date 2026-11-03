"""Small text helpers shared by the group-chat context modules."""

from __future__ import annotations

CHARS_PER_TOKEN = 4


def tokens(text: str) -> int:
    """Rough token count (about 4 characters per token)."""
    return len(text or "") // CHARS_PER_TOKEN


def shorten(text: str, limit: int) -> str:
    """text cut to about limit chars, keeping its start and end."""
    text = text or ""
    if len(text) <= limit:
        return text
    if limit < 80:
        return text[:max(limit - 1, 0)] + "…"
    note = f"\n[… {len(text) - limit} chars cut …]\n"
    keep = max(limit - len(note), 20)
    head = keep * 2 // 3
    return text[:head] + note + text[len(text) - (keep - head):]


def speaker(msg: dict) -> str:
    if msg.get("role") == "user":
        return "User"
    if msg.get("role") == "member":
        return msg.get("author_name") or "AI"
    return "System"


def is_chat(msg: dict) -> bool:
    return msg.get("role") in ("user", "member")


def line(msg: dict, viewer_id: str | None = None, limit: int | None = None) -> str:
    """One message as it appears in a prompt: "Name: text" ("You" for the viewer)."""
    who = "You" if viewer_id and msg.get("author") == viewer_id else speaker(msg)
    body = msg.get("content") or ""
    if limit is not None:
        body = shorten(body, limit)
    return f"{who}: {body}"
