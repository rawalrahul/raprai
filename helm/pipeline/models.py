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
    condition: Optional[dict] = None,
    fallback_ais: Optional[list[str]] = None,
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
        "artifact_files": [],           # structured: [{name, path, size, type}]
        "error": None,
        "stream_buffer": "",            # live streaming output (partial, cleared on complete)

        # Metadata
        "expected_output": expected_output,  # text | code | file | analysis
        "priority": priority,
        "retry_count": 0,
        "max_retries": 2,

        # Conditional branching: {"check": "step-1", "field": "status",
        #                         "equals": "completed", "otherwise": "skip"}
        "condition": condition,

        # Auto-fallback: list of AIs to try on failure (in order)
        "fallback_ais": fallback_ais or [],
        "fallback_index": 0,

        # Cost tracking
        "estimated_tokens": 0,
        "estimated_cost_usd": 0.0,
        "actual_tokens": 0,
        "actual_cost_usd": 0.0,
    }


def make_pipeline(
    prompt: str,
    session_id: str,
    cwd: str,
    planner_ai: str = "claude",
    steps: Optional[list[dict]] = None,
    template_id: Optional[str] = None,
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

        # Template tracking
        "template_id": template_id,    # if created from a template

        # Shared artifact registry: {step_id: [{name, path, size, type}]}
        "artifact_registry": {},

        # Cost estimation
        "estimated_total_cost": 0.0,
        "actual_total_cost": 0.0,
    }


# ---------------------------------------------------------------------------
# Pipeline templates
# ---------------------------------------------------------------------------

def make_template(
    name: str,
    pipeline: dict,
    description: str = "",
) -> dict:
    """Create a reusable pipeline template from a completed pipeline."""
    return {
        "id": f"tpl-{_uid()}",
        "name": name,
        "description": description or pipeline.get("original_prompt", "")[:200],
        "created_at": time.time(),
        "planner_ai": pipeline.get("planner_ai", "claude"),
        "steps_template": [
            {
                "id": s["id"],
                "title": s["title"],
                "description": s["description"],
                "assigned_ai": s["assigned_ai"],
                "depends_on": s["depends_on"],
                "expected_output": s.get("expected_output", "text"),
                "condition": s.get("condition"),
                "fallback_ais": s.get("fallback_ais", []),
            }
            for s in pipeline["steps"]
        ],
        "use_count": 0,
    }


def instantiate_template(template: dict, prompt: str, session_id: str, cwd: str) -> dict:
    """Create a new pipeline from a template, replacing the prompt."""
    steps = []
    for st in template["steps_template"]:
        steps.append(make_step(
            step_id=st["id"],
            title=st["title"],
            description=st["description"],
            assigned_ai=st["assigned_ai"],
            depends_on=st.get("depends_on", []),
            expected_output=st.get("expected_output", "text"),
            condition=st.get("condition"),
            fallback_ais=st.get("fallback_ais", []),
        ))

    pipeline = make_pipeline(
        prompt=prompt,
        session_id=session_id,
        cwd=cwd,
        planner_ai=template.get("planner_ai", "claude"),
        steps=steps,
        template_id=template["id"],
    )
    pipeline["status"] = "awaiting_approval"
    compute_edges(pipeline)
    template["use_count"] = template.get("use_count", 0) + 1
    return pipeline


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
            "artifact_files": s.get("artifact_files", []),
            "expected_output": s.get("expected_output", "text"),
            "retry_count": s.get("retry_count", 0),
            "session_id": s.get("session_id"),
            # Truncated output preview for UI tooltip
            "output_preview": (s.get("output") or "")[:300],
            # Live streaming buffer
            "stream_buffer": (s.get("stream_buffer") or "")[-500:],
            # Conditional branching
            "condition": s.get("condition"),
            # Fallback AIs
            "fallback_ais": s.get("fallback_ais", []),
            "fallback_index": s.get("fallback_index", 0),
            # Cost
            "estimated_tokens": s.get("estimated_tokens", 0),
            "estimated_cost_usd": s.get("estimated_cost_usd", 0.0),
            "actual_tokens": s.get("actual_tokens", 0),
            "actual_cost_usd": s.get("actual_cost_usd", 0.0),
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
        "template_id": pipeline.get("template_id"),
        "artifact_registry": pipeline.get("artifact_registry", {}),
        "estimated_total_cost": pipeline.get("estimated_total_cost", 0.0),
        "actual_total_cost": pipeline.get("actual_total_cost", 0.0),
    }


def evaluate_condition(pipeline: dict, step: dict) -> bool:
    """Evaluate a step's condition. Returns True if the step should run, False to skip.

    Condition format: {"check": "step-1", "field": "status"|"output",
                       "equals"|"contains": "value", "otherwise": "skip"}
    """
    cond = step.get("condition")
    if not cond:
        return True  # no condition = always run

    check_step_id = cond.get("check", "")
    target = find_step(pipeline, check_step_id)
    if not target:
        return True  # missing ref = run anyway

    field = cond.get("field", "status")
    actual = ""
    if field == "status":
        actual = target.get("status", "")
    elif field == "output":
        actual = target.get("output", "") or ""
    elif field == "error":
        actual = target.get("error", "") or ""

    # Check match
    if "equals" in cond:
        return actual == cond["equals"]
    if "not_equals" in cond:
        return actual != cond["not_equals"]
    if "contains" in cond:
        return cond["contains"].lower() in actual.lower()
    if "not_contains" in cond:
        return cond["not_contains"].lower() not in actual.lower()

    return True


def ready_steps(pipeline: dict) -> list[dict]:
    """Return steps that are pending and have all dependencies completed.
    Also evaluates conditional branching — skips steps whose conditions are not met.
    """
    completed_ids = {s["id"] for s in pipeline["steps"]
                     if s["status"] in ("completed", "skipped")}
    result = []
    for s in pipeline["steps"]:
        if s["status"] != "pending":
            continue
        deps = set(s.get("depends_on", []))
        if not deps.issubset(completed_ids):
            continue

        # Evaluate condition
        if not evaluate_condition(pipeline, s):
            s["status"] = "skipped"
            s["output"] = "(condition not met — skipped)"
            s["output_summary"] = "(condition not met — skipped)"
            continue

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
