"""
helm/memory.py — Shared AI Memory.

Persistent knowledge store that all AI sessions (Claude, Ollama, Gemini,
Codex, etc.) read from and write to.  Memories survive session restarts
and are injected into every AI prompt so that knowledge learned in one
session or AI is available everywhere.

Public API:
    add_memory(content, category, source_ai, session_id) → int (id)
    edit_memory(memory_id, content, category) → bool
    delete_memory(memory_id) → bool
    pin_memory(memory_id, pinned) → bool
    archive_memory(memory_id) → bool
    list_memories(category, include_archived, limit) → list[dict]
    search_memories(query, limit) → list[dict]
    get_memory_block(prompt, max_tokens) → str
    extract_memories_from_session(sess) → list[dict]   (session-end)
"""

import re
import time
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Categories — keep this small and high-signal
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "preference",   # "I prefer Python", "use dark theme"
    "fact",         # "My GitHub username is X", "project uses FastAPI"
    "project",      # "HelmHQ uses SQLite WAL mode"
    "person",       # "Bob is the tech lead"
    "decision",     # "We chose bcrypt over Argon2"
    "instruction",  # "Always run tests before committing"
}

DEFAULT_CATEGORY = "fact"

# Max tokens for the injected memory block (keeps prompt overhead small)
MAX_MEMORY_TOKENS = int(__import__("os").environ.get("MEMORY_MAX_TOKENS", "500"))

# Chars-per-token estimate (consistent with context_manager.py)
_CPT = 4.0


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _db():
    from helm.db import get_db
    return get_db()


def add_memory(
    content: str,
    category: str = DEFAULT_CATEGORY,
    source_ai: str = "",
    session_id: str = "",
) -> int:
    """Store a new memory. Returns the row id."""
    content = content.strip()
    if not content:
        raise ValueError("Memory content cannot be empty")
    if category not in VALID_CATEGORIES:
        category = DEFAULT_CATEGORY

    # Dedup: check for near-duplicate (>80% overlap via simple ratio)
    existing = list_memories(include_archived=False, limit=200)
    for mem in existing:
        if _similarity(content.lower(), mem["content"].lower()) > 0.80:
            # Update existing instead of creating duplicate
            _touch(mem["id"])
            logger.info("Memory dedup: updating existing #%d instead of creating new", mem["id"])
            return mem["id"]

    db = _db()
    cur = db.execute(
        """INSERT INTO memories (content, category, source_ai, session_id)
           VALUES (?, ?, ?, ?)""",
        (content, category, source_ai, session_id),
    )
    db.commit()
    mid = cur.lastrowid
    logger.info("Memory added #%d: [%s] %s", mid, category, content[:80])
    return mid


def edit_memory(memory_id: int, content: str = "", category: str = "") -> bool:
    """Update a memory's content and/or category."""
    db = _db()
    parts, vals = [], []
    if content:
        parts.append("content = ?")
        vals.append(content.strip())
    if category and category in VALID_CATEGORIES:
        parts.append("category = ?")
        vals.append(category)
    if not parts:
        return False
    vals.append(memory_id)
    db.execute(f"UPDATE memories SET {', '.join(parts)} WHERE id = ?", vals)
    db.commit()
    return True


def delete_memory(memory_id: int) -> bool:
    """Permanently delete a memory."""
    db = _db()
    db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    db.commit()
    return True


def pin_memory(memory_id: int, pinned: bool = True) -> bool:
    """Pin/unpin a memory (pinned memories are always injected)."""
    db = _db()
    db.execute("UPDATE memories SET pinned = ? WHERE id = ?", (1 if pinned else 0, memory_id))
    db.commit()
    return True


def archive_memory(memory_id: int) -> bool:
    """Archive a memory (excluded from injection, kept for history)."""
    db = _db()
    db.execute("UPDATE memories SET archived = 1 WHERE id = ?", (memory_id,))
    db.commit()
    return True


