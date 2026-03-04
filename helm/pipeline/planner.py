"""
helm/pipeline/planner.py — AI-powered task decomposition.

Takes a user's complex prompt and uses a configurable AI to decompose it
into a structured task graph (Pipeline with PipelineSteps).
"""

import asyncio
import json
import os
import re
import shutil
from typing import Optional

from helm.config import logger
from .models import make_pipeline, make_step, compute_edges, validate_dag


# ---------------------------------------------------------------------------
# Planner meta-prompt
# ---------------------------------------------------------------------------

_PLANNER_PROMPT_TEMPLATE = """\
You are a task planner for a multi-AI orchestration system called RAPR AI.

Your job: decompose the user's complex request into a structured set of subtasks \
that can be assigned to different AIs and executed in sequence or in parallel.

## Available AIs and their strengths

{ai_descriptions}

## User's request

{prompt}

## Working directory

{cwd}

## Instructions

Analyze the user's request and break it into 2-8 clear, actionable subtasks.

For each subtask:
- Give it a short, descriptive title (3-6 words)
- Write a complete, self-contained prompt that the assigned AI can execute independently
- Assign the best-fit AI based on the task nature
- List dependencies: if this step needs output from a prior step, list that step's ID
- Steps with NO shared dependencies can run in parallel

Output ONLY valid JSON — no explanation, no markdown fences, just the JSON object:

{{
  "steps": [
    {{
      "id": "step-1",
      "title": "Short descriptive title",
      "description": "Full detailed prompt for the AI to execute this subtask.",
      "assigned_ai": "claude",
      "depends_on": [],
      "expected_output": "text",
      "fallback_ais": ["gemini"]
    }},
    {{
      "id": "step-2",
      "title": "Another task title",
      "description": "Full prompt for this task. Reference step-1's output if needed.",
      "assigned_ai": "gemini",
      "depends_on": ["step-1"],
      "expected_output": "code",
      "fallback_ais": ["claude"]
    }},
    {{
      "id": "step-3",
      "title": "Conditional review step",
      "description": "Review the code only if step-2 produced code output.",
      "assigned_ai": "claude",
      "depends_on": ["step-2"],
      "expected_output": "analysis",
      "condition": {{"check": "step-2", "field": "status", "equals": "completed"}},
      "fallback_ais": []
    }}
  ]
}}

Rules:
- Step IDs must be sequential: step-1, step-2, step-3, etc.
- expected_output must be one of: "text", "code", "file", "analysis"
- Only assign AIs from the available list above
- Keep descriptions detailed enough that the AI can work independently
- If a step needs output from a dependency, mention it: "Using the analysis from the previous step..."
- Don't over-decompose: 2-5 steps for moderate tasks, up to 8 for very complex ones
- fallback_ais: list of alternative AIs to try if the primary fails (ordered by preference). Optional — omit or set to [] if no fallback needed
- condition: optional — makes a step conditional on a prior step's result. Format: {{"check": "step-id", "field": "status"|"output", "equals"|"contains": "value"}}. If the condition is not met, the step is skipped. Use sparingly — only when a step genuinely depends on a specific outcome
"""


# ---------------------------------------------------------------------------
# AI descriptions (used in planner prompt)
# ---------------------------------------------------------------------------

_AI_DESCRIPTIONS = {
    "claude": "claude — Best for complex reasoning, analysis, long-form writing, "
              "code review, architectural decisions, and nuanced tasks",
    "gemini": "gemini — Good for research, summarisation, web-aware tasks, "
              "quick analysis, and information gathering",
    "codex":  "codex — Specialized for code generation, refactoring, debugging, "
              "writing tests, and implementation tasks",
    "ollama": "ollama ({model}) — Local/private model, good for general tasks, "
              "file creation (presentations, documents, PDFs), and offline work",
}


