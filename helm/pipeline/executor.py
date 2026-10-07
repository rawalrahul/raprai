"""
helm/pipeline/executor.py — Pipeline orchestration engine.

Manages the execution of a pipeline: launches steps in parallel (up to
concurrency limit), passes context between dependent steps, handles
retries and failures, and broadcasts live updates.
"""

import asyncio
import os
import pathlib
import time
from typing import Optional

import helm.state as _st
from helm.config import logger
from helm.broadcast import push_message, push_state
from helm.session_mgr import make_session

from .models import (
    find_step, ready_steps, is_pipeline_done, is_pipeline_blocked,
    pipeline_state_payload, pipeline_progress, compute_edges,
)
from .context import build_step_context, maybe_summarize


# ---------------------------------------------------------------------------
# Broadcast helper
# ---------------------------------------------------------------------------

async def broadcast_pipeline_update(pipeline: dict):
    """Send pipeline state to all WS clients + track in chat history."""
    from helm.broadcast import broadcast
    if not _st.ws_clients:
        logger.debug(
            "Pipeline update for %s but no WS clients connected — "
            "UI won't update until a client reconnects",
            pipeline.get("id", "?")[:8],
        )
    try:
        await broadcast({
            "type": "pipeline_update",
            "pipeline": pipeline_state_payload(pipeline),
        })
    except Exception as exc:
        logger.error("Failed to broadcast pipeline update: %s", exc)


async def broadcast_step_stream(pipeline_id: str, step_id: str, chunk: str):
    """Send a live streaming chunk for a running step."""
    from helm.broadcast import broadcast
    await broadcast({
        "type": "pipeline_step_stream",
        "pipeline_id": pipeline_id,
        "step_id": step_id,
        "chunk": chunk,
    })


# ---------------------------------------------------------------------------
# Concurrency limit
# ---------------------------------------------------------------------------

def _max_parallel() -> int:
    return max(1, int(os.environ.get("PIPELINE_MAX_PARALLEL", "3")))


# ---------------------------------------------------------------------------
# Single step execution
# ---------------------------------------------------------------------------

def _build_artifact_context(pipeline: dict, step: dict) -> str:
    """Build file artifact context from dependency steps' artifact registries."""
    parts = []
    registry = pipeline.get("artifact_registry", {})
    for dep_id in step.get("depends_on", []):
        dep_artifacts = registry.get(dep_id, [])
        if dep_artifacts:
            lines = [f"Files from '{dep_id}':"]
            for af in dep_artifacts:
                lines.append(f"  - {af['name']} ({af['path']}, {af.get('size', '?')} bytes)")
            parts.append("\n".join(lines))
    if parts:
        return "\n\n=== File artifacts from previous steps ===\n" + "\n".join(parts) + "\n=== End artifacts ===\n"
    return ""


