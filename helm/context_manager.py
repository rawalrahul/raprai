"""
helm/context_manager.py — Context Window Management for all AI sessions.

Tracks token usage per session, warns when context is filling up,
and auto-summarises older messages to keep conversations within the
model's context window — preventing quality degradation in long chats.

Key concepts:
  • Each AI model has a known context-window size (tokens).
  • Every message is estimated at ~4 chars per token (refined by actual
    counts when the AI backend reports them).
  • When usage crosses WARN_THRESHOLD (70%), a warning is pushed.
  • When usage crosses SUMMARISE_THRESHOLD (80%), older messages are
    summarised into a compact "previously…" block and the originals
    are dropped from the active context.
  • The Ollama path trims `sess["ollama_messages"]` directly.
  • The Claude path trims `sess["claude_msgs"]` (list of user strings).
  • Integrations (Gemini, Codex) are single-turn CLIs — no persistent
    context — but we still track estimated usage for the UI indicator.
"""

import os
import time
from typing import Optional

from helm.config import logger


# ---------------------------------------------------------------------------
# Summary persistence helpers
# ---------------------------------------------------------------------------

def save_summary_to_db(history_id: str, summary: str, token_count: int = 0):
    """Persist a compaction summary to the conversation_summaries table."""
    if not history_id or not summary:
        return
    try:
        from helm.db import get_db
        db = get_db()
        db.execute(
            "INSERT INTO conversation_summaries (history_id, summary, token_count) "
            "VALUES (?, ?, ?)",
            (history_id, summary, token_count),
        )
        db.commit()
    except Exception as e:
        logger.debug("Failed to save summary for %s: %s", history_id, e)


def load_summaries_from_db(history_id: str) -> list[str]:
    """Load all stored summaries for a session, ordered chronologically."""
    try:
        from helm.db import get_db
        db = get_db()
        rows = db.execute(
            "SELECT summary FROM conversation_summaries "
            "WHERE history_id = ? ORDER BY id ASC",
            (history_id,),
        ).fetchall()
        return [r["summary"] for r in rows]
    except Exception as e:
        logger.debug("Failed to load summaries for %s: %s", history_id, e)
        return []

# ---------------------------------------------------------------------------
# AI Model Context Windows (tokens)
# ---------------------------------------------------------------------------
# Override any of these via env vars, e.g. CONTEXT_WINDOW_CLAUDE=200000

_DEFAULT_WINDOWS: dict[str, int] = {
    # Claude Code models
    "claude":           200_000,
    # Ollama models — conservative defaults; user can override
    "ollama":           128_000,
    "qwen2.5":          128_000,
    "qwen2.5-coder":    128_000,
    "qwen3":            128_000,
    "llama3.1":         128_000,
    "llama3.2":         128_000,
    "llama3.3":         128_000,
    "mistral":           32_000,
    "mistral-nemo":     128_000,
    "deepseek-r1":      128_000,
    "gemma2":             8_192,
    "gemma3":           128_000,
    "phi3":             128_000,
    "codellama":         16_384,
    # Integration CLIs (single-turn, but tracked for UI)
    "gemini":         1_000_000,
    "codex":          1_000_000,  # GPT-4.1 default (1M)
    "openai":         1_000_000,  # GPT-4.1 default (1M); override via CONTEXT_WINDOW_OPENAI
}

# Thresholds (fraction of context window)
WARN_THRESHOLD      = float(os.environ.get("CONTEXT_WARN_PCT",      "0.70"))
SUMMARISE_THRESHOLD = float(os.environ.get("CONTEXT_SUMMARISE_PCT", "0.80"))

# How many of the most recent messages to always preserve (never summarise)
KEEP_RECENT = int(os.environ.get("CONTEXT_KEEP_RECENT", "6"))

# Minimum messages before we ever attempt summarisation
MIN_MESSAGES_FOR_SUMMARY = 10

# Chars-per-token estimate (refined when actual counts are available)
CHARS_PER_TOKEN = 4.0


