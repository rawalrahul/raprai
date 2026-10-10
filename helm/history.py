"""
helm/history.py — SQLite-backed chat history: read, write, cache, search.

All history is stored in helmhq.db in the `messages` and `chat_names` tables.

The `history_id` is a stable hash of the normalised CWD path:
    history_id = "p_" + md5(normalized_path)[:12]

Legacy JSONL data is auto-imported by helm/db.py on first startup.
"""

import json
import pathlib
import re
import time
from datetime import datetime
from typing import Optional

import helm.state as _st
from helm.config import (
    CHAT_LOG_DIR,
    HISTORY_ID_RE,
    logger,
)


# ---------------------------------------------------------------------------
# Path → stable ID
# ---------------------------------------------------------------------------

def path_to_id(path: str) -> str:
    """Generate a stable unique ID for a file path (normalised, lowercase)."""
    import hashlib
    norm = str(pathlib.Path(path).expanduser().resolve()).lower().replace("\\", "/")
    return "p_" + hashlib.md5(norm.encode("utf-8")).hexdigest()[:12]


# Legacy alias used throughout the codebase
_path_to_id = path_to_id


# ---------------------------------------------------------------------------
# Chat names
# ---------------------------------------------------------------------------

def load_chat_names() -> dict:
    """Load all chat names → {history_id: display_name}."""
    from helm.db import get_db
    try:
        rows = get_db().execute("SELECT history_id, name FROM chat_names").fetchall()
        return {row["history_id"]: row["name"] for row in rows}
    except Exception:
        return {}


_load_chat_names = load_chat_names  # legacy alias


def save_chat_name(date: str, name: str) -> None:
    """Persist (or clear) a custom display name for a session history_id."""
    from helm.db import get_db
    db = get_db()
    name = name.strip()
    if name:
        db.execute(
            "INSERT OR REPLACE INTO chat_names (history_id, name, updated_at) "
            "VALUES (?, ?, datetime('now'))",
            (date, name),
        )
    else:
        db.execute("DELETE FROM chat_names WHERE history_id = ?", (date,))
    db.commit()


_save_chat_name = save_chat_name  # legacy alias


def get_session_display_name(date_str: str) -> str:
    """Return the best human-readable name for a session history_id.

    Priority:
      1. Custom / auto-saved folder name from chat_names table
      2. Folder name extracted from the first CWD record in messages
      3. The raw history_id as a last resort
    """
    from helm.db import get_db
    db = get_db()

    # 1. Check chat_names
    row = db.execute(
        "SELECT name FROM chat_names WHERE history_id = ?", (date_str,)
    ).fetchone()
    if row and row["name"]:
        return row["name"]

    # 2. Check first CWD record in messages
    row = db.execute(
        "SELECT path FROM messages WHERE history_id = ? AND type = 'cwd' AND path IS NOT NULL LIMIT 1",
        (date_str,),
    ).fetchone()
    if row and row["path"]:
        folder = pathlib.Path(row["path"]).name or ""
        if folder and folder not in (".", "~", "/"):
            return folder

    return date_str


_get_session_display_name = get_session_display_name  # legacy alias


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def ts() -> str:
    return datetime.now().isoformat()


_ts = ts  # legacy alias


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def is_valid_history_id(hid: str) -> bool:
    """Accept YYYY-MM-DD or p_[hash] keys."""
    return bool(HISTORY_ID_RE.fullmatch(hid))


_is_valid_history_id = is_valid_history_id  # legacy alias


# ---------------------------------------------------------------------------
# Read history
# ---------------------------------------------------------------------------

def get_history_messages(hid: str) -> list[dict]:
    """Retrieve all messages from the database by history_id."""
    from helm.db import get_db
    db = get_db()
    rows = db.execute(
        "SELECT * FROM messages WHERE history_id = ? AND type = 'message' ORDER BY id",
        (hid,),
    ).fetchall()

    messages = []
    for row in rows:
        msg = {
            "type": "message",
            "role": row["role"],
            "content": row["content"],
            "ai": row["ai"],
            "session_id": row["session_id"],
            "session_name": row["session_name"],
            "session_emoji": row["session_emoji"],
            "timestamp": row["timestamp"],
            "ts": row["ts"],
        }
        # Merge any extra fields
        if row["extra"]:
            try:
                extra = json.loads(row["extra"])
                msg.update(extra)
            except Exception:
                pass
        # Remove None values to match legacy format
        msg = {k: v for k, v in msg.items() if v is not None}
        messages.append(msg)

    return messages


