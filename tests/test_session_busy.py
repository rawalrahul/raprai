"""Interrupting a task leaves `busy` to the run that owns the session.

Interrupt and stop used to clear busy straight away while the killed run still held
the session's lock, so the session showed as idle while the next message had to wait.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm.session_mgr import clear_busy_after_kill


def test_busy_kept_while_a_run_holds_the_lock():
    async def go():
        lock = asyncio.Lock()
        sess = {"busy": True, "task_start": 1.0, "_lock": lock}
        await lock.acquire()
        clear_busy_after_kill(sess)
        assert sess["busy"] is True          # the run's own finally clears it
        lock.release()
        clear_busy_after_kill(sess)
        assert sess["busy"] is False and sess["task_start"] is None
    asyncio.run(go())
