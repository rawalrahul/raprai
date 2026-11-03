"""
The room's running facts: decisions, requirements, owners of open tasks.

The summarising AI returns the full updated list each time it folds or merges
(it sees the current list, so it can drop what is done). RAPR keeps it short
and free of duplicates; an empty answer leaves the list as it was.
"""

from __future__ import annotations

from helm.groupchat_context.text import shorten

MAX_FACTS = 20
FACT_CHARS = 240


def clean(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        item = shorten(" ".join((raw or "").split()), FACT_CHARS)
        key = item.lower().rstrip(".")
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out[-MAX_FACTS:]


def update(group: dict, new_items: list[str]) -> bool:
    """Replace the room facts with the AI's updated list. True if they changed."""
    items = clean(new_items)
    if not items or items == group.get("facts"):
        return False
    group["facts"] = items
    return True
