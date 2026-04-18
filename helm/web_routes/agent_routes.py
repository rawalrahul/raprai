"""
helm/web_routes/agent_routes.py — Agent REST API endpoints.

CRUD, run management, webhook trigger, and AI-assisted graph generation.
"""

import asyncio
import os
import time

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.agent.models import (
    ensure_manager_node as _ensure_manager_node,
    make_agent, make_node, node_definition,
    run_state_payload, agent_slug, make_webhook_token, workflow_root_nodes,
)
from helm.agent.repair import (
    choose_node_ai as _repair_choose_node_ai,
    description_needs_initial_input as _repair_description_needs_initial_input,
    initial_input_question as _repair_initial_input_question,
    looks_like_fake_input_instruction as _repair_looks_like_fake_input_instruction,
    looks_like_input_step as _repair_looks_like_input_step,
    repair_agent_graph as _repair_agent_graph_core,
)
from helm.agent.storage import (
    save_agent, delete_agent, save_run, load_recent_runs, load_run,
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
            pass
    return JSONResponse({"templates": templates})


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
    input_data = body.get("input_data") or None

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
        if webhook.get("enabled") and webhook.get("token") == token:
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
    except Exception:
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

Return a JSON array of up to 7 workflow steps (nodes). The backend will add the supervisory Manager node automatically. Each step is an object with:
- "title": short display name (max 50 chars)
- "type": one of "ai", "shell", "http", "file", "deliver", "input", "condition", "loop", "transform", "join"
- "task": detailed instructions for the AI executing this step (1-3 sentences)
- "ai": which AI to use — "claude", "gemini", or "ollama"
- "children": array of titles of steps that should come AFTER this one (direct children only)
- "x": horizontal canvas position (start at 100, add 220 per column)
- "y": vertical canvas position (start at 100, add 150 per row)

Rules:
- Use "input" where user data or approval is required.
- Use "ai" for reasoning/research/writing/ranking, "shell" for local CLI, "http" for APIs, "file" for files, "condition" for branches, "loop" for repeated item processing, "transform" for cheap data cleanup, "join" for merging branches, and "deliver" for final delivery.
- PREFER PARALLEL DAGs over linear chains: if two or more steps are independent (do not need each other's output), give them the same parent so they run concurrently. Always use a "join" node to merge parallel branches before steps that need all their outputs.
- Example parallel pattern: root → [branch_a, branch_b] both as children of root, then join → deliver. Do NOT chain branch_a → branch_b if they are independent.
- Add RETRY_PARENT guidance to validation/review nodes when quality matters.
- Include optional config fields only when useful: retry_max, loop_max, timeout, http_method, http_url, file_op, file_path, deliver_channel, deliver_to, input_timeout, transform_op, transform_key, transform_pattern, transform_length, join_separator, manager_max_iter, env_vars.
- Max 3 children per node
- Keep it focused and practical
- Use claude for code/analysis, gemini for research/web, ollama for local tasks
- Do not create a hardcoded example agent. Create a reusable workflow structure that asks the user for the missing inputs at execution time.
- Do not include a Manager node; it is added automatically above the workflow and supervises the executable root nodes.

Respond with ONLY a valid JSON array, no markdown, no explanation."""

    try:
        from helm.pipeline.planner import _call_planner_ai
        from helm.session_mgr import session_cwd
        timeout = float(os.environ.get("AGENT_GENERATION_TIMEOUT", "600"))
        result = await asyncio.wait_for(
            _call_planner_ai(planner_ai, prompt, session_cwd()),
            timeout=timeout if timeout > 0 else None,
        )
    except asyncio.TimeoutError:
        logger.error("Agent graph generation timed out after %ss", timeout)
        return JSONResponse(
            {"error": f"Agent generation timed out after {int(timeout)} seconds. Try a shorter description or switch the planner AI in Settings."},
            status_code=504,
        )
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
    normalized_title_to_id: dict[str, str] = {}
    for raw in raw_nodes:
        node = make_node(
            title=str(raw.get("title", "Step"))[:60],
            task=str(raw.get("task", "")),
            ai=str(raw.get("ai", "claude")),
            x=float(raw.get("x", 100)),
            y=float(raw.get("y", 100)),
            node_type=str(raw.get("type", "ai")),
        )
        for key in (
            "timeout", "http_method", "http_url", "http_headers", "http_body",
            "file_op", "file_path", "deliver_channel", "deliver_to",
            "deliver_subject", "input_timeout", "loop_max", "retry_max",
            "transform_op", "transform_key", "transform_pattern", "transform_length",
            "env_vars", "join_separator", "manager_max_iter",
        ):
            if key in raw:
                node[key] = raw[key]
        title_to_id[raw.get("title", "")] = node["id"]
        normalized_title_to_id[_normalize_node_title(raw.get("title", ""))] = node["id"]
        node["_children_titles"] = raw.get("children", [])
        nodes.append(node)

    for node in nodes:
        children_titles = node.pop("_children_titles", [])
        node["children"] = [
            title_to_id.get(t) or normalized_title_to_id.get(_normalize_node_title(t))
            for t in children_titles
            if title_to_id.get(t) or normalized_title_to_id.get(_normalize_node_title(t))
        ][:3]

    _repair_generated_agent_graph(description, nodes)
    _ensure_manager_node(nodes)

    logger.info("Agent graph generation: returned %d nodes for description len=%d", len(nodes), len(description))
    return JSONResponse({"nodes": [node_definition(n) for n in nodes]})


# ---------------------------------------------------------------------------
# Builder chat — iterative graph editing via natural language
# ---------------------------------------------------------------------------

@router.post("/api/agents/builder-chat")
async def builder_chat(request: Request):
    """
    Accept a natural-language instruction + current node graph + conversation
    history.  Return updated nodes + a human-readable reply.

    The frontend replaces _builderNodes wholesale on success and re-renders.
    Manager node is always re-injected if the AI drops it.
    """
    import json as _json, re as _re

    body = await request.json()
    description = (body.get("description") or "").strip()
    nodes_raw = body.get("nodes") or []
    history = (body.get("history") or [])[-20:]   # last 10 exchanges
    message = (body.get("message") or "").strip()

    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    nodes_json = _json.dumps(nodes_raw, indent=2, ensure_ascii=False)

    system = f"""You are an expert workflow builder assistant editing an agent node graph.

{"Original description: " + description if description else "This is a manually built agent."}

Current workflow nodes (JSON):
{nodes_json}

Node types: ai, shell, http, file, deliver, input, condition, loop, transform, join, manager
  ai        — reasoning / writing / analysis (ai field: claude | gemini | ollama)
  shell     — run CLI commands
  http      — call external APIs
  file      — read/write files
  deliver   — send results (email, telegram…)
  input     — pause and ask user for input
  condition — branch on yes/no
  loop      — iterate over a list
  transform — cheap data manipulation (no AI call)
  join      — merge multiple parallel branches
  manager   — NEVER REMOVE — supervises workflow, handles node failures, collects user feedback, triggers reruns automatically

RULES:
1. Return ALL nodes (not just changed ones) — frontend does a full replace.
2. Preserve existing node IDs for unchanged nodes. New nodes: generate a unique random 10-char hex string as id.
3. Keep x/y of unchanged nodes. Place new nodes near their neighbours (+220 x, same y).
4. Every children entry must be a valid id present in the returned array.
5. NEVER remove or omit the Manager node. If the user asks, keep it and explain in reply.
6. Max 3 children per node.
7. AI selection: claude for code/analysis, gemini for research/web, ollama for local tasks.

Respond with ONLY valid JSON, no markdown, no code fences:
{{"reply": "<human explanation of changes>", "nodes": [<complete updated node array>]}}"""

    # Build conversation string
    conv_lines = []
    for h in history:
        role = "USER" if h.get("role") == "user" else "ASSISTANT"
        conv_lines.append(f"{role}: {h.get('content', '')}")
    conv_lines.append(f"USER: {message}")
    full_prompt = system + "\n\n" + "\n\n".join(conv_lines)

    planner_ai = os.environ.get("PIPELINE_PLANNER_AI", "claude")
    try:
        from helm.pipeline.planner import _call_planner_ai
        from helm.session_mgr import session_cwd
        timeout = float(os.environ.get("BUILDER_CHAT_TIMEOUT", "120"))
        result = await asyncio.wait_for(
            _call_planner_ai(planner_ai, full_prompt, session_cwd()),
            timeout=timeout if timeout > 0 else None,
        )
    except asyncio.TimeoutError:
        return JSONResponse({"error": "Builder chat timed out — try rephrasing"}, status_code=504)
    except Exception as exc:
        logger.error("Builder chat AI call failed: %s", exc)
        return JSONResponse({"error": f"AI call failed: {exc}"}, status_code=500)

    # Parse {reply, nodes} from AI response
    json_text = _re.sub(r"```(?:json)?\s*|\s*```", "", result).strip()
    obj = None
    try:
        obj = _json.loads(json_text)
    except _json.JSONDecodeError:
        m = _re.search(r"\{.*\}", json_text, _re.DOTALL)
        if m:
            try:
                obj = _json.loads(m.group(0))
            except Exception:
                pass
    if not obj or not isinstance(obj.get("nodes"), list):
        logger.error("Builder chat: could not parse AI response: %s", result[:400])
        return JSONResponse(
            {"error": "Could not parse AI response — try rephrasing or simplify the request"},
            status_code=500,
        )

    reply = str(obj.get("reply", "Done."))
    updated_nodes_raw = obj["nodes"]
    if len(updated_nodes_raw) < 1:
        return JSONResponse({"error": "AI returned empty node list — try rephrasing"}, status_code=500)

    parsed = [_parse_node(n) for n in updated_nodes_raw]

    # Guard: re-inject manager if AI dropped it
    had_manager = any(n.get("type") == "manager" for n in nodes_raw)
    has_manager = any(n.get("type") == "manager" for n in parsed)
    if had_manager and not has_manager:
        _ensure_manager_node(parsed)
        reply += (" The Manager node was kept — it handles node failures, "
                  "collects your feedback, and reruns the workflow automatically.")

    return JSONResponse({
        "reply": reply,
        "nodes": [node_definition(n) for n in parsed],
    })


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


def _normalize_node_title(title: str) -> str:
    """Normalize generated node titles for fuzzy child-reference matching."""
    import re
    return re.sub(r"[^a-z0-9]+", "", str(title).lower())


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


def _repair_generated_agent_graph(description: str, nodes: list[dict]) -> None:
    """
    Make generated workflow JSON executable instead of merely descriptive.

    LLMs often create AI nodes that say "ask the user for X"; those must become
    real input nodes, otherwise the workflow just fakes the interaction.
    """
    _repair_agent_graph_core(description, nodes)


def _repair_generated_node(description: str, node: dict, index: int) -> None:
    text = f"{node.get('title', '')} {node.get('task', '')}".lower()
    node_type = str(node.get("type", "ai")).lower()
    if node_type not in {"ai", "shell", "http", "file", "deliver", "input", "condition", "loop", "transform", "join", "manager"}:
        node_type = "ai"

    if _looks_like_input_step(text):
        node_type = "input"
        if not node.get("task") or _looks_like_fake_input_instruction(node.get("task", "")):
            node["task"] = _initial_input_question(description)
    elif "human" in text and any(word in text for word in ("review", "approval", "approve", "confirm", "clarify")):
        node_type = "input"
        node["task"] = node.get("task") or "Review the previous output and provide approval, corrections, or clarification."
    elif any(word in text for word in ("loop", "iterate", "for each", "each job", "each item", "each listing")):
        node_type = "loop"
        node.setdefault("loop_max", 10)
    elif any(word in text for word in ("condition", "decide whether", "branch")):
        node_type = "condition"

    node["type"] = node_type
    node["ai"] = _choose_node_ai(node_type, text, node.get("ai"))

    if node_type == "ai" and any(word in text for word in ("validate", "quality", "review", "check", "rank", "score")):
        task = node.get("task", "")
        if "RETRY_PARENT:" not in task:
            node["task"] = (
                task.rstrip()
                + "\n\nIf the previous output is weak, incomplete, irrelevant, missing required details, or not usable, output exactly: RETRY_PARENT: <clear reason>."
            )
        node.setdefault("retry_max", 2)

    if node_type in {"shell", "http"}:
        node.setdefault("timeout", 60)
    if node_type == "input":
        node.setdefault("input_timeout", 3600)

        if index == 0 and _description_needs_initial_input(description):
            node["type"] = "input"
            if _looks_like_fake_input_instruction(node.get("task", "")):
                node["task"] = _initial_input_question(description)


def _looks_like_input_step(text: str) -> bool:
    return _repair_looks_like_input_step(text)


def _looks_like_fake_input_instruction(task: str) -> bool:
    return _repair_looks_like_fake_input_instruction(task)


def _description_needs_initial_input(description: str) -> bool:
    return _repair_description_needs_initial_input(description)


def _initial_input_question(description: str) -> str:
    return _repair_initial_input_question(description)


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
        return "(file uploaded; automatic text extraction is not available for this file type. Use the saved path above.)"
    except Exception as exc:
        return f"(file uploaded, but text extraction failed: {exc})"


def _choose_node_ai(node_type: str, text: str, requested_ai: str | None) -> str:
    return _repair_choose_node_ai(node_type, text, requested_ai)


def _short_title(title: str) -> str:
    title = str(title or "Collect User Input").strip()
    return title[:60] or "Collect User Input"


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
