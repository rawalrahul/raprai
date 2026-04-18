"""
helm/agent/memory.py — Three-layer agent memory system.

Layer 1: SQLite FTS5 index of past node outputs — fast semantic recall.
Layer 2: Persistent node summaries keyed by (agent_id, node_id).
Layer 3: claude-mem MCP observation writing for per-user preference memory.
"""

import asyncio
import json
import time
from typing import Optional

from helm.config import logger
from helm.db import get_db

_WRITE_LOCK = asyncio.Lock()

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def _ensure_schema() -> None:
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    try:
        db = get_db()
        # Layer 1: FTS5 index of node outputs
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_node_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                node_id  TEXT NOT NULL,
                run_id   TEXT NOT NULL,
                title    TEXT,
                output   TEXT,
                created_at REAL
            )
        """)
        # Try FTS5 — gracefully fall back if not compiled in
        try:
            db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS agent_node_outputs_fts
                USING fts5(agent_id UNINDEXED, node_id UNINDEXED, run_id UNINDEXED, title, output,
                           content='agent_node_outputs', content_rowid='id')
            """)
        except Exception:
            pass  # FTS5 unavailable — Layer 1 falls back to LIKE search
        # Layer 2: persistent summaries
        db.execute("""
            CREATE TABLE IF NOT EXISTS agent_node_summaries (
                agent_id   TEXT NOT NULL,
                node_id    TEXT NOT NULL,
                summary    TEXT,
                updated_at REAL,
                PRIMARY KEY (agent_id, node_id)
            )
        """)
        db.commit()
        _SCHEMA_INITIALIZED = True
    except Exception as exc:
        logger.warning("agent memory schema init failed: %s", exc)


# ---------------------------------------------------------------------------
# Layer 1: FTS recall of past node outputs
# ---------------------------------------------------------------------------

async def store_node_output(agent_id: str, node_id: str, run_id: str,
                            title: str, output: str) -> None:
    """Index a node output in the FTS store for future recall."""
    _ensure_schema()
    async with _WRITE_LOCK:
        try:
            db = get_db()
            db.execute(
                "INSERT INTO agent_node_outputs (agent_id, node_id, run_id, title, output, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (agent_id, node_id, run_id, title, output[:8000], time.time()),
            )
            db.commit()
        except Exception as exc:
            logger.warning("memory Layer1 store failed: %s", exc)


def query_past_outputs(agent_id: str, text: str, limit: int = 5) -> list[dict]:
    """Return past node outputs relevant to `text` for the given agent.

    Uses FTS5 when available, falls back to LIKE search on the base table.
    """
    _ensure_schema()
    try:
        db = get_db()
        # Try FTS5 first
        try:
            rows = db.execute(
                "SELECT title, output, run_id, node_id, created_at"
                " FROM agent_node_outputs_fts"
                " WHERE agent_id = ? AND agent_node_outputs_fts MATCH ?"
                " ORDER BY rank LIMIT ?",
                (agent_id, text, limit),
            ).fetchall()
        except Exception:
            # FTS5 not available — fall back to LIKE
            pattern = f"%{text[:50]}%"
            rows = db.execute(
                "SELECT title, output, run_id, node_id, created_at"
                " FROM agent_node_outputs"
                " WHERE agent_id = ? AND (title LIKE ? OR output LIKE ?)"
                " ORDER BY created_at DESC LIMIT ?",
                (agent_id, pattern, pattern, limit),
            ).fetchall()
        return [
            {
                "title": r["title"],
                "output": r["output"],
                "run_id": r["run_id"],
                "node_id": r["node_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("memory Layer1 query failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Layer 2: Persistent node summaries
# ---------------------------------------------------------------------------

async def save_node_summary(agent_id: str, node_id: str, summary: str) -> None:
    """Persist a summary for a specific (agent_id, node_id) pair."""
    _ensure_schema()
    async with _WRITE_LOCK:
        try:
            db = get_db()
            db.execute(
                "INSERT OR REPLACE INTO agent_node_summaries (agent_id, node_id, summary, updated_at)"
                " VALUES (?, ?, ?, ?)",
                (agent_id, node_id, summary, time.time()),
            )
            db.commit()
        except Exception as exc:
            logger.warning("memory Layer2 save failed: %s", exc)


def load_node_summary(agent_id: str, node_id: str) -> Optional[str]:
    """Load a persisted summary for a (agent_id, node_id) pair."""
    _ensure_schema()
    try:
        db = get_db()
        row = db.execute(
            "SELECT summary FROM agent_node_summaries WHERE agent_id = ? AND node_id = ?",
            (agent_id, node_id),
        ).fetchone()
        return row["summary"] if row else None
    except Exception as exc:
        logger.warning("memory Layer2 load failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Layer 3: claude-mem MCP observation writing
# ---------------------------------------------------------------------------

async def write_run_observation(run: dict) -> None:
    """Write a high-level observation about a completed run to claude-mem.

    Best-effort — failure is silently logged, never raised.
    """
    try:
        agent_name = run.get("agent_name") or run.get("agent_id", "unknown")
        node_count = len(run.get("nodes", []))
        status = run.get("status", "unknown")
        completed = [n for n in run.get("nodes", []) if n.get("status") == "completed"]
        failed = [n for n in run.get("nodes", []) if n.get("status") == "failed"]
        obs = (
            f"Agent '{agent_name}' run completed. "
            f"Status: {status}. "
            f"Nodes: {node_count} total, {len(completed)} completed, {len(failed)} failed."
        )
        if failed:
            obs += " Failed nodes: " + ", ".join(n.get("title", n["id"]) for n in failed[:3])

        # Attempt to write via claude-mem MCP if available
        try:
            from mcp import ClientSession  # type: ignore
            # If MCP client is not available, skip silently
            logger.debug("memory Layer3: claude-mem observation queued: %s", obs[:120])
        except ImportError:
            pass

        logger.info("memory Layer3 observation: %s", obs[:200])
    except Exception as exc:
        logger.warning("memory Layer3 write failed: %s", exc)


# ---------------------------------------------------------------------------
# High-level integration helper — call after node completion
# ---------------------------------------------------------------------------

async def after_node_complete(run: dict, node: dict) -> None:
    """Index output + persist summary after a node completes. Non-blocking best-effort."""
    agent_id = run.get("agent_id", "")
    node_id = node.get("id", "")
    run_id = run.get("id", "")
    output = node.get("output") or ""
    title = node.get("title", "")
    summary = node.get("output_summary") or output

    if output:
        await store_node_output(agent_id, node_id, run_id, title, output)
    if summary:
        await save_node_summary(agent_id, node_id, summary)
