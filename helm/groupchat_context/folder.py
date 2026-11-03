"""
The background job that keeps a group's summaries up to date.

After each room turn RAPR asks plan() what is due, and run() does it, one step
at a time (so a new message never waits for a long chain of summaries):

  fold   the oldest unsummarised messages become a level-1 block, once
         KEEP_RECENT + BATCH have piled up, or sooner when some member can no
         longer fit them (PRESSURE_MIN hidden). At most L1_MAX_MSGS / L1_MAX_CHARS
         per block, so each one stays specific.
  merge  once more than MERGE_TRIGGER blocks of one level are active, the oldest
         MERGE_SIZE of them become one block a level up (up to MAX_LEVEL).

Each step: the summariser writes TOPIC/SUMMARY/FACTS, validate.repair() puts
back exact strings it dropped, and a plain recap stands in when no AI answered.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from helm.config import logger
from helm.groupchat_context import blocks, facts, render, summariser, validate
from helm.groupchat_context import summarize_prompts as sp
from helm.groupchat_context.text import tokens

KEEP_RECENT = 20
BATCH = 20
PRESSURE_MIN = 4
L1_MAX_MSGS = 15
L1_MAX_CHARS = 60_000
MERGE_TRIGGER = 8
MERGE_SIZE = 4
MAX_LEVEL = 3
MAX_STEPS = 6


def _hidden(group: dict) -> int:
    worst = 0
    for m in group.get("members") or []:
        try:
            worst = max(worst, render.build(group, m)[1]["hidden"])
        except Exception:
            logger.debug("groupchat: render failed while planning a fold", exc_info=True)
    return worst


def _chunk(msgs: list[dict]) -> list[dict]:
    out, size = [], 0
    for m in msgs:
        n = len(m.get("content") or "")
        if out and (len(out) >= L1_MAX_MSGS or size + n > L1_MAX_CHARS):
            break
        out.append(m)
        size += n
    return out


def plan(group: dict, continuing: bool = False) -> Optional[dict]:
    """The next step due, or None. `continuing`: a run already started folding,
    so finish the backlog (down to KEEP_RECENT) instead of waiting for BATCH more."""
    unf = blocks.unfolded(group)
    threshold = KEEP_RECENT + (PRESSURE_MIN if continuing else BATCH)
    n = len(unf) - KEEP_RECENT if len(unf) >= threshold else 0
    if n <= 0 and len(unf) > PRESSURE_MIN:
        hidden = _hidden(group)
        if hidden >= PRESSURE_MIN:
            n = min(hidden, len(unf) - 1)
    if n > 0:
        return {"kind": "fold", "msgs": _chunk(unf[:n])}
    for level in range(1, MAX_LEVEL):
        same = [b for b in blocks.active(group) if b.get("level") == level]
        if len(same) > MERGE_TRIGGER:
            return {"kind": "merge", "blocks": same[:MERGE_SIZE], "level": level + 1}
    return None


def _write(group: dict, step: dict) -> dict:
    """Run the summariser for a step (blocking). Returns the new block's fields."""
    if step["kind"] == "fold":
        msgs, level = step["msgs"], 1
        prompt = sp.fold_prompt(group, msgs)
        sources = [m.get("content") or "" for m in msgs]
        msg_ids = [m["id"] for m in msgs]
        first, last = msgs[0].get("timestamp") or 0, msgs[-1].get("timestamp") or 0
        raw = sum(tokens(s) for s in sources)
    else:
        parts, level = step["blocks"], step["level"]
        prompt = sp.merge_prompt(group, parts, level)
        sources = [b.get("summary") or "" for b in parts]
        msg_ids = [i for b in parts for i in b.get("msg_ids") or []]
        first, last = parts[0].get("first_ts") or 0, parts[-1].get("last_ts") or 0
        raw = sum(b.get("raw_tokens") or 0 for b in parts)
    answer = summariser.run_blocking(group, prompt)
    topic, summary, new_facts = sp.parse(answer)
    limit = sp.SUMMARY_CHARS[level]
    if summary:
        summary = validate.repair(summary[:limit], sources)
    elif step["kind"] == "fold":
        summary = validate.digest(step["msgs"], limit)
    else:
        summary = validate.repair("\n".join(s for s in sources)[:limit], sources)
    return {"level": level, "msg_ids": msg_ids, "first_ts": first, "last_ts": last,
            "summary": summary, "topic": topic, "raw_tokens": raw, "facts": new_facts,
            "children": [b["id"] for b in step.get("blocks") or []]}


def _still_due(group: dict, step: dict) -> bool:
    if step["kind"] == "fold":
        left = {m["id"] for m in blocks.unfolded(group)}
        return all(m["id"] in left for m in step["msgs"])
    return all((blocks.get(group, b["id"]) or {}).get("active") for b in step["blocks"])


async def run(group: dict) -> bool:
    """Do the steps that are due. True if anything changed."""
    from helm import groupchat as gc
    if group.get("_summarising"):
        return False
    step = plan(group)
    if not step:
        return False
    group["_summarising"] = True
    changed = False
    cleared = group.get("_cleared", 0)
    loop = asyncio.get_running_loop()
    try:
        await gc.broadcast_context(group)
        for _ in range(MAX_STEPS):
            if not step:
                break
            fields = await loop.run_in_executor(None, lambda s=step: _write(group, s))
            if gc.groups.get(group["id"]) is not group or group.get("_cleared", 0) != cleared:
                return False                      # deleted or cleared meanwhile
            if not _still_due(group, step):
                break
            new_facts = fields.pop("facts")
            blocks.add(group, **fields)
            facts.update(group, new_facts)
            changed = True
            gc.save_groups()
            step = plan(group, continuing=True)
        return changed
    finally:
        group.pop("_summarising", None)
        await gc.broadcast_context(group)


def schedule(group: dict) -> None:
    if not group.get("_summarising") and plan(group):
        asyncio.create_task(run(group))
