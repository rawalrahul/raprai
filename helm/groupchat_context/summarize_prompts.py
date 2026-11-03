"""
What RAPR asks the summarising AI to write, and how its answer is read.

The answer has three parts so one call also keeps the room facts current:

    TOPIC: a few words
    SUMMARY:
    - bullet points
    FACTS:
    - the full, updated list of room facts
"""

from __future__ import annotations

import re

from helm.groupchat_context.text import line, shorten

SOURCE_MSG_CHARS = 4000
SOURCE_TOTAL_CHARS = 80_000
SUMMARY_CHARS = {1: 1800, 2: 2600, 3: 3600}     # longest summary per level
SUMMARY_WORDS = {1: 180, 2: 260, 3: 360}

_RULES = (
    "Keep: the user's goals, requirements and preferences; decisions and who made them; "
    "who agreed to do what; open questions; facts, names, numbers, versions, commands, "
    "file paths and URLs, copied exactly. Note disagreements between the assistants and "
    "how they were settled. Drop small talk and repetition."
)

_FACTS_RULES = (
    "FACTS is the room's running list of what everyone must keep in mind: decisions, "
    "requirements, constraints, owners of open tasks (\"Codex: write the tests\"), and "
    "key names/paths. Start from the current facts, add what is new, update what changed, "
    "and drop what is done or no longer true. At most 20 short lines."
)


def _frame(group: dict) -> str:
    about = f'The group is for: {group["about"]}\n' if group.get("about") else ""
    facts = "\n".join(f"- {f}" for f in group.get("facts") or []) or "(none yet)"
    return (f'You keep the records of a group chat called "{group["name"]}" between the user '
            f"and several AI assistants. {about}"
            "The assistants will often see only your summary, not the messages it covers, so "
            "keep what they will need.\n\n"
            f"Current room facts:\n{facts}\n\n")


def _answer_format(level: int) -> str:
    return (
        "---\nReply in exactly this format, nothing before or after:\n"
        "TOPIC: <3 to 8 words>\n"
        f"SUMMARY:\n- <short bullet points, at most about {SUMMARY_WORDS[level]} words>\n"
        "FACTS:\n- <the full updated list of room facts>\n\n"
        f"{_RULES}\n{_FACTS_RULES}"
    )


def fold_prompt(group: dict, msgs: list[dict]) -> str:
    """Level 1: summarise a run of raw messages."""
    convo = "\n\n".join(line(m, limit=SOURCE_MSG_CHARS) for m in msgs)
    convo = shorten(convo, SOURCE_TOTAL_CHARS)
    return (f"{_frame(group)}Messages to summarise (oldest first):\n\n{convo}\n\n"
            f"{_answer_format(1)}")


def merge_prompt(group: dict, parts: list[dict], level: int) -> str:
    """Level 2/3: merge several older summaries into one."""
    body = "\n\n".join(f"[{b['id']}{' · ' + b['topic'] if b.get('topic') else ''}]\n{b['summary']}"
                       for b in parts)
    return (f"{_frame(group)}Merge these consecutive summaries (oldest first) into one. Keep "
            f"every decision, owner, open question and exact string; drop only repetition.\n\n"
            f"{body}\n\n{_answer_format(level)}")


_SECTION_RE = re.compile(r"^\s*(TOPIC|SUMMARY|FACTS)\s*:\s*(.*)$", re.IGNORECASE)


def parse(text: str) -> tuple[str, str, list[str]]:
    """(topic, summary, facts) from the AI's answer. Without the headings the
    whole answer is taken as the summary and facts are left unchanged ([])."""
    topic, summary_lines, facts = "", [], []
    section = None
    for raw in (text or "").splitlines():
        m = _SECTION_RE.match(raw)
        if m:
            section = m.group(1).upper()
            rest = m.group(2).strip()
            if section == "TOPIC":
                topic = rest
            elif rest and section == "SUMMARY":
                summary_lines.append(rest)
            elif rest and section == "FACTS":
                facts.append(rest.lstrip("-* ").strip())
            continue
        if section == "FACTS":
            item = raw.strip().lstrip("-*•").strip()
            if item and item.lower() not in ("(none)", "none"):
                facts.append(item)
        elif section in ("SUMMARY", None):
            summary_lines.append(raw.rstrip())
    summary = "\n".join(summary_lines).strip()
    return topic[:80], summary, facts
