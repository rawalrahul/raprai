"""
helm/pipeline/cost.py — Token cost estimation for pipeline steps.

Estimates cost before execution based on prompt length, AI model, and expected output type.
"""

import os

# ---------------------------------------------------------------------------
# Per-AI token pricing (USD per 1K tokens, approximate)
# Format: {ai_key: {"input": cost_per_1k, "output": cost_per_1k}}
# ---------------------------------------------------------------------------

_PRICING = {
    "claude": {"input": 0.003, "output": 0.015},      # Claude Sonnet
    "gemini": {"input": 0.001, "output": 0.002},      # Gemini Pro
    "codex":  {"input": 0.003, "output": 0.015},      # OpenAI Codex / GPT-4
    "ollama": {"input": 0.0,   "output": 0.0},         # Local = free
    "openai": {"input": 0.005, "output": 0.015},      # GPT-4o
}

# Multiplier for expected output types (rough output length estimates)
_OUTPUT_MULTIPLIERS = {
    "text": 1.0,
    "code": 1.5,
    "file": 2.0,
    "analysis": 1.2,
}


def _chars_to_tokens(chars: int) -> int:
    """Rough character-to-token conversion (avg ~4 chars per token for English)."""
    return max(1, chars // 4)


def calculate_cost(ai_key: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost from actual token counts using the pricing table.

    Returns cost in USD (e.g. 0.0035 for $0.0035).
    Falls back to "openai" pricing for unknown AI keys.
    """
    pricing = _PRICING.get(ai_key, _PRICING.get("openai", {"input": 0.005, "output": 0.015}))
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000.0


def get_pricing(ai_key: str) -> dict:
    """Return pricing dict for an AI key (or openai default)."""
    return _PRICING.get(ai_key, _PRICING.get("openai", {"input": 0.005, "output": 0.015}))


def estimate_step_cost(step: dict, context_length: int = 0) -> dict:
    """
    Estimate token usage and cost for a single step.

    Returns: {"input_tokens", "output_tokens", "total_tokens", "cost_usd"}
    """
    ai = step.get("assigned_ai", "claude")
    pricing = _PRICING.get(ai, _PRICING.get("claude"))

    # Input tokens: description + context from deps
    desc_len = len(step.get("description", ""))
    input_chars = desc_len + context_length
    input_tokens = _chars_to_tokens(input_chars)

    # Output tokens: estimate based on expected output type
    output_type = step.get("expected_output", "text")
    multiplier = _OUTPUT_MULTIPLIERS.get(output_type, 1.0)
    # Base estimate: output is usually ~60% of input for most tasks
    output_tokens = int(input_tokens * 0.6 * multiplier)

    # Minimum output estimate
    output_tokens = max(output_tokens, 200)

    total_tokens = input_tokens + output_tokens

    cost_usd = (
        (input_tokens / 1000) * pricing["input"]
        + (output_tokens / 1000) * pricing["output"]
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }


def estimate_pipeline_cost(pipeline: dict) -> dict:
    """
    Estimate total cost for an entire pipeline.

    Updates each step's estimated_tokens and estimated_cost_usd fields.
    Returns: {"total_tokens", "total_cost_usd", "per_step": [{step_id, ...}]}
    """
    from .models import find_step

    total_tokens = 0
    total_cost = 0.0
    per_step = []

    for step in pipeline["steps"]:
        # Estimate context length from dependencies
        context_len = 0
        for dep_id in step.get("depends_on", []):
            dep = find_step(pipeline, dep_id)
            if dep:
                # Assume ~2000 chars context per dep (summary or truncated)
                context_len += min(2000, len(dep.get("description", "")) + 500)

        est = estimate_step_cost(step, context_length=context_len)

        step["estimated_tokens"] = est["total_tokens"]
        step["estimated_cost_usd"] = est["cost_usd"]

        total_tokens += est["total_tokens"]
        total_cost += est["cost_usd"]

        per_step.append({
            "step_id": step["id"],
            "ai": step["assigned_ai"],
            **est,
        })

    pipeline["estimated_total_cost"] = round(total_cost, 6)

    return {
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "per_step": per_step,
    }
