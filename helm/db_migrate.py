"""
helm/db_migrate.py — Schema versioning and migration runner.

Each migration is a function that takes a sqlite3.Connection and applies
schema changes.  Migrations are applied in order and tracked in the
schema_version table so they only run once.

To add a new migration:
  1. Write a function: def v2_description(conn): ...
  2. Append it to the MIGRATIONS list
  3. That's it — next startup will auto-apply it
"""

import sqlite3

from helm.config import logger
from helm.db import get_schema_version, set_schema_version


# ---------------------------------------------------------------------------
# Migration functions (applied in order, once each)
# ---------------------------------------------------------------------------

def v1_initial(conn: sqlite3.Connection):
    """
    Version 1: Initial schema.

    Tables are already created by db._SCHEMA_SQL, so this migration
    just records that we're at version 1.  Future migrations will
    ALTER TABLE, add indexes, etc.
    """
    # Nothing to do — tables already created by init_db()
    pass


def v2_add_content_fts(conn: sqlite3.Connection):
    """
    Version 2: Add a full-text search virtual table for message content.

    This makes history search fast even with millions of messages.
    Uses FTS5 (available in Python 3.10+ sqlite3 module).
    """
    try:
        conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                history_id,
                content='messages',
                content_rowid='id'
            );

            -- Triggers to keep FTS in sync with messages table
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages
            WHEN NEW.type = 'message' AND NEW.content IS NOT NULL
            BEGIN
                INSERT INTO messages_fts(rowid, content, history_id)
                VALUES (NEW.id, NEW.content, NEW.history_id);
            END;

            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages
            WHEN OLD.type = 'message' AND OLD.content IS NOT NULL
            BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content, history_id)
                VALUES ('delete', OLD.id, OLD.content, OLD.history_id);
            END;

            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages
            WHEN NEW.type = 'message' AND NEW.content IS NOT NULL
            BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content, history_id)
                VALUES ('delete', OLD.id, OLD.content, OLD.history_id);
                INSERT INTO messages_fts(rowid, content, history_id)
                VALUES (NEW.id, NEW.content, NEW.history_id);
            END;
        """)

        # Populate FTS with existing data
        conn.execute("""
            INSERT INTO messages_fts(rowid, content, history_id)
            SELECT id, content, history_id FROM messages
            WHERE type = 'message' AND content IS NOT NULL
        """)
        conn.commit()
    except Exception as e:
        # FTS5 may not be available on all builds — degrade gracefully
        logger.warning("FTS5 not available, search will use LIKE fallback: %s", e)
        conn.rollback()


# ---------------------------------------------------------------------------
# Migration registry (append new migrations here)
# ---------------------------------------------------------------------------

def v3_add_helmpack_tables(conn: sqlite3.Connection):
    """
    Version 3: Add tables for RAPR Packages marketplace package tracking.

    - packages: installed package metadata
    - package_installs: transaction log for install/uninstall operations
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS packages (
            id TEXT NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            author TEXT DEFAULT '',
            version TEXT NOT NULL,
            installed_at TEXT NOT NULL DEFAULT (datetime('now')),
            source_url TEXT DEFAULT '',
            install_path TEXT DEFAULT '',
            manifest_hash TEXT DEFAULT '',
            package_hash TEXT DEFAULT '',
            PRIMARY KEY (id, type)
        );

        CREATE TABLE IF NOT EXISTS package_installs (
            transaction_id TEXT PRIMARY KEY,
            package_id TEXT NOT NULL,
            package_type TEXT NOT NULL,
            operation TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            error_message TEXT,
            previous_state TEXT
        );
    """)
    conn.commit()


def v4_add_memories_table(conn: sqlite3.Connection):
    """
    Version 4: Add shared AI memory table.

    Stores cross-session, cross-AI knowledge (facts, preferences, decisions)
    that gets injected into every AI session for continuity.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content    TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT 'fact',
            source_ai  TEXT DEFAULT '',
            session_id TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_used  TEXT,
            use_count  INTEGER NOT NULL DEFAULT 0,
            pinned     INTEGER NOT NULL DEFAULT 0,
            archived   INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived);
    """)
    conn.commit()


def v5_add_cloud_backup_tables(conn: sqlite3.Connection):
    """Version 5: Add cloud backup configuration and job history tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cloud_backup_config (
            provider      TEXT PRIMARY KEY,
            enabled       INTEGER NOT NULL DEFAULT 0,
            frequency     TEXT NOT NULL DEFAULT 'daily',
            scheduled_hour INTEGER DEFAULT 2,
            scheduled_weekday INTEGER DEFAULT 0,
            remote_folder TEXT DEFAULT '',
            last_backup_at TEXT,
            next_backup_at TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cloud_backup_jobs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            provider      TEXT NOT NULL,
            job_type      TEXT NOT NULL DEFAULT 'manual',
            status        TEXT NOT NULL DEFAULT 'pending',
            started_at    TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at  TEXT,
            error_message TEXT,
            backup_size   INTEGER,
            remote_id     TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_backup_jobs_provider
            ON cloud_backup_jobs(provider);
        CREATE INDEX IF NOT EXISTS idx_backup_jobs_status
            ON cloud_backup_jobs(status);
    """)
    conn.commit()


def v6_add_summaries_and_decay(conn: sqlite3.Connection):
    """
    Version 6: Conversation summaries persistence + memory decay score.

    - conversation_summaries: stores compaction summaries per session for
      richer session resume (instead of raw last-10 messages).
    - memories.decay_score: 0.0–1.0 float that decreases over time for
      unaccessed memories, used in relevance ranking.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            history_id  TEXT NOT NULL,
            summary     TEXT NOT NULL,
            token_count INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_convsumm_history
            ON conversation_summaries(history_id);
    """)

    # Add decay_score column to memories (default 1.0 = fully fresh)
    try:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN decay_score REAL NOT NULL DEFAULT 1.0"
        )
    except Exception:
        pass  # Column already exists

    conn.commit()


def v7_add_cost_usd(conn: sqlite3.Connection):
    """Add cost_usd column to usage_stats for dollar-based budget tracking."""
    try:
        conn.execute(
            "ALTER TABLE usage_stats ADD COLUMN cost_usd REAL NOT NULL DEFAULT 0.0"
        )
    except Exception:
        pass  # Column already exists
    conn.commit()


def v8_encrypt_memory_content(conn: sqlite3.Connection):
    """
    Version 8: Encrypt memory content at rest + add search_text column.

    Encrypts the ``content`` column of every existing memory using the
    token-vault Fernet key.  A new ``search_text`` column stores
    lowercased keywords (category + source_ai + first significant words)
    so keyword search still works without decrypting every row.
    """
    # 1. Add search_text column (idempotent)
    try:
        conn.execute(
            "ALTER TABLE memories ADD COLUMN search_text TEXT NOT NULL DEFAULT ''"
        )
    except Exception:
        pass  # Column already exists

    # 2. Batch-encrypt existing memory content
    try:
        from helm.token_vault import encrypt_value, _fernet
        f = _fernet()
        if not f:
            logger.warning("v8: cryptography not installed — skipping content encryption")
            # Still populate search_text even without encryption
            rows = conn.execute("SELECT id, content, category, source_ai FROM memories").fetchall()
            for row in rows:
                mid, content, category, source_ai = row["id"], row["content"], row["category"], row["source_ai"] or ""
                search_text = _build_search_text(content, category, source_ai)
                conn.execute(
                    "UPDATE memories SET search_text = ? WHERE id = ?",
                    (search_text, mid),
                )
            conn.commit()
            return

        rows = conn.execute("SELECT id, content, category, source_ai FROM memories").fetchall()
        encrypted_count = 0
        for row in rows:
            mid, content, category, source_ai = row["id"], row["content"], row["category"], row["source_ai"] or ""
            # Build search_text from plaintext BEFORE encrypting
            search_text = _build_search_text(content, category, source_ai)
            # Encrypt content
            cipher = encrypt_value(content)
            conn.execute(
                "UPDATE memories SET content = ?, search_text = ? WHERE id = ?",
                (cipher, search_text, mid),
            )
            encrypted_count += 1

        conn.commit()
        if encrypted_count:
            logger.info("v8: encrypted %d memory content entries", encrypted_count)
    except Exception as exc:
        logger.error("v8: memory encryption failed: %s", exc)
        conn.rollback()


def _build_search_text(content: str, category: str, source_ai: str) -> str:
    """Build a lowercase keyword string for search without exposing full content."""
    import re
    words = re.findall(r"[a-z0-9]+", content.lower())
    # Keep first 15 significant words (skip very short ones)
    significant = [w for w in words if len(w) > 2][:15]
    parts = [category.lower(), source_ai.lower()] + significant
    return " ".join(parts)


def v9_add_packages_keywords(conn: sqlite3.Connection):
    """Version 9: Add keywords and updated_at columns to packages table."""
    for col, defn in [
        ("keywords", "TEXT DEFAULT '[]'"),
        ("updated_at", "REAL DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE packages ADD COLUMN {col} {defn}")
        except Exception:
            pass  # Column already exists
    conn.commit()


def v10_add_agent_tables(conn: sqlite3.Connection):
    """
    Version 10: Add agents and agent_runs tables for the Agent workflow system.

    - agents: saved agent definitions (node graphs + triggers)
    - agent_runs: execution history for each agent
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT,
            graph_json  TEXT NOT NULL,
            created_at  REAL NOT NULL,
            updated_at  REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id           TEXT PRIMARY KEY,
            agent_id     TEXT NOT NULL,
            status       TEXT NOT NULL,
            trigger      TEXT NOT NULL,
            result_json  TEXT,
            started_at   REAL NOT NULL,
            completed_at REAL
        );

        CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id
            ON agent_runs(agent_id);
        CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at
            ON agent_runs(started_at);
    """)
    conn.commit()


def v11_add_agent_versions(conn: sqlite3.Connection):
    """Version 11: Agent version history — snapshot on every save, keep last 10."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_versions (
            id          TEXT PRIMARY KEY,
            agent_id    TEXT NOT NULL,
            version_num INTEGER NOT NULL,
            graph_json  TEXT NOT NULL,
            saved_at    REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_agent_versions_agent_id
            ON agent_versions(agent_id);
    """)
    conn.commit()


MIGRATIONS: list[tuple[int, str, callable]] = [
    (1, "Initial schema", v1_initial),
    (2, "Add FTS5 full-text search", v2_add_content_fts),
    (3, "Add RAPR Packages tracking", v3_add_helmpack_tables),
    (4, "Add shared AI memory", v4_add_memories_table),
    (5, "Add cloud backup", v5_add_cloud_backup_tables),
    (6, "Add summaries + memory decay", v6_add_summaries_and_decay),
    (7, "Add dollar cost tracking to usage_stats", v7_add_cost_usd),
    (8, "Encrypt memory content at rest", v8_encrypt_memory_content),
    (9, "Add keywords/updated_at to packages", v9_add_packages_keywords),
    (10, "Add agents + agent_runs tables", v10_add_agent_tables),
    (11, "Add agent version history", v11_add_agent_versions),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_migrations(conn: sqlite3.Connection):
    """
    Check current schema version and apply any pending migrations.

    Each migration runs in its own transaction.  If a migration fails,
    only that migration is rolled back — earlier ones are preserved.
    """
    current = get_schema_version(conn)
    pending = [(v, desc, fn) for v, desc, fn in MIGRATIONS if v > current]

    if not pending:
        return

    logger.info(
        "Database at version %d — applying %d migration(s)...",
        current, len(pending),
    )

    for version, description, migrate_fn in pending:
        try:
            logger.info("  Migration v%d: %s", version, description)
            migrate_fn(conn)
            set_schema_version(conn, version)
            logger.info("  Migration v%d: OK", version)
        except Exception as e:
            logger.error("  Migration v%d FAILED: %s", version, e)
            # Don't abort — try remaining migrations
            # (some may be independent)
            break

    final = get_schema_version(conn)
    logger.info("Database now at version %d", final)
