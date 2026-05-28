"""
Task classifier for Helm HQ — keyword-based, no external calls.
Fast synchronous dispatch tagger.
"""

import re
import hashlib
from typing import Dict

TASK_TYPES: Dict[str, list] = {
    "computer_use": ["open app", "click", "screenshot", "navigate", "fill form", "close window", "computer use", "desktop", "right click", "drag", "type in"],
    "code.debug": ["debug", "fix bug", "error", "traceback", "exception", "not working", "broken", "fails", "crash"],
    "code.write": ["write code", "create function", "implement", "build a", "make a script", "add feature", "new component"],
    "code.refactor": ["refactor", "clean up", "reorganize", "restructure", "simplify"],
    "code.explain": ["explain this code", "what does this do", "how does", "understand"],
    "code.test": ["write test", "unit test", "test case", "coverage", "pytest", "jest"],
    "agent_build": ["build an agent", "create agent", "agent that", "new agent", "agentbuilder"],
    "file_ops": ["read file", "write file", "save to", "open file", "delete file", "rename", "move file", "copy file", "create folder"],
    "research": ["search for", "find information", "look up", "what is", "research", "tell me about", "summarize this"],
    "chat": ["how are you", "what do you think", "opinion", "hello", "hi", "thanks"],
    "scheduled": ["schedule", "every day", "cron", "remind me", "recurring"],
    "email": ["email", "gmail", "inbox", "send email", "reply to", "draft email"],
    "system": ["install", "configure", "settings", "enable", "disable", "setup"],
}

# Specificity ordering for tie-breaking: higher index = more specific
_SPECIFICITY_ORDER = [
    "chat", "research", "file_ops", "system", "email", "scheduled",
    "agent_build", "code.explain", "code.test", "code.refactor",
    "code.write", "code.debug", "computer_use",
]

KNOWN_APPS = [
    "chrome", "firefox", "edge", "excel", "word", "notepad", "gmail",
    "outlook", "vscode", "terminal", "explorer", "slack", "discord",
    "spotify", "zoom", "teams", "photoshop", "figma",
]

ACTION_VERBS = [
    "open", "close", "create", "write", "send", "read", "find",
    "search", "fix", "debug", "build", "run", "install", "delete",
    "edit", "move", "copy", "save", "check", "list", "show", "get",
]


def classify_task(text: str) -> str:
    """Return best matching task_type key. computer_use always wins if any keyword hits."""
    lower = text.lower()

    # computer_use has highest priority: any single keyword triggers it
    for kw in TASK_TYPES["computer_use"]:
        if kw in lower:
            return "computer_use"

    scores: Dict[str, int] = {}
    for task_type, keywords in TASK_TYPES.items():
        if task_type == "computer_use":
            continue
        count = sum(1 for kw in keywords if kw in lower)
        if count > 0:
            scores[task_type] = count

    if not scores:
        return "chat"

    max_score = max(scores.values())
    candidates = [t for t, s in scores.items() if s == max_score]

    if len(candidates) == 1:
        return candidates[0]

    # Tie-break: prefer higher specificity index
    return max(candidates, key=lambda t: _SPECIFICITY_ORDER.index(t) if t in _SPECIFICITY_ORDER else -1)


def task_fingerprint(text: str, task_type: str) -> str:
    """Stable 16-char sha256 fingerprint for a task."""
    normalized = text.lower().strip()
    normalized = re.sub(r'\b(a|an|the|this|that|my|your)\b', '', normalized)
    normalized = re.sub(r'C:\\Users\\[^\\]+', '<user_home>', normalized)
    normalized = re.sub(r'/home/[^/]+', '<user_home>', normalized)
    normalized = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '<date>', normalized)
    normalized = re.sub(r'\b\d+\b', '<N>', normalized)

    apps = sorted([app for app in KNOWN_APPS if app in normalized])

    domains = sorted(re.findall(r'\b([a-z0-9-]+\.(com|org|net|io|dev|ai))\b', normalized))

    verb = "do"
    words = normalized.split()
    for w in words:
        if w in ACTION_VERBS:
            verb = w
            break

    components = [task_type, verb] + apps + [d[0] for d in domains]
    fingerprint_input = "|".join(sorted(set(components)))
    return hashlib.sha256(fingerprint_input.encode()).hexdigest()[:16]


def classify_and_fingerprint(text: str) -> dict:
    """Return task_type, task_fingerprint, and confidence."""
    lower = text.lower()
    task_type = classify_task(text)

    # Count matched keywords for confidence
    if task_type == "computer_use":
        matched = sum(1 for kw in TASK_TYPES["computer_use"] if kw in lower)
    elif task_type in TASK_TYPES:
        matched = sum(1 for kw in TASK_TYPES[task_type] if kw in lower)
    else:
        matched = 0

    if matched == 0:
        confidence = 0.3
    elif matched <= 2:
        confidence = 0.6
    else:
        confidence = 0.9

    return {
        "task_type": task_type,
        "task_fingerprint": task_fingerprint(text, task_type),
        "confidence": confidence,
    }


def complexity_score(text: str) -> int:
    """Return 1-5 complexity score for a task text."""
    lower = text.lower()
    words = text.split()
    word_count = len(words)

    # Level 5: agent build or automate triggers
    if "build an agent" in lower or "automate" in lower:
        return 5

    # Level 4: 80+ words or pipeline/workflow/multiple/each
    if word_count >= 80 or any(kw in lower for kw in ("pipeline", "workflow", "multiple", "each")):
        return 4

    # Level 3: 30-80 words or multi-step signals
    if word_count >= 30 or any(kw in lower for kw in ("then", "also", "and then")):
        return 3

    # Level 2: 10-30 words
    if word_count >= 10:
        return 2

    # Level 1: under 10 words
    return 1
