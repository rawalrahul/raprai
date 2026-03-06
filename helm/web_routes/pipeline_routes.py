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
    make_template, instantiate_template,
)
from helm.pipeline.executor import (
    broadcast_pipeline_update, retry_step, reassign_step, skip_step,
)
from helm.pipeline.cost import estimate_pipeline_cost

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
            "artifact_files": step.get("artifact_files", []),
            "elapsed_seconds": step.get("elapsed_seconds", 0),
            "retry_count": step.get("retry_count", 0),
            "session_id": step.get("session_id"),
            "condition": step.get("condition"),
            "fallback_ais": step.get("fallback_ais", []),
            "fallback_index": step.get("fallback_index", 0),
            "estimated_tokens": step.get("estimated_tokens", 0),
            "estimated_cost_usd": step.get("estimated_cost_usd", 0.0),
            "actual_tokens": step.get("actual_tokens", 0),
            "actual_cost_usd": step.get("actual_cost_usd", 0.0),
            "stream_buffer": (step.get("stream_buffer") or "")[-500:],
        }
    })


# ---------------------------------------------------------------------------
# Pipeline Templates
# ---------------------------------------------------------------------------

@router.get("/api/pipeline/templates")
async def list_templates():
    """List all saved pipeline templates (from DB + in-memory)."""
    # Load from DB into state if not already loaded
    _load_pipeline_templates_from_db()

    items = []
    for tpl in sorted(
        _st.pipeline_templates.values(),
        key=lambda t: t.get("created_at", 0),
        reverse=True,
    ):
        items.append({
            "id": tpl["id"],
            "name": tpl["name"],
            "description": tpl.get("description", ""),
            "planner_ai": tpl.get("planner_ai", ""),
            "step_count": len(tpl.get("steps_template", [])),
            "use_count": tpl.get("use_count", 0),
            "created_at": tpl.get("created_at", 0),
        })
    return JSONResponse({"templates": items})


@router.post("/api/pipeline/{pipeline_id}/save-template")
async def save_template(pipeline_id: str, request: Request):
    """Save a completed pipeline as a reusable template."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    if pl["status"] != "completed":
        return JSONResponse(
            {"error": "Only completed pipelines can be saved as templates"},
            status_code=400,
        )

    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        name = f"Template from {pl['original_prompt'][:50]}"

    tpl = make_template(name, pl, description=body.get("description", ""))
    _st.pipeline_templates[tpl["id"]] = tpl
    _save_pipeline_template_to_db(tpl)

    return JSONResponse({"ok": True, "template": {
        "id": tpl["id"],
        "name": tpl["name"],
        "step_count": len(tpl.get("steps_template", [])),
    }})


@router.post("/api/pipeline/from-template")
async def pipeline_from_template(request: Request):
    """Create a new pipeline from a saved template."""
    import os
    from helm.session_mgr import focused_session, session_cwd

    body = await request.json()
    tpl_id = (body.get("template_id") or "").strip()
    prompt = (body.get("prompt") or "").strip()

    if not tpl_id:
        return JSONResponse({"error": "template_id is required"}, status_code=400)

    tpl = _st.pipeline_templates.get(tpl_id)
    if not tpl:
        return JSONResponse({"error": "Template not found"}, status_code=404)

    if not prompt:
        prompt = tpl.get("description", "Run pipeline from template")

    fs = focused_session()
    cwd = fs["cwd"] if fs else session_cwd()
    sid = fs["id"] if fs else None

    pipeline = instantiate_template(tpl, prompt, sid, cwd)
    # Estimate cost
    estimate_pipeline_cost(pipeline)

    _st.pipelines[pipeline["id"]] = pipeline
    await broadcast_pipeline_update(pipeline)

    return JSONResponse({"pipeline": pipeline_state_payload(pipeline)})


@router.delete("/api/pipeline/template/{template_id}")
async def delete_template(template_id: str):
    """Delete a pipeline template."""
    if template_id not in _st.pipeline_templates:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    del _st.pipeline_templates[template_id]
    _delete_pipeline_template_from_db(template_id)
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

@router.get("/api/pipeline/{pipeline_id}/cost")
async def get_pipeline_cost(pipeline_id: str):
    """Get cost estimation for a pipeline."""
    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    cost = estimate_pipeline_cost(pl)
    return JSONResponse({"cost": cost})


# ---------------------------------------------------------------------------
# Pipeline template DB helpers
# ---------------------------------------------------------------------------

def _save_pipeline_template_to_db(tpl: dict) -> None:
    """Persist a pipeline template to SQLite."""
    import json
    try:
        from helm.db import get_db
        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO pipeline_templates
               (id, name, description, planner_ai, steps_template,
                use_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                tpl["id"],
                tpl["name"],
                tpl.get("description", ""),
                tpl.get("planner_ai", ""),
                json.dumps(tpl.get("steps_template", []), ensure_ascii=False),
                tpl.get("use_count", 0),
                tpl.get("created_at", 0),
            ),
        )
        db.commit()
    except Exception as e:
        logger.warning("Could not save pipeline template to DB: %s", e)


def _load_pipeline_templates_from_db() -> None:
    """Load pipeline templates from SQLite into state (if not already loaded)."""
    import json
    if _st.pipeline_templates:
        return  # Already loaded
    try:
        from helm.db import get_db
        db = get_db()
        rows = db.execute("SELECT * FROM pipeline_templates").fetchall()
        for row in rows:
            tpl = {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "planner_ai": row["planner_ai"] or "",
                "steps_template": json.loads(row["steps_template"]) if row["steps_template"] else [],
                "use_count": row["use_count"],
                "created_at": row["created_at"],
            }
            _st.pipeline_templates[tpl["id"]] = tpl
    except Exception as e:
        logger.warning("Could not load pipeline templates from DB: %s", e)


def _delete_pipeline_template_from_db(template_id: str) -> None:
    """Delete a pipeline template from SQLite."""
    try:
        from helm.db import get_db
        db = get_db()
        db.execute("DELETE FROM pipeline_templates WHERE id = ?", (template_id,))
        db.commit()
    except Exception as e:
        logger.warning("Could not delete pipeline template from DB: %s", e)
