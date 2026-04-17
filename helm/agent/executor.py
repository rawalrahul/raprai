"""
helm/agent/executor.py - Agent DAG execution engine.

Traverses the agent graph in topological order, launching ready nodes
concurrently, injecting parent context, streaming chunks via WebSocket,
and routing nodes by type.
"""

import asyncio
import os
import re
import time

import helm.state as _st
from helm.config import logger
from helm.session_mgr import make_session

from .context import build_node_prompt
from .models import (
    find_node,
    is_run_done,
    parent_nodes,
    ready_nodes,
    run_state_payload,
)


async def broadcast_run_update(run: dict):
    """Broadcast full run state to all WS clients."""
    from helm.broadcast import broadcast
    try:
        await broadcast({"type": "agent_run_update", "run": run_state_payload(run)})
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


def _max_parallel() -> int:
    return max(1, int(os.environ.get("PIPELINE_MAX_PARALLEL", "3")))


def _extract_retry_request(output: str) -> str | None:
    """Return RETRY_PARENT reason from node output, if present."""
    match = re.search(r"RETRY_PARENT\s*:\s*(.+)", output or "", re.IGNORECASE)
    return match.group(1).strip() if match else None


def _should_retry_node(run: dict, node: dict) -> bool:
    """Return True if node should be retried, incrementing its counter."""
    max_retries = node.get("retry_max", 0)
    if not max_retries:
        return False
    retries = run.setdefault("node_retries", {})
    count = retries.get(node["id"], 0)
    if count < max_retries:
        retries[node["id"]] = count + 1
        return True
    return False


def _apply_condition_skips(run: dict) -> None:
    """Skip the unselected branch after completed condition nodes."""
    for node in run["nodes"]:
        if node.get("type") != "condition" or node.get("status") != "completed":
            continue
        children = node.get("children", [])
        if len(children) < 2:
            continue
        skip_id = children[1] if node.get("output") == "true" else children[0]
        skipped = find_node(run, skip_id)
        if skipped and skipped.get("status") == "pending":
            skipped["status"] = "skipped"
            skipped["output"] = "(skipped - condition branch not taken)"


async def _execute_node(run: dict, node: dict, semaphore: asyncio.Semaphore):
    """Execute one typed node."""
    from helm.ai_runner.core import process_message
    from helm.agent.context import build_node_context
    from helm.agent.nodes.condition import execute_condition_node
    from helm.agent.nodes.deliver import execute_deliver_node
    from helm.agent.nodes.file import execute_file_node
    from helm.agent.nodes.http import execute_http_node
    from helm.agent.nodes.input_node import execute_input_node
    from helm.agent.nodes.loop import parse_list_from_output
    from helm.agent.nodes.shell import execute_shell_node

    async with semaphore:
        node["status"] = "running"
        node["started_at"] = time.time()
        node["stream_buffer"] = ""
        await broadcast_run_update(run)

        if run.get("trigger") == "telegram" and run.get("session_id"):
            await _tg_notify(run, f"Running: {node['title']} -> {node.get('type', 'ai')}")

        from helm.session_mgr import focused_session, session_cwd
        fs = focused_session()
        cwd = fs["cwd"] if fs else session_cwd()

        node_type = node.get("type", "ai")
        context = build_node_context(run, node)

        try:
            if node_type == "shell":
                output = await execute_shell_node(node, context=context, cwd=cwd)
            elif node_type == "http":
                output = await execute_http_node(node, context=context)
            elif node_type == "file":
                output = await execute_file_node(node, context=context)
            elif node_type == "deliver":
                output = await execute_deliver_node(node, context=context)
            elif node_type == "condition":
                output = await execute_condition_node(node, context=context)
            elif node_type == "input":
                if not parent_nodes(run["nodes"], node["id"]) and run.get("input_data"):
                    output = run["input_data"]
                else:
                    run["status"] = "waiting_input"
                    await broadcast_run_update(run)
                    output = await execute_input_node(node, run=run, context=context)
                    run["status"] = "running"
            elif node_type == "loop":
                items = parse_list_from_output(context, max_items=node.get("loop_max", 10))
                output = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
                if not items:
                    output = "(no items to iterate)"
            else:
                child_sess = make_session(node.get("ai", "claude"), cwd=cwd)
                child_sess["agent_run_id"] = run["id"]
                child_sess["agent_node_id"] = node["id"]
                node["session_id"] = child_sess["id"]

                prompt = build_node_prompt(run, node)
                stream_count = [0]

                async def _stream_hook(chunk: str):
                    node["stream_buffer"] = (node.get("stream_buffer", "") + chunk)[-2000:]
                    stream_count[0] += 1
                    if stream_count[0] % 5 == 0:
                        await broadcast_run_stream(run["id"], node["id"], chunk)

                child_sess["_pipeline_stream_hook"] = _stream_hook
                output = await process_message(
                    prompt, source="agent", session_id=child_sess["id"]
                )

            retry_reason = _extract_retry_request(output)
            if retry_reason and node_type == "ai":
                retries = run.setdefault("feedback_retries", {})
                count = retries.get(node["id"], 0)
                if count < 3:
                    retries[node["id"]] = count + 1
                    for parent in parent_nodes(run["nodes"], node["id"]):
                        if parent.get("type", "ai") == "ai":
                            parent["status"] = "pending"
                            parent["output"] = None
                            parent["output_summary"] = None
                            parent["error"] = None
                            parent["_feedback"] = f"\n\n[Feedback from child node]: {retry_reason}"
                    node["status"] = "pending"
                    node["output"] = None
                    node["error"] = None
                    return

            node["output"] = output
            node["status"] = "completed"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            node["stream_buffer"] = ""
            node["output_summary"] = await _maybe_summarize(output, node.get("ai", "claude"))

            elapsed = f"{node['elapsed_seconds']:.1f}s"
            logger.info(
                "Agent run %s node %s (%s) completed in %s",
                run["id"][:8], node["id"], node["title"], elapsed,
            )

            if run.get("trigger") == "telegram":
                await _tg_notify(run, f"Completed: {node['title']} ({elapsed})")

        except asyncio.CancelledError:
            node["status"] = "skipped"
            node["output"] = "(cancelled)"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            raise

        except Exception as exc:
            if _should_retry_node(run, node):
                attempt = run.get("node_retries", {}).get(node["id"], 1)
                logger.info("Retrying node %s (attempt %d)", node["id"], attempt)
                node["status"] = "pending"
                node["error"] = None
                node["output"] = None
                return
            node["status"] = "failed"
            node["error"] = str(exc)
            node["output"] = f"Error: {exc}"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            logger.error("Agent run %s node %s failed: %s", run["id"][:8], node["id"], exc)
            if run.get("trigger") == "telegram":
                await _tg_notify(run, f"Failed: {node['title']} - {exc}")

        finally:
            await broadcast_run_update(run)
            try:
                from .storage import save_run
                save_run(run)
            except Exception as e:
                logger.warning("Could not save agent run: %s", e)


