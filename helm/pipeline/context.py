"""
helm/pipeline/context.py — Smart context passing between pipeline steps.

Full output if short (<threshold), auto-summarized if long.
"""

import asyncio
import os
from typing import Optional

from helm.config import logger


# Default: 2000 chars. Override via PIPELINE_CONTEXT_THRESHOLD env var.
def _threshold() -> int:
    return int(os.environ.get("PIPELINE_CONTEXT_THRESHOLD", "2000"))


async def maybe_summarize(output: str, planner_ai: str) -> str:
    """Return output as-is if short, or summarize via planner AI if long."""
    if not output:
        return ""

    if len(output) <= _threshold():
        return output

    # Truncate input to avoid blowing the summarizer's context
    truncated = output[:8000]

    summary_prompt = (
        "Summarize the following AI output concisely. Preserve ALL key information: "
        "file names, code snippets, decisions, numbers, and conclusions. "
        "Keep it under 1500 characters.\n\n"
        f"---\n{truncated}\n---"
    )

    try:
        from helm.pipeline.planner import _call_planner_ai
        summary = await _call_planner_ai(planner_ai, summary_prompt, ".")
        if summary and len(summary) < len(output):
            logger.info("Context summarized: %d → %d chars", len(output), len(summary))
            return summary
    except Exception as exc:
        logger.warning("Context summarization failed: %s — using truncated output", exc)

    # Fallback: hard truncate with indicator
    return output[:_threshold()] + "\n\n…(output truncated)"


def build_step_context(pipeline: dict, step: dict) -> str:
    """Collect outputs from all dependency steps to build this step's input context."""
    from .models import find_step

    parts = []
    for dep_id in step.get("depends_on", []):
        dep = find_step(pipeline, dep_id)
        if not dep or dep.get("status") != "completed":
            continue

        # Prefer summary, fall back to full output
        text = dep.get("output_summary") or dep.get("output") or ""
        if text:
            parts.append(
                f"### Result from: {dep['title']} (by {dep['assigned_ai']})\n{text}"
            )

    if not parts:
        return ""

    return (
        "=== Context from previous pipeline steps ===\n\n"
        + "\n\n---\n\n".join(parts)
        + "\n\n=== End of context ==="
    )