_get_history_messages = get_history_messages  # legacy alias


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def _resolve_session_cwd(session_id: Optional[str]) -> str:
    """Look up the CWD for a session, falling back to the deleted-session cache."""
    from helm.config import _DEFAULT_CWD
    if session_id:
        # 1. Live session
        if session_id in _st.sessions:
            return _st.sessions[session_id].get("cwd") or _DEFAULT_CWD
        # 2. Recently deleted session — still know its CWD
        if session_id in _st.deleted_session_cwds:
            return _st.deleted_session_cwds[session_id]
    return _DEFAULT_CWD


def save_message_to_log(msg: dict, session_id: Optional[str] = None):
    """Insert a message into the SQLite database."""
    from helm.db import get_db
    try:
        cwd = _resolve_session_cwd(session_id)
        history_id = path_to_id(cwd)

        # Separate known fields from extra
        known_keys = {"type", "role", "content", "ai", "session_id",
                      "session_name", "session_emoji", "timestamp", "ts"}
        extra = {k: v for k, v in msg.items() if k not in known_keys}

        db = get_db()
        db.execute(
            """INSERT INTO messages
               (history_id, type, role, content, ai, session_id,
                session_name, session_emoji, timestamp, ts, extra)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                history_id,
                msg.get("type", "message"),
                msg.get("role"),
                msg.get("content"),
                msg.get("ai"),
                msg.get("session_id") or session_id,
                msg.get("session_name"),
                msg.get("session_emoji"),
                msg.get("timestamp") or ts(),
                msg.get("ts"),
                json.dumps(extra, ensure_ascii=False) if extra else None,
            ),
        )
        db.commit()
    except Exception as e:
        logger.warning("Could not save message to DB: %s", e)


_save_message_to_log = save_message_to_log  # legacy alias


def save_cwd_to_log(path: str, session_id: Optional[str] = None):
    """Persist the current working directory as a record in the database.

    Also auto-names the session after the folder if no name has been set yet.

    The record is only written when a real session is active for this path.
    This prevents orphan history entries created by folder browsing without
    an active session.
    """
    from helm.db import get_db
    try:
        history_id = path_to_id(path)
        # Only write the record when a live session is tracking this path.
        if session_id and session_id in _st.sessions:
            db = get_db()
            db.execute(
                """INSERT INTO messages
                   (history_id, type, path, timestamp)
                   VALUES (?, 'cwd', ?, ?)""",
                (history_id, path, ts()),
            )
            db.commit()

        # Always update the display name for this path (pre-populates it for later).
        existing = load_chat_names()
        if not existing.get(history_id):
            folder_name = pathlib.Path(path).name or path
            if folder_name and folder_name not in (".", "~", "/"):
                save_chat_name(history_id, folder_name)
    except Exception as e:
        logger.warning("Could not save CWD to DB: %s", e)


_save_cwd_to_log = save_cwd_to_log  # legacy alias


def save_ai_to_log(model: Optional[str], session_id: Optional[str] = None):
    """Persist the active AI model as a record in the database."""
    from helm.db import get_db
    try:
        cwd = _resolve_session_cwd(session_id)
        history_id = path_to_id(cwd)
        db = get_db()
        db.execute(
            """INSERT INTO messages
               (history_id, type, model, timestamp)
               VALUES (?, 'ai', ?, ?)""",
            (history_id, model, ts()),
        )
        db.commit()
    except Exception as e:
        logger.warning("Could not save AI to DB: %s", e)


_save_ai_to_log = save_ai_to_log  # legacy alias


def _unsaved(obj):
    """json.dumps fallback: values that can't be saved (locks, tasks) are stored as null."""
    return None


def save_last_state():
    """Persist all session state to the database for resume fallback."""
    from helm.db import get_db
    try:
        sessions_data = {}
        volatile_keys = {"terminal", "session_started", "total_task_seconds",
                         "task_count", "changes"}
        for sid, sess in _st.sessions.items():
            # Keys starting with "_" are runtime-only (e.g. "_lock", an asyncio.Lock).
            sessions_data[sid] = {k: v for k, v in sess.items()
                                  if k not in volatile_keys and not k.startswith("_")}

        db = get_db()
        state = {
            "sessions": sessions_data,
            "focused_id": _st.focused_id,
            "counter": _st.session_counter,
            "timestamp": ts(),
        }
        for key, value in state.items():
            db.execute(
                "INSERT OR REPLACE INTO session_state (key, value, updated_at) "
                "VALUES (?, ?, datetime('now'))",
                (key, json.dumps(value, ensure_ascii=False, default=_unsaved)),
            )
        db.commit()
    except Exception as e:
        logger.warning("Could not save last state: %s", e)


_save_last_state = save_last_state  # legacy alias


# ---------------------------------------------------------------------------
# History cache — fast query from SQLite
# ---------------------------------------------------------------------------

def scan_log_fast(history_id_or_path) -> dict:
    """Query metadata for a single history_id from the database.

    Accepts either a history_id string or a pathlib.Path (for backward compat
    with code that passed a log file path — we extract the stem).
    """
    if isinstance(history_id_or_path, pathlib.Path):
        history_id = history_id_or_path.stem
    else:
        history_id = str(history_id_or_path)

    from helm.db import get_db
    db = get_db()

    try:
        # Count messages
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE history_id = ? AND type = 'message'",
            (history_id,),
        ).fetchone()
        count = row["cnt"] if row else 0

        # Get first CWD
        cwd_row = db.execute(
            "SELECT path FROM messages WHERE history_id = ? AND type = 'cwd' AND path IS NOT NULL LIMIT 1",
            (history_id,),
        ).fetchone()
        first_cwd = ""
        if cwd_row and cwd_row["path"]:
            folder = pathlib.Path(cwd_row["path"]).name or ""
            if folder and folder not in (".", "~", "/"):
                first_cwd = folder

        # Get latest assistant message info (preview, ai, ts)
        last_row = db.execute(
            """SELECT content, ai, ts FROM messages
               WHERE history_id = ? AND type = 'message' AND role = 'assistant'
               ORDER BY id DESC LIMIT 1""",
            (history_id,),
        ).fetchone()

        preview = ""
        last_ai = ""
        last_ts = None

        if last_row:
            if last_row["content"]:
                preview = last_row["content"][:100].replace("\n", " ")
            last_ai = last_row["ai"] or ""
            last_ts = last_row["ts"]

        # If no assistant message, get any last AI
        if not last_ai:
            ai_row = db.execute(
                """SELECT ai FROM messages
                   WHERE history_id = ? AND type = 'message' AND ai IS NOT NULL
                   ORDER BY id DESC LIMIT 1""",
                (history_id,),
            ).fetchone()
            if ai_row:
                last_ai = ai_row["ai"] or ""

        return {
            "date": history_id,
            "count": count,
            "name": "",
            "preview": preview,
            "ai": last_ai,
            "ts": last_ts,
            "default_name": first_cwd,
        }
    except Exception:
        return {
            "date": history_id, "count": 0, "name": "", "preview": "",
            "ai": "", "ts": None, "default_name": "",
        }


