"""
Build one member's prompt: the group's shared history, shown at the level of
detail that member's budget allows (see fit.py), wrapped in the fixed text
from sections.py.
"""

from __future__ import annotations

from typing import Optional

from helm.groupchat_context import blocks, budget, fit, recall, sections
from helm.groupchat_context.text import CHARS_PER_TOKEN

AUTO_RECALL_SHARE = 0.1        # of the room, kept for automatic recall while summaries exist
MIN_ROOM_CHARS = 1000


def _news_marker(messages: list[fit.Seg], member_id: str) -> list[str]:
    """Message lines, with a marker after the member's own last message when
    others have spoken since."""
    texts = [s.text for s in messages]
    last_own = max((i for i, s in enumerate(messages)
                    if s.msg and s.msg.get("author") == member_id), default=-1)
    if 0 <= last_own < len(texts) - 1:
        texts.insert(last_own + 1, sections.NEWS_MARK)
    return texts


def build(group: dict, member: dict, recalled: str = "") -> tuple[str, dict]:
    """(prompt, info) for `member`. `recalled` is text the member asked for."""
    budget_tokens = budget.budget_tokens(member)
    head = sections.header(group, member)
    tail_static = sections.facts(group) + sections.pins(group) + sections.recalled(recalled)
    # Reserve the instructions with the recall hint; it is the longer variant.
    instr_full = sections.instructions(group, member, can_recall=True)
    fixed = len(head) + len(tail_static) + len(instr_full) + len(sections.EARLIER_TITLE) \
        + len(sections.RECENT_TITLE) + 100
    room = max(budget_tokens * CHARS_PER_TOKEN - fixed, MIN_ROOM_CHARS)

    # Keep a slice for automatic recall when parts of the chat are summarised.
    reserve = int(room * AUTO_RECALL_SHARE) if blocks.active(group) and not recalled else 0
    fitted = fit.fit(group, member["id"], room - reserve)
    can_recall = bool(fitted.summaries) or fitted.hidden_blocks > 0
    instr = sections.instructions(group, member, can_recall=can_recall)

    earlier = ""
    if fitted.summaries:
        earlier = sections.EARLIER_TITLE + "\n\n".join(s.text for s in fitted.summaries) + "\n\n"
        if fitted.hidden_blocks:
            earlier = f"(… {fitted.hidden_blocks} older summaries not shown)\n\n" + earlier
    lines = _news_marker(fitted.messages, member["id"])
    if fitted.hidden_messages:
        lines.insert(0, f"(… {fitted.hidden_messages} earlier messages not shown)")
    transcript = "\n\n".join(lines) or "(no messages yet)"

    used = len(earlier) + len(transcript)
    auto = ""
    if fitted.summaries and not recalled:
        auto = recall.auto_recall(group, member["id"], fitted.shown_ids, max(room - used, reserve))

    prompt = (f"{head}{earlier}{sections.RECENT_TITLE}{transcript}\n\n"
              f"{auto}{tail_static}").rstrip() + instr
    info = {
        "member": member["id"],
        "tokens": len(prompt) // CHARS_PER_TOKEN,
        "budget": budget_tokens,
        "shown": sum(1 for s in fitted.messages if s.msg),
        "hidden": fitted.hidden_messages,
        "summaries": len(fitted.summaries),
        "expanded": fitted.expanded,
        "offline": budget.is_offline(member),
        "auto_recall": bool(auto),
    }
    return prompt, info


def build_prompt(group: dict, member: dict, recalled: Optional[str] = None) -> str:
    return build(group, member, recalled or "")[0]