async def _execute_step(pipeline: dict, step: dict, semaphore: asyncio.Semaphore):
    """Execute one pipeline step in its own session.

    Features: live streaming, artifact handoff, cost tracking, auto-fallback retry.
    """
    from helm.ai_runner.core import process_message

    async with semaphore:
        sid = pipeline["session_id"]  # parent session for notifications
        step_ai = step["assigned_ai"]

        # Build context from dependencies
        context = build_step_context(pipeline, step)

        # Build artifact context (file handoff)
        artifact_ctx = _build_artifact_context(pipeline, step)

        # Build the full prompt
        prompt = step["description"]
        if context:
            prompt = f"{context}\n\n---\n\nYour task:\n{prompt}"
        if artifact_ctx:
            prompt += f"\n\n{artifact_ctx}"

        # Add artifacts directory instruction
        artifacts_path = pathlib.Path(pipeline["cwd"]) / pipeline["artifacts_dir"] / step["id"]
        artifacts_path.mkdir(parents=True, exist_ok=True)
        prompt += (
            f"\n\nSave any output files to this directory: "
            f"{artifacts_path.resolve()}"
        )

        # ── Destructive step check — always require approval for destructive ops ──
        import helm.approval as _appr
        combined_text = f"{step['title']} {step['description']}"
        if _appr.looks_destructive(combined_text):
            approval_req = _appr.create_request(
                session_id=sid,
                action="pipeline_step",
                description=(
                    f"Pipeline step **{step['title']}** (via {step_ai}) "
                    f"may perform destructive operations (delete/remove files)"
                ),
                details=[step["description"][:200]],
                pipeline_id=pipeline["id"],
                step_id=step["id"],
            )
            await _appr.broadcast_approval(approval_req)
            await push_message(
                "system",
                f"⚠️ Step **{step['title']}** may delete or modify files.\n"
                f"Approve or deny via the UI banner or Telegram.",
                source="pipeline", session_id=sid,
            )
            result = await _appr.wait(approval_req["id"], timeout=300)
            if result != "approved":
                step["status"] = "skipped"
                step["output"] = f"(step {result} by user)"
                step["output_summary"] = step["output"]
                step["completed_at"] = time.time()
                step["elapsed_seconds"] = 0
                await push_message(
                    "system",
                    f"⏭️ Step **{step['title']}** skipped — {result}",
                    source="pipeline", session_id=sid,
                )
                await broadcast_pipeline_update(pipeline)
                return

        # Create child session for this step
        child_sess = make_session(step_ai, cwd=pipeline["cwd"])
        child_sess["pipeline_id"] = pipeline["id"]
        child_sess["pipeline_step_id"] = step["id"]
        step["session_id"] = child_sess["id"]
        step["status"] = "running"
        step["started_at"] = time.time()
        step["stream_buffer"] = ""

        await broadcast_pipeline_update(pipeline)
        await push_message(
            "system",
            f"▶️ Pipeline step **{step['title']}** started → {step_ai}",
            source="pipeline", session_id=sid,
        )

        # Set up streaming callback for this step
        _stream_count = [0]

        async def _stream_hook(chunk: str):
            """Called periodically with output chunks during step execution."""
            step["stream_buffer"] = (step.get("stream_buffer", "") + chunk)[-2000:]
            _stream_count[0] += 1
            # Broadcast every 5th chunk to avoid flooding
            if _stream_count[0] % 5 == 0:
                await broadcast_step_stream(pipeline["id"], step["id"], chunk)

        # Store streaming hook on child session so AI runner can call it
        child_sess["_pipeline_stream_hook"] = _stream_hook

        try:
            output = await process_message(
                prompt, source="pipeline", session_id=child_sess["id"]
            )

            step["output"] = output
            step["status"] = "completed"
            step["completed_at"] = time.time()
            step["elapsed_seconds"] = step["completed_at"] - step["started_at"]
            step["stream_buffer"] = ""  # clear buffer after completion

            # Smart context: summarize if long
            step["output_summary"] = await maybe_summarize(
                output, pipeline["planner_ai"]
            )

            # Capture file artifacts + register in pipeline artifact registry
            if artifacts_path.exists():
                step_artifacts = []
                artifact_files = []
                for f in artifacts_path.rglob("*"):
                    if not f.is_file():
                        continue
                    rel = str(f.relative_to(pathlib.Path(pipeline["cwd"])))
                    step_artifacts.append(rel)
                    artifact_files.append({
                        "name": f.name,
                        "path": str(f.resolve()),
                        "size": f.stat().st_size,
                        "type": f.suffix.lstrip(".") or "unknown",
                    })
                step["artifacts"] = step_artifacts
                step["artifact_files"] = artifact_files
                # Register in pipeline-level artifact registry for downstream steps
                if artifact_files:
                    pipeline.setdefault("artifact_registry", {})[step["id"]] = artifact_files

            # Track actual cost (from session usage_stats if available)
            usage = child_sess.get("usage_stats", {})
            step["actual_tokens"] = usage.get("total_tokens", 0)
            if step["actual_tokens"]:
                from helm.pipeline.cost import _PRICING, _chars_to_tokens
                pricing = _PRICING.get(step_ai, _PRICING.get("claude"))
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
                step["actual_cost_usd"] = round(
                    (in_tok / 1000) * pricing["input"]
                    + (out_tok / 1000) * pricing["output"], 6
                )
                pipeline["actual_total_cost"] = round(
                    pipeline.get("actual_total_cost", 0) + step["actual_cost_usd"], 6
                )

            await push_message(
                "system",
                f"✅ Pipeline step **{step['title']}** completed "
                f"({step['elapsed_seconds']:.1f}s)"
                f"{' · $'+format(step['actual_cost_usd'],'.4f') if step.get('actual_cost_usd') else ''}",
                source="pipeline", session_id=sid,
            )

        except Exception as exc:
            step["error"] = str(exc)
            step["completed_at"] = time.time()
            step["elapsed_seconds"] = (step["completed_at"] or 0) - (step["started_at"] or 0)

            # Classify the error for better diagnostics
            err_str = str(exc)
            if "not found" in err_str.lower() or "not recognized" in err_str.lower():
                err_hint = f"(AI `{step_ai}` may not be installed)"
            elif "timeout" in err_str.lower():
                err_hint = "(request timed out — AI may be overloaded)"
            elif "connection" in err_str.lower() or "urlopen" in err_str.lower():
                err_hint = f"(cannot reach `{step_ai}` — is it running?)"
            else:
                err_hint = ""

            logger.error(
                "Pipeline step %s (%s via %s) failed after %.1fs: %s",
                step["id"], step["title"], step_ai,
                step["elapsed_seconds"], exc, exc_info=True,
            )

            # --- Auto-fallback retry with different AI ---
            fallback_ais = step.get("fallback_ais", [])
            fallback_idx = step.get("fallback_index", 0)

            if fallback_idx < len(fallback_ais):
                next_ai = fallback_ais[fallback_idx]
                step["fallback_index"] = fallback_idx + 1
                step["assigned_ai"] = next_ai
                step["status"] = "pending"
                step["error"] = None
                step["output"] = None
                step["stream_buffer"] = ""
                step["retry_count"] = step.get("retry_count", 0) + 1

                logger.info("Step %s failed with %s — auto-fallback to %s",
                            step["id"], step_ai, next_ai)
                await push_message(
                    "system",
                    f"⚠️ Step **{step['title']}** failed with {step_ai} — "
                    f"retrying with {next_ai}…\n"
                    f"Error: `{err_str[:150]}`",
                    source="pipeline", session_id=sid,
                )
            else:
                step["status"] = "failed"
                await push_message(
                    "system",
                    f"❌ Pipeline step **{step['title']}** failed\n"
                    f"**AI:** {step_ai}\n"
                    f"**Error:** `{err_str[:200]}` {err_hint}\n"
                    f"**Fallbacks exhausted** — retry manually or skip this step",
                    source="pipeline", session_id=sid,
                )

        finally:
            # Clean up child session (stop it, keep for inspection)
            child_sess["busy"] = False
            child_sess["task_start"] = None
            child_sess["status"] = "stopped"
            child_sess.pop("_pipeline_stream_hook", None)
            await broadcast_pipeline_update(pipeline)
            await push_state()