async def execute_agent_run(run_id: str) -> None:
    """Execute an AgentRun from start to finish."""
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
        await _tg_notify(run, f"Starting agent: {run['agent_name']} ({len(run['nodes'])} nodes)")

    semaphore = asyncio.Semaphore(_max_parallel())

    run_timeout = (agent or {}).get("run_timeout", 1800) if agent else 1800

    async def _run_loop():
        while True:
            if run["status"] == "cancelled":
                break
            if is_run_done(run):
                break
            pending_ready = ready_nodes(run["nodes"])
            if not pending_ready:
                still_running = [n for n in run["nodes"] if n["status"] == "running"]
                if not still_running:
                    for n in run["nodes"]:
                        if n["status"] == "pending":
                            n["status"] = "skipped"
                    break
                await asyncio.sleep(0.2)
                continue
            tasks = [
                asyncio.create_task(_execute_node(run, node, semaphore))
                for node in pending_ready
            ]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            _apply_condition_skips(run)

    try:
        if run_timeout and run_timeout > 0:
            await asyncio.wait_for(_run_loop(), timeout=run_timeout)
        else:
            await _run_loop()
    except asyncio.TimeoutError:
        run["timed_out"] = True
        run["status"] = "failed"
        for n in run["nodes"]:
            if n["status"] in ("pending", "running"):
                n["status"] = "skipped"
                n["error"] = "run timed out"
        logger.warning("Agent run %s timed out after %ss", run_id[:8], run_timeout)
        if run.get("trigger") == "telegram":
            await _tg_notify(run, f"Agent timed out after {run_timeout}s")
    except asyncio.CancelledError:
        run["status"] = "cancelled"
        for n in run["nodes"]:
            if n["status"] in ("pending", "running"):
                n["status"] = "skipped"
        logger.info("Agent run %s cancelled", run_id[:8])

    finally:
        if run["status"] in ("running", "waiting_input"):
            failed = any(n["status"] == "failed" for n in run["nodes"])
            run["status"] = "failed" if failed else "completed"

        run["completed_at"] = time.time()
        await broadcast_run_update(run)

        if agent:
            agent["last_run_at"] = run["completed_at"]
            agent["run_count"] = agent.get("run_count", 0) + 1
            try:
                from .storage import save_agent
                save_agent(agent)
            except Exception as e:
                logger.warning("Could not update agent stats: %s", e)

        try:
            from .storage import save_run
            save_run(run)
        except Exception as e:
            logger.warning("Could not save final agent run: %s", e)

        _st.agent_runs.pop(run_id, None)

        progress = {s: 0 for s in ("completed", "failed", "skipped")}
        for n in run["nodes"]:
            progress[n["status"]] = progress.get(n["status"], 0) + 1
        total = len(run["nodes"])
        done = progress.get("completed", 0)

        if run.get("trigger") == "telegram":
            if run["status"] == "completed":
                await _tg_notify(run, f"Agent complete - {done}/{total} steps succeeded")
            else:
                await _tg_notify(
                    run,
                    f"Agent finished with errors - {done}/{total} succeeded, "
                    f"{progress.get('failed', 0)} failed",
                )

        logger.info(
            "Agent run %s finished: %s (%d/%d succeeded)",
            run_id[:8], run["status"], done, total,
        )


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
        planner = os.environ.get("PIPELINE_PLANNER_AI", ai)
        summary = await _call_planner_ai(planner, summary_prompt, ".")
        if summary and len(summary) < len(output):
            return summary
    except Exception as exc:
        logger.warning("Agent context summarisation failed: %s", exc)

    return output[:threshold] + "\n\n...(output truncated)"


async def _tg_notify(run: dict, text: str):
    """Send a Telegram message in the context of the run's session."""
    try:
        from helm.broadcast import push_message
        await push_message("system", text, source="agent", session_id=run.get("session_id"))
    except Exception as exc:
        logger.debug("agent tg_notify error: %s", exc)