def list_memories(
    category: str = "",
    include_archived: bool = False,
    limit: int = 100,
) -> list[dict]:
    """List all memories, optionally filtered by category."""
    db = _db()
    sql = "SELECT * FROM memories"
    params: list = []
    clauses = []

    if not include_archived:
        clauses.append("archived = 0")
    if category and category in VALID_CATEGORIES:
        clauses.append("category = ?")
        params.append(category)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    # Pinned first, then by use_count desc, then newest
    sql += " ORDER BY pinned DESC, use_count DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def search_memories(query: str, limit: int = 20) -> list[dict]:
    """Search memories by keyword matching against content."""
    if not query.strip():
        return list_memories(limit=limit)

    db = _db()
    terms = query.lower().split()

    # Score each non-archived memory
    rows = db.execute(
        "SELECT * FROM memories WHERE archived = 0"
    ).fetchall()

    scored = []
    for row in rows:
        content_lower = (row["content"] or "").lower()
        category_lower = (row["category"] or "").lower()
        score = 0.0
        for term in terms:
            if term in content_lower:
                score += 3.0
            if term in category_lower:
                score += 1.0
        if score > 0:
            d = dict(row)
            d["_score"] = score
            scored.append(d)

    scored.sort(key=lambda x: (-x["_score"], -x.get("pinned", 0), -x.get("use_count", 0)))
    return scored[:limit]


def _touch(memory_id: int):
    """Bump use_count and last_used for a memory."""
    db = _db()
    db.execute(
        "UPDATE memories SET use_count = use_count + 1, last_used = datetime('now') WHERE id = ?",
        (memory_id,),
    )
    db.commit()


def _similarity(a: str, b: str) -> float:
    """Simple Jaccard-like similarity on word sets."""
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    intersection = sa & sb
    union = sa | sb
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Memory injection — build the block that goes into AI prompts
# ---------------------------------------------------------------------------

def get_memory_block(prompt: str = "", max_tokens: int = 0) -> str:
    """Build a memory block string for injection into AI prompts.

    Returns an empty string if no memories exist.  Prioritises pinned
    memories, then relevance to the current prompt, then recency.

    The block is capped at max_tokens (default MAX_MEMORY_TOKENS) to
    keep prompt overhead small.
    """
    if max_tokens <= 0:
        max_tokens = MAX_MEMORY_TOKENS

    max_chars = int(max_tokens * _CPT)

    try:
        all_memories = list_memories(include_archived=False, limit=200)
    except Exception as e:
        logger.warning("Memory block: failed to load memories: %s", e)
        return ""

    if not all_memories:
        return ""

    # Separate pinned from normal
    pinned = [m for m in all_memories if m.get("pinned")]
    normal = [m for m in all_memories if not m.get("pinned")]

    # Score normal memories by relevance to current prompt
    if prompt:
        prompt_lower = prompt.lower()
        prompt_terms = set(prompt_lower.split())
        for m in normal:
            content_lower = m["content"].lower()
            content_terms = set(content_lower.split())
            overlap = prompt_terms & content_terms
            m["_relevance"] = len(overlap)
        normal.sort(key=lambda m: (-m["_relevance"], -m.get("use_count", 0)))
    else:
        normal.sort(key=lambda m: (-m.get("use_count", 0), -m.get("id", 0)))

    # Build block: pinned first, then top relevant
    selected = []
    used_chars = 0

    for m in pinned + normal:
        entry = f"- [{m['category']}] {m['content']}"
        entry_chars = len(entry) + 1  # +1 for newline
        if used_chars + entry_chars > max_chars:
            break
        selected.append(entry)
        used_chars += entry_chars
        # Touch to track usage
        try:
            _touch(m["id"])
        except Exception:
            pass

    if not selected:
        return ""

    block = (
        "[MEMORY — Things you know about the user and their projects. "
        "Use this context naturally; don't repeat it back unless asked.]\n"
        + "\n".join(selected)
        + "\n[END MEMORY]\n\n"
    )
    return block


# ---------------------------------------------------------------------------
# Session-end memory extraction (lightweight, no LLM needed)
# ---------------------------------------------------------------------------

