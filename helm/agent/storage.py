"""
helm/agent/storage.py — SQLite persistence for agents and agent runs.

Tables: agents, agent_runs  (added via db_migrate.py v10)

Public API:
  load_all_agents()          → populates _st.agents at startup
  save_agent(agent)          → upsert
  delete_agent(agent_id)
  save_run(run)              → upsert
  load_recent_runs(agent_id, limit=20) → list[dict]
"""

import asyncio
import json
import time

import helm.state as _st
from helm.config import logger
from helm.db import get_db

from .models import node_runtime_snapshot

# Module-level write lock — serialises all INSERT/UPDATE/DELETE calls so that
# concurrent async coroutines cannot interleave writes on the same connection.
_WRITE_LOCK = asyncio.Lock()


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

def load_all_agents() -> None:
    """Load all saved agents from DB into _st.agents."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT id, name, description, graph_json, created_at, updated_at "
            "FROM agents ORDER BY created_at"
        ).fetchall()
        for row in rows:
            agent = json.loads(row["graph_json"])
            # Ensure top-level scalars are in sync with DB columns
            agent["id"] = row["id"]
            agent["name"] = row["name"]
            agent["description"] = row["description"] or ""
            agent["created_at"] = row["created_at"]
            agent["updated_at"] = row["updated_at"]
            _st.agents[agent["id"]] = agent
        logger.info("Agents: loaded %d agent(s) from DB", len(_st.agents))
    except Exception as exc:
        logger.warning("Could not load agents from DB: %s", exc)


_NODE_SAVE_KEYS = (
    "id", "title", "task", "type", "ai", "children", "x", "y",
    "timeout", "http_method", "http_url", "http_headers", "http_body",
    "file_op", "file_path", "deliver_channel", "deliver_to",
    "deliver_subject", "input_timeout", "loop_max", "retry_max",
    "transform_op", "transform_key", "transform_pattern", "transform_length",
    "env_vars", "join_separator", "manager_max_iter", "manager_reset_vars",
    "condition_expr", "loop_input_key",
)
_MAX_VERSIONS = 10


def _strip_runtime(agent: dict) -> dict:
    """Return a copy of agent with only saveable fields in nodes."""
    saveable = dict(agent)
    saveable["nodes"] = [
        {k: v for k, v in n.items() if k in _NODE_SAVE_KEYS}
        for n in agent.get("nodes", [])
    ]
    return saveable


def save_agent(agent: dict) -> None:
    """Upsert an agent and snapshot a version row (keeping last 10)."""
    try:
        db = get_db()
        agent["updated_at"] = time.time()
        saveable = _strip_runtime(agent)
        graph_json = json.dumps(saveable, ensure_ascii=False)
        db.execute(
            """INSERT OR REPLACE INTO agents
               (id, name, description, graph_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                agent["id"],
                agent["name"],
                agent.get("description", ""),
                graph_json,
                agent.get("created_at", time.time()),
                agent["updated_at"],
            ),
        )
        # Version snapshot
        try:
            last = db.execute(
                "SELECT MAX(version_num) AS v FROM agent_versions WHERE agent_id = ?",
                (agent["id"],),
            ).fetchone()
            next_ver = (last["v"] or 0) + 1
            db.execute(
                """INSERT INTO agent_versions (id, agent_id, version_num, graph_json, saved_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    f"{agent['id']}_v{next_ver}",
                    agent["id"],
                    next_ver,
                    graph_json,
                    agent["updated_at"],
                ),
            )
            # Trim to last _MAX_VERSIONS
            old = db.execute(
                "SELECT id FROM agent_versions WHERE agent_id = ? "
                "ORDER BY version_num DESC LIMIT -1 OFFSET ?",
                (agent["id"], _MAX_VERSIONS),
            ).fetchall()
            for row in old:
                db.execute("DELETE FROM agent_versions WHERE id = ?", (row["id"],))
        except Exception as exc:
            logger.debug("Version snapshot skipped (table may not exist yet): %s", exc)
        db.commit()
    except Exception as exc:
        logger.warning("Could not save agent %s: %s", agent.get("id", "?"), exc)


def delete_agent(agent_id: str) -> None:
    """Delete an agent and its runs from the DB."""
    try:
        db = get_db()
        db.execute("DELETE FROM agent_runs WHERE agent_id = ?", (agent_id,))
        db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        db.commit()
    except Exception as exc:
        logger.warning("Could not delete agent %s: %s", agent_id, exc)


# ---------------------------------------------------------------------------
# Agent runs
# ---------------------------------------------------------------------------

async def save_run(run: dict) -> None:
    """Upsert a run into the agent_runs table (async, serialised by _WRITE_LOCK)."""
    async with _WRITE_LOCK:
        try:
            db = get_db()
            db.execute(
                """INSERT OR REPLACE INTO agent_runs
                   (id, agent_id, status, trigger, result_json, started_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run["id"],
                    run["agent_id"],
                    run["status"],
                    run["trigger"],
                    json.dumps(run, ensure_ascii=False),
                    run["started_at"],
                    run.get("completed_at"),
                ),
            )
            db.commit()
        except Exception as exc:
            logger.warning("Could not save agent run %s: %s", run.get("id", "?"), exc)


