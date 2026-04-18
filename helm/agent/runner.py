"""
helm/agent/runner.py — Agent trigger entry point and schedule cron runner.

trigger_agent_run()       — create a run and fire the executor
register_agent_schedules() — start the agent cron loop at startup
"""

import asyncio
import time
from typing import Optional

import helm.state as _st
from helm.config import logger

from .models import ensure_manager_node, make_run, workflow_root_nodes
from .repair import repair_agent_graph
from .executor import execute_agent_run
from .storage import save_agent, save_run


# ---------------------------------------------------------------------------
# Trigger entry point
# ---------------------------------------------------------------------------

async def trigger_agent_run(
    agent_id: str,
    trigger: str,
    session_id: Optional[str] = None,
    input_data: Optional[str] = None,
    dry_run: bool = False,
) -> Optional[dict]:
    """
    Create an AgentRun and launch the executor as a background task.

    Returns the new run dict, or None if the agent is not found.
    trigger: "telegram" | "schedule" | "webhook" | "ui"
    """
    agent = _st.agents.get(agent_id)
    if not agent:
        logger.warning("trigger_agent_run: agent %s not found", agent_id)
        return None

    if not agent.get("nodes"):
        logger.warning("trigger_agent_run: agent %s has no nodes", agent_id)
        return None

    repaired = repair_agent_graph(
        f"{agent.get('name', '')} {agent.get('description', '')}",
        agent["nodes"],
    )
    had_manager = any(n.get("type") == "manager" for n in agent.get("nodes", []))
    ensure_manager_node(agent["nodes"], manager_title=agent.get("name"))
    if repaired or not had_manager:
        save_agent(agent)

    # For scheduled triggers, fall back to agent's static schedule input_data
    if input_data is None and trigger == "schedule":
        input_data = agent.get("trigger", {}).get("schedule", {}).get("input_data") or None

    run = make_run(agent, trigger=trigger, session_id=session_id, input_data=input_data)
    if dry_run:
        run["dry_run"] = True
    _prepare_initial_input_node(run)
    _st.agent_runs[run["id"]] = run

    # Persist immediately so it's visible even before the executor runs
    await save_run(run)

    asyncio.create_task(execute_agent_run(run["id"]))
    logger.info(
        "Agent run %s triggered (%s) for agent %s (%s)",
        run["id"][:8], trigger, agent_id, agent["name"],
    )
    return run


_RESUME_UPLOAD_PHRASES = (
    "upload your resume", "paste your resume", "upload resume", "attach resume",
    "upload your cv", "paste your cv", "provide your resume", "provide resume",
    "submit your resume", "send your resume",
)


def _prepare_initial_input_node(run: dict) -> None:
    """
    Convert a misgenerated first step into an input node only when the node
    explicitly asks for a resume upload, or when the agent opts in via
    agent['needs_resume_input']=True.

    B4: Old fuzzy job+resume keyword scan produced false positives on any agent
    mentioning "profile" or "role". Now restricted to:
      (a) explicit upload/paste phrase in root node title or task, OR
      (b) agent-level flag needs_resume_input=True.
    """
    if run.get("input_data") or not run.get("nodes"):
        return
    nodes = run["nodes"]
    roots = workflow_root_nodes(nodes) or [n for n in nodes if n.get("type") != "manager"][:1]
    if any(node.get("type") == "input" for node in roots):
        return

    root = roots[0]
    root_text = f"{root.get('title', '')} {root.get('task', '')}".lower()

    needs_resume = run.get("needs_resume_input") or any(
        phrase in root_text for phrase in _RESUME_UPLOAD_PHRASES
    )
    if not needs_resume:
        return

    root["type"] = "input"
    root["input_timeout"] = root.get("input_timeout", 3600)
    root["task"] = (
        "Please upload your resume file or paste the resume contents. Also provide target job title, "
        "preferred location or remote preference, experience level, salary expectations, and any companies "
        "or roles to avoid."
    )


