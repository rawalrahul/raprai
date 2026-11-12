"""An agent run's status while nodes wait for the person, and cancelling such a run.

Input and manager nodes run in parallel, but the run had one "waiting_input" flag: the
first answered question set it back to "running" while another still waited. And the
cancel endpoint refused runs that were waiting for input.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from helm.agent import executor as ex


def _run():
    return {"id": "r1", "status": "running", "nodes": [
        {"id": "a", "status": "running"}, {"id": "b", "status": "running"},
        {"id": "c", "status": "pending"}]}


def test_run_waits_until_the_last_question_is_answered(monkeypatch):
    async def quiet(run):
        return None
    monkeypatch.setattr(ex, "broadcast_run_update", quiet)

    async def go():
        run = _run()
        a, b = asyncio.Future(), asyncio.Future()
        ta = asyncio.create_task(ex._waiting_for_person(run, a))
        tb = asyncio.create_task(ex._waiting_for_person(run, b))
        await asyncio.sleep(0)
        assert run["status"] == "waiting_input"
        a.set_result("x")
        await ta
        assert run["status"] == "waiting_input"     # b still waits
        b.set_result("y")
        await tb
        assert run["status"] == "running"
    asyncio.run(go())


def test_waiting_run_can_be_cancelled(monkeypatch):
    async def quiet(run):
        return None
    monkeypatch.setattr(ex, "broadcast_run_update", quiet)

    async def go():
        run = _run()
        question = asyncio.Future()
        task = asyncio.create_task(ex._waiting_for_person(run, question))
        ex._run_tasks["r1"] = task
        await asyncio.sleep(0)
        assert run["status"] == "waiting_input"
        assert ex.cancel_run(run)
        await asyncio.gather(task, return_exceptions=True)
        assert task.cancelled()
        assert run["status"] == "cancelled"           # not flipped back to running
        assert {n["status"] for n in run["nodes"]} == {"skipped"}
        assert not ex.cancel_run(run)
    asyncio.run(go())
