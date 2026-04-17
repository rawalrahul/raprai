"""
helm/agent/models.py — Agent data structures and DAG helpers.

AgentNode  — one node on the canvas (config + per-run status fields)
Agent      — saved agent definition (graph + triggers)
AgentRun   — one execution instance (deep-copied snapshot of nodes with live state)
"""

import secrets
import time
from typing import Optional


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_node_id() -> str:
    return secrets.token_hex(5)  # "a1b2c3d4e5"


def make_agent_id() -> str:
    return "ag-" + secrets.token_hex(8)


def make_run_id() -> str:
    return "run-" + secrets.token_hex(8)


def make_webhook_token() -> str:
    return secrets.token_urlsafe(24)


# ---------------------------------------------------------------------------
# AgentNode
# ---------------------------------------------------------------------------

def make_node(
    title: str = "New Step",
    task: str = "",
    ai: str = "claude",
    x: float = 100.0,
    y: float = 100.0,
    node_id: Optional[str] = None,
    node_type: str = "ai",
) -> dict:
    """Create a new AgentNode dict."""
    return {
        "id": node_id or make_node_id(),
        "title": title,
        "task": task,
        "type": node_type,
        "ai": ai,
        "children": [],          # list of child node IDs (max 3)
        "x": x,
        "y": y,
        # Runtime fields — reset per run, stored in AgentRun snapshot
        "status": "pending",     # pending | running | completed | failed | skipped
        "output": None,
        "output_summary": None,
        "error": None,
        "stream_buffer": "",
        "session_id": None,
        "started_at": None,
        "completed_at": None,
        "elapsed_seconds": 0.0,
    }


def node_definition(node: dict) -> dict:
    """Strip runtime fields from a node — only save the graph definition."""
    definition = {
        "id": node["id"],
        "title": node["title"],
        "task": node["task"],
        "type": node.get("type", "ai"),
        "ai": node["ai"],
        "children": list(node["children"]),
        "x": node.get("x", 100.0),
        "y": node.get("y", 100.0),
    }
    for key in (
        "timeout", "http_method", "http_url", "http_headers", "http_body",
        "file_op", "file_path", "deliver_channel", "deliver_to",
        "deliver_subject", "input_timeout", "loop_max", "retry_max",
        "transform_op", "transform_key", "transform_pattern", "transform_length",
        "env_vars",
    ):
        if key in node:
            definition[key] = node[key]
    return definition


def node_runtime_snapshot(node: dict) -> dict:
    """Deep copy a node for an AgentRun snapshot, resetting runtime fields."""
    snap = node_definition(node)
    snap.update({
        "status": "pending",
        "output": None,
        "output_summary": None,
        "error": None,
        "stream_buffer": "",
        "session_id": None,
        "started_at": None,
        "completed_at": None,
        "elapsed_seconds": 0.0,
    })
    return snap


# ---------------------------------------------------------------------------
# Agent (saved definition)
# ---------------------------------------------------------------------------

def make_agent(name: str, description: str = "", nodes: Optional[list] = None) -> dict:
    """Create a new Agent dict (not yet saved)."""
    now = time.time()
    return {
        "id": make_agent_id(),
        "name": name,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "nodes": nodes or [],
        "trigger": {
            "telegram": True,
            "schedule": {
                "enabled": False,
                "expression": "",
                "cron": "",
                "next_run": None,
            },
            "webhook": {
                "enabled": False,
                "token": make_webhook_token(),
            },
        },
        "last_run_at": None,
        "run_count": 0,
        "run_timeout": 1800,   # seconds; 0 = no timeout
    }


# ---------------------------------------------------------------------------
# AgentRun
# ---------------------------------------------------------------------------

def make_run(
    agent: dict,
    trigger: str,
    session_id: Optional[str] = None,
    input_data: Optional[str] = None,
) -> dict:
    """Create an AgentRun for one execution of an agent."""
    # Deep-copy nodes, resetting runtime state
    nodes_snapshot = [node_runtime_snapshot(n) for n in agent["nodes"]]
    return {
        "id": make_run_id(),
        "agent_id": agent["id"],
        "agent_name": agent["name"],
        "trigger": trigger,          # "telegram" | "schedule" | "webhook" | "ui"
        "status": "running",         # running | completed | failed | cancelled
        "nodes": nodes_snapshot,
        "input_data": input_data,
        "vars": {},
        "feedback_retries": {},
        "node_retries": {},
        "started_at": time.time(),
        "completed_at": None,
        "session_id": session_id,    # for WS broadcasts + Telegram replies
    }


# ---------------------------------------------------------------------------
# DAG helpers
# ---------------------------------------------------------------------------

def find_node(run_or_agent: dict, node_id: str) -> Optional[dict]:
    """Find a node by ID in an agent definition or a run snapshot."""
    for n in run_or_agent.get("nodes", []):
        if n["id"] == node_id:
            return n
    return None


def root_nodes(nodes: list[dict]) -> list[dict]:
    """Return nodes that have no incoming edges (not listed as any node's child)."""
    child_ids: set[str] = set()
    for n in nodes:
        for cid in n.get("children", []):
            child_ids.add(cid)
    return [n for n in nodes if n["id"] not in child_ids]


def parent_nodes(nodes: list[dict], node_id: str) -> list[dict]:
    """Return all nodes whose children list contains node_id."""
    return [n for n in nodes if node_id in n.get("children", [])]


def ready_nodes(nodes: list[dict]) -> list[dict]:
    """Return nodes whose parents are all terminal and the node itself is pending."""
    terminal = {"completed", "failed", "skipped"}
    result = []
    for n in nodes:
        if n["status"] != "pending":
            continue
        parents = parent_nodes(nodes, n["id"])
        if all(p["status"] in terminal for p in parents):
            result.append(n)
    return result


def is_run_done(run: dict) -> bool:
    """True when every node is in a terminal state."""
    terminal = {"completed", "failed", "skipped"}
    return all(n["status"] in terminal for n in run["nodes"])


def run_progress(run: dict) -> dict:
    """Summary counts for a run's nodes."""
    counts = {"total": 0, "pending": 0, "running": 0, "completed": 0, "failed": 0, "skipped": 0}
    for n in run["nodes"]:
        counts["total"] += 1
        counts[n["status"]] = counts.get(n["status"], 0) + 1
    return counts


def run_state_payload(run: dict) -> dict:
    """Serialisable summary of a run for WS broadcasts and API responses."""
    return {
        "id": run["id"],
        "agent_id": run["agent_id"],
        "agent_name": run["agent_name"],
        "trigger": run["trigger"],
        "status": run["status"],
        "nodes": run["nodes"],
        "input_data": run.get("input_data"),
        "started_at": run["started_at"],
        "completed_at": run.get("completed_at"),
        "progress": run_progress(run),
    }


def agent_slug(name: str) -> str:
    """Convert agent name to slug: lowercase, spaces → hyphens."""
    return name.lower().replace(" ", "-")


def agent_slug_match(name: str, slug: str) -> bool:
    """Fuzzy match: strip hyphens+spaces and compare lowercase."""
    normalise = lambda s: s.lower().replace("-", "").replace(" ", "")
    return normalise(name) == normalise(slug)
