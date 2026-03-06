"""
helm/heartbeat.py — Heartbeat / Soul System.

A background task that periodically scans recent chat history for incomplete
or pending tasks and notifies the user via Telegram with actionable buttons.

Configurable via .env / Settings:
    HEARTBEAT_INTERVAL  — seconds between check-ins (default: 86400 = 24h)
    HEARTBEAT_AI        — AI to use for summarization ("gemini" | "ollama")
    HEARTBEAT_ENABLED   — "1" to enable, "0" to disable (default: "1")
"""

import asyncio
import os
import pathlib
import time
from typing import Optional

import helm.state as _st
from helm.config import logger
from helm.paths import user_data_dir as _udd

# ---------------------------------------------------------------------------
# Config helpers — read live from os.environ so Settings UI changes take
# effect without restart
# ---------------------------------------------------------------------------

def _interval() -> float:
    """Heartbeat interval in seconds (default 24 hours)."""
    return max(60, float(os.environ.get("HEARTBEAT_INTERVAL", "86400")))

def _ai() -> str:
    """Which AI to use for summarising pending items."""
    return os.environ.get("HEARTBEAT_AI", "gemini").lower()

def _enabled() -> bool:
    return os.environ.get("HEARTBEAT_ENABLED", "1").strip() in ("1", "true", "yes")

def _interval_label() -> str:
    """Human-readable label for the current interval (e.g. '15 min', '2 hrs')."""
    secs = _interval()
    if secs < 3600:
        m = round(secs / 60)
        return f"{m} min"
    h = round(secs / 3600)
    return f"{h} hr{'s' if h != 1 else ''}"


# ---------------------------------------------------------------------------
# Pending-task detection — scan recent history logs
# ---------------------------------------------------------------------------

# Patterns that suggest incomplete work
_PENDING_SIGNALS = [
    "todo",
    "TODO",
    "i'll do",
    "will do later",
    "do this later",
    "need to finish",
    "pending",
    "PENDING",
    "continue later",
    "come back to",
    "not done yet",
    "unfinished",
    "remind me",
    "next step",
    "follow up",
    "follow-up",
    "still need to",
    "haven't done",
    "left off",
    "pick this up",
    "in progress",
]


def scan_pending_tasks(max_logs: int = 10, max_age_hours: float = 0) -> list[dict]:
    """
    Scan recent chat messages in SQLite for pending-task signals.

    Args:
        max_logs: Maximum number of distinct sessions to return.
        max_age_hours: Only consider messages newer than this many hours.
                       0 means use 2× the heartbeat interval as the window.

    Returns a list of dicts:
        {"history_id": str, "folder": str, "ai": str, "snippet": str, "ts": float}
    """
    from helm.db import get_db

    # Time-window: only surface messages from the last 2× heartbeat interval
    if max_age_hours > 0:
        cutoff_ts = time.time() - (max_age_hours * 3600)
    else:
        cutoff_ts = time.time() - (_interval() * 2)

    try:
        db = get_db()
    except Exception:
        return []

    # Query recent messages from SQLite — keyword matching done in Python
    rows = db.execute(
        """SELECT history_id, content, ai, ts
           FROM messages
           WHERE type = 'message'
             AND ts > ?
           ORDER BY ts DESC
           LIMIT 2000""",
        (cutoff_ts,),
    ).fetchall()

    if not rows:
        return []

    # Get folder (CWD) info per history_id
    history_ids = list(dict.fromkeys(r["history_id"] for r in rows))[:max_logs]
    folder_map = {}
    for hid in history_ids:
        cwd_row = db.execute(
            """SELECT path FROM messages
               WHERE history_id = ? AND type = 'cwd' AND path IS NOT NULL
               ORDER BY id DESC LIMIT 1""",
            (hid,),
        ).fetchone()
        if cwd_row and cwd_row["path"]:
            folder_map[hid] = pathlib.Path(cwd_row["path"]).name or cwd_row["path"]

    pending = []
    hid_set = set(history_ids)
    for row in rows:
        hid = row["history_id"]
        if hid not in hid_set:
            continue

        content = (row["content"] or "").lower()
        for signal in _PENDING_SIGNALS:
            if signal.lower() in content:
                snippet = (row["content"] or "")[:150].replace("\n", " ")
                pending.append({
                    "history_id": hid,
                    "folder": folder_map.get(hid, hid),
                    "ai": row["ai"] or "",
                    "snippet": snippet,
                    "ts": row["ts"] or 0,
                    "signal": signal,
                })
                break

    # Deduplicate — keep only the most recent match per history_id
    seen = {}
    for p in pending:
        hid = p["history_id"]
        if hid not in seen or p["ts"] > seen[hid]["ts"]:
            seen[hid] = p
    return list(seen.values())


# ---------------------------------------------------------------------------
# Telegram notification
# ---------------------------------------------------------------------------

async def _notify_telegram(pending_items: list[dict]):
    """Send a summary of pending items to the user via Telegram."""
    if not _st.telegram_app or not pending_items:
        return

    from helm.config import ALLOWED_USER_IDS
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Build message
    lines = ["🫀 **Heartbeat Check-in**\n"]
    lines.append(f"I found {len(pending_items)} pending item(s) from your recent sessions:\n")

    buttons = []
    for i, item in enumerate(pending_items[:5]):  # cap at 5
        label = item["folder"]
        ai = item["ai"] or "unknown"
        snippet = item["snippet"][:80]
        lines.append(f"**{i+1}. [{ai}] {label}**")
        lines.append(f"   _{snippet}_\n")
        buttons.append([
            InlineKeyboardButton(
                f"▶ Continue #{i+1} ({label})",
                callback_data=f"heartbeat:resume:{item['history_id']}"
            ),
            InlineKeyboardButton("✕ Dismiss", callback_data=f"heartbeat:dismiss:{item['history_id']}")
        ])

    buttons.append([InlineKeyboardButton("🔕 Snooze", callback_data="heartbeat:snooze")])

    text = "\n".join(lines)
    markup = InlineKeyboardMarkup(buttons)

    # Send to all allowed users
    for uid in ALLOWED_USER_IDS:
        try:
            await _st.telegram_app.bot.send_message(
                chat_id=uid,
                text=text,
                parse_mode="Markdown",
                reply_markup=markup,
            )
        except Exception as exc:
            logger.warning("Heartbeat: could not notify user %s: %s", uid, exc)