_scan_log_fast = scan_log_fast  # legacy alias


def migrate_history_to_paths():
    """Legacy stub — migration is now handled by db._import_legacy_data()."""
    pass


_migrate_history_to_paths = migrate_history_to_paths  # legacy alias


def rebuild_hist_cache_sync() -> list:
    """Rebuild the history cache from SQLite."""
    from helm.db import get_db
    db = get_db()

    try:
        # Get all unique history_ids that have messages
        rows = db.execute(
            """SELECT DISTINCT history_id FROM messages
               WHERE type = 'message'
               ORDER BY id DESC"""
        ).fetchall()

        history_ids = [row["history_id"] for row in rows]
        sessions = [scan_log_fast(hid) for hid in history_ids]

        # Sort by latest message ts (or count as fallback)
        sessions.sort(key=lambda s: s.get("ts") or 0, reverse=True)

        names = load_chat_names()
        for s in sessions:
            s["name"] = names.get(s["date"], "") or s.pop("default_name", "")

        _st.hist_cache = sessions
        _st.hist_cache_ts = time.time()
        return sessions

    except Exception as e:
        logger.warning("Failed to rebuild history cache: %s", e)
        _st.hist_cache = []
        _st.hist_cache_ts = time.time()
        return []


_rebuild_hist_cache_sync = rebuild_hist_cache_sync  # legacy alias
