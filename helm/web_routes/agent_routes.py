"""
helm/web_routes/agent_routes.py — Agent REST API endpoints.

CRUD, run management, webhook trigger, and AI-assisted graph generation.
"""

import hmac
import os
import time

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.agent.models import (
    ensure_manager_node as _ensure_manager_node,
    make_agent, make_node, run_state_payload, agent_slug, make_webhook_token, workflow_root_nodes,
)
from helm.agent.repair import (
    initial_input_question as _repair_initial_input_question,
)
from helm.agent.storage import (
    save_agent, delete_agent, save_run, load_recent_runs, load_run,
    load_agent_versions, load_agent_version, load_all_run_stats,
)
from helm.agent.runner import trigger_agent_run

router = APIRouter()

# B8: cycle detection — reject graphs with A→B→A cycles on save
def _has_cycle(nodes: list[dict]) -> bool:
    """DFS cycle detection on node children graph. Returns True if any cycle found."""
    children_map: dict[str, list[str]] = {n["id"]: list(n.get("children", [])) for n in nodes}
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node_id: str) -> bool:
        visited.add(node_id)
        in_stack.add(node_id)
        for child_id in children_map.get(node_id, []):
            if child_id not in visited:
                if dfs(child_id):
                    return True
            elif child_id in in_stack:
                return True
        in_stack.discard(node_id)
        return False

    for node_id in children_map:
        if node_id not in visited:
            if dfs(node_id):
                return True
    return False


# B18: per-agent webhook throttle — track last trigger time
_webhook_last_trigger: dict[str, float] = {}
_WEBHOOK_MIN_INTERVAL = 5.0  # seconds


# ---------------------------------------------------------------------------
# List / Get agents
# ---------------------------------------------------------------------------

@router.get("/api/agents")
async def list_agents():
    """List all saved agents (lightweight payload)."""
    items = []
    for ag in sorted(_st.agents.values(), key=lambda a: a.get("created_at", 0), reverse=True):
        items.append(_agent_summary(ag))
    return JSONResponse({"agents": items})


@router.get("/api/agents/templates")
async def list_agent_templates():
    """List built-in agent workflow templates."""
    import glob as _glob, json as _json, os as _os
    template_dir = _os.path.join(_os.path.dirname(__file__), '..', 'agent', 'templates')
    templates = []
    for path in _glob.glob(_os.path.join(template_dir, '*.json')):
        try:
            with open(path, encoding="utf-8") as f:
                t = _json.load(f)
            templates.append({
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "node_count": len(t.get("nodes", [])),
                "template": t,
            })
        except Exception:
            logger.warning("Agent templates: skipped one that couldn't be read", exc_info=True)
    return JSONResponse({"templates": templates})


@router.get("/api/agents/stats")
async def agent_stats():
    """Aggregate run stats across all agents for the monitoring dashboard."""
    rows = load_all_run_stats()
    stats_by_agent = {r["agent_id"]: r for r in rows}

    agents_out = []
    total_runs = total_ok = total_fail = 0
    for ag in _st.agents.values():
        s = stats_by_agent.get(ag["id"], {})
        n_total = s.get("total", 0) or 0
        n_ok = s.get("ok", 0) or 0
        n_fail = s.get("fail", 0) or 0
        avg_sec = s.get("avg_sec")
        agents_out.append({
            "id": ag["id"],
            "name": ag["name"],
            "total_runs": n_total,
            "ok_runs": n_ok,
            "fail_runs": n_fail,
            "success_rate": round(n_ok / n_total, 3) if n_total else None,
            "avg_duration": round(avg_sec, 1) if avg_sec is not None else None,
            "last_run_at": s.get("last_at"),
            "last_status": s.get("last_status"),
        })
        total_runs += n_total
        total_ok += n_ok
        total_fail += n_fail

    agents_out.sort(key=lambda a: a["last_run_at"] or 0, reverse=True)
    return JSONResponse({
        "agents": agents_out,
        "totals": {
            "total_runs": total_runs,
            "ok_runs": total_ok,
            "fail_runs": total_fail,
            "success_rate": round(total_ok / total_runs, 3) if total_runs else None,
        },
    })


