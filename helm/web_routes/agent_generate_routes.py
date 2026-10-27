"""
helm/web_routes/agent_generate_routes.py — Building an agent workflow with an AI:
from a description (/api/agents/generate) and through the builder chat.
"""

import asyncio
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from helm.config import logger
from helm.agent.models import (
    ensure_manager_node as _ensure_manager_node,
    make_node, node_definition,
)
from helm.agent.repair import (
    choose_node_ai as _repair_choose_node_ai,
    description_needs_initial_input as _repair_description_needs_initial_input,
    looks_like_fake_input_instruction as _repair_looks_like_fake_input_instruction,
    looks_like_input_step as _repair_looks_like_input_step,
    repair_agent_graph as _repair_agent_graph_core,
)
from .agent_routes import _initial_input_question, _parse_node

router = APIRouter()


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
    raw_nodes = None
    try:
        raw_nodes = _extract_json_array(result)
    except Exception:
        logger.debug("Couldn't find a JSON node list in the AI's reply", exc_info=True)
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
            except ValueError:
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


def _choose_node_ai(node_type: str, text: str, requested_ai: str | None) -> str:
    return _repair_choose_node_ai(node_type, text, requested_ai)


def _short_title(title: str) -> str:
    title = str(title or "Collect User Input").strip()
    return title[:60] or "Collect User Input"