# Patterns that indicate a memorable fact
_REMEMBER_PATTERNS = [
    re.compile(r"(?:my|our|the)\s+(?:project|app|repo|site|tool)\s+(?:is|uses?|called)\s+(.+)", re.I),
    re.compile(r"(?:i|we)\s+(?:prefer|like|always use|want|need)\s+(.+)", re.I),
    re.compile(r"(?:i'm|i am|my name is|call me)\s+(.+)", re.I),
    re.compile(r"(?:we decided|decision:?|let'?s go with)\s+(.+)", re.I),
    re.compile(r"(?:remember|note|important):\s*(.+)", re.I),
    re.compile(r"(?:my|our)\s+(?:github|repo|email|username|stack)\s+(?:is)\s+(.+)", re.I),
]

# Category hints from keywords
_CATEGORY_HINTS = {
    "prefer": "preference", "like": "preference", "always": "instruction",
    "project": "project", "app": "project", "repo": "project",
    "name": "person", "team": "person", "lead": "person",
    "decided": "decision", "chose": "decision", "go with": "decision",
    "remember": "instruction", "note": "instruction",
    "github": "fact", "email": "fact", "username": "fact",
}


def _guess_category(text: str) -> str:
    """Guess a memory category from keywords in the text."""
    text_lower = text.lower()
    for keyword, cat in _CATEGORY_HINTS.items():
        if keyword in text_lower:
            return cat
    return DEFAULT_CATEGORY


def extract_memories_from_session(sess: dict) -> list[dict]:
    """Extract memorable facts from a session's conversation history.

    Called at session end (or periodically). Scans user messages for
    patterns that indicate facts worth remembering.

    Returns list of {content, category, source_ai} dicts (not yet saved).
    """
    ai = sess.get("ai") or "shell"
    sid = sess.get("id", "")
    extracted: list[dict] = []
    seen_contents: set[str] = set()

    # Get user messages based on AI type
    user_texts: list[str] = []
    if ai == "ollama" and sess.get("ollama_messages"):
        user_texts = [
            m["content"] for m in sess["ollama_messages"]
            if m.get("role") == "user" and isinstance(m.get("content"), str)
        ]
    elif ai == "claude":
        user_texts = list(sess.get("claude_msgs", []))
    elif sess.get("_integration_history"):
        user_texts = [h["q"] for h in sess["_integration_history"]]

    for text in user_texts:
        for pattern in _REMEMBER_PATTERNS:
            match = pattern.search(text)
            if match:
                fact = match.group(0).strip()
                # Clean up and cap length
                fact = fact[:200]
                if fact.lower() not in seen_contents and len(fact) > 10:
                    seen_contents.add(fact.lower())
                    extracted.append({
                        "content": fact,
                        "category": _guess_category(fact),
                        "source_ai": ai,
                        "session_id": sid,
                    })

    return extracted


def save_extracted_memories(sess: dict) -> int:
    """Extract and save memories from a session. Returns count saved."""
    candidates = extract_memories_from_session(sess)
    saved = 0
    for mem in candidates:
        try:
            add_memory(
                content=mem["content"],
                category=mem["category"],
                source_ai=mem["source_ai"],
                session_id=mem.get("session_id", ""),
            )
            saved += 1
        except Exception as e:
            logger.warning("Failed to save extracted memory: %s", e)
    if saved:
        logger.info("Session %s: extracted and saved %d memories", sess.get("id", "?"), saved)
    return saved


# ---------------------------------------------------------------------------
# Memory stats (for UI)
# ---------------------------------------------------------------------------

def memory_stats() -> dict:
    """Return summary stats for the memory sidebar."""
    try:
        db = _db()
        total = db.execute("SELECT COUNT(*) FROM memories WHERE archived = 0").fetchone()[0]
        pinned = db.execute("SELECT COUNT(*) FROM memories WHERE archived = 0 AND pinned = 1").fetchone()[0]
        archived = db.execute("SELECT COUNT(*) FROM memories WHERE archived = 1").fetchone()[0]
        cats = db.execute(
            "SELECT category, COUNT(*) as cnt FROM memories WHERE archived = 0 GROUP BY category"
        ).fetchall()
        return {
            "total": total,
            "pinned": pinned,
            "archived": archived,
            "by_category": {r["category"]: r["cnt"] for r in cats},
        }
    except Exception:
        return {"total": 0, "pinned": 0, "archived": 0, "by_category": {}}
