"""
helm/db.py — SQLite database core for RAPR AI.

Provides a single helmhq.db file for all persistent data (chat history,
scheduled tasks, auth sessions, usage stats, templates, generated files).

Features:
  - WAL mode for concurrent read/write
  - Thread-local connections (safe for FastAPI + background threads)
  - Schema versioning via db_migrate.py
  - Auto-migration from legacy JSONL files on first run

Public API:
    get_db()     → sqlite3.Connection (thread-local, auto-created)
    init_db()    → create tables + run migrations + import legacy data
    close_all()  → close all thread-local connections (call on shutdown)
"""

import json
import pathlib
import sqlite3
import threading
from typing import Optional

from helm.config import logger
from helm.paths import user_data_dir

# ---------------------------------------------------------------------------
# Database path
# ---------------------------------------------------------------------------

DB_NAME = "helmhq.db"


def db_path() -> pathlib.Path:
    """Return the absolute path to the SQLite database file."""
    return user_data_dir() / DB_NAME


# ---------------------------------------------------------------------------
# Thread-local connection pool
# ---------------------------------------------------------------------------

_local = threading.local()
_all_connections: list[sqlite3.Connection] = []
_all_connections_lock = threading.Lock()


def get_db() -> sqlite3.Connection:
    """
    Return a thread-local SQLite connection.

    Each thread gets its own connection (required by SQLite).
    Connections are configured for:
      - WAL journal mode (concurrent reads + writes)
      - NORMAL synchronous (fast + safe with WAL)
      - Foreign keys enabled
      - Row factory = sqlite3.Row (dict-like access)
    """
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn

    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Increase cache for better performance on larger databases
    conn.execute("PRAGMA cache_size=-8000")  # 8 MB

    _local.conn = conn
    with _all_connections_lock:
        _all_connections.append(conn)

    return conn


def close_all():
    """Close all thread-local connections. Call on app shutdown."""
    with _all_connections_lock:
        for conn in _all_connections:
            try:
                conn.close()
            except Exception:
                pass
        _all_connections.clear()
    _local.conn = None


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Chat messages (replaces JSONL files)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'message',
    role TEXT,
    content TEXT,
    ai TEXT,
    session_id TEXT,
    session_name TEXT,
    session_emoji TEXT,
    path TEXT,
    model TEXT,
    timestamp TEXT NOT NULL,
    ts REAL,
    extra TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_history_id ON messages(history_id);
CREATE INDEX IF NOT EXISTS idx_messages_hid_type ON messages(history_id, type);

-- Chat session names (replaces chat_names.json)
CREATE TABLE IF NOT EXISTS chat_names (
    history_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Session state snapshot (replaces last_state.json)
CREATE TABLE IF NOT EXISTS session_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Scheduled tasks (replaces scheduled_tasks.json)
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ai TEXT,
    cwd TEXT,
    prompt TEXT NOT NULL,
    cron TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    next_run REAL,
    last_run REAL,
    run_count INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL,
    extra TEXT
);

-- Session templates (replaces templates.json)
CREATE TABLE IF NOT EXISTS session_templates (
    name TEXT PRIMARY KEY,
    ai TEXT DEFAULT '',
    cwd TEXT DEFAULT '',
    model TEXT DEFAULT '',
    prompt TEXT DEFAULT '',
    timestamp TEXT,
    extra TEXT
);

-- Usage stats (previously in-memory only — now persisted)
CREATE TABLE IF NOT EXISTS usage_stats (
    ai_key TEXT PRIMARY KEY,
    tasks INTEGER NOT NULL DEFAULT 0,
    seconds REAL NOT NULL DEFAULT 0.0,
    chars_in INTEGER NOT NULL DEFAULT 0,
    chars_out INTEGER NOT NULL DEFAULT 0,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    tokens_source TEXT DEFAULT 'estimate',
    last_used REAL NOT NULL DEFAULT 0.0,
    period_start REAL NOT NULL
);

-- Auth sessions (previously in-memory only — now persisted)
CREATE TABLE IF NOT EXISTS auth_sessions (
    token TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);