def _build_ai_descriptions(available_ais: list[str],
                           ollama_model: str = "") -> str:
    """Build the AI description block for the planner prompt."""
    lines = []
    for ai in available_ais:
        desc = _AI_DESCRIPTIONS.get(ai, f"{ai} — General-purpose AI")
        if ai == "ollama" and ollama_model:
            desc = desc.replace("{model}", ollama_model)
        else:
            desc = desc.replace(" ({model})", "")
        lines.append(f"- {desc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Planner AI dispatch
# ---------------------------------------------------------------------------

def _get_ollama_model() -> str:
    """Resolve the Ollama model: default_models > env var > fallback."""
    import helm.state as _st
    return (_st.default_models.get("ollama", "")
            or os.environ.get("OLLAMA_MODEL", "")
            or "qwen3:4b")


async def _call_planner_ai(planner_ai: str, prompt: str, cwd: str) -> str:
    """Call the planner AI and return raw text output."""
    from helm.ai_runner.core import run_ai_popen
    import helm.state as _st

    logger.info("Calling planner AI: %s (cwd=%s, prompt_len=%d)",
                planner_ai, cwd, len(prompt))

    if planner_ai == "claude":
        try:
            from helm.ai_runner.claude import build_claude_cmd, parse_claude_json_output
            # Planner runs non-interactively — no human to approve permissions
            cmd = build_claude_cmd(prompt, has_history=False, auto_approve=True)
            raw = await asyncio.to_thread(run_ai_popen, cmd, cwd, "claude", {})
            if not raw or not raw.strip():
                logger.error("Claude planner returned empty output — "
                             "is Claude CLI installed and authenticated?")
                return ""
            parsed = parse_claude_json_output(raw)
            return parsed["text"]
        except Exception as exc:
            logger.error("Claude planner call failed: %s", exc, exc_info=True)
            raise RuntimeError(
                f"Claude planner failed: {exc}. "
                f"Check that Claude CLI is installed (`claude --version`) "
                f"and authenticated."
            ) from exc

    elif planner_ai == "ollama":
        import urllib.request
        model = _get_ollama_model()
        logger.info("Ollama planner using model: %s", model)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a task planner. Output ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            result = (data.get("message", {}).get("content") or "").strip()
            if not result:
                logger.error("Ollama planner returned empty content (model=%s)", model)
            return result
        except urllib.error.URLError as exc:
            logger.error("Ollama planner unreachable: %s — is `ollama serve` running?", exc)
            raise RuntimeError(
                f"Cannot reach Ollama at localhost:11434 — is `ollama serve` running? ({exc})"
            ) from exc
        except Exception as exc:
            logger.error("Ollama planner call failed (model=%s): %s", model, exc, exc_info=True)
            raise RuntimeError(f"Ollama planner error (model={model}): {exc}") from exc

    elif planner_ai in _st.integrations:
        try:
            integration = _st.integrations[planner_ai]
            cmd = integration["build_command"](prompt, model=None)
            raw = await asyncio.to_thread(run_ai_popen, cmd, cwd, planner_ai, {})
            if not raw or not raw.strip():
                logger.error("%s planner returned empty output", planner_ai)
            return raw
        except Exception as exc:
            logger.error("%s planner call failed: %s", planner_ai, exc, exc_info=True)
            raise RuntimeError(
                f"{planner_ai} planner failed: {exc}. "
                f"Check that {planner_ai} CLI is installed and configured."
            ) from exc

    logger.error("Unknown planner AI: %s — no handler found", planner_ai)
    raise RuntimeError(
        f"Unknown planner AI '{planner_ai}'. "
        f"Set PIPELINE_PLANNER_AI to one of: claude, ollama, gemini, codex"
    )


def _parse_planner_json(raw: str) -> Optional[dict]:
    """Extract JSON from planner AI response (handles markdown fences, etc)."""
    text = raw.strip()

    # Strip markdown code fences
    fence = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if fence:
        text = fence.group(1)

    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Find first { ... } block
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


# ---------------------------------------------------------------------------
# Available AI discovery
# ---------------------------------------------------------------------------

def discover_available_ais() -> list[str]:
    """Return list of AI keys that are currently available."""
    import helm.state as _st
    available = []

    # Built-in CLIs
    if shutil.which("claude"):
        available.append("claude")
    if shutil.which("ollama"):
        available.append("ollama")

    # Registered integrations (gemini, codex, etc.)
    for key in _st.integrations:
        if key not in available:
            available.append(key)

    return available


def _pick_planner_ai(preferred: str, available: list[str]) -> str:
    """Pick the planner AI — preferred if available, else best fallback."""
    if preferred in available:
        return preferred

    # Priority: claude > gemini > ollama > first available
    for fallback in ("claude", "gemini", "ollama"):
        if fallback in available:
            return fallback

    return available[0] if available else "claude"


# ---------------------------------------------------------------------------
# Complexity detection (for auto-suggest)
# ---------------------------------------------------------------------------

_MULTI_TASK_PATTERNS = [
    re.compile(r'\b(?:first|then|next|after that|finally|step \d+|phase \d+)\b', re.I),
    re.compile(r'\b(?:and also|additionally|moreover|furthermore)\b', re.I),
    re.compile(r'^\s*\d+[.)]\s', re.MULTILINE),          # numbered lists
    re.compile(r'^\s*[-*]\s', re.MULTILINE),               # bullet lists
]

_ACTION_VERBS = re.compile(
    r'\b(?:create|build|implement|write|design|analyze|research|test|deploy|'
    r'generate|review|optimize|refactor|compare|summarize|set up|configure|'
    r'integrate|migrate|convert|document)\b', re.I
)


def looks_complex(text: str) -> bool:
    """Heuristic: does this prompt look like it needs pipeline decomposition?"""
    # Short prompts are rarely complex enough
    if len(text) < 150:
        return False

    score = 0

    # Count distinct action verbs
    verbs = set(v.lower() for v in _ACTION_VERBS.findall(text))
    if len(verbs) >= 3:
        score += 2
    elif len(verbs) >= 2:
        score += 1

    # Check for sequential/multi-task language
    for pat in _MULTI_TASK_PATTERNS:
        if pat.search(text):
            score += 1

    # Long prompts with multiple sentences
    sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if s.strip()]
    if len(sentences) >= 4:
        score += 1

    return score >= 3


