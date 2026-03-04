"""
helm/pipeline/models.py — Pipeline and PipelineStep data structures.

Uses plain dicts (matching Helm's session pattern) with factory functions.
"""

import time
import uuid
from typing import Optional


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def make_step(
    step_id: str,
    title: str,
    description: str,
    assigned_ai: str = "claude",
    depends_on: Optional[list[str]] = None,
    expected_output: str = "text",
    priority: int = 0,
) -> dict:
    """Create a PipelineStep dict."""
    return {
        "id": step_id,
        "title": title,
        "description": description,
        "assigned_ai": assigned_ai,
        "status": "pending",          # pending | running | completed | failed | skipped
        "depends_on": depends_on or [],

        # Execution state
        "session_id": None,
        "started_at": None,
        "completed_at": None,
        "elapsed_seconds": 0.0,

        # Results
        "output": None,
        "output_summary": None,
        "artifacts": [],               # file paths created during step
        "error": None,

        # Metadata
        "expected_output": expected_output,  # text | code | file | analysis
        "priority": priority,
        "retry_count": 0,
        "max_retries": 2,
    }


def make_pipeline(
    prompt: str,
    session_id: str,
    cwd: str,
    planner_ai: str = "claude",
    steps: Optional[list[dict]] = None,
) -> dict:
    """Create a Pipeline dict."""
    pid = f"pl-{_uid()}"
    return {
        "id": pid,
        "status": "planning",         # planning | awaiting_approval | running
                                       # | paused | completed | failed | cancelled
        "original_prompt": prompt,
        "planner_ai": planner_ai,
        "session_id": session_id,      # parent session that spawned this
        "cwd": cwd,
        "artifacts_dir": f".helm-pipeline/{pid}",

        "created_at": time.time(),
        "started_at": None,
        "completed_at": None,

        "steps": steps or [],
        "edges": [],                   # [(from_id, to_id)] — computed from depends_on

        # Assembled final output
        "final_output": None,
    }


def compute_edges(pipeline: dict) -> list[list[str]]:
    """Derive edges list from step dependencies. Returns [[from_id, to_id], ...]"""
    edges = []
    for step in pipeline["steps"]:
        for dep_id in step.get("depends_on", []):
            edges.append([dep_id, step["id"]])
    pipeline["edges"] = edges
    return edges


def validate_dag(pipeline: dict) -> list[str]:
    """Check for cycles in the dependency graph. Returns list of error strings (empty = valid)."""
    errors = []
    step_ids = {s["id"] for s in pipeline["steps"]}

    # Check all dependency references are valid
    for step in pipeline["steps"]:
        for dep in step.get("depends_on", []):
            if dep not in step_ids:
                errors.append(f"Step '{step['id']}' depends on unknown step '{dep}'")

    # Topological sort to detect cycles
    in_degree = {s["id"]: 0 for s in pipeline["steps"]}
    adj: dict[str, list[str]] = {s["id"]: [] for s in pipeline["steps"]}

    for step in pipeline["steps"]:
        for dep in step.get("depends_on", []):
            if dep in adj:
                adj[dep].append(step["id"])
                in_degree[step["id"]] += 1

    queue = [sid for sid, deg in in_degree.items() if deg == 0]
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for child in adj.get(node, []):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if visited < len(step_ids):
        errors.append("Dependency graph contains a cycle — tasks cannot be ordered")

    return errors


def find_step(pipeline: dict, step_id: str) -> Optional[dict]:
    """Find a step by ID."""
    for s in pipeline["steps"]:
        if s["id"] == step_id:
            return s
    return None


def pipeline_progress(pipeline: dict) -> dict:
    """Compute progress summary."""
    steps = pipeline["steps"]
    total = len(steps)
    counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "skipped": 0}
    for s in steps:
        status = s.get("status", "pending")
        counts[status] = counts.get(status, 0) + 1
    return {
        "total": total,
        **counts,
    }


def pipeline_state_payload(pipeline: dict) -> dict:
    """Serialisable version for WS broadcast (strip large outputs to keep payload small)."""
    steps_light = []
    for s in pipeline["steps"]:
        steps_light.append({
            "id": s["id"],
            "title": s["title"],
            "description": s["description"][:200],   # truncate for broadcast
            "assigned_ai": s["assigned_ai"],
            "status": s["status"],
            "depends_on": s["depends_on"],
            "elapsed_seconds": s.get("elapsed_seconds", 0),
            "error": (s.get("error") or "")[:200],
            "artifacts": s.get("artifacts", []),
            "expected_output": s.get("expected_output", "text"),
            "retry_count": s.get("retry_count", 0),
            "session_id": s.get("session_id"),
            # Truncated output preview for UI tooltip
            "output_preview": (s.get("output") or "")[:300],
        })
    return {
        "id": pipeline["id"],
        "status": pipeline["status"],
        "original_prompt": pipeline["original_prompt"][:500],
        "planner_ai": pipeline["planner_ai"],
        "session_id": pipeline["session_id"],
        "cwd": pipeline["cwd"],
        "created_at": pipeline["created_at"],
        "started_at": pipeline.get("started_at"),
        "completed_at": pipeline.get("completed_at"),
        "steps": steps_light,
        "edges": pipeline.get("edges", []),
        "progress": pipeline_progress(pipeline),
    }


def ready_steps(pipeline: dict) -> list[dict]:
    """Return steps that are pending and have all dependencies completed."""
    completed_ids = {s["id"] for s in pipeline["steps"] if s["status"] == "completed"}
    result = []
    for s in pipeline["steps"]:
        if s["status"] != "pending":
            continue
        deps = set(s.get("depends_on", []))
        if deps.issubset(completed_ids):
            result.append(s)
    # Sort by priority (lower = higher priority)
    result.sort(key=lambda s: s.get("priority", 0))
    return result


def is_pipeline_done(pipeline: dict) -> bool:
    """True if no steps are pending or running."""
    for s in pipeline["steps"]:
        if s["status"] in ("pending", "running"):
            return False
    return True


def is_pipeline_blocked(pipeline: dict) -> bool:
    """True if remaining pending steps all depend on a failed step (dead end)."""
    failed_ids = {s["id"] for s in pipeline["steps"] if s["status"] == "failed"}
    if not failed_ids:
        return False

    for s in pipeline["steps"]:
        if s["status"] != "pending":
            continue
        deps = set(s.get("depends_on", []))
        # If any dep is failed and not retryable, this step is blocked
        if deps.intersection(failed_ids):
            continue  # blocked
        return False   # at least one pending step is NOT blocked
    return True
