"""
helm/web_routes/agent_routes.py — Agent REST API endpoints.

CRUD, run management, webhook trigger, and AI-assisted graph generation.
"""

import asyncio
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.agent.models import (
    make_agent, make_node, node_definition,
    run_state_payload, agent_slug, make_webhook_token,
)
from helm.agent.storage import (
    save_agent, delete_agent, save_run, load_recent_runs, load_run,
)
from helm.agent.runner import trigger_agent_run

router = APIRouter()


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

    ag = make_agent(
        name=name,
        description=body.get("description", ""),
        nodes=[_parse_node(n) for n in body.get("nodes", [])],
    )

    # Apply trigger overrides from body
    _apply_trigger(ag, body.get("trigger", {}))

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
        ag["nodes"] = [_parse_node(n) for n in body["nodes"]]
    if "trigger" in body:
        _apply_trigger(ag, body["trigger"])

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
    except Exception:
        pass

    # Use focused session_id for WS streaming
    from helm.session_mgr import focused_session
    fs = focused_session()
    session_id = body.get("session_id") or (fs["id"] if fs else None)

    run = await trigger_agent_run(agent_id, trigger="ui", session_id=session_id)
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
    save_run(run)

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
async def webhook_trigger(token: str):
    """Trigger an agent via its webhook token."""
    for ag in _st.agents.values():
        webhook = ag.get("trigger", {}).get("webhook", {})
        if webhook.get("enabled") and webhook.get("token") == token:
            run = await trigger_agent_run(ag["id"], trigger="webhook")
            if run:
                return JSONResponse({"ok": True, "run_id": run["id"]})
            return JSONResponse({"error": "Agent has no nodes"}, status_code=400)

    return JSONResponse({"error": "Invalid webhook token"}, status_code=404)


# ---------------------------------------------------------------------------
# AI-assisted graph generation
# ---------------------------------------------------------------------------

@router.post("/api/agents/generate")
async def generate_agent_graph(request: Request):
    """
    Generate a suggested node graph from a description using AI.
    Returns a list of AgentNode dicts for the user to review before saving.
    """
    body = await request.json()
    description = (body.get("description") or "").strip()
    if not description:
        return JSONResponse({"error": "description is required"}, status_code=400)

    planner_ai = os.environ.get("PIPELINE_PLANNER_AI", "claude")

    prompt = f"""You are designing a workflow automation agent.

The user wants to build an agent that does the following:
{description}

Return a JSON array of steps (nodes) for this agent. Each step is an object with:
- "title": short display name (max 50 chars)
- "task": detailed instructions for the AI executing this step (1-3 sentences)
- "ai": which AI to use — "claude", "gemini", or "ollama"
- "children": array of titles of steps that should come AFTER this one (direct children only)
- "x": horizontal canvas position (start at 100, add 220 per column)
- "y": vertical canvas position (start at 100, add 150 per row)

Rules:
- Max 8 nodes
- Max 3 children per node
- Keep it focused and practical
- Use claude for code/analysis, gemini for research/web, ollama for local tasks

Respond with ONLY a valid JSON array, no markdown, no explanation."""

    try:
        from helm.pipeline.planner import _call_planner_ai
        from helm.session_mgr import session_cwd
        result = await _call_planner_ai(planner_ai, prompt, session_cwd())
    except Exception as exc:
        logger.error("Agent graph generation failed: %s", exc)
        return JSONResponse({"error": f"AI generation failed: {exc}"}, status_code=500)

    # Parse JSON from AI response — robust extraction
    import json, re
    raw_nodes = None
    try:
        raw_nodes = _extract_json_array(result)
    except Exception as exc:
        pass
    if raw_nodes is None:
        logger.error("Could not parse agent generation result:\n%s", result[:800])
        return JSONResponse({"error": "Could not parse AI response — try again or simplify description"}, status_code=500)

    # Convert title-based children references to IDs
    nodes = []
    title_to_id: dict[str, str] = {}
    for raw in raw_nodes:
        node = make_node(
            title=str(raw.get("title", "Step"))[:60],
            task=str(raw.get("task", "")),
            ai=str(raw.get("ai", "claude")),
            x=float(raw.get("x", 100)),
            y=float(raw.get("y", 100)),
        )
        title_to_id[raw.get("title", "")] = node["id"]
        node["_children_titles"] = raw.get("children", [])
        nodes.append(node)

    for node in nodes:
        children_titles = node.pop("_children_titles", [])
        node["children"] = [
            title_to_id[t] for t in children_titles if t in title_to_id
        ][:3]

    logger.info("Agent graph generation: returned %d nodes for description len=%d", len(nodes), len(description))
    return JSONResponse({"nodes": [node_definition(n) for n in nodes]})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json_array(text: str) -> list:
    """Extract the first JSON array from AI response text (handles markdown fences, preamble)."""
    import json, re
    # Strip markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # Try direct parse first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "nodes" in parsed:
            return parsed["nodes"]  # some models wrap in {"nodes": [...]}
    except (json.JSONDecodeError, ValueError):
        pass

    # Find the first [...] block in the text
    start = text.find("[")
    if start != -1:
        # Find matching closing bracket
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except (json.JSONDecodeError, ValueError):
                        break

    return None


def _agent_summary(ag: dict) -> dict:
    """Lightweight agent dict for list views."""
    return {
        "id": ag["id"],
        "name": ag["name"],
        "description": ag.get("description", ""),
        "node_count": len(ag.get("nodes", [])),
        "trigger": ag.get("trigger", {}),
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
    )
    node["children"] = [str(c) for c in raw.get("children", [])][:3]
    return node


def _apply_trigger(ag: dict, trigger_body: dict) -> None:
    """Apply trigger overrides from request body to agent dict."""
    from helm.scheduler import natural_to_cron, next_cron_run

    trig = ag.setdefault("trigger", {})

    if "telegram" in trigger_body:
        trig["telegram"] = bool(trigger_body["telegram"])

    sched_body = trigger_body.get("schedule", {})
    sched = trig.setdefault("schedule", {"enabled": False, "expression": "", "cron": "", "next_run": None})
    if "enabled" in sched_body:
        sched["enabled"] = bool(sched_body["enabled"])
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
