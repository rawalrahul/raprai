"""A session whose AI process died mid-task stays a usable session in a known state.

The watchdog used to set its status to "crashed (exit 1)", a value nothing else knew:
the rest of RAPR only checks for "stopped", so the session looked live anyway, and its
status never went back to "running".
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.state as _st
from helm import resilience


class DeadProc:
    def poll(self):
        return 3


def test_watchdog_records_crash_without_inventing_a_status(monkeypatch):
    async def quiet(*a, **k):
        return None
    monkeypatch.setattr("helm.broadcast.broadcast", quiet)
    monkeypatch.setattr(resilience, "_watchdog_running", False)
    sess = {"id": "s-crash", "status": "running", "busy": True, "task_start": 1.0, "proc": DeadProc()}
    monkeypatch.setitem(_st.sessions, "s-crash", sess)

    async def go():
        task = asyncio.create_task(resilience.ai_watchdog(check_interval=0.05))
        for _ in range(50):
            await asyncio.sleep(0.05)
            if not sess["busy"]:
                break
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    asyncio.run(go())

    assert sess["status"] == "running"
    assert sess["busy"] is False and sess["task_start"] is None
    assert sess["last_crash"]["exit_code"] == 3
    assert "proc" not in sess
