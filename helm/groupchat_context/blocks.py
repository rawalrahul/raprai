"""
Write-once summary blocks.

A block summarises a run of chat messages:
  level 1  a short run of raw messages
  level 2  several old level-1 blocks merged
  level 3  several old level-2 blocks merged

Blocks are stored on the group (group["blocks"]) and never rewritten: merging
makes a new block and marks the old ones inactive (they stay, so a merged part
can still be opened one level down). Each block knows every message it covers
(`msg_ids`, oldest first), so it can always be expanded back to the exact words.

The active blocks, oldest first, followed by the messages no block covers yet,
make up the whole conversation.
"""

from __future__ import annotations

import time
from typing import Optional

from helm.groupchat_context.text import is_chat


def all_blocks(group: dict) -> list[dict]:
    return group.setdefault("blocks", [])


def get(group: dict, block_id: str) -> Optional[dict]:
    return next((b for b in group.get("blocks") or [] if b["id"] == block_id), None)


def active(group: dict) -> list[dict]:
    """Blocks currently standing for their messages, oldest first."""
    return [b for b in group.get("blocks") or [] if b.get("active")]


def covered_ids(group: dict) -> set[str]:
    out: set[str] = set()
    for b in active(group):
        out.update(b.get("msg_ids") or [])
    return out


def last_covered_ts(group: dict) -> float:
    return max((b.get("last_ts") or 0 for b in active(group)), default=0)


def unfolded(group: dict) -> list[dict]:
    """Chat messages in the room that no active block covers, oldest first."""
    covered = covered_ids(group)
    edge = last_covered_ts(group)
    return [m for m in group.get("messages") or []
            if is_chat(m) and m["id"] not in covered and (m.get("timestamp") or 0) >= edge]


def _new_id(group: dict) -> str:
    n = int(group.get("next_block") or 1)
    group["next_block"] = n + 1
    return f"b{n}"


def add(group: dict, *, level: int, msg_ids: list[str], first_ts: float, last_ts: float,
        summary: str, topic: str = "", children: Optional[list[str]] = None,
        raw_tokens: int = 0, legacy: bool = False) -> dict:
    """Add a block; the child blocks it merges stop being active."""
    children = children or []
    for cid in children:
        child = get(group, cid)
        if child:
            child["active"] = False
            child["merged_into"] = None   # set below once the id exists
    block = {
        "id": _new_id(group),
        "level": level,
        "msg_ids": list(msg_ids),
        "children": list(children),
        "summary": summary,
        "topic": topic,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "raw_tokens": raw_tokens,
        "created": time.time(),
        "active": True,
    }
    if legacy:
        block["legacy"] = True
    for cid in children:
        child = get(group, cid)
        if child:
            child["merged_into"] = block["id"]
    all_blocks(group).append(block)
    group["blocks"].sort(key=lambda b: (b.get("first_ts") or 0, -b.get("level", 1)))
    return block


def children_of(group: dict, block: dict) -> list[dict]:
    return [c for c in (get(group, cid) for cid in block.get("children") or []) if c]


def clear(group: dict) -> None:
    for k in ("blocks", "next_block", "facts"):
        group.pop(k, None)


def migrate_legacy_summary(group: dict) -> None:
    """Turn the old single running summary into one level-2 block."""
    summary = group.get("summary")
    upto = group.get("summary_upto")
    if summary and not group.get("blocks"):
        msgs = [m for m in group.get("messages") or [] if is_chat(m)]
        idx = next((i for i, m in enumerate(msgs) if m["id"] == upto), -1)
        covered = msgs[: idx + 1]
        # Boundary already trimmed from the room: everything left is newer.
        add(group, level=2, msg_ids=[m["id"] for m in covered],
            first_ts=(covered[0].get("timestamp") if covered else 0) or 0,
            last_ts=(covered[-1].get("timestamp") if covered else 0) or 0,
            summary=summary, topic="Earlier conversation", legacy=True)
    for k in ("summary", "summary_upto", "summary_count"):
        group.pop(k, None)