# ---------------------------------------------------------------------------
# Step retry
# ---------------------------------------------------------------------------

async def retry_step(pipeline: dict, step_id: str) -> bool:
    """Retry a failed step. Returns True if retry was started."""
    step = find_step(pipeline, step_id)
    if not step or step["status"] != "failed":
        return False

    if step["retry_count"] >= step.get("max_retries", 2):
        logger.warning("Step %s has exceeded max retries (%d)", step_id, step["retry_count"])
        return False

    step["retry_count"] += 1
    step["status"] = "pending"
    step["error"] = None
    step["output"] = None
    step["output_summary"] = None
    step["session_id"] = None

    logger.info("Retrying step %s (attempt %d)", step_id, step["retry_count"] + 1)

    # If pipeline is not running, restart the executor
    if pipeline["status"] in ("failed", "paused"):
        pipeline["status"] = "running"
        asyncio.create_task(execute_pipeline(pipeline["id"]))

    return True


# ---------------------------------------------------------------------------
# Step reassignment
# ---------------------------------------------------------------------------

async def reassign_step(pipeline: dict, step_id: str, new_ai: str) -> bool:
    """Change the AI assignment for a pending or failed step."""
    step = find_step(pipeline, step_id)
    if not step or step["status"] not in ("pending", "failed"):
        return False

    step["assigned_ai"] = new_ai
    if step["status"] == "failed":
        step["status"] = "pending"
        step["error"] = None
        step["retry_count"] = 0

    await broadcast_pipeline_update(pipeline)
    return True


# ---------------------------------------------------------------------------
# Skip step
# ---------------------------------------------------------------------------

async def skip_step(pipeline: dict, step_id: str) -> bool:
    """Skip a pending or failed step."""
    step = find_step(pipeline, step_id)
    if not step or step["status"] not in ("pending", "failed"):
        return False

    step["status"] = "skipped"
    step["output"] = "(step skipped by user)"
    step["output_summary"] = "(step skipped by user)"
    await broadcast_pipeline_update(pipeline)
    return True


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

