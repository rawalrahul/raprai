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
# Terminal states — any status that means a node is done processing.
# Add new terminal statuses here; is_run_done and ready_nodes use this set.
# ---------------------------------------------------------------------------

TERMINAL_STATES = {
    "completed",
    "failed",
    "skipped",
    "cancelled",
    "timed_out",
    "cancelled_by_user",
}


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


def ensure_manager_node(nodes: list[dict], manager_title: str | None = None) -> None:
    """
    Ensure every executable workflow has one supervisory Manager node.

    The manager is drawn above the workflow and points at executable roots.
    Those edges are supervisory: ready_nodes() ignores them as prerequisites,
    then runs the manager after every non-manager node has reached a terminal
    state so it can review success/failure with the user.
    """
    if not nodes:
        return

    title = (manager_title or "Manager Review").strip() or "Manager Review"
    managers = [n for n in nodes if n.get("type") == "manager"]
    if managers:
        manager = managers[0]
        for extra in managers[1:]:
            nodes.remove(extra)
    else:
        max_x = max(float(n.get("x", 100)) for n in nodes)
        leaf_ys = [float(n.get("y", 100)) for n in nodes if not n.get("children")]
        y = sum(leaf_ys) / len(leaf_ys) if leaf_ys else 100.0
        manager = make_node(
            title=title,
            task=(
                "Review the full workflow result with the user. Ask if they are happy "
                "with the output. If not, collect the issue, identify the node most "
                "responsible, improve that node, and rerun the workflow."
            ),
            ai="claude",
            x=max_x + 260,
            y=y,
            node_type="manager",
        )
        manager["manager_max_iter"] = 3
        manager["input_timeout"] = 3600
        manager["deliver_channel"] = "ui"
        nodes.append(manager)

    if manager_title or not manager.get("title"):
        manager["title"] = title
    manager["type"] = "manager"
    manager["ai"] = manager.get("ai") or "claude"
    manager["task"] = manager.get("task") or (
        "Review the full workflow result with the user. Ask if they are happy "
        "with the output. If not, collect the issue, identify the node most "
        "responsible, improve that node, and rerun the workflow."
    )
    manager.setdefault("manager_max_iter", 3)
    manager.setdefault("input_timeout", 3600)
    manager.setdefault("deliver_channel", "ui")

    manager_id = manager["id"]
    non_manager_nodes = [n for n in nodes if n is not manager]
    for node in non_manager_nodes:
        node["children"] = [cid for cid in node.get("children", []) if cid != manager_id]

    if non_manager_nodes:
        min_x = min(float(n.get("x", 100)) for n in non_manager_nodes)
        max_x = max(float(n.get("x", 100)) for n in non_manager_nodes)
        min_y = min(float(n.get("y", 100)) for n in non_manager_nodes)
        manager["x"] = (min_x + max_x) / 2
        manager["y"] = max(20.0, min_y - 170.0)

    manager["children"] = [n["id"] for n in non_manager_nodes]


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
        "env_vars", "join_separator", "manager_max_iter",
        # A1: AI fallback fields
        "ai_fallback", "stuck_threshold",
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
                "input_data": None,
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
        "manager_iterations": 0,
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
    """Return executable roots, ignoring Manager supervision edges."""
    return workflow_root_nodes(nodes)


def workflow_root_nodes(nodes: list[dict]) -> list[dict]:
    """Return non-manager nodes that have no incoming non-manager edges."""
    child_ids: set[str] = set()
    for n in nodes:
        if n.get("type") == "manager":
            continue
        for cid in n.get("children", []):
            child_ids.add(cid)
    return [n for n in nodes if n.get("type") != "manager" and n["id"] not in child_ids]


def parent_nodes(
    nodes: list[dict],
    node_id: str,
    *,
    include_manager: bool = True,
) -> list[dict]:
    """Return all nodes whose children list contains node_id."""
    return [
        n for n in nodes
        if node_id in n.get("children", [])
        and (include_manager or n.get("type") != "manager")
    ]


def ready_nodes(nodes: list[dict]) -> list[dict]:
    """Return nodes whose parents are all terminal and the node itself is pending."""
    terminal = {"completed", "failed", "skipped"}
    non_manager_nodes = [n for n in nodes if n.get("type") != "manager"]
    result = []
    for n in nodes:
        if n["status"] != "pending":
            continue
        if n.get("type") == "manager":
            if not non_manager_nodes or all(w["status"] in terminal for w in non_manager_nodes):
                result.append(n)
            continue
        parents = parent_nodes(nodes, n["id"], include_manager=False)
        if all(p["status"] in terminal for p in parents):
            result.append(n)
    return result


def is_run_done(run: dict) -> bool:
    """True when every node is in a terminal state."""
    return all(n["status"] in TERMINAL_STATES for n in run["nodes"])


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
