"""
helm/telegram_bot/history.py — /history, /resume and /clear_context.
"""

import json
from typing import Optional

import helm.state as _st
from helm.config import logger

from .auth import authorized_only, tg_send_chunks
from .keyboards import sessions_keyboard, session_controls_keyboard


@authorized_only
async def tg_history(update, context):
    """/history [n] — show last n user+assistant messages from the database (default 5, max 20)."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    try:
        n = max(1, min(20, int(arg))) if arg else 5
    except ValueError:
        n = 5

    # Query recent messages from SQLite
    from helm.db import get_db
    try:
        db = get_db()
        rows = db.execute(
            """SELECT role, content, ai, timestamp, ts
               FROM messages
               WHERE type = 'message' AND role IN ('user', 'assistant')
               ORDER BY id DESC
               LIMIT ?""",
            (n,),
        ).fetchall()
    except Exception:
        await update.message.reply_text("Could not read history from database.")
        return

    if not rows:
        await update.message.reply_text("No history found.")
        return

    # Reverse to show oldest-first
    rows = list(reversed(rows))

    lines_out = []
    for m in rows:
        role = "You" if m["role"] == "user" else (m["ai"] or "AI").title()
        ts = (m["timestamp"] or "")[:16].replace("T", " ")
        preview = (m["content"] or "")[:200]
        if len(m["content"] or "") > 200:
            preview += "..."
        lines_out.append(f"[{ts}] {role}:\n{preview}")

    await tg_send_chunks(update, "\n\n".join(lines_out))


async def perform_resume(message, date_str: str = "") -> None:
    """Core resume logic — usable from both /resume command and inline button."""
    from helm.session_mgr import make_session
    from helm.ai_runner import change_cwd
    from helm.history import load_chat_names
    from helm.broadcast import push_state

    # --- Resolve history_id (from SQLite) ---
    from helm.db import get_db
    from helm.history import get_history_messages

    if date_str:
        # Verify this history_id exists in the DB
        db = get_db()
        exists = db.execute(
            "SELECT 1 FROM messages WHERE history_id = ? AND type = 'message' LIMIT 1",
            (date_str,),
        ).fetchone()
        if not exists:
            await message.reply_text(f"❌ No history found for {date_str}.")
            return
    else:
        # Find the most recent history_id
        db = get_db()
        row = db.execute(
            """SELECT DISTINCT history_id FROM messages
               WHERE type = 'message'
               ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        if not row:
            await message.reply_text("No chat history saved yet.")
            return
        date_str = row["history_id"]

    # --- Read messages from SQLite ---
    messages: list[dict] = get_history_messages(date_str)
    if not messages:
        await message.reply_text(f"No conversation messages found in session {date_str}.")
        return

    # --- Get CWD and AI from the history's own records ---
    last_cwd: Optional[str] = None
    last_ai:  Optional[str] = None

    db = get_db()
    cwd_row = db.execute(
        """SELECT path FROM messages
           WHERE history_id = ? AND type = 'cwd' AND path IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (date_str,),
    ).fetchone()
    if cwd_row:
        last_cwd = cwd_row["path"]

    ai_row = db.execute(
        """SELECT model FROM messages
           WHERE history_id = ? AND type = 'ai' AND model IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (date_str,),
    ).fetchone()
    if ai_row:
        last_ai = ai_row["model"]

    # --- Fallback: load CWD/AI from session_state table ---
    if not last_cwd or not last_ai:
        try:
            state_row = db.execute(
                "SELECT value FROM session_state WHERE key = 'sessions'"
            ).fetchone()
            if state_row:
                sessions_saved = json.loads(state_row["value"])
                if sessions_saved:
                    first = next(iter(sessions_saved.values()))
                    if not last_cwd:
                        last_cwd = first.get("cwd") or None
                    if not last_ai:
                        last_ai = first.get("ai") or None
        except Exception:
            logger.debug("Couldn't read the last session for /resume", exc_info=True)

    # --- Build context string from last 10 exchanges ---
    turns = messages[-10:]
    lines_ctx = []
    for m in turns:
        role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
        body = (m.get("content") or "")[:300]
        if len(m.get("content", "")) > 300:
            body += "..."
        lines_ctx.append(f"{role}: {body}")

    label = load_chat_names().get(date_str) or date_str
    context_prefix = (
        f"[Previous conversation — {label}]\n"
        + "\n".join(lines_ctx)
        + "\n[End context]\n\n"
    )

    # --- Create a new session for the resumed work ---
    valid_ai = last_ai and (last_ai == "claude" or last_ai in _st.integrations)
    ai_to_use = last_ai if valid_ai else None
    sess = make_session(ai_to_use, cwd=last_cwd)
    _st.focused_id = sess["id"]

    cwd_note = ""
    if last_cwd:
        cwd_ok = await change_cwd(last_cwd, source="telegram", session_id=sess["id"])
        cwd_note = (
            f"\n📂 Directory restored: `{last_cwd}`"
            if cwd_ok
            else f"\n⚠️ Could not restore directory: `{last_cwd}`"
        )

    # Inject the context prefix into the next message sent to this session
    _st.pending_tg_context = context_prefix

    await push_state()

    if valid_ai:
        if last_ai == "claude":
            ai_label = "🤖 Claude Code"
        elif last_ai in _st.integrations:
            info = _st.integrations[last_ai]
            ai_label = f"{info['emoji']} {info['name']}"
        else:
            ai_label = last_ai.title()
        ai_note = f"\n{ai_label} re-activated — just type to continue."
    else:
        ai_note = "\nPick an AI below to continue:"

    await message.reply_text(
        f"✅ *Resumed: {label}* ({len(turns)} exchanges loaded){cwd_note}{ai_note}",
        parse_mode="Markdown",
        reply_markup=session_controls_keyboard() if valid_ai else sessions_keyboard(),
    )


_perform_resume = perform_resume  # legacy alias


@authorized_only
async def tg_resume(update, context):
    """/resume [date] — restore a past session's directory, AI model, and context."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    await perform_resume(update.message, date_str=arg)


@authorized_only
async def tg_clear_context(update, context):
    """Discard any pending resume context without sending it."""
    if _st.pending_tg_context:
        _st.pending_tg_context = None
        await update.message.reply_text("✅ Pending context cleared.")
    else:
        await update.message.reply_text("No pending context to clear.")