# ---------------------------------------------------------------------------
# Schedule cron runner
# ---------------------------------------------------------------------------

async def agent_cron_runner() -> None:
    """
    Background loop that checks for scheduled agents every 30 seconds.

    Completely separate from the existing cron_runner() for scheduled_tasks.
    """
    from helm.scheduler import next_cron_run

    logger.info("Agent cron runner started")
    while True:
        try:
            await asyncio.sleep(30)
            now = time.time()

            for agent in list(_st.agents.values()):
                sched = agent.get("trigger", {}).get("schedule", {})
                if not sched.get("enabled"):
                    continue
                cron = sched.get("cron", "")
                next_run = sched.get("next_run")
                if not cron or not next_run:
                    continue
                if now < next_run:
                    continue

                logger.info(
                    "Agent schedule: firing run for '%s' (cron: %s)",
                    agent["name"], cron,
                )
                await trigger_agent_run(agent["id"], trigger="schedule")

                # Advance next_run
                new_next = next_cron_run(cron)
                sched["next_run"] = new_next

                from .storage import save_agent
                save_agent(agent)

        except asyncio.CancelledError:
            logger.info("Agent cron runner stopping")
            break
        except Exception as exc:
            logger.error("Agent cron runner error: %s", exc)


async def resume_interrupted_runs() -> None:
    """
    A4: On boot, find runs that were in-flight when the server last stopped.

    Input futures and asyncio tasks cannot survive a restart, so we cannot
    transparently resume mid-execution.  Instead:
      - Nodes that were "running" → marked "failed" (server restarted)
      - Nodes still "pending"    → marked "skipped"
      - Run status               → "failed"
    A WS broadcast tells any connected UI about the finalised state.
    """
    from .storage import load_recent_runs, save_run
    from .executor import broadcast_run_update
    import time as _time

    try:
        db_module = __import__("helm.db", fromlist=["get_db"])
        db = db_module.get_db()
        rows = db.execute(
            "SELECT result_json FROM agent_runs "
            "WHERE status IN ('running', 'waiting_input') ORDER BY started_at"
        ).fetchall()
    except Exception as exc:
        logger.warning("resume_interrupted_runs: DB query failed: %s", exc)
        return

    count = 0
    for row in rows:
        try:
            import json
            run = json.loads(row["result_json"])
        except Exception:
            continue
        interrupted = False
        for n in run.get("nodes", []):
            if n.get("status") == "running":
                n["status"] = "failed"
                n["error"] = "interrupted: server restarted"
                n["completed_at"] = _time.time()
                interrupted = True
            elif n.get("status") == "pending":
                n["status"] = "skipped"
                n["output"] = "(skipped: server restarted before node ran)"
                interrupted = True
        if interrupted:
            run["status"] = "failed"
            run["completed_at"] = _time.time()
            _st.agent_runs[run["id"]] = run
            try:
                await broadcast_run_update(run)
            except Exception:
                pass
            await save_run(run)
            _st.agent_runs.pop(run["id"], None)
            count += 1
            logger.info(
                "A4 checkpoint: finalised interrupted run %s (%s)",
                run["id"][:8], run.get("agent_name", "?"),
            )
    if count:
        logger.info("A4 checkpoint: cleaned up %d interrupted run(s)", count)


def register_agent_schedules() -> None:
    """
    Called at startup to load agents into state and launch the cron runner.
    Also resolves the initial next_run for any agents with a schedule.
    """
    from helm.scheduler import next_cron_run
    from .storage import load_all_agents, save_agent

    load_all_agents()

    # Fix up missing next_run values
    now = time.time()
    for agent in _st.agents.values():
        sched = agent.get("trigger", {}).get("schedule", {})
        if sched.get("enabled") and sched.get("cron") and not sched.get("next_run"):
            sched["next_run"] = next_cron_run(sched["cron"])
            save_agent(agent)

    # The asyncio task is created in web_app.py after the event loop is running
