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
    Version 3: Add tables for HelmPack marketplace package tracking.

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


MIGRATIONS: list[tuple[int, str, callable]] = [
    (1, "Initial schema", v1_initial),
    (2, "Add FTS5 full-text search", v2_add_content_fts),
    (3, "Add HelmPack package tracking", v3_add_helmpack_tables),
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