@router.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get full agent definition."""
    ag = _st.agents.get(agent_id)
    if not ag:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return JSONResponse({"agent": ag})


# ---------------------------------------------------------------------------
# Create / Update / Delete
# ---------------------------------------------------------------------------

@router.post("/api/agents")
async def create_agent(request: Request):
    """Create a new agent."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)

    parsed_nodes = [_parse_node(n) for n in body.get("nodes", [])]
    if _has_cycle(parsed_nodes):
        return JSONResponse({"error": "Workflow graph contains a cycle"}, status_code=400)
    ag = make_agent(
        name=name,
        description=body.get("description", ""),
        nodes=parsed_nodes,
    )
    _ensure_manager_node(ag["nodes"], manager_title=name)

    # Apply trigger overrides from body
    _apply_trigger(ag, body.get("trigger", {}))
    ag["output_dir"] = (body.get("output_dir") or "").strip() or None

    _st.agents[ag["id"]] = ag
    save_agent(ag)

    return JSONResponse({"agent": ag}, status_code=201)


@router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, request: Request):
    """Update an existing agent (canvas save)."""
    ag = _st.agents.get(agent_id)
    if not ag:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    body = await request.json()
    if "name" in body:
        ag["name"] = (body["name"] or "").strip() or ag["name"]
    if "description" in body:
        ag["description"] = body["description"]
    if "nodes" in body:
        parsed_nodes = [_parse_node(n) for n in body["nodes"]]
        if _has_cycle(parsed_nodes):
            return JSONResponse({"error": "Workflow graph contains a cycle"}, status_code=400)
        ag["nodes"] = parsed_nodes
        _ensure_manager_node(ag["nodes"], manager_title=ag["name"])
    if "trigger" in body:
        _apply_trigger(ag, body["trigger"])
    if "output_dir" in body:
        ag["output_dir"] = (body["output_dir"] or "").strip() or None

    ag["updated_at"] = time.time()
    save_agent(ag)

    return JSONResponse({"agent": ag})


@router.delete("/api/agents/{agent_id}")
async def delete_agent_endpoint(agent_id: str):
    """Delete an agent and all its runs."""
    if agent_id not in _st.agents:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    del _st.agents[agent_id]
    delete_agent(agent_id)
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------

@router.post("/api/agents/{agent_id}/run")
async def run_agent(agent_id: str, request: Request):
    """Trigger a manual run of an agent."""
    body = {}
    try:
        body = await request.json()
    except ValueError:
        pass

    # Use focused session_id for WS streaming
    from helm.session_mgr import focused_session
    fs = focused_session()
    session_id = body.get("session_id") or (fs["id"] if fs else None)
    input_data = body.get("input_data") or None
    dry_run = bool(body.get("dry_run", False))

    ag = _st.agents.get(agent_id)
    if ag and input_data is None and _agent_requires_initial_input(ag):
        return JSONResponse({
            "needs_input": True,
            "question": _agent_initial_input_question(ag),
        })

    run = await trigger_agent_run(
        agent_id,
        trigger="ui",
        session_id=session_id,
        input_data=input_data,
        dry_run=dry_run,
    )
    if not run:
        return JSONResponse({"error": "Agent not found or has no nodes"}, status_code=404)

    return JSONResponse({"run": run_state_payload(run)})


@router.post("/api/agents/{agent_id}/runs/{run_id}/cancel")
async def cancel_run(agent_id: str, run_id: str):
    """Cancel a running run."""
    run = _st.agent_runs.get(run_id)
    if not run:
        # Try loading from DB — it may already be completed
        run = load_run(run_id)
        if not run:
            return JSONResponse({"error": "Run not found"}, status_code=404)
        return JSONResponse({"error": "Run is already complete"}, status_code=400)

    if run["status"] != "running":
        return JSONResponse({"error": f"Run is '{run['status']}', not running"}, status_code=400)

    run["status"] = "cancelled"
    for n in run["nodes"]:
        if n["status"] in ("pending", "running"):
            n["status"] = "skipped"

    from helm.agent.executor import broadcast_run_update
    await broadcast_run_update(run)
    await save_run(run)

    return JSONResponse({"ok": True})


@router.get("/api/agents/{agent_id}/runs")
async def list_runs(agent_id: str):
    """List recent runs for an agent."""
    if agent_id not in _st.agents:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Start with any in-memory runs
    runs = [
        run_state_payload(r)
        for r in _st.agent_runs.values()
        if r["agent_id"] == agent_id
    ]

    # Add completed runs from DB
    db_runs = load_recent_runs(agent_id, limit=20)
    seen = {r["id"] for r in runs}
    for r in db_runs:
        if r["id"] not in seen:
            runs.append(run_state_payload(r))
            seen.add(r["id"])

    runs.sort(key=lambda r: r.get("started_at", 0), reverse=True)
    return JSONResponse({"runs": runs[:20]})