async def _notify_telegram_idle():
    """No pending tasks found — send a friendly check-in to the user."""
    if not _st.telegram_app:
        return

    from helm.config import ALLOWED_USER_IDS
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    text = (
        "🫀 **Heartbeat Check-in**\n\n"
        "All clear! I didn't find any pending tasks from your recent sessions.\n\n"
        "Need anything? Just send me a message or tap below to start a new session."
    )
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("💬 Start a session", callback_data="action:menu"),
        InlineKeyboardButton("🔕 Snooze", callback_data="heartbeat:snooze"),
    ]])

    for uid in ALLOWED_USER_IDS:
        try:
            await _st.telegram_app.bot.send_message(
                chat_id=uid,
                text=text,
                parse_mode="Markdown",
                reply_markup=markup,
            )
        except Exception as exc:
            logger.warning("Heartbeat idle: could not notify user %s: %s", uid, exc)


# ---------------------------------------------------------------------------
# Heartbeat callback handler (for inline buttons)
# ---------------------------------------------------------------------------

async def heartbeat_callback(update, context):
    """Handle heartbeat inline button presses."""
    query = update.callback_query
    data = query.data  # "heartbeat:resume:XXXX" or "heartbeat:dismiss:XXXX" or "heartbeat:snooze"

    parts = data.split(":", 2)
    action = parts[1] if len(parts) > 1 else ""
    payload = parts[2] if len(parts) > 2 else ""

    if action == "snooze":
        # Snooze indefinitely until user sends Continue/Dismiss or disables heartbeat
        _st._heartbeat_snoozed = True
        await query.answer("Snoozed ✓")
        await query.edit_message_text(
            "🔕 Heartbeat snoozed. I won't check in again until you "
            "continue a task, dismiss, or re-enable from Settings."
        )
        return

    if action == "dismiss":
        # Clear snooze so heartbeat resumes on next interval
        _st._heartbeat_snoozed = False
        await query.answer("Dismissed ✓")
        await query.edit_message_text("✓ Dismissed. Heartbeat will check in again next cycle.")
        return

    if action == "resume":
        # Clear snooze and resume the session from history
        _st._heartbeat_snoozed = False
        from helm.telegram_bot import perform_resume
        await query.answer("Resuming…")
        await perform_resume(payload, update, context)
        return

    await query.answer()


# ---------------------------------------------------------------------------
# Persistent last-heartbeat timestamp — survives restarts
# ---------------------------------------------------------------------------

_HEARTBEAT_TS_FILE = _udd() / ".heartbeat_last"


def _load_last_heartbeat() -> float:
    """Load the last heartbeat timestamp from disk (0.0 if missing/corrupt)."""
    try:
        return float(_HEARTBEAT_TS_FILE.read_text().strip())
    except Exception:
        return 0.0


def _save_last_heartbeat(ts: float):
    """Persist the last heartbeat timestamp to disk."""
    try:
        _HEARTBEAT_TS_FILE.write_text(str(ts))
    except Exception as exc:
        logger.warning("Heartbeat: could not save timestamp: %s", exc)


# ---------------------------------------------------------------------------
# Main heartbeat runner — launched as asyncio.create_task at startup
# ---------------------------------------------------------------------------

_last_heartbeat: float = 0.0

async def heartbeat_runner():
    """Background loop: sleep for HEARTBEAT_INTERVAL, then scan and notify."""
    global _last_heartbeat

    # Restore last heartbeat timestamp from disk so we don't fire
    # immediately after every restart.
    _last_heartbeat = _load_last_heartbeat()

    # Wait 60s after startup before first check
    await asyncio.sleep(60)
    logger.info("Heartbeat runner started (interval=%ss, last_heartbeat=%.0f)", _interval(), _last_heartbeat)

    while True:
        try:
            if not _enabled():
                await asyncio.sleep(300)  # check again in 5 min
                continue

            interval = _interval()

            # Check if snoozed (indefinite until user interacts)
            if getattr(_st, "_heartbeat_snoozed", False):
                await asyncio.sleep(60)
                continue

            # Sleep for the configured interval
            elapsed = time.time() - _last_heartbeat
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)

            _last_heartbeat = time.time()
            _save_last_heartbeat(_last_heartbeat)

            # Skip if user is currently active (any session busy or used recently)
            active = any(
                s.get("busy") or (time.time() - (s.get("last_used") or 0) < interval * 0.5)
                for s in _st.sessions.values()
                if s.get("status") != "stopped"
            )
            if active:
                logger.info("Heartbeat: user is active — staying silent.")
                continue

            logger.info("Heartbeat: scanning for pending tasks…")

            # Scan history
            pending = await asyncio.to_thread(scan_pending_tasks)

            if pending:
                logger.info("Heartbeat: found %d pending item(s), notifying user.", len(pending))
                await _notify_telegram(pending)
            else:
                logger.info("Heartbeat: no pending items. Sending greeting.")
                await _notify_telegram_idle()

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Heartbeat runner error: %s", exc)
            await asyncio.sleep(60)
