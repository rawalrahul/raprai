"""
helm/web_routes/pipeline_routes.py — Pipeline REST API endpoints.

Handles pipeline CRUD, approval, execution control, and step management.
"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.pipeline.models import (
    find_step, pipeline_state_payload, pipeline_progress,
)
from helm.pipeline.executor import (
    broadcast_pipeline_update, retry_step, reassign_step, skip_step,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# List / Get pipelines
# ---------------------------------------------------------------------------

@router.get("/api/pipelines")
async def list_pipelines():
    """List all pipelines (lightweight payload)."""
    items = []
    for pl in sorted(
        _st.pipelines.values(),
        key=lambda p: p.get("created_at", 0),
        reverse=True,
    ):
        items.append({
            "id": pl["id"],
            "status": pl["status"],
            "original_prompt": pl["original_prompt"][:200],
            "planner_ai": pl["planner_ai"],
            "created_at": pl["created_at"],
            "progress": pipeline_progress(pl),
        })
    return JSONResponse({"pipelines": items})


@router.get("/api/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get full pipeline state."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    return JSONResponse({"pipeline": pipeline_state_payload(pl)})


# ---------------------------------------------------------------------------
# Plan (submit prompt for decomposition)
# ---------------------------------------------------------------------------

@router.post("/api/pipeline/plan")
async def plan_pipeline_endpoint(request: Request):
    """Submit a prompt for pipeline planning. Returns the plan for approval."""
    import os
    from helm.session_mgr import focused_session, session_cwd
    from helm.pipeline.planner import plan_pipeline

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    fs = focused_session()
    cwd = fs["cwd"] if fs else session_cwd()
    sid = fs["id"] if fs else None

    planner_ai = (
        body.get("planner_ai")
        or os.environ.get("PIPELINE_PLANNER_AI", "claude")
    )

    pipeline = await plan_pipeline(
        prompt=prompt,
        session_id=sid,
        cwd=cwd,
        planner_ai=planner_ai,
    )

    _st.pipelines[pipeline["id"]] = pipeline
    await broadcast_pipeline_update(pipeline)

    return JSONResponse({
        "pipeline": pipeline_state_payload(pipeline),
    })


# ---------------------------------------------------------------------------
# Approve + Execute
# ---------------------------------------------------------------------------

@router.post("/api/pipeline/{pipeline_id}/approve")
async def approve_pipeline(pipeline_id: str, request: Request):
    """Approve a pipeline plan and start execution."""
    from helm.pipeline.executor import execute_pipeline

    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    if pl["status"] != "awaiting_approval":
        return JSONResponse(
            {"error": f"Pipeline is '{pl['status']}', expected 'awaiting_approval'"},
            status_code=400,
        )

    # Apply any edits from the approval UI (reordered steps, changed AIs, etc.)
    body = await request.json()
    if "steps" in body:
        # User edited the steps during approval
        for updated in body["steps"]:
            step = find_step(pl, updated.get("id", ""))
            if step:
                if "assigned_ai" in updated:
                    step["assigned_ai"] = updated["assigned_ai"]
                if "description" in updated:
                    step["description"] = updated["description"]
                if "title" in updated:
                    step["title"] = updated["title"]

    # Recompute edges in case deps changed
    from helm.pipeline.models import compute_edges
    compute_edges(pl)

    # Start execution in background
    asyncio.create_task(execute_pipeline(pipeline_id))

    return JSONResponse({"ok": True, "status": "running"})


# ---------------------------------------------------------------------------
# Pause / Resume / Cancel
# ---------------------------------------------------------------------------

@router.post("/api/pipeline/{pipeline_id}/pause")
async def pause_pipeline(pipeline_id: str):
    """Pause pipeline (running steps finish, no new steps start)."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    if pl["status"] != "running":
        return JSONResponse({"error": f"Cannot pause: status is '{pl['status']}'"}, status_code=400)

    pl["status"] = "paused"
    await broadcast_pipeline_update(pl)
    return JSONResponse({"ok": True, "status": "paused"})


@router.post("/api/pipeline/{pipeline_id}/resume")
async def resume_pipeline(pipeline_id: str):
    """Resume a paused pipeline."""
    from helm.pipeline.executor import execute_pipeline

    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    if pl["status"] != "paused":
        return JSONResponse({"error": f"Cannot resume: status is '{pl['status']}'"}, status_code=400)

    pl["status"] = "running"
    asyncio.create_task(execute_pipeline(pipeline_id))
    await broadcast_pipeline_update(pl)
    return JSONResponse({"ok": True, "status": "running"})


@router.post("/api/pipeline/{pipeline_id}/cancel")
async def cancel_pipeline(pipeline_id: str):
    """Cancel entire pipeline."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    pl["status"] = "cancelled"
    # Mark all pending steps as skipped
    for step in pl["steps"]:
        if step["status"] in ("pending",):
            step["status"] = "skipped"

    await broadcast_pipeline_update(pl)
    return JSONResponse({"ok": True, "status": "cancelled"})


# ---------------------------------------------------------------------------
# Step-level actions
# ---------------------------------------------------------------------------

@router.post("/api/pipeline/{pipeline_id}/step/{step_id}/retry")
async def retry_step_endpoint(pipeline_id: str, step_id: str):
    """Retry a failed step."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    ok = await retry_step(pl, step_id)
    if not ok:
        return JSONResponse({"error": "Cannot retry this step"}, status_code=400)
    return JSONResponse({"ok": True})


@router.post("/api/pipeline/{pipeline_id}/step/{step_id}/reassign")
async def reassign_step_endpoint(pipeline_id: str, step_id: str, request: Request):
    """Change AI assignment for a step."""
    body = await request.json()
    new_ai = (body.get("ai") or "").strip()
    if not new_ai:
        return JSONResponse({"error": "ai is required"}, status_code=400)

    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    ok = await reassign_step(pl, step_id, new_ai)
    if not ok:
        return JSONResponse({"error": "Cannot reassign this step"}, status_code=400)
    return JSONResponse({"ok": True})


@router.post("/api/pipeline/{pipeline_id}/step/{step_id}/skip")
async def skip_step_endpoint(pipeline_id: str, step_id: str):
    """Skip a step."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    ok = await skip_step(pl, step_id)
    if not ok:
        return JSONResponse({"error": "Cannot skip this step"}, status_code=400)
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Get full step output (for expanded view)
# ---------------------------------------------------------------------------

@router.get("/api/pipeline/{pipeline_id}/step/{step_id}")
async def get_step_detail(pipeline_id: str, step_id: str):
    """Get full step details including complete output."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    step = find_step(pl, step_id)
    if not step:
        return JSONResponse({"error": "Step not found"}, status_code=404)

    return JSONResponse({
        "step": {
            "id": step["id"],
            "title": step["title"],
            "description": step["description"],
            "assigned_ai": step["assigned_ai"],
            "status": step["status"],
            "depends_on": step["depends_on"],
            "output": step.get("output"),
            "output_summary": step.get("output_summary"),
            "error": step.get("error"),
            "artifacts": step.get("artifacts", []),
            "elapsed_seconds": step.get("elapsed_seconds", 0),
            "retry_count": step.get("retry_count", 0),
            "session_id": step.get("session_id"),
        }
    })