@router.get("/api/agents/runs/{run_id}")
async def get_run(run_id: str):
    """Get live or completed run state."""
    # Check in-memory first (live run)
    run = _st.agent_runs.get(run_id)
    if run:
        return JSONResponse({"run": run_state_payload(run)})

    # Fall back to DB
    run = load_run(run_id)
    if not run:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    return JSONResponse({"run": run_state_payload(run)})


# ---------------------------------------------------------------------------
# Webhook trigger (no auth — token in URL)
# ---------------------------------------------------------------------------

@router.post("/api/agents/webhook/{token}")
async def webhook_trigger(token: str, request: Request):
    """Trigger an agent via its webhook token. Request body becomes input_data."""
    body_bytes = await request.body()
    input_data = body_bytes.decode("utf-8", errors="replace").strip() or None

    for ag in _st.agents.values():
        webhook = ag.get("trigger", {}).get("webhook", {})
        stored_token = webhook.get("token") or ""
        if webhook.get("enabled") and hmac.compare_digest(stored_token, token):
            # B18: per-agent rate limit — reject triggers fired too quickly
            now = time.time()
            min_interval = webhook.get("min_interval", _WEBHOOK_MIN_INTERVAL)
            last = _webhook_last_trigger.get(ag["id"], 0.0)
            if now - last < min_interval:
                return JSONResponse(
                    {"error": "Rate limited", "retry_after": min_interval - (now - last)},
                    status_code=429,
                )
            _webhook_last_trigger[ag["id"]] = now
            run = await trigger_agent_run(
                ag["id"],
                trigger="webhook",
                input_data=input_data,
            )
            if run:
                return JSONResponse({"ok": True, "run_id": run["id"]})
            return JSONResponse({"error": "Agent has no nodes"}, status_code=400)

    return JSONResponse({"error": "Invalid webhook token"}, status_code=404)


# B20: rotate webhook token — invalidates old token, issues fresh one
@router.post("/api/agents/{agent_id}/webhook/rotate")
async def rotate_webhook_token(agent_id: str):
    """Generate a new webhook token for an agent and invalidate the old one."""
    ag = _st.agents.get(agent_id)
    if not ag:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    trig = ag.setdefault("trigger", {})
    webhook = trig.setdefault("webhook", {"enabled": False})
    webhook["token"] = make_webhook_token()
    save_agent(ag)
    return JSONResponse({"token": webhook["token"]})


@router.post("/api/agents/runs/{run_id}/resume")
async def resume_agent_run(run_id: str, request: Request):
    """Resume a run waiting for human input."""
    body = {}
    try:
        body = await request.json()
    except ValueError:
        pass

    user_input = (body.get("input") or "").strip()
    if not user_input:
        return JSONResponse({"error": "input is required"}, status_code=400)

    from helm.agent.nodes.input_node import resume_run
    if not resume_run(run_id, user_input):
        return JSONResponse({"error": "Run not waiting for input"}, status_code=400)
    return JSONResponse({"ok": True})


@router.post("/api/agents/input-file")
async def upload_agent_input_file(file: UploadFile = File(...)):
    """Upload a file for an agent input node and return extractable text."""
    from helm.config import _DEFAULT_CWD
    from helm.security import MAX_UPLOAD_SIZE, validate_upload

    filename = file.filename or f"agent_input_{int(time.time())}"
    try:
        data = await file.read()
    except Exception as exc:
        return JSONResponse({"error": f"Failed to read upload: {exc}"}, status_code=400)

    error = validate_upload(filename, len(data))
    if error:
        return JSONResponse({"error": error}, status_code=400)
    if len(data) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            {"error": f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB."},
            status_code=413,
        )

    from helm.session_mgr import focused_session
    fs = focused_session()
    cwd = fs.get("cwd", _DEFAULT_CWD) if fs else _DEFAULT_CWD
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name.startswith("."):
        safe_name = f"agent_input_{int(time.time())}"
    save_path = os.path.join(cwd, safe_name)
    resolved = os.path.realpath(save_path)
    if not resolved.startswith(os.path.realpath(cwd)):
        return JSONResponse({"error": "Invalid upload path"}, status_code=400)

    try:
        with open(save_path, "wb") as f:
            f.write(data)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)

    extracted = _extract_agent_input_file_text(save_path, safe_name)
    input_text = (
        f"Uploaded file: {safe_name}\n"
        f"Saved path: {save_path}\n\n"
        f"=== Extracted File Text ===\n{extracted}\n=== End Extracted File Text ==="
    )
    return JSONResponse({
        "filename": safe_name,
        "path": save_path,
        "size": len(data),
        "text": extracted,
        "input_text": input_text,
    })


