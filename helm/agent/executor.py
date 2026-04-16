"""
helm/agent/executor.py — Agent DAG execution engine.

Traverses the agent graph in topological order, launching ready nodes
concurrently (up to PIPELINE_MAX_PARALLEL), injecting parent context,
streaming chunks via WebSocket, and broadcasting run state updates.
"""

import asyncio
import os
import time
from typing import Optional

import helm.state as _st
from helm.config import logger
from helm.session_mgr import make_session

from .models import (
    find_node, ready_nodes, is_run_done, run_state_payload,
    parent_nodes,
)
from .context import build_node_prompt


# ---------------------------------------------------------------------------
# Broadcast helpers
# ---------------------------------------------------------------------------

async def broadcast_run_update(run: dict):
    """Broadcast full run state to all WS clients."""
    from helm.broadcast import broadcast
    try:
        await broadcast({
            "type": "agent_run_update",
            "run": run_state_payload(run),
        })
    except Exception as exc:
        logger.error("Failed to broadcast agent run update: %s", exc)


async def broadcast_run_stream(run_id: str, node_id: str, chunk: str):
    """Broadcast a live stream chunk for a running node."""
    from helm.broadcast import broadcast
    try:
        await broadcast({
            "type": "agent_run_stream",
            "run_id": run_id,
            "node_id": node_id,
            "chunk": chunk,
        })
    except Exception as exc:
        logger.debug("agent_run_stream broadcast error: %s", exc)


# ---------------------------------------------------------------------------
# Concurrency limit (reuses the same env var as Pipeline)
# ---------------------------------------------------------------------------

def _max_parallel() -> int:
    return max(1, int(os.environ.get("PIPELINE_MAX_PARALLEL", "3")))


# ---------------------------------------------------------------------------
# Single node execution
# ---------------------------------------------------------------------------

async def _execute_node(run: dict, node: dict, semaphore: asyncio.Semaphore):
    """Execute one node: create session, build prompt, call AI, stream chunks."""
    from helm.ai_runner.core import process_message

    async with semaphore:
        node["status"] = "running"
        node["started_at"] = time.time()
        node["stream_buffer"] = ""
        await broadcast_run_update(run)

        # Notify Telegram if this run was triggered from Telegram
        tg_session_id = run.get("session_id")
        if run.get("trigger") == "telegram" and tg_session_id:
            await _tg_notify(
                run,
                f"● Running: {node['title']} → {node['ai']}",
            )

        # Determine CWD — use focused session's CWD if available
        from helm.session_mgr import session_cwd, focused_session
        fs = focused_session()
        cwd = fs["cwd"] if fs else session_cwd()

        # Create a child session for this node
        child_sess = make_session(node["ai"], cwd=cwd)
        child_sess["agent_run_id"] = run["id"]
        child_sess["agent_node_id"] = node["id"]
        node["session_id"] = child_sess["id"]

        # Build full prompt with parent context injected
        prompt = build_node_prompt(run, node)

        # Streaming hook — throttled to every 5th chunk
        _stream_count = [0]

        async def _stream_hook(chunk: str):
            node["stream_buffer"] = (node.get("stream_buffer", "") + chunk)[-2000:]
            _stream_count[0] += 1
            if _stream_count[0] % 5 == 0:
                await broadcast_run_stream(run["id"], node["id"], chunk)

        child_sess["_pipeline_stream_hook"] = _stream_hook

        try:
            output = await process_message(
                prompt, source="agent", session_id=child_sess["id"]
            )

            node["output"] = output
            node["status"] = "completed"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            node["stream_buffer"] = ""

            # Summarize if long so children get compact context
            node["output_summary"] = await _maybe_summarize(output, node["ai"])

            elapsed = f"{node['elapsed_seconds']:.1f}s"
            logger.info(
                "Agent run %s node %s (%s) completed in %s",
                run["id"][:8], node["id"], node["title"], elapsed,
            )

            if run.get("trigger") == "telegram":
                await _tg_notify(run, f"✓ Completed: {node['title']} ({elapsed})")

        except asyncio.CancelledError:
            node["status"] = "skipped"
            node["output"] = "(cancelled)"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            raise

        except Exception as exc:
            node["status"] = "failed"
            node["error"] = str(exc)
            node["output"] = f"Error: {exc}"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            logger.error(
                "Agent run %s node %s failed: %s",
                run["id"][:8], node["id"], exc,
            )
            if run.get("trigger") == "telegram":
                await _tg_notify(run, f"✗ Failed: {node['title']} — {exc}")

        finally:
            await broadcast_run_update(run)
            # Persist run state after each node
            try:
                from .storage import save_run
                save_run(run)
            except Exception as e:
                logger.warning("Could not save agent run: %s", e)


# ---------------------------------------------------------------------------
# Main executor entry point
# ---------------------------------------------------------------------------

