"""
Check a model-written summary, and a plain recap for when there is none.

The strings an AI later needs exactly — file paths, URLs, numbers, versions,
code names in backticks, ids — are the first thing a summary tends to lose. So
RAPR pulls them out of the source messages and, if the summary dropped some,
appends them word for word instead of throwing the summary away.
"""

from __future__ import annotations

import re

from helm.groupchat_context.text import shorten, speaker

MAX_KEEP = 25              # at most this many key strings appended
KEEP_LINE_CHARS = 800

_PATTERNS = [
    re.compile(r"https?://[^\s)>\]\"']+"),                                   # URLs
    re.compile(r"`([^`\n]{2,80})`"),                                          # `code`
    re.compile(r"(?<![\w/])(?:[\w.-]+/)+[\w.-]+\.\w{1,6}\b"),                 # a/b/file.py
    re.compile(r"\b[\w-]+\.(?:py|js|ts|tsx|jsx|json|md|yml|yaml|toml|go|rs|"
               r"java|kt|swift|rb|php|cs|cpp|c|h|sql|sh|ps1|html|css)\b"),    # file.py
    re.compile(r"\bv?\d+\.\d+(?:\.\d+)+\b"),                                  # 1.2.3
    re.compile(r"[$€£₹]\s?\d[\d,]*(?:\.\d+)?\b"),                             # $500
    re.compile(r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|ms|s|kb|mb|gb|tb|k|m)\b", re.I), # 30%, 200ms
    re.compile(r"#\d{2,}\b"),                                                 # #123
]


def key_strings(texts: list[str]) -> list[str]:
    """Distinct key strings, in the order they first appear."""
    seen: dict[str, None] = {}
    for text in texts:
        for pat in _PATTERNS:
            for m in pat.finditer(text or ""):
                s = (m.group(1) if m.groups() else m.group(0)).strip().rstrip(".,;:")
                if len(s) >= 2 and s.lower() not in (k.lower() for k in seen):
                    seen[s] = None
    return list(seen)


def missing(summary: str, texts: list[str]) -> list[str]:
    low = (summary or "").lower()
    return [k for k in key_strings(texts) if k.lower() not in low]


def repair(summary: str, texts: list[str]) -> str:
    """The summary, plus any key strings it dropped."""
    lost = missing(summary, texts)[:MAX_KEEP]
    if not lost:
        return summary
    keep = shorten("; ".join(lost), KEEP_LINE_CHARS)
    return f"{summary.rstrip()}\n- Kept word for word: {keep}"


def digest(msgs: list[dict], max_chars: int) -> str:
    """A plain recap: one short line per message, oldest first."""
    lines = [f"- {speaker(m)}: {shorten(' '.join((m.get('content') or '').split()), 160)}"
             for m in msgs]
    out = "\n".join(lines)
    while len(out) > max_chars and len(lines) > 1:
        lines.pop(0)
        out = "\n".join(lines)
    return repair(shorten(out, max_chars), [m.get("content") or "" for m in msgs])