# ---------------------------------------------------------------------------
# AI-assisted graph generation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Builder chat — iterative graph editing via natural language
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent_requires_initial_input(agent: dict) -> bool:
    """Return True when a saved agent should collect input before execution."""
    nodes = agent.get("nodes", [])
    if not nodes:
        return False
    roots = workflow_root_nodes(nodes) or [n for n in nodes if n.get("type") != "manager"][:1]
    root_text = " ".join(f"{n.get('title', '')} {n.get('task', '')} {n.get('type', '')}" for n in roots).lower()
    all_text = f"{agent.get('name', '')} {agent.get('description', '')} " + " ".join(
        f"{n.get('title', '')} {n.get('task', '')}" for n in nodes
    )
    all_text = all_text.lower()
    if any(n.get("type") == "input" for n in roots):
        return True
    # Legacy repair for job-finder agents that were saved before input nodes
    # existed. Keep this intentionally narrow so ordinary agents still run.
    job_terms = ("job", "career", "role", "position", "linkedin")
    resume_terms = ("resume", "cv", "profile")
    preference_terms = ("preferences", "criteria", "requirements")
    if any(term in all_text for term in job_terms) and (
        any(term in all_text for term in resume_terms)
        or (any(term in root_text for term in preference_terms) and any(term in all_text for term in resume_terms))
    ):
        return True
    return False


def _agent_initial_input_question(agent: dict) -> str:
    """Question shown before starting an input-requiring agent."""
    nodes = agent.get("nodes", [])
    roots = workflow_root_nodes(nodes) or [n for n in nodes if n.get("type") != "manager"][:1]
    for node in roots:
        if node.get("type") == "input" and node.get("task"):
            return node["task"]
    text = f"{agent.get('name', '')} {agent.get('description', '')} " + " ".join(
        f"{n.get('title', '')} {n.get('task', '')}" for n in nodes
    )
    return _initial_input_question(text)


def _initial_input_question(description: str) -> str:
    return _repair_initial_input_question(description)


_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".oga", ".opus", ".webm", ".flac", ".aac", ".amr"}


def _extract_agent_input_file_text(path: str, filename: str) -> str:
    """Best-effort text extraction for files uploaded into agent input nodes."""
    ext = os.path.splitext(filename.lower())[1]
    try:
        if ext in {".txt", ".md", ".csv", ".json", ".log"}:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()[:50000]
        if ext == ".pdf":
            try:
                from pdfminer.high_level import extract_text
            except ImportError:
                return "(PDF uploaded, but pdfminer.six is not installed. Use the saved path above or install pdfminer.six.)"
            return (extract_text(path) or "").strip()[:50000] or "(empty PDF)"
        if ext == ".docx":
            try:
                from docx import Document
            except ImportError:
                return "(DOCX uploaded, but python-docx is not installed. Use the saved path above or install python-docx.)"
            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return text[:50000] or "(empty DOCX)"
        if ext in _AUDIO_EXTS:
            # Transcribe audio via the same Whisper pipeline used by /transcribe.
            try:
                from helm.web_routes.voice_routes import _transcribe
            except Exception as exc:
                return f"(audio uploaded, but transcription module is unavailable: {exc})"
            try:
                transcript = (_transcribe(path) or "").strip()
            except Exception as exc:
                return f"(audio uploaded, but transcription failed: {exc})"
            return transcript[:50000] or "(audio transcribed but no speech detected)"
        return "(file uploaded; automatic text extraction is not available for this file type. Use the saved path above.)"
    except Exception as exc:
        return f"(file uploaded, but text extraction failed: {exc})"


def _agent_summary(ag: dict) -> dict:
    """Lightweight agent dict for list views."""
    return {
        "id": ag["id"],
        "name": ag["name"],
        "description": ag.get("description", ""),
        "node_count": len(ag.get("nodes", [])),
        "trigger": ag.get("trigger", {}),
        "output_dir": ag.get("output_dir") or None,
        "last_run_at": ag.get("last_run_at"),
        "run_count": ag.get("run_count", 0),
        "created_at": ag.get("created_at", 0),
        "updated_at": ag.get("updated_at", 0),
    }


def _parse_node(raw: dict) -> dict:
    """Parse a node dict from API request body."""
    from helm.agent.models import make_node_id
    node = make_node(
        title=str(raw.get("title", "New Step"))[:60],
        task=str(raw.get("task", "")),
        ai=str(raw.get("ai", "claude")),
        x=float(raw.get("x", 100)),
        y=float(raw.get("y", 100)),
        node_id=raw.get("id") or make_node_id(),
        node_type=str(raw.get("type", "ai")),
    )
    node["children"] = [str(c) for c in raw.get("children", [])][:3]
    for key in (
        "timeout", "http_method", "http_url", "http_headers", "http_body",
        "file_op", "file_path", "deliver_channel", "deliver_to",
        "deliver_subject", "input_timeout", "loop_max", "retry_max",
        "transform_op", "transform_key", "transform_pattern", "transform_length",
        "env_vars", "join_separator", "manager_max_iter",
    ):
        if key in raw:
            node[key] = raw[key]
    return node