# ---------------------------------------------------------------------------
# Main planner entry point
# ---------------------------------------------------------------------------

async def plan_pipeline(
    prompt: str,
    session_id: str,
    cwd: str,
    planner_ai: str = "claude",
    max_retries: int = 2,
) -> dict:
    """
    Decompose a user prompt into a Pipeline with steps.

    1. Build meta-prompt
    2. Call planner AI
    3. Parse JSON response
    4. Validate DAG
    5. Return Pipeline dict with status="awaiting_approval"
    """
    available = discover_available_ais()
    if not available:
        raise RuntimeError(
            "No AIs available. Install at least one: "
            "Claude CLI, Ollama, Gemini CLI, or Codex CLI."
        )

    actual_planner = _pick_planner_ai(planner_ai, available)
    if actual_planner != planner_ai:
        logger.warning(
            "Preferred planner '%s' not available — falling back to '%s'",
            planner_ai, actual_planner,
        )

    logger.info(
        "Planning pipeline: planner=%s, available_ais=%s, prompt_len=%d",
        actual_planner, available, len(prompt),
    )

    ollama_model = _get_ollama_model()
    ai_desc = _build_ai_descriptions(available, ollama_model)

    meta_prompt = _PLANNER_PROMPT_TEMPLATE.format(
        ai_descriptions=ai_desc,
        prompt=prompt,
        cwd=cwd,
    )

    # Try calling the planner AI with retries
    parsed = None
    last_error = ""
    for attempt in range(1, max_retries + 1):
        logger.info("Pipeline planner attempt %d/%d via %s",
                     attempt, max_retries, actual_planner)

        raw = await _call_planner_ai(actual_planner, meta_prompt, cwd)
        if not raw:
            last_error = f"Planner AI ({actual_planner}) returned empty response"
            continue

        parsed = _parse_planner_json(raw)
        if parsed and "steps" in parsed:
            break
        else:
            last_error = f"Could not parse JSON from planner response: {raw[:200]}"
            # On retry, add a stronger hint
            meta_prompt += (
                "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Output ONLY the JSON object — no markdown, no explanation."
            )

    if not parsed or "steps" not in parsed:
        # Fallback: create a single-step pipeline (run the whole thing as one task)
        logger.warning("Planner failed after %d attempts (%s) — creating single-step pipeline",
                       max_retries, last_error)
        pipeline = make_pipeline(prompt, session_id, cwd, planner_ai=actual_planner)
        best_ai = available[0] if available else "claude"
        pipeline["steps"] = [
            make_step("step-1", "Execute task", prompt, assigned_ai=best_ai)
        ]
        pipeline["status"] = "awaiting_approval"
        compute_edges(pipeline)
        return pipeline

    # Build Pipeline from parsed response
    pipeline = make_pipeline(prompt, session_id, cwd, planner_ai=actual_planner)

    for raw_step in parsed["steps"]:
        sid = raw_step.get("id", f"step-{len(pipeline['steps']) + 1}")
        title = raw_step.get("title", "Untitled step")
        desc = raw_step.get("description", "")
        ai = raw_step.get("assigned_ai", "claude")
        deps = raw_step.get("depends_on", [])
        expected = raw_step.get("expected_output", "text")
        condition = raw_step.get("condition")
        fallback_ais = raw_step.get("fallback_ais", [])

        # Validate assigned AI is available
        if ai not in available:
            ai = available[0] if available else "claude"

        # Validate fallback AIs
        fallback_ais = [fa for fa in fallback_ais if fa in available and fa != ai]

        # Auto-generate fallback if none provided: pick a different AI
        if not fallback_ais:
            for candidate in available:
                if candidate != ai:
                    fallback_ais = [candidate]
                    break

        step = make_step(sid, title, desc, assigned_ai=ai,
                         depends_on=deps, expected_output=expected,
                         condition=condition, fallback_ais=fallback_ais)
        pipeline["steps"].append(step)

    compute_edges(pipeline)

    # Validate DAG
    errors = validate_dag(pipeline)
    if errors:
        logger.warning("Pipeline DAG validation errors: %s", errors)
        # Remove circular deps as best effort
        for step in pipeline["steps"]:
            step["depends_on"] = [
                d for d in step["depends_on"]
                if d in {s["id"] for s in pipeline["steps"]}
            ]
        compute_edges(pipeline)

    pipeline["status"] = "awaiting_approval"

    # Estimate cost before presenting to user for approval
    from .cost import estimate_pipeline_cost
    estimate_pipeline_cost(pipeline)

    return pipeline