async def execute_pipeline(pipeline_id: str) -> None:
    """
    Main orchestration loop. Runs steps in parallel (up to concurrency limit)
    as their dependencies complete. Blocks until pipeline is done/failed/cancelled.
    """
    pipeline = _st.pipelines.get(pipeline_id)
    if not pipeline:
        logger.error("Pipeline %s not found", pipeline_id)
        return

    sid = pipeline["session_id"]
    pipeline["status"] = "running"
    pipeline["started_at"] = time.time()

    # Create artifacts directory
    artifacts_base = pathlib.Path(pipeline["cwd"]) / pipeline["artifacts_dir"]
    artifacts_base.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(_max_parallel())
    running_tasks: dict[str, asyncio.Task] = {}  # step_id -> Task

    await broadcast_pipeline_update(pipeline)
    prog = pipeline_progress(pipeline)
    await push_message(
        "system",
        f"🚀 Pipeline started — {prog['total']} steps, "
        f"max {_max_parallel()} parallel",
        source="pipeline", session_id=sid,
    )

    try:
        while True:
            # Check for pause/cancel
            if pipeline["status"] == "paused":
                await push_message(
                    "system", "⏸️ Pipeline paused. Resume to continue.",
                    source="pipeline", session_id=sid,
                )
                # Wait until unpaused or cancelled
                while pipeline["status"] == "paused":
                    await asyncio.sleep(1)
                if pipeline["status"] == "cancelled":
                    break

            if pipeline["status"] == "cancelled":
                break

            # Clean up finished tasks
            done_ids = [
                sid for sid, t in running_tasks.items() if t.done()
            ]
            for did in done_ids:
                task = running_tasks.pop(did)
                # Re-raise any exceptions from the task
                if task.exception():
                    logger.error("Step task exception: %s", task.exception())

            # Check if done
            if is_pipeline_done(pipeline):
                break

            # Check if blocked (all pending depend on failed)
            if is_pipeline_blocked(pipeline) and not running_tasks:
                pipeline["status"] = "failed"
                await push_message(
                    "system",
                    "❌ Pipeline blocked — remaining steps depend on failed steps. "
                    "Retry failed steps or skip them to continue.",
                    source="pipeline", session_id=sid,
                )
                break

            # Launch ready steps
            ready = ready_steps(pipeline)
            for step in ready:
                if step["id"] in running_tasks:
                    continue  # already launched

                task = asyncio.create_task(
                    _execute_step(pipeline, step, semaphore)
                )
                running_tasks[step["id"]] = task

            # Wait a bit before checking again
            if running_tasks:
                # Wait for at least one task to complete
                done, _ = await asyncio.wait(
                    running_tasks.values(),
                    timeout=2.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            else:
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        pipeline["status"] = "cancelled"
        logger.info("Pipeline %s was cancelled", pipeline_id)
    except Exception as exc:
        pipeline["status"] = "failed"
        logger.error("Pipeline %s orchestration error: %s", pipeline_id, exc, exc_info=True)
        await push_message(
            "system",
            f"❌ **Pipeline orchestration error:** `{str(exc)[:200]}`\n"
            f"The pipeline loop crashed unexpectedly. Check server logs for details.",
            source="pipeline", session_id=sid,
        )

    # Finalize
    if pipeline["status"] == "running":
        # All steps done
        all_completed = all(
            s["status"] in ("completed", "skipped")
            for s in pipeline["steps"]
        )
        pipeline["status"] = "completed" if all_completed else "failed"
        from helm.kelvin_stickers import kelvin_sticker_soon
        kelvin_sticker_soon("done" if all_completed else "error")

    pipeline["completed_at"] = time.time()

    # Assemble final output
    parts = []
    for step in pipeline["steps"]:
        status_icon = {"completed": "✅", "failed": "❌", "skipped": "⏭️"}.get(
            step["status"], "❓"
        )
        parts.append(f"{status_icon} **{step['title']}** ({step['assigned_ai']})")
        if step.get("output"):
            preview = step["output"][:300]
            if len(step["output"]) > 300:
                preview += "…"
            parts.append(preview)
        if step.get("artifacts"):
            parts.append("📁 Files: " + ", ".join(step["artifacts"]))
        parts.append("")

    pipeline["final_output"] = "\n".join(parts)

    elapsed = (pipeline["completed_at"] or 0) - (pipeline["started_at"] or 0)
    prog = pipeline_progress(pipeline)
    summary = (
        f"{'🎉' if pipeline['status'] == 'completed' else '⚠️'} "
        f"Pipeline **{pipeline['status']}** — "
        f"{prog['completed']} completed, {prog['failed']} failed, "
        f"{prog['skipped']} skipped in {elapsed:.1f}s"
    )

    await push_message("system", summary, source="pipeline", session_id=sid)
    await broadcast_pipeline_update(pipeline)
    await push_state()
