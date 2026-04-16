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

from .models import make_run
from .executor import execute_agent_run
from .storage import save_run


# ---------------------------------------------------------------------------
# Trigger entry point
# ---------------------------------------------------------------------------

async def trigger_agent_run(
    agent_id: str,
    trigger: str,
    session_id: Optional[str] = None,
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

    run = make_run(agent, trigger=trigger, session_id=session_id)
    _st.agent_runs[run["id"]] = run

    # Persist immediately so it's visible even before the executor runs
    save_run(run)

    asyncio.create_task(execute_agent_run(run["id"]))
    logger.info(
        "Agent run %s triggered (%s) for agent %s (%s)",
        run["id"][:8], trigger, agent_id, agent["name"],
    )
    return run


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