-- Generated files log (previously in-memory only)
CREATE TABLE IF NOT EXISTS generated_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    ext TEXT,
    size INTEGER,
    ai TEXT,
    session_id TEXT,
    session_name TEXT,
    ts REAL NOT NULL
);

-- Pipeline templates (previously in-memory only)
CREATE TABLE IF NOT EXISTS pipeline_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    planner_ai TEXT DEFAULT '',
    steps_template TEXT,
    use_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    extra TEXT
);

-- Brute-force lockout attempts (persisted across restarts)
CREATE TABLE IF NOT EXISTS lockout_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    failed_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lockout_ip ON lockout_attempts(ip);

-- OAuth pending flows (persisted for resilience)
CREATE TABLE IF NOT EXISTS oauth_pending_flows (
    state TEXT PRIMARY KEY,
    flow_data TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


def _create_tables(conn: sqlite3.Connection):
    """Create all tables if they don't exist."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


# ---------------------------------------------------------------------------
# Schema version helpers
# ---------------------------------------------------------------------------

def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version (0 if no migrations have run)."""
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] or 0 if row else 0
    except sqlite3.OperationalError:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int):
    """Record that a migration version has been applied."""
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
        (version,),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Legacy data import (JSONL → SQLite)
# ---------------------------------------------------------------------------

