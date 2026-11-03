"""
Getting detail back from summarised parts of a group chat.

Three ways in:
  • automatically: when a member sees summaries, the earlier messages that best
    match the user's latest message are added word for word (if they fit);
  • by asking: a member replies "(recall b3)", "(recall b3, b5)" or
    "(recall: search words)" and is run once more with those messages shown;
  • over MCP: group_recall / group_search (see mcp_tools.py).

Search is keyword scoring with rarer words counting more: no model, no index
to keep in sync, and fast enough for a chat's few thousand messages.
"""

from __future__ import annotations

import math
import re
from typing import Optional

from helm.groupchat_context import archive, blocks
from helm.groupchat_context.text import line, shorten

RECALL_RE = re.compile(r"^\s*\(\s*recall\s*(:)?\s*(.+?)\s*\)\s*\.?\s*$", re.IGNORECASE | re.DOTALL)
BLOCK_ID_RE = re.compile(r"^b\d+$", re.IGNORECASE)
AUTO_MAX_HITS = 4
AUTO_MIN_SCORE = 2.0
_WORD_RE = re.compile(r"[a-z0-9_./-]{3,}")
_STOP = {
    "the", "and", "for", "you", "are", "with", "that", "this", "have", "was", "but", "not",
    "can", "will", "what", "how", "our", "your", "from", "they", "them", "then", "there",
    "about", "would", "could", "should", "please", "just", "like", "also", "into", "out",
    "all", "any", "its", "it's", "let", "lets", "now", "one", "get", "use", "make", "need",
}


def parse_request(reply: str) -> Optional[dict]:
    """{"blocks": [...]} or {"query": "..."} when the reply is a recall request."""
    m = RECALL_RE.match(reply or "")
    if not m:
        return None
    body = m.group(2).strip()
    parts = [p.strip() for p in re.split(r"[,\s]+", body) if p.strip()]
    if not m.group(1) and parts and all(BLOCK_ID_RE.match(p) for p in parts):
        return {"blocks": [p.lower() for p in parts]}
    return {"query": body} if body else None


_SUFFIXES = ("ing", "ed", "es", "s", "e")


def _stem(word: str) -> str:
    """Light stemming so price / prices / pricing match."""
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    return word


def _words(text: str) -> list[str]:
    """Search terms: whole tokens (paths kept whole), plus their parts and stems,
    so "pricing.py" finds "src/pricing.py" and "price" finds "pricing"."""
    out: list[str] = []
    for tok in _WORD_RE.findall((text or "").lower()):
        tok = tok.strip("./-")
        if not tok or tok in _STOP:
            continue
        out.append(tok)
        parts = [p for p in re.split(r"[./-]", tok) if len(p) >= 3 and p not in _STOP]
        if "/" in tok:
            out.append(tok.rsplit("/", 1)[1])             # the file name
        out.extend(_stem(p) for p in parts if _stem(p) != tok)
    return out


def _folded_messages(group: dict) -> list[tuple[dict, str]]:
    """(message, id of the active block holding it) for every summarised message."""
    out = []
    for b in blocks.active(group):
        for m in archive.lookup(group, b.get("msg_ids") or []):
            if m:
                out.append((m, b["id"]))
    return out


def search(group: dict, query: str, limit: int = 8,
           exclude_ids: Optional[set] = None) -> list[dict]:
    """Best-matching earlier messages: [{block, message, score}], best first."""
    terms = set(_words(query))
    if not terms:
        return []
    exclude_ids = exclude_ids or set()
    docs = _folded_messages(group)
    if not docs:
        return []
    bags = [(m, bid, set(_words(m.get("content", "")))) for m, bid in docs]
    n = len(bags)
    df = {t: sum(1 for _, _, bag in bags if t in bag) for t in terms}
    hits = []
    for m, bid, bag in bags:
        if m["id"] in exclude_ids:
            continue
        score = sum(math.log(1 + n / df[t]) for t in terms if t in bag and df[t])
        if score > 0:
            hits.append({"block": bid, "message": m, "score": round(score, 3)})
    hits.sort(key=lambda h: (-h["score"], -(h["message"].get("timestamp") or 0)))
    return hits[:limit]


def expand_blocks(group: dict, ids: list[str], viewer: Optional[str] = None,
                  limit_chars: int = 200_000) -> str:
    """The exact messages behind the given blocks (inactive ones too)."""
    parts = []
    for bid in ids:
        b = blocks.get(group, bid)
        if not b:
            parts.append(f"[{bid}: no such summary]")
            continue
        msgs = [m for m in archive.lookup(group, b.get("msg_ids") or []) if m]
        if not msgs:
            parts.append(f"[{bid}: its messages are no longer stored; the summary is all there is]\n"
                         f"{b.get('summary', '')}")
            continue
        body = "\n\n".join(line(m, viewer) for m in msgs)
        parts.append(f"[{bid} · {len(msgs)} messages, word for word]\n{body}")
    return shorten("\n\n".join(parts), limit_chars)


def answer_search(group: dict, query: str, viewer: Optional[str] = None,
                  limit_chars: int = 60_000) -> str:
    hits = search(group, query)
    if not hits:
        return f'[nothing earlier in the chat matches "{query}"]'
    hits.sort(key=lambda h: h["message"].get("timestamp") or 0)
    body = "\n\n".join(f"[from {h['block']}] {line(h['message'], viewer)}" for h in hits)
    return shorten(body, limit_chars)


def fulfil(group: dict, request: dict, viewer: Optional[str] = None,
           limit_chars: int = 200_000) -> str:
    """Text for a parsed recall request."""
    if request.get("blocks"):
        return expand_blocks(group, request["blocks"], viewer, limit_chars)
    return answer_search(group, request.get("query", ""), viewer, limit_chars)


def latest_user_text(group: dict) -> str:
    for m in reversed(group.get("messages") or []):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def auto_recall(group: dict, viewer: str, shown_ids: set, room_chars: int) -> str:
    """Summarised messages that match the user's latest message, if they fit."""
    if room_chars < 500 or not blocks.active(group):
        return ""
    hits = [h for h in search(group, latest_user_text(group), AUTO_MAX_HITS, shown_ids)
            if h["score"] >= AUTO_MIN_SCORE]
    if not hits:
        return ""
    hits.sort(key=lambda h: h["message"].get("timestamp") or 0)
    lines, used = [], 0
    for h in hits:
        text = f"[from {h['block']}] {line(h['message'], viewer, max(room_chars // len(hits) - 40, 200))}"
        if used + len(text) + 2 > room_chars:
            break
        lines.append(text)
        used += len(text) + 2
    if not lines:
        return ""
    return ("Earlier messages that may matter for the latest question (word for word):\n\n"
            + "\n\n".join(lines) + "\n\n")