def _apply_trigger(ag: dict, trigger_body: dict) -> None:
    """Apply trigger overrides from request body to agent dict."""
    from helm.scheduler import natural_to_cron, next_cron_run

    trig = ag.setdefault("trigger", {})

    if "telegram" in trigger_body:
        trig["telegram"] = bool(trigger_body["telegram"])

    sched_body = trigger_body.get("schedule", {})
    sched = trig.setdefault("schedule", {"enabled": False, "expression": "", "cron": "", "next_run": None, "input_data": None})
    if "enabled" in sched_body:
        sched["enabled"] = bool(sched_body["enabled"])
    if "input_data" in sched_body:
        sched["input_data"] = sched_body["input_data"] or None
    if "expression" in sched_body:
        expr = (sched_body["expression"] or "").strip()
        sched["expression"] = expr
        if expr:
            cron = natural_to_cron(expr)
            sched["cron"] = cron or ""
            sched["next_run"] = next_cron_run(cron) if cron else None

    webhook_body = trigger_body.get("webhook", {})
    webhook = trig.setdefault("webhook", {"enabled": False, "token": make_webhook_token()})
    if "enabled" in webhook_body:
        webhook["enabled"] = bool(webhook_body["enabled"])
    if not webhook.get("token"):
        webhook["token"] = make_webhook_token()


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

@router.get("/api/agents/{agent_id}/export")
async def export_agent(agent_id: str):
    """Download agent definition as JSON."""
    ag = _st.agents.get(agent_id)
    if not ag:
        return JSONResponse({"error": "not found"}, status_code=404)
    from helm.agent.storage import _strip_runtime
    export_data = _strip_runtime(ag)
    export_data.pop("id", None)          # strip ID — re-import creates a fresh one
    export_data.pop("created_at", None)
    export_data.pop("updated_at", None)
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in ag["name"])
    return JSONResponse(
        export_data,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'},
    )


@router.post("/api/agents/import")
async def import_agent(request: Request):
    """Create a new agent from an exported JSON payload."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    name = (body.get("name") or "Imported Agent").strip()
    description = (body.get("description") or "").strip()
    new_id = agent_slug(name)
    # Avoid ID collisions
    base = new_id
    counter = 2
    while new_id in _st.agents:
        new_id = f"{base}_{counter}"
        counter += 1

    parsed_nodes = [_parse_node(n) for n in body.get("nodes", [])]
    if _has_cycle(parsed_nodes):
        return JSONResponse({"error": "Workflow graph contains a cycle"}, status_code=400)

    agent = make_agent(name=name, description=description, nodes=parsed_nodes)
    agent["id"] = new_id
    agent["trigger"] = body.get("trigger", {})
    _ensure_manager_node(agent["nodes"], manager_title=agent["name"])
    _st.agents[agent["id"]] = agent
    save_agent(agent)
    return JSONResponse({"id": agent["id"], "name": agent["name"]})


# ---------------------------------------------------------------------------
# Agent version history
# ---------------------------------------------------------------------------

@router.get("/api/agents/{agent_id}/versions")
async def list_agent_versions(agent_id: str):
    """List saved versions for an agent."""
    if agent_id not in _st.agents:
        return JSONResponse({"error": "not found"}, status_code=404)
    versions = load_agent_versions(agent_id)
    return JSONResponse({"versions": versions})


@router.post("/api/agents/{agent_id}/versions/{version_id}/restore")
async def restore_agent_version(agent_id: str, version_id: str):
    """Restore agent to a previous version snapshot."""
    ag = _st.agents.get(agent_id)
    if not ag:
        return JSONResponse({"error": "not found"}, status_code=404)
    snapshot = load_agent_version(version_id)
    if not snapshot:
        return JSONResponse({"error": "version not found"}, status_code=404)
    # Merge snapshot nodes/trigger back, keep current id/name/description
    ag["nodes"] = snapshot.get("nodes", ag["nodes"])
    ag["trigger"] = snapshot.get("trigger", ag.get("trigger", {}))
    _ensure_manager_node(ag["nodes"], manager_title=ag["name"])
    save_agent(ag)
    return JSONResponse({"ok": True, "agent": ag})