def _import_legacy_data(conn: sqlite3.Connection):
    """
    One-time migration: import existing JSONL/JSON files into SQLite.

    Only runs when the messages table is empty (fresh DB or first upgrade).
    Renames chat_logs/ → chat_logs_backup/ after successful import.
    """
    from helm.config import CHAT_LOG_DIR

    # Check if we already have data
    row = conn.execute("SELECT COUNT(*) FROM messages").fetchone()
    if row and row[0] > 0:
        return  # Already imported

    if not CHAT_LOG_DIR.exists():
        return

    import re
    from helm.config import HISTORY_ID_RE

    imported_messages = 0
    imported_names = 0
    imported_tasks = 0
    imported_templates = 0

    # ---- 1. Import JSONL chat logs ----
    log_files = [
        f for f in CHAT_LOG_DIR.glob("*.jsonl")
        if HISTORY_ID_RE.fullmatch(f.stem)
    ]

    for log_file in log_files:
        history_id = log_file.stem
        try:
            for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue

                rec_type = rec.get("type", "message")
                timestamp = rec.get("timestamp") or rec.get("ts_str") or ""
                ts = rec.get("ts")

                if rec_type == "message":
                    conn.execute(
                        """INSERT INTO messages
                           (history_id, type, role, content, ai, session_id,
                            session_name, session_emoji, timestamp, ts, extra)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            history_id, "message",
                            rec.get("role"), rec.get("content"),
                            rec.get("ai"), rec.get("session_id"),
                            rec.get("session_name"), rec.get("session_emoji"),
                            timestamp, ts,
                            json.dumps({k: v for k, v in rec.items()
                                        if k not in ("type", "role", "content", "ai",
                                                     "session_id", "session_name",
                                                     "session_emoji", "timestamp", "ts")}
                                       ) if rec else None,
                        ),
                    )
                    imported_messages += 1

                elif rec_type == "cwd":
                    conn.execute(
                        """INSERT INTO messages
                           (history_id, type, path, timestamp, ts)
                           VALUES (?, 'cwd', ?, ?, ?)""",
                        (history_id, rec.get("path"), timestamp, ts),
                    )

                elif rec_type == "ai":
                    conn.execute(
                        """INSERT INTO messages
                           (history_id, type, model, timestamp, ts)
                           VALUES (?, 'ai', ?, ?, ?)""",
                        (history_id, rec.get("model"), timestamp, ts),
                    )

        except Exception as e:
            logger.warning("Failed to import log %s: %s", log_file.name, e)

    conn.commit()

    # ---- 2. Import chat_names.json ----
    names_file = CHAT_LOG_DIR / "chat_names.json"
    if names_file.exists():
        try:
            names = json.loads(names_file.read_text(encoding="utf-8"))
            for hid, name in names.items():
                if name and name.strip():
                    conn.execute(
                        "INSERT OR REPLACE INTO chat_names (history_id, name) VALUES (?, ?)",
                        (hid, name.strip()),
                    )
                    imported_names += 1
            conn.commit()
        except Exception as e:
            logger.warning("Failed to import chat_names.json: %s", e)

    # ---- 3. Import scheduled_tasks.json ----
    tasks_file = CHAT_LOG_DIR / "scheduled_tasks.json"
    if tasks_file.exists():
        try:
            data = json.loads(tasks_file.read_text(encoding="utf-8"))
            tasks = data.get("tasks", {})
            for tid, task in tasks.items():
                conn.execute(
                    """INSERT OR REPLACE INTO scheduled_tasks
                       (id, name, ai, cwd, prompt, cron, enabled, next_run,
                        last_run, run_count, created)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task.get("id", tid),
                        task.get("name", f"Task {tid}"),
                        task.get("ai"),
                        task.get("cwd"),
                        task.get("prompt", ""),
                        task.get("cron", ""),
                        1 if task.get("enabled", True) else 0,
                        task.get("next_run"),
                        task.get("last_run"),
                        task.get("run_count", 0),
                        task.get("created", 0),
                    ),
                )
                imported_tasks += 1
            conn.commit()
        except Exception as e:
            logger.warning("Failed to import scheduled_tasks.json: %s", e)

    # ---- 4. Import templates.json ----
    templates_file = CHAT_LOG_DIR / "templates.json"
    if templates_file.exists():
        try:
            templates = json.loads(templates_file.read_text(encoding="utf-8"))
            for name, tpl in templates.items():
                conn.execute(
                    """INSERT OR REPLACE INTO session_templates
                       (name, ai, cwd, model, prompt, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        name,
                        tpl.get("ai", ""),
                        tpl.get("cwd", ""),
                        tpl.get("model", ""),
                        tpl.get("prompt", ""),
                        tpl.get("timestamp", ""),
                    ),
                )
                imported_templates += 1
            conn.commit()
        except Exception as e:
            logger.warning("Failed to import templates.json: %s", e)

    # ---- 5. Import last_state.json ----
    state_file = CHAT_LOG_DIR / "last_state.json"
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            for key, value in state_data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO session_state (key, value) VALUES (?, ?)",
                    (key, json.dumps(value, ensure_ascii=False)),
                )
            conn.commit()
        except Exception as e:
            logger.warning("Failed to import last_state.json: %s", e)

    # ---- 6. Rename old chat_logs to backup ----
    if imported_messages > 0 or imported_names > 0:
        backup_dir = CHAT_LOG_DIR.parent / "chat_logs_backup"
        try:
            if not backup_dir.exists():
                CHAT_LOG_DIR.rename(backup_dir)
                logger.info(
                    "Legacy migration complete: %d messages, %d names, %d tasks, %d templates. "
                    "Old files moved to chat_logs_backup/",
                    imported_messages, imported_names, imported_tasks, imported_templates,
                )
            else:
                logger.info(
                    "Legacy migration complete: %d messages, %d names, %d tasks, %d templates. "
                    "chat_logs_backup/ already exists — old files kept in place.",
                    imported_messages, imported_names, imported_tasks, imported_templates,
                )
        except Exception as e:
            logger.warning("Could not rename chat_logs → chat_logs_backup: %s", e)
    else:
        logger.info("No legacy data found to import.")


# ---------------------------------------------------------------------------
# Initialization entry point
# ---------------------------------------------------------------------------

_init_done = False
_init_lock = threading.Lock()


def init_db():
    """
    Initialize the database: create tables, run migrations, import legacy data.

    Safe to call multiple times — only runs once per process.
    """
    global _init_done
    if _init_done:
        return

    with _init_lock:
        if _init_done:
            return

        conn = get_db()

        # Create tables
        _create_tables(conn)

        # Run schema migrations
        from helm.db_migrate import run_migrations
        run_migrations(conn)

        # Import legacy JSONL data if this is the first run
        try:
            _import_legacy_data(conn)
        except Exception as e:
            logger.error("Legacy data import failed: %s", e)

        # Clean up expired auth sessions
        import time
        conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (time.time(),))
        conn.commit()

        _init_done = True
        logger.info("Database initialized: %s", db_path())
