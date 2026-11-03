"""How full each member's prompt is, for the context meter in the app."""

from __future__ import annotations

from helm.config import logger
from helm.groupchat_context import blocks, budget, render
from helm.groupchat_context.text import is_chat


def context_info(group: dict) -> dict:
    """The tightest member's numbers at the top level (what the header pill
    shows), plus one entry per member and the summary/fact counts."""
    per_member = []
    for m in group.get("members") or []:
        try:
            _, info = render.build(group, m)
        except Exception:
            logger.debug("groupchat: context info failed for %s", m.get("name"), exc_info=True)
            continue
        info["pct"] = round(100 * info["tokens"] / max(info["budget"], 1))
        info["name"] = m.get("name")
        info["ai"] = m.get("ai")
        per_member.append(info)
    worst = max(per_member, key=lambda i: (i["pct"], i["hidden"]), default=None)
    worst = worst or {"tokens": 0, "budget": 0, "pct": 0, "shown": 0, "hidden": 0, "member": None}
    total = sum(1 for m in group.get("messages") or [] if is_chat(m))
    active = blocks.active(group)
    covered = blocks.covered_ids(group)
    return {
        "messages": total,
        "summarised": sum(1 for m in group.get("messages") or [] if m["id"] in covered),
        "has_summary": bool(active),
        "summaries": len(active),
        "levels": sorted({b.get("level", 1) for b in active}),
        "facts": len(group.get("facts") or []),
        "pinned": len(group.get("pinned") or []),
        "shown": worst["shown"],
        "hidden": worst["hidden"],
        "tokens": worst["tokens"],
        "budget": worst["budget"],
        "pct": worst["pct"],
        "tightest": worst["member"],
        "members": per_member,
        "online_budget": budget.online_tokens(),
        "summarising": bool(group.get("_summarising")),
    }


def blocks_view(group: dict) -> list[dict]:
    """The active summaries for the "What the AIs see" panel, oldest first."""
    return [{"id": b["id"], "level": b.get("level", 1), "topic": b.get("topic", ""),
             "summary": b.get("summary", ""), "messages": len(b.get("msg_ids") or []),
             "legacy": bool(b.get("legacy"))} for b in blocks.active(group)]
