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

import json
import time

import helm.state as _st
from helm.config import logger
from helm.db import get_db

from .models import node_runtime_snapshot


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


def save_agent(agent: dict) -> None:
    """Upsert an agent into the agents table."""
    try:
        db = get_db()
        agent["updated_at"] = time.time()
        # Store only node definitions (strip runtime state)
        saveable = dict(agent)
        saveable["nodes"] = [
            {k: v for k, v in n.items()
             if k in ("id", "title", "task", "ai", "children", "x", "y")}
            for n in agent.get("nodes", [])
        ]
        db.execute(
            """INSERT OR REPLACE INTO agents
               (id, name, description, graph_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                agent["id"],
                agent["name"],
                agent.get("description", ""),
                json.dumps(saveable, ensure_ascii=False),
                agent.get("created_at", time.time()),
                agent["updated_at"],
            ),
        )
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

def save_run(run: dict) -> None:
    """Upsert a run into the agent_runs table."""
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