def load_recent_runs(agent_id: str, limit: int = 20) -> list[dict]:
    """Load the most recent runs for an agent from the DB."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT result_json FROM agent_runs "
            "WHERE agent_id = ? ORDER BY started_at DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        runs = []
        for row in rows:
            try:
                runs.append(json.loads(row["result_json"]))
            except Exception:
                pass
        return runs
    except Exception as exc:
        logger.warning("Could not load runs for agent %s: %s", agent_id, exc)
        return []


def load_run(run_id: str) -> dict | None:
    """Load a single run from the DB (used for completed runs evicted from memory)."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT result_json FROM agent_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if row:
            return json.loads(row["result_json"])
    except Exception as exc:
        logger.warning("Could not load run %s: %s", run_id, exc)
    return None


# ---------------------------------------------------------------------------
# Agent versions
# ---------------------------------------------------------------------------

def load_agent_versions(agent_id: str) -> list[dict]:
    """Return version list for an agent, newest first."""
    try:
        db = get_db()
        rows = db.execute(
            "SELECT id, version_num, saved_at FROM agent_versions "
            "WHERE agent_id = ? ORDER BY version_num DESC",
            (agent_id,),
        ).fetchall()
        return [{"id": r["id"], "version_num": r["version_num"], "saved_at": r["saved_at"]} for r in rows]
    except Exception as exc:
        logger.warning("Could not load versions for %s: %s", agent_id, exc)
        return []


def load_agent_version(version_id: str) -> dict | None:
    """Load a specific version's graph JSON."""
    try:
        db = get_db()
        row = db.execute(
            "SELECT graph_json FROM agent_versions WHERE id = ?", (version_id,)
        ).fetchone()
        if row:
            return json.loads(row["graph_json"])
    except Exception as exc:
        logger.warning("Could not load version %s: %s", version_id, exc)
    return None


# ---------------------------------------------------------------------------
# Monitoring stats
# ---------------------------------------------------------------------------

def load_all_run_stats() -> list[dict]:
    """Aggregate run stats per agent from DB (used by monitoring dashboard)."""
    try:
        db = get_db()
        rows = db.execute(
            """SELECT agent_id,
                      COUNT(*)                                   AS total,
                      SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS ok,
                      SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) AS fail,
                      AVG(CASE WHEN completed_at IS NOT NULL
                               THEN completed_at - started_at END)        AS avg_sec,
                      MAX(started_at)                            AS last_at,
                      MAX(CASE WHEN started_at = (SELECT MAX(started_at)
                                                    FROM agent_runs ar2
                                                   WHERE ar2.agent_id = agent_runs.agent_id)
                               THEN status END)                  AS last_status
               FROM agent_runs
               GROUP BY agent_id"""
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("Could not load run stats: %s", exc)
        return []
