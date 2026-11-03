"""
Fit the conversation into one member's budget.

The conversation is a list of segments, oldest first: each active summary
block, then each message no block covers yet. Then:

  • Room to spare: open summaries back up, newest first, one level at a time
    (a level-2 block becomes its level-1 blocks, a level-1 block its messages),
    as long as the result still fits. A member with a big window ends up seeing
    most or all of the chat word for word; a small one sees summaries.
  • Too big: shorten older messages (the newest KEEP_FULL stay whole), then
    leave out the oldest unsummarised messages, then the oldest summaries.
    The newest message is always shown, cut down if need be.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from helm.groupchat_context import archive, blocks
from helm.groupchat_context.sections import block_text
from helm.groupchat_context.text import line

KEEP_FULL = 6              # newest messages never shortened
OLD_MESSAGE_CHARS = 2000   # older messages may be cut to this when space is short
SEP = 2                    # "\n\n" between segments


@dataclass
class Seg:
    kind: str                       # "block" | "msg"
    block: Optional[dict] = None
    msg: Optional[dict] = None
    text: str = ""


@dataclass
class Fitted:
    summaries: list[Seg] = field(default_factory=list)   # blocks still shown as summaries
    messages: list[Seg] = field(default_factory=list)    # messages shown word for word
    hidden_messages: int = 0       # unsummarised messages left out
    hidden_blocks: int = 0         # summaries left out (tiny budgets only)
    expanded: int = 0              # summaries opened back up
    shown_ids: set = field(default_factory=set)


def _msg_seg(msg: dict, viewer: str, limit: Optional[int] = None) -> Seg:
    return Seg("msg", msg=msg, text=line(msg, viewer, limit))


def _cost(segs: list[Seg]) -> int:
    return sum(len(s.text) + SEP for s in segs)


def _expand_one(group: dict, seg: Seg, viewer: str) -> Optional[list[Seg]]:
    """The segments one level below a block, or None if it can't be opened."""
    b = seg.block
    if b.get("legacy"):
        return None
    kids = blocks.children_of(group, b)
    if kids:
        return [Seg("block", block=k, text=block_text(k)) for k in kids]
    msgs = archive.lookup(group, b.get("msg_ids") or [])
    if not msgs or any(m is None for m in msgs):
        return None
    return [_msg_seg(m, viewer) for m in msgs]


def _open_up(group: dict, segs: list[Seg], room: int, viewer: str) -> tuple[list[Seg], int]:
    used = _cost(segs)
    opened = 0
    stuck: set[str] = set()
    while True:
        target = None
        for i in range(len(segs) - 1, -1, -1):
            s = segs[i]
            if s.kind == "block" and s.block["id"] not in stuck:
                target = i
                break
        if target is None:
            return segs, opened
        seg = segs[target]
        below = _expand_one(group, seg, viewer)
        extra = (_cost(below) - _cost([seg])) if below is not None else None
        if below is None or used + extra > room:
            stuck.add(seg.block["id"])
            # A newer block that doesn't fit means older ones are skipped too,
            # so the opened part stays one recent stretch.
            if below is not None:
                return segs, opened
            continue
        segs[target:target + 1] = below
        used += extra
        opened += 1


def _squeeze(segs: list[Seg], room: int, viewer: str) -> tuple[list[Seg], int, int]:
    """Make segs fit room. Returns (segs, hidden messages, hidden blocks)."""
    msg_idx = [i for i, s in enumerate(segs) if s.kind == "msg"]
    older = msg_idx[:-KEEP_FULL] if len(msg_idx) > KEEP_FULL else []
    for i in older:                                   # 1. shorten older messages
        if _cost(segs) <= room:
            break
        segs[i] = _msg_seg(segs[i].msg, viewer, OLD_MESSAGE_CHARS)
    hidden_msgs = hidden_blocks = 0
    while _cost(segs) > room:                         # 2. drop oldest, messages first
        msgs = [i for i, s in enumerate(segs) if s.kind == "msg"]
        blks = [i for i, s in enumerate(segs) if s.kind == "block"]
        if len(msgs) > 1:
            del segs[msgs[0]]
            hidden_msgs += 1
        elif blks:
            del segs[blks[0]]
            hidden_blocks += 1
        else:
            break
    if segs and _cost(segs) > room:                   # 3. the newest message alone, cut
        last = segs[-1]
        if last.kind == "msg":
            segs[-1] = _msg_seg(last.msg, viewer, max(room - 100, 200))
    return segs, hidden_msgs, hidden_blocks


def fit(group: dict, viewer: str, room_chars: int) -> Fitted:
    segs = [Seg("block", block=b, text=block_text(b)) for b in blocks.active(group)]
    segs += [_msg_seg(m, viewer) for m in blocks.unfolded(group)]
    opened = 0
    if _cost(segs) <= room_chars:
        segs, opened = _open_up(group, segs, room_chars, viewer)
        hidden_m = hidden_b = 0
    else:
        segs, hidden_m, hidden_b = _squeeze(segs, room_chars, viewer)
    out = Fitted(hidden_messages=hidden_m, hidden_blocks=hidden_b, expanded=opened)
    # Summaries stay before messages: a block never follows a shown message.
    for s in segs:
        if s.kind == "block" and not out.messages:
            out.summaries.append(s)
        elif s.kind == "block":
            out.messages.append(Seg("msg", text=block_text(s.block), block=s.block))
        else:
            out.messages.append(s)
            out.shown_ids.add(s.msg["id"])
    return out
