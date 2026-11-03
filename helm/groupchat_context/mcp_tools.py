"""
group_search / group_recall for AIs that have RAPR's MCP server.

A member is told its group's id in the prompt; with these tools it can read
summarised parts of the chat word for word without waiting for another round.
They read the same files the app writes, so they work from `rapr mcp` too.
"""

from __future__ import annotations

from typing import Callable, Optional

from helm.groupchat_context import recall

OUTPUT_CHARS = 60_000


def _find_group(ref: str) -> Optional[dict]:
    """The group as last saved (read fresh: the app may be another process)."""
    import json
    from helm import groupchat as gc
    try:
        data = json.loads(gc._store_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ref = (ref or "").strip()
    found = [g for g in data.get("groups") or [] if g.get("id") == ref]
    found = found or [g for g in data.get("groups") or [] if (g.get("name") or "").lower() == ref.lower()]
    return found[0] if found else None


def tool_group_search(args: dict, ctx=None) -> str:
    g = _find_group(args.get("group", ""))
    if not g:
        return f'No group chat "{args.get("group", "")}".'
    query = (args.get("query") or "").strip()
    if not query:
        return "Give a few search words."
    return recall.answer_search(g, query, limit_chars=OUTPUT_CHARS)


def tool_group_recall(args: dict, ctx=None) -> str:
    g = _find_group(args.get("group", ""))
    if not g:
        return f'No group chat "{args.get("group", "")}".'
    ids = args.get("blocks") or []
    if isinstance(ids, str):
        ids = [i for i in ids.replace(",", " ").split() if i]
    if not ids:
        return "Give one or more summary ids, e.g. [\"b3\"]."
    return recall.expand_blocks(g, [i.lower() for i in ids], limit_chars=OUTPUT_CHARS)


_GROUP = {"type": "string", "description": "The group chat's id (g-…) or exact name."}

TOOLS: dict[str, tuple[dict, Callable]] = {
    "group_search": ({
        "description": "Search the summarised (older) part of a RAPR group chat and return the "
                       "matching messages word for word. Use when your group-chat prompt shows "
                       "summaries and you need exact details.",
        "inputSchema": {"type": "object", "required": ["group", "query"], "properties": {
            "group": _GROUP,
            "query": {"type": "string", "description": "A few search words."},
        }},
        "annotations": {"readOnlyHint": True},
    }, tool_group_search),
    "group_recall": ({
        "description": "Open summaries of a RAPR group chat (ids like b3 shown in your prompt) and "
                       "return the messages they cover, word for word.",
        "inputSchema": {"type": "object", "required": ["group", "blocks"], "properties": {
            "group": _GROUP,
            "blocks": {"type": "array", "items": {"type": "string"},
                       "description": "Summary ids, e.g. [\"b3\", \"b4\"]."},
        }},
        "annotations": {"readOnlyHint": True},
    }, tool_group_recall),
}
