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
    unarchive_memory(memory_id) → bool
    list_memories(category, include_archived, limit) → list[dict]
    search_memories(query, limit) → list[dict]
    get_memory_block(prompt, max_tokens) → str
    touch_memory(memory_id) → None
    extract_memories_from_session(sess) → list[dict]   (session-end)
    save_extracted_memories(sess) → int
    enforce_memory_cap() → int   (auto-archive oldest if over cap)
    apply_memory_decay() → dict  (reduce decay_score, auto-archive stale)
"""

import os
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
MAX_MEMORY_TOKENS = int(os.environ.get("MEMORY_MAX_TOKENS", "500"))

# Max active (non-archived) memories before auto-archiving oldest
MAX_ACTIVE_MEMORIES = int(os.environ.get("MEMORY_MAX_ACTIVE", "500"))

# Chars-per-token estimate (consistent with context_manager.py)
_CPT = 4.0

# ---------------------------------------------------------------------------
# Stop words — filtered from search queries and relevance scoring
# ---------------------------------------------------------------------------
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "its", "his", "her", "this", "that", "these", "those",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
    "into", "about", "between", "through", "after", "before", "above",
    "and", "or", "but", "not", "no", "if", "so", "than", "too", "very",
    "just", "also", "how", "what", "when", "where", "who", "which",
    "all", "any", "some", "each", "every", "both", "few", "more",
    "other", "such", "only", "same", "then", "there", "here",
    "up", "out", "off", "over", "under", "again", "once",
})


def _meaningful_terms(text: str) -> set[str]:
    """Extract meaningful (non-stop) words from text, lowered."""
    return {w for w in text.lower().split() if w not in _STOP_WORDS and len(w) > 1}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _db():
    from helm.db import get_db
    return get_db()


def _encrypt(plaintext: str) -> str:
    """Encrypt memory content for DB storage."""
    try:
        from helm.token_vault import encrypt_value
        return encrypt_value(plaintext)
    except Exception:
        return plaintext


def _decrypt(cipher: str) -> str:
    """Decrypt memory content from DB."""
    try:
        from helm.token_vault import decrypt_value
        return decrypt_value(cipher)
    except Exception:
        return cipher


def _make_search_text(content: str, category: str, source_ai: str = "") -> str:
    """Build a lowercase keyword string for searchable indexing."""
    words = re.findall(r"[a-z0-9]+", content.lower())
    significant = [w for w in words if len(w) > 2][:15]
    parts = [category.lower(), (source_ai or "").lower()] + significant
    return " ".join(parts)


def _decrypt_row(row_dict: dict) -> dict:
    """Decrypt the 'content' field of a memory row dict."""
    if "content" in row_dict and row_dict["content"]:
        row_dict["content"] = _decrypt(row_dict["content"])
    return row_dict


def add_memory(
    content: str,
    category: str = DEFAULT_CATEGORY,
    source_ai: str = "",
    session_id: str = "",
) -> int:
    """Store a new memory. Returns the row id.

    Dedup: checks ALL non-archived memories via SQL for near-duplicates
    (>80% Jaccard word overlap).  If a duplicate is found, bumps its
    use_count instead of creating a new row.

    After insert, enforces MAX_ACTIVE_MEMORIES cap by auto-archiving
    the oldest, least-used memories.
    """
    content = content.strip()
    if not content:
        raise ValueError("Memory content cannot be empty")
    if category not in VALID_CATEGORIES:
        category = DEFAULT_CATEGORY

    # Dedup: fetch ALL non-archived content for comparison (only id + content)
    db = _db()
    rows = db.execute(
        "SELECT id, content FROM memories WHERE archived = 0"
    ).fetchall()

    content_lower = content.lower()
    for row in rows:
        # Decrypt stored content for comparison
        existing_content = _decrypt(row["content"] or "")
        if _similarity(content_lower, existing_content.lower()) > 0.80:
            # Existing duplicate — bump usage, don't create new
            touch_memory(row["id"])
            logger.info("Memory dedup: bumped existing #%d instead of creating new", row["id"])
            return row["id"]

    # Build search_text from plaintext, then encrypt content for storage
    search_text = _make_search_text(content, category, source_ai)
    encrypted_content = _encrypt(content)

    try:
        cur = db.execute(
            """INSERT INTO memories (content, category, source_ai, session_id, search_text)
               VALUES (?, ?, ?, ?, ?)""",
            (encrypted_content, category, source_ai, session_id, search_text),
        )
    except Exception:
        # Fallback: search_text column may not exist yet (pre-v8 migration)
        cur = db.execute(
            """INSERT INTO memories (content, category, source_ai, session_id)
               VALUES (?, ?, ?, ?)""",
            (encrypted_content, category, source_ai, session_id),
        )
    db.commit()
    mid = cur.lastrowid
    logger.info("Memory added #%d: [%s] %s", mid, category, content[:80])

    # Enforce cap — auto-archive excess memories
    enforce_memory_cap()

    return mid


def edit_memory(memory_id: int, content: str = "", category: str = "") -> bool:
    """Update a memory's content and/or category.

    Returns True if the row was found and updated, False otherwise.
    Content is encrypted before storage; search_text is rebuilt from plaintext.
    """
    db = _db()
    parts, vals = [], []
    plaintext_content = content.strip() if content else ""

    if plaintext_content:
        parts.append("content = ?")
        vals.append(_encrypt(plaintext_content))
    if category and category in VALID_CATEGORIES:
        parts.append("category = ?")
        vals.append(category)
    if not parts:
        return False

    # Rebuild search_text if content changed
    if plaintext_content:
        # Determine category for search_text (use new category if provided, else fetch existing)
        cat_for_search = category if (category and category in VALID_CATEGORIES) else ""
        if not cat_for_search:
            row = db.execute("SELECT category, source_ai FROM memories WHERE id = ?", (memory_id,)).fetchone()
            cat_for_search = row["category"] if row else DEFAULT_CATEGORY
            source_ai = row["source_ai"] if row else ""
        else:
            row = db.execute("SELECT source_ai FROM memories WHERE id = ?", (memory_id,)).fetchone()
            source_ai = row["source_ai"] if row else ""
        parts.append("search_text = ?")
        vals.append(_make_search_text(plaintext_content, cat_for_search, source_ai))

    vals.append(memory_id)
    cur = db.execute(f"UPDATE memories SET {', '.join(parts)} WHERE id = ?", vals)
    db.commit()
    return cur.rowcount > 0


def delete_memory(memory_id: int) -> bool:
    """Permanently delete a memory. Returns True if a row was actually deleted."""
    db = _db()
    cur = db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    db.commit()
    return cur.rowcount > 0


def pin_memory(memory_id: int, pinned: bool = True) -> bool:
    """Pin/unpin a memory (pinned memories are always injected)."""
    db = _db()
    cur = db.execute("UPDATE memories SET pinned = ? WHERE id = ?", (1 if pinned else 0, memory_id))
    db.commit()
    return cur.rowcount > 0


def archive_memory(memory_id: int) -> bool:
    """Archive a memory (excluded from injection, kept for history)."""
    db = _db()
    cur = db.execute("UPDATE memories SET archived = 1 WHERE id = ?", (memory_id,))
    db.commit()
    return cur.rowcount > 0


def unarchive_memory(memory_id: int) -> bool:
    """Restore an archived memory back to active status."""
    db = _db()
    cur = db.execute("UPDATE memories SET archived = 0 WHERE id = ?", (memory_id,))
    db.commit()
    return cur.rowcount > 0


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
    return [_decrypt_row(dict(r)) for r in rows]


def search_memories(query: str, limit: int = 20) -> list[dict]:
    """Search memories by keyword matching.

    First searches the ``search_text`` column (unencrypted keywords) for fast
    filtering, then decrypts content for display.  Falls back to scanning
    decrypted content if search_text is empty (pre-v8 rows).

    Filters out stop words so common words like 'the', 'is', 'a' don't
    pollute results.  Falls back to all terms if stop-word filtering
    removes everything (e.g. query is "is it?").
    """
    if not query.strip():
        return list_memories(limit=limit)

    db = _db()
    raw_terms = query.lower().split()

    # Filter stop words, but fall back to raw terms if all are stop words
    meaningful = [t for t in raw_terms if t not in _STOP_WORDS and len(t) > 1]
    terms = meaningful if meaningful else raw_terms

    # Score each non-archived memory
    rows = db.execute(
        "SELECT * FROM memories WHERE archived = 0"
    ).fetchall()

    scored = []
    for row in rows:
        d = dict(row)
        # Use search_text for scoring (fast, unencrypted keywords)
        search_text = (d.get("search_text") or "").lower()
        category_lower = (d.get("category") or "").lower()

        # If search_text is populated, score against it
        if search_text:
            score = 0.0
            for term in terms:
                if term in search_text:
                    score += 3.0
                if term in category_lower:
                    score += 1.0
        else:
            # Fallback for pre-v8 rows: decrypt and score against content
            decrypted = _decrypt(d.get("content") or "")
            content_lower = decrypted.lower()
            score = 0.0
            for term in terms:
                if term in content_lower:
                    score += 3.0
                if term in category_lower:
                    score += 1.0

        if score > 0:
            d = _decrypt_row(d)
            d["_score"] = score
            scored.append(d)

    scored.sort(key=lambda x: (-x["_score"], -x.get("pinned", 0), -x.get("use_count", 0)))
    return scored[:limit]


def touch_memory(memory_id: int):
    """Bump use_count, last_used, and reset decay_score for a memory.

    Call this when a memory is genuinely referenced or helpful —
    NOT on every prompt injection (which inflates counts).
    Resets decay_score to 1.0 (fully fresh) since the memory is actively useful.
    """
    db = _db()
    db.execute(
        "UPDATE memories SET use_count = use_count + 1, "
        "last_used = datetime('now'), decay_score = 1.0 WHERE id = ?",
        (memory_id,),
    )
    db.commit()


# Internal alias kept for backward compatibility
_touch = touch_memory


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity on meaningful word sets (stop words excluded).

    Falls back to full word sets if stop-word filtering empties either side.
    """
    sa_meaningful = _meaningful_terms(a)
    sb_meaningful = _meaningful_terms(b)

    # Fall back to full word sets if filtering removed everything
    sa = sa_meaningful if sa_meaningful else set(a.split())
    sb = sb_meaningful if sb_meaningful else set(b.split())

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

    Relevance scoring uses meaningful (non-stop-word) term overlap
    so common words don't dominate the ranking.

    The block is capped at max_tokens (default MAX_MEMORY_TOKENS) to
    keep prompt overhead small.
    """
    if max_tokens <= 0:
        max_tokens = MAX_MEMORY_TOKENS

    max_chars = int(max_tokens * _CPT)

    try:
        all_memories = list_memories(include_archived=False, limit=500)
    except Exception as e:
        logger.warning("Memory block: failed to load memories: %s", e)
        return ""

    if not all_memories:
        return ""

    # Separate pinned from normal
    pinned = [m for m in all_memories if m.get("pinned")]
    normal = [m for m in all_memories if not m.get("pinned")]

    # Score normal memories by relevance to current prompt (stop-word aware)
    # decay_score (0.0–1.0) is factored in as a multiplier on relevance
    if prompt:
        prompt_terms = _meaningful_terms(prompt)
        if prompt_terms:
            for m in normal:
                content_terms = _meaningful_terms(m["content"])
                overlap = prompt_terms & content_terms
                decay = m.get("decay_score", 1.0)
                m["_relevance"] = len(overlap) * decay
            normal.sort(key=lambda m: (-m["_relevance"], -m.get("use_count", 0)))
        else:
            # Prompt was all stop words — fall back to decay-weighted use_count
            normal.sort(key=lambda m: (
                -m.get("use_count", 0) * m.get("decay_score", 1.0),
                -m.get("id", 0),
            ))
    else:
        normal.sort(key=lambda m: (
            -m.get("use_count", 0) * m.get("decay_score", 1.0),
            -m.get("id", 0),
        ))

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
# Memory cap enforcement — prevent unbounded growth
# ---------------------------------------------------------------------------

def enforce_memory_cap() -> int:
    """Auto-archive oldest, least-used memories if active count > cap.

    Pinned memories are never auto-archived.
    Returns the number of memories archived.
    """
    try:
        db = _db()
        count = db.execute(
            "SELECT COUNT(*) FROM memories WHERE archived = 0"
        ).fetchone()[0]

        if count <= MAX_ACTIVE_MEMORIES:
            return 0

        excess = count - MAX_ACTIVE_MEMORIES

        # Find the oldest, least-used, non-pinned memories to archive
        rows = db.execute(
            """SELECT id FROM memories
               WHERE archived = 0 AND pinned = 0
               ORDER BY use_count ASC, id ASC
               LIMIT ?""",
            (excess,),
        ).fetchall()

        if not rows:
            return 0

        ids = [r["id"] for r in rows]
        placeholders = ",".join("?" * len(ids))
        db.execute(
            f"UPDATE memories SET archived = 1 WHERE id IN ({placeholders})",
            ids,
        )
        db.commit()
        logger.info("Memory cap enforced: auto-archived %d memories (cap=%d)",
                     len(ids), MAX_ACTIVE_MEMORIES)
        return len(ids)
    except Exception as e:
        logger.warning("Memory cap enforcement failed: %s", e)
        return 0


# ---------------------------------------------------------------------------
# Session-end memory extraction (lightweight, no LLM needed)
# ---------------------------------------------------------------------------

# Patterns that indicate a memorable fact.
#
# IMPORTANT: These are deliberately strict to avoid capturing task-specific
# instructions as permanent memories.  Each pattern requires strong signal
# words and uses non-greedy matching + length caps.
#
# What we DON'T want to capture:
#   "I want you to fix this bug"    — task instruction, not a preference
#   "I need the output in JSON"     — one-time request, not lasting
#   "I like the way you did that"   — compliment, not a preference
#
# What we DO want to capture:
#   "I always prefer Python over JS"   — lasting preference
#   "Our project is called RAPR AI"    — project fact
#   "My name is Aashima"               — personal fact
#   "We decided to use SQLite"         — architectural decision

_REMEMBER_PATTERNS = [
    # Project identity: "our project is called X", "the app uses FastAPI"
    re.compile(
        r"(?:my|our|the)\s+(?:project|app|repo|site|tool|product|service)"
        r"\s+(?:is\s+called|is\s+named|uses?)\s+(.{3,80}?)(?:\.|,|$)",
        re.I,
    ),
    # Lasting preferences: "I always prefer X", "I prefer X over Y", "we always use X"
    # Excludes task verbs: want, need, like (too vague without "always"/"prefer")
    re.compile(
        r"(?:i|we)\s+(?:always\s+(?:use|prefer|like)|prefer)\s+(.{3,80}?)(?:\.|,|$)",
        re.I,
    ),
    # Personal identity: "my name is X", "I'm X" (only when followed by a name-like word)
    re.compile(
        r"(?:my\s+name\s+is|i'?m\s+called|call\s+me)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
        re.I,
    ),
    # Decisions: "we decided to use X", "let's go with X"
    re.compile(
        r"(?:we\s+decided\s+(?:to\s+)?(?:use|go\s+with)|decision:\s*|let'?s\s+go\s+with)\s+(.{3,80}?)(?:\.|,|$)",
        re.I,
    ),
    # Explicit "remember this": "remember: X", "note: X", "important: X"
    re.compile(
        r"(?:remember|note|important)\s*:\s*(.{5,200}?)(?:\.|$)",
        re.I,
    ),
    # Account/identity facts: "my github is X", "our email is X"
    re.compile(
        r"(?:my|our)\s+(?:github|repo|email|username|stack|domain|website)"
        r"\s+(?:is|are)\s+(.{3,80}?)(?:\.|,|\s|$)",
        re.I,
    ),
]

# Category hints from keywords
_CATEGORY_HINTS = {
    "prefer": "preference", "always use": "preference", "always prefer": "preference",
    "project": "project", "app": "project", "repo": "project", "product": "project",
    "name is": "person", "call me": "person", "team": "person", "lead": "person",
    "decided": "decision", "chose": "decision", "go with": "decision",
    "remember": "instruction", "note": "instruction", "important": "instruction",
    "github": "fact", "email": "fact", "username": "fact", "domain": "fact",
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

    Returns list of {content, category, source_ai, session_id} dicts
    (not yet saved — call save_extracted_memories() to persist).
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
                # Use the captured group (the actual fact), not the full match
                fact = match.group(1).strip()
                # Clean trailing punctuation
                fact = fact.rstrip(".,;:!?")
                # Skip if too short (likely a false positive)
                if len(fact) < 5:
                    continue
                # Skip if it looks like a task instruction rather than a fact
                if _is_task_instruction(fact):
                    continue
                if fact.lower() not in seen_contents:
                    seen_contents.add(fact.lower())
                    extracted.append({
                        "content": fact,
                        "category": _guess_category(text),  # use full text for category hints
                        "source_ai": ai,
                        "session_id": sid,
                    })

    return extracted


def _is_task_instruction(text: str) -> bool:
    """Return True if text looks like a one-time task instruction, not a fact.

    Filters out common false positives like:
      "fix this bug", "create a file", "run the tests"
    """
    task_verbs = {
        "fix", "create", "make", "build", "run", "test", "check", "update",
        "add", "remove", "delete", "change", "modify", "write", "read",
        "show", "display", "print", "send", "open", "close", "save",
        "generate", "convert", "move", "copy", "rename", "install",
        "deploy", "debug", "refactor", "review", "merge", "commit",
    }
    words = text.lower().split()
    if words and words[0] in task_verbs:
        return True
    # "you to <verb>" pattern
    if len(words) >= 3 and words[0] == "you" and words[1] == "to" and words[2] in task_verbs:
        return True
    return False


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
            "cap": MAX_ACTIVE_MEMORIES,
            "by_category": {r["category"]: r["cnt"] for r in cats},
        }
    except Exception:
        return {"total": 0, "pinned": 0, "archived": 0, "cap": MAX_ACTIVE_MEMORIES, "by_category": {}}


# ---------------------------------------------------------------------------
# Memory Decay
# ---------------------------------------------------------------------------

# Decay factor per cycle (e.g., 0.95 means lose 5% relevance per decay run).
# Pinned memories are exempt. Memories drop to 0 and get auto-archived.
DECAY_FACTOR = float(os.environ.get("MEMORY_DECAY_FACTOR", "0.95"))
DECAY_ARCHIVE_THRESHOLD = float(os.environ.get("MEMORY_DECAY_ARCHIVE", "0.1"))


def apply_memory_decay() -> dict:
    """Apply time-based decay to all non-pinned, non-archived memories.

    Reduces decay_score by DECAY_FACTOR (multiplicative).
    Memories that drop below DECAY_ARCHIVE_THRESHOLD are auto-archived.

    Returns stats: {"decayed": int, "archived": int}.
    """
    db = _db()
    try:
        # Decay all non-pinned, non-archived memories
        cur = db.execute(
            "UPDATE memories SET decay_score = decay_score * ? "
            "WHERE archived = 0 AND pinned = 0 AND decay_score > 0",
            (DECAY_FACTOR,),
        )
        decayed = cur.rowcount

        # Auto-archive memories that have decayed below threshold
        cur2 = db.execute(
            "UPDATE memories SET archived = 1 "
            "WHERE archived = 0 AND pinned = 0 AND decay_score < ?",
            (DECAY_ARCHIVE_THRESHOLD,),
        )
        archived = cur2.rowcount

        db.commit()

        if decayed > 0 or archived > 0:
            logger.info(
                "Memory decay: %d memories decayed (factor %.2f), %d auto-archived (below %.2f)",
                decayed, DECAY_FACTOR, archived, DECAY_ARCHIVE_THRESHOLD,
            )

        return {"decayed": decayed, "archived": archived}
    except Exception as e:
        logger.warning("Memory decay failed: %s", e)
        return {"decayed": 0, "archived": 0}