def context_window_for(ai: str, model: str = "") -> int:
    """Return the context window size (tokens) for the given AI + model combo."""
    # Check env override first
    env_key = f"CONTEXT_WINDOW_{ai.upper()}"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass

    # Check model-specific window
    if model:
        base_model = model.lower().split(":")[0]
        if base_model in _DEFAULT_WINDOWS:
            return _DEFAULT_WINDOWS[base_model]

    # Fall back to AI-level default
    return _DEFAULT_WINDOWS.get(ai, 128_000)


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length. ~4 chars per token on average."""
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# ---------------------------------------------------------------------------
# Per-session context tracking
# ---------------------------------------------------------------------------

# Session-level context state stored in sess["_context"]:
# {
#     "total_tokens":    int,     # running estimate of tokens in context
#     "actual_tokens":   int,     # last actual count from AI backend (if any)
#     "messages_count":  int,     # number of messages in active context
#     "warned":          bool,    # have we sent the 70% warning?
#     "summarised_at":   float,   # last time we summarised (timestamp)
#     "summaries":       list,    # list of summary strings from prior compactions
# }


def _ensure_context_state(sess: dict) -> dict:
    """Initialise context tracking state on a session if not present."""
    if "_context" not in sess:
        sess["_context"] = {
            "total_tokens": 0,
            "actual_tokens": 0,
            "messages_count": 0,
            "warned": False,
            "summarised_at": 0.0,
            "summaries": [],
        }
    return sess["_context"]


def update_token_count(sess: dict, input_tokens: int = 0, output_tokens: int = 0,
                       prompt_text: str = "", output_text: str = "") -> dict:
    """Update the session's running token count.

    If actual token counts are provided (from AI backend), use those.
    Otherwise estimate from text lengths.

    For multi-turn AIs (Ollama, Claude), context_usage() recalculates from
    their message lists anyway, so this mainly tracks the running total.
    For single-turn AIs (Gemini, Codex), we ACCUMULATE so the context bar
    shows cumulative session usage rather than just the last call.

    Returns the context state dict.
    """
    ctx = _ensure_context_state(sess)
    ai = sess.get("ai") or "shell"

    if input_tokens > 0 or output_tokens > 0:
        this_call = input_tokens + output_tokens
        ctx["actual_tokens"] = this_call
        if ai in ("ollama", "claude"):
            # Multi-turn: set total (recalculated from messages in context_usage)
            ctx["total_tokens"] = this_call
        else:
            # Single-turn: accumulate across calls so UI bar grows
            ctx["total_tokens"] = ctx.get("total_tokens", 0) + this_call
    else:
        # Estimate from text
        added = estimate_tokens(prompt_text) + estimate_tokens(output_text)
        ctx["total_tokens"] += added

    ctx["messages_count"] = _count_active_messages(sess)
    return ctx


def context_usage(sess: dict) -> dict:
    """Return context window usage info for a session.

    Returns:
        {
            "used_tokens":    int,
            "window_tokens":  int,
            "pct":            float (0-100),
            "status":         "ok" | "warn" | "critical",
            "messages_count": int,
        }
    """
    ctx = _ensure_context_state(sess)
    ai = sess.get("ai") or "shell"
    model = sess.get("model") or ""
    window = context_window_for(ai, model)

    used = ctx.get("total_tokens", 0)
    # If we have Ollama messages, re-estimate from actual content
    if ai == "ollama" and sess.get("ollama_messages"):
        used = _estimate_ollama_tokens(sess)
        ctx["total_tokens"] = used
    elif ai == "claude" and sess.get("claude_msgs"):
        used = _estimate_claude_tokens(sess)
        ctx["total_tokens"] = used

    pct = (used / window * 100) if window > 0 else 0
    if pct >= SUMMARISE_THRESHOLD * 100:
        status = "critical"
    elif pct >= WARN_THRESHOLD * 100:
        status = "warn"
    else:
        status = "ok"

    return {
        "used_tokens": used,
        "window_tokens": window,
        "pct": round(pct, 1),
        "status": status,
        "messages_count": ctx.get("messages_count", 0),
    }


def _count_active_messages(sess: dict) -> int:
    """Count messages currently in the active context for this session."""
    ai = sess.get("ai")
    if ai == "ollama" and sess.get("ollama_messages"):
        return len(sess["ollama_messages"])
    if ai == "claude":
        return len(sess.get("claude_msgs", []))
    # Single-turn AIs: use task_count as proxy for message count
    return int(sess.get("task_count", 0))


def _estimate_ollama_tokens(sess: dict) -> int:
    """Estimate total tokens in Ollama conversation history."""
    msgs = sess.get("ollama_messages") or []
    total = 0
    for m in msgs:
        content = m.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        # Tool calls also consume tokens
        for tc in m.get("tool_calls", []):
            fn = tc.get("function", {})
            total += estimate_tokens(str(fn.get("arguments", "")))
            total += estimate_tokens(fn.get("name", ""))
    return total


def _estimate_claude_tokens(sess: dict) -> int:
    """Estimate total tokens in Claude conversation history."""
    msgs = sess.get("claude_msgs", [])
    total = 0
    for text in msgs:
        total += estimate_tokens(text)
    # Claude also gets the system prompt, skills, plugins — estimate overhead
    total += 2000  # rough overhead for system prompt + injections
    return total


# ---------------------------------------------------------------------------
# Context compaction — summarise older messages
# ---------------------------------------------------------------------------

async def check_and_compact(sess: dict, source: str = "web") -> Optional[str]:
    """Check if context needs compaction and perform it if so.

    Called after each AI response. If context exceeds SUMMARISE_THRESHOLD,
    summarises older messages and trims the conversation.

    Returns a status message if action was taken, None otherwise.
    """
    from helm.broadcast import push_message

    ai = sess.get("ai") or "shell"
    sid = sess.get("id", "")

    # Only Ollama needs our context management.
    # Claude, Gemini, Codex, NemoClaw, and other AIs handle context natively.
    if ai != "ollama":
        return None

    usage = context_usage(sess)
    ctx = _ensure_context_state(sess)

    # Send warning at 70%
    if usage["pct"] >= WARN_THRESHOLD * 100 and not ctx.get("warned"):
        ctx["warned"] = True
        warn_msg = (
            f"⚠️ **Context window {usage['pct']:.0f}% full** "
            f"({usage['used_tokens']:,} / {usage['window_tokens']:,} tokens). "
            f"Older messages will be summarised automatically at "
            f"{int(SUMMARISE_THRESHOLD * 100)}% to maintain quality."
        )
        await push_message("system", warn_msg, source=source, session_id=sid)
        return warn_msg

    # Auto-summarise at 80%
    if usage["pct"] >= SUMMARISE_THRESHOLD * 100:
        msg_count = usage["messages_count"]
        if msg_count < MIN_MESSAGES_FOR_SUMMARY:
            return None

        # Rate-limit: don't summarise more than once per 60 seconds
        if time.time() - ctx.get("summarised_at", 0) < 60:
            return None

        await push_message(
            "system",
            "🗜️ **Compacting context** — summarising older messages to free up space…",
            source=source, session_id=sid,
        )

        # Only Ollama reaches here (early return above for other AIs)
        result = await _compact_ollama(sess)

        if result:
            ctx["summarised_at"] = time.time()
            ctx["warned"] = False  # reset warning for next cycle

            # Persist summary to DB for session resume
            history_id = sess.get("history_id", sid)
            est_tokens = len(result) // 4
            save_summary_to_db(history_id, result, est_tokens)

            # Recalculate
            new_usage = context_usage(sess)
            compact_msg = (
                f"✅ **Context compacted** — "
                f"{usage['pct']:.0f}% → {new_usage['pct']:.0f}% "
                f"({new_usage['used_tokens']:,} / {new_usage['window_tokens']:,} tokens). "
                f"Conversation quality restored."
            )
            await push_message("system", compact_msg, source=source, session_id=sid)
            return compact_msg

    return None


async def _compact_ollama(sess: dict) -> Optional[str]:
    """Summarise and trim Ollama conversation messages."""
    import asyncio

    msgs = sess.get("ollama_messages")
    if not msgs or len(msgs) < MIN_MESSAGES_FOR_SUMMARY:
        return None

    # Keep system prompt (first message) and last KEEP_RECENT messages
    system_msg = msgs[0] if msgs[0].get("role") == "system" else None
    start_idx = 1 if system_msg else 0

    if len(msgs) - start_idx <= KEEP_RECENT:
        return None  # Not enough to trim

    # Messages to summarise (everything except system + last KEEP_RECENT)
    to_summarise = msgs[start_idx:-KEEP_RECENT]
    to_keep = msgs[-KEEP_RECENT:]

    # Build a summary of the older conversation
    summary = _build_summary_from_messages(to_summarise)

    ctx = _ensure_context_state(sess)
    ctx["summaries"].append(summary)

    # Reconstruct messages: system + summary-as-system-note + recent messages
    new_msgs = []
    if system_msg:
        new_msgs.append(system_msg)

    # Add summary as a system message
    all_summaries = "\n\n".join(ctx["summaries"])
    new_msgs.append({
        "role": "system",
        "content": (
            f"[CONTEXT SUMMARY — The following summarises earlier parts of this "
            f"conversation that were compacted to save context space.]\n\n"
            f"{all_summaries}\n\n"
            f"[END SUMMARY — The recent messages below are the current conversation.]"
        ),
    })

    new_msgs.extend(to_keep)
    sess["ollama_messages"] = new_msgs

    logger.info(
        "Ollama context compacted: %d messages → %d (summarised %d, kept %d recent)",
        len(msgs), len(new_msgs), len(to_summarise), len(to_keep),
    )
    return summary


async def _compact_claude(sess: dict) -> Optional[str]:
    """Summarise and trim Claude conversation messages.

    Claude Code uses `sess["claude_msgs"]` — a list of user prompt strings.
    Each new call sends the full history via `--resume` semantics, so trimming
    this list effectively reduces context.
    """
    msgs = sess.get("claude_msgs", [])
    if len(msgs) < MIN_MESSAGES_FOR_SUMMARY:
        return None

    if len(msgs) <= KEEP_RECENT:
        return None

    # Summarise older messages
    to_summarise_texts = msgs[:-KEEP_RECENT]
    to_keep = msgs[-KEEP_RECENT:]

    # Build summary
    summary_parts = []
    for i, text in enumerate(to_summarise_texts):
        # Truncate each message to 200 chars for the summary
        snippet = text[:200].replace("\n", " ")
        if len(text) > 200:
            snippet += "…"
        summary_parts.append(f"  {i+1}. {snippet}")

    summary = (
        f"[Earlier in this session, the user made {len(to_summarise_texts)} requests "
        f"including:\n" + "\n".join(summary_parts[:10])  # Cap at 10 entries
    )
    if len(summary_parts) > 10:
        summary += f"\n  … and {len(summary_parts) - 10} more requests"
    summary += "\n]"

    ctx = _ensure_context_state(sess)
    ctx["summaries"].append(summary)

    # Prepend a context-restoration note to the first kept message
    context_note = (
        "[Note: Earlier messages in this conversation were summarised to save context. "
        f"Summary of {len(to_summarise_texts)} prior messages:\n"
        + "\n".join(summary_parts[:10])
        + "]\n\n"
    )

    # Replace the message list
    sess["claude_msgs"] = [context_note + to_keep[0]] + to_keep[1:]

    logger.info(
        "Claude context compacted: %d messages → %d (summarised %d, kept %d recent)",
        len(msgs), len(sess["claude_msgs"]), len(to_summarise_texts), len(to_keep),
    )
    return summary


def _build_summary_from_messages(messages: list[dict]) -> str:
    """Build a concise natural-language summary from a list of Ollama-style messages."""
    user_msgs = []
    assistant_msgs = []
    tool_names = set()

    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user":
            snippet = content[:150].replace("\n", " ")
            if len(content) > 150:
                snippet += "…"
            user_msgs.append(snippet)
        elif role == "assistant":
            snippet = content[:150].replace("\n", " ")
            if len(content) > 150:
                snippet += "…"
            assistant_msgs.append(snippet)
        elif role == "tool":
            # Extract tool name from nearby messages if possible
            pass
        for tc in m.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_names.add(fn.get("name", "unknown"))

    parts = []
    if user_msgs:
        parts.append(
            f"The user made {len(user_msgs)} request(s) including: "
            + "; ".join(user_msgs[:5])
        )
        if len(user_msgs) > 5:
            parts.append(f"  (and {len(user_msgs) - 5} more)")
    if tool_names:
        parts.append(f"Tools used: {', '.join(sorted(tool_names))}")
    if assistant_msgs:
        parts.append(
            f"The AI provided {len(assistant_msgs)} response(s), last one about: "
            + (assistant_msgs[-1] if assistant_msgs else "various topics")
        )

    return "\n".join(parts) if parts else "Earlier conversation (details compacted)."


# ---------------------------------------------------------------------------
# Manual compaction (triggered by user via /compact or API)
# ---------------------------------------------------------------------------

async def force_compact(sess: dict, source: str = "web") -> str:
    """Force-compact a session's context regardless of current usage level."""
    from helm.broadcast import push_message

    ai = sess.get("ai") or "shell"
    sid = sess.get("id", "")

    if ai != "ollama":
        # Claude, Gemini, Codex, NemoClaw handle context natively —
        # no need for manual compaction. Reset the counter for the UI.
        ctx = _ensure_context_state(sess)
        ctx["total_tokens"] = 0
        ctx["warned"] = False
        ai_name = ai.title() if ai else "This AI"
        return f"ℹ️ {ai_name} manages its own context window natively — no compaction needed."

    before = context_usage(sess)
    result = await _compact_ollama(sess)

    if not result:
        return "Not enough messages to compact (need at least 10)."

    after = context_usage(sess)
    msg = (
        f"🗜️ Context compacted: {before['pct']:.0f}% → {after['pct']:.0f}% "
        f"({after['used_tokens']:,} / {after['window_tokens']:,} tokens)"
    )
    return msg


# ---------------------------------------------------------------------------
# Context info for session state payload (sent to UI)
# ---------------------------------------------------------------------------

def context_info_for_session(sess: dict) -> dict:
    """Return context info dict suitable for inclusion in the session state payload."""
    usage = context_usage(sess)
    ctx = _ensure_context_state(sess)
    return {
        "used_tokens": usage["used_tokens"],
        "window_tokens": usage["window_tokens"],
        "pct": usage["pct"],
        "status": usage["status"],
        "messages_count": usage["messages_count"],
        "summaries_count": len(ctx.get("summaries", [])),
    }