async def execute_agent_run(run_id: str) -> None:
    """
    Execute an AgentRun from start to finish.

    Performs topological traversal of the DAG, launching ready nodes
    concurrently up to PIPELINE_MAX_PARALLEL.
    """
    run = _st.agent_runs.get(run_id)
    if not run:
        logger.error("execute_agent_run: run %s not found", run_id)
        return

    agent_id = run["agent_id"]
    agent = _st.agents.get(agent_id)

    logger.info(
        "Agent run %s starting (%s, %d nodes)",
        run_id[:8], run["agent_name"], len(run["nodes"]),
    )

    if run.get("trigger") == "telegram":
        await _tg_notify(
            run,
            f"▶ Starting agent: {run['agent_name']} ({len(run['nodes'])} nodes)",
        )

    semaphore = asyncio.Semaphore(_max_parallel())

    try:
        while True:
            if run["status"] == "cancelled":
                break

            # Check if all nodes are done
            if is_run_done(run):
                break

            # Find nodes that are ready to run now
            pending_ready = ready_nodes(run["nodes"])

            # Filter out nodes already running (status != pending)
            # ready_nodes already returns only pending nodes
            if not pending_ready:
                # Nothing ready — either everything is running or we're blocked
                # Check if any nodes are still running
                still_running = [n for n in run["nodes"] if n["status"] == "running"]
                if not still_running:
                    # Deadlock / orphaned nodes — mark remaining pending as skipped
                    for n in run["nodes"]:
                        if n["status"] == "pending":
                            n["status"] = "skipped"
                    break
                # Wait briefly then check again
                await asyncio.sleep(0.2)
                continue

            # Launch all ready nodes concurrently
            tasks = [
                asyncio.create_task(_execute_node(run, node, semaphore))
                for node in pending_ready
            ]
            # Wait for at least one to finish before re-checking readiness
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    except asyncio.CancelledError:
        run["status"] = "cancelled"
        for n in run["nodes"]:
            if n["status"] in ("pending", "running"):
                n["status"] = "skipped"
        logger.info("Agent run %s cancelled", run_id[:8])

    finally:
        # Finalize run
        if run["status"] == "running":
            failed = any(n["status"] == "failed" for n in run["nodes"])
            run["status"] = "failed" if failed else "completed"

        run["completed_at"] = time.time()
        await broadcast_run_update(run)

        # Update agent stats
        if agent:
            agent["last_run_at"] = run["completed_at"]
            agent["run_count"] = agent.get("run_count", 0) + 1
            try:
                from .storage import save_agent
                save_agent(agent)
            except Exception as e:
                logger.warning("Could not update agent stats: %s", e)

        # Persist final run state
        try:
            from .storage import save_run
            save_run(run)
        except Exception as e:
            logger.warning("Could not save final agent run: %s", e)

        # Evict from in-memory runs (keep only DB copy)
        _st.agent_runs.pop(run_id, None)

        # Telegram completion message
        progress = {s: 0 for s in ("completed", "failed", "skipped")}
        for n in run["nodes"]:
            progress[n["status"]] = progress.get(n["status"], 0) + 1
        total = len(run["nodes"])
        done = progress.get("completed", 0)

        if run.get("trigger") == "telegram":
            if run["status"] == "completed":
                await _tg_notify(run, f"✓ Agent complete — {done}/{total} steps succeeded")
            else:
                await _tg_notify(
                    run,
                    f"✗ Agent finished with errors — {done}/{total} succeeded, "
                    f"{progress.get('failed', 0)} failed",
                )

        logger.info(
            "Agent run %s finished: %s (%d/%d succeeded)",
            run_id[:8], run["status"], done, total,
        )


# ---------------------------------------------------------------------------
# Summarization helper
# ---------------------------------------------------------------------------

async def _maybe_summarize(output: str, ai: str) -> str:
    """Return output as-is if short, otherwise summarize via AI."""
    threshold = int(os.environ.get("PIPELINE_CONTEXT_THRESHOLD", "2000"))
    if not output or len(output) <= threshold:
        return output or ""

    truncated = output[:8000]
    summary_prompt = (
        "Summarize the following AI output concisely. "
        "Preserve ALL key information: file names, code snippets, decisions, numbers, conclusions. "
        "Keep it under 1500 characters.\n\n"
        f"---\n{truncated}\n---"
    )
    try:
        from helm.pipeline.planner import _call_planner_ai
        import os as _os
        planner = _os.environ.get("PIPELINE_PLANNER_AI", ai)
        summary = await _call_planner_ai(planner, summary_prompt, ".")
        if summary and len(summary) < len(output):
            return summary
    except Exception as exc:
        logger.warning("Agent context summarisation failed: %s", exc)

    return output[:threshold] + "\n\n…(output truncated)"


# ---------------------------------------------------------------------------
# Telegram notification helper
# ---------------------------------------------------------------------------

async def _tg_notify(run: dict, text: str):
    """Send a Telegram message in the context of the run's session."""
    try:
        from helm.broadcast import push_message
        await push_message(
            "system", text, source="agent", session_id=run.get("session_id")
        )
    except Exception as exc:
        logger.debug("agent tg_notify error: %s", exc)
