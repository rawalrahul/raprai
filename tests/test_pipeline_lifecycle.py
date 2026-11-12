"""Pipeline status changes follow one set of rules, and only one loop drives a pipeline.

Resuming a paused pipeline used to start a second orchestration loop while the first
was still waiting out the pause, so a step could be launched twice. Cancel didn't stop
steps in flight, could turn a finished pipeline into "cancelled", and Telegram's resume
retried failed steps past their retry limit.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.state as _st
from helm.pipeline import executor as ex
from helm.pipeline.models import make_pipeline, make_step, transition


@pytest.fixture
def pipe(tmp_path, monkeypatch):
    async def quiet(*a, **k):
        return None
    monkeypatch.setattr(ex, "push_message", quiet)
    monkeypatch.setattr(ex, "push_state", quiet)
    monkeypatch.setattr(ex, "broadcast_pipeline_update", quiet)
    monkeypatch.setattr("helm.kelvin_stickers.kelvin_sticker_soon", lambda *a, **k: None)
    monkeypatch.setenv("PIPELINE_MAX_PARALLEL", "1")

    pl = make_pipeline("task", "s1", str(tmp_path))
    pl["steps"] = [make_step("a", "A", "do a"), make_step("b", "B", "do b")]
    pl["status"] = "awaiting_approval"
    _st.pipelines[pl["id"]] = pl
    yield pl
    _st.pipelines.pop(pl["id"], None)


def _fake_steps(monkeypatch, gate: asyncio.Event, launches: list):
    async def fake(pipeline, step, semaphore):
        async with semaphore:
            launches.append(step["id"])
            step["status"] = "running"
            await gate.wait()
            step["status"] = "completed"
    monkeypatch.setattr(ex, "_execute_step", fake)


def test_resume_after_pause_runs_each_step_once(pipe, monkeypatch):
    async def go():
        gate, launches = asyncio.Event(), []
        _fake_steps(monkeypatch, gate, launches)
        assert ex.approve_pipeline(pipe)
        await asyncio.sleep(0.2)
        assert ex.pause_pipeline(pipe)
        await asyncio.sleep(1.2)          # the first loop is now waiting out the pause
        assert ex.resume_pipeline(pipe)
        await asyncio.sleep(0.2)
        gate.set()
        for _ in range(100):
            if pipe["status"] == "completed":
                break
            await asyncio.sleep(0.1)
        return launches

    launches = asyncio.run(go())
    assert pipe["status"] == "completed"
    assert sorted(launches) == ["a", "b"]      # never twice


def test_cancel_stops_steps_in_flight_and_cannot_undo_an_ending(pipe, monkeypatch):
    async def go():
        gate, launches = asyncio.Event(), []
        _fake_steps(monkeypatch, gate, launches)
        loop = ex.start_pipeline(pipe["id"])
        await asyncio.sleep(0.2)
        task = ex._step_tasks[pipe["id"]]["a"]
        assert ex.cancel_pipeline(pipe)
        await asyncio.wait_for(loop, 5)
        return task

    task = asyncio.run(go())
    assert task.cancelled()
    assert pipe["status"] == "cancelled"
    assert {s["status"] for s in pipe["steps"]} == {"skipped"}
    assert not ex.cancel_pipeline(pipe)
    assert not ex.resume_pipeline(pipe, retry_failed=True)


def test_completed_pipeline_cannot_be_cancelled(pipe):
    pipe["status"] = "completed"
    assert not ex.cancel_pipeline(pipe)
    assert pipe["status"] == "completed"


def test_cancel_before_the_loop_starts_is_kept(pipe):
    async def go():
        loop = ex.start_pipeline(pipe["id"])   # created, not run yet
        assert ex.cancel_pipeline(pipe)
        await loop
    asyncio.run(go())
    assert pipe["status"] == "cancelled"


def test_second_approval_is_refused(pipe, monkeypatch):
    async def go():
        _fake_steps(monkeypatch, asyncio.Event(), [])
        assert ex.approve_pipeline(pipe)
        assert not ex.approve_pipeline(pipe)
        ex.cancel_pipeline(pipe)
        await asyncio.sleep(0.1)
    asyncio.run(go())


def test_resume_of_failed_pipeline_respects_retry_limit(pipe, monkeypatch):
    monkeypatch.setattr(ex, "start_pipeline", lambda pid: None)
    pipe["status"] = "failed"
    a, b = pipe["steps"]
    a.update(status="failed", retry_count=2, max_retries=2)   # out of retries
    b.update(status="failed", retry_count=0, max_retries=2)
    assert ex.resume_pipeline(pipe, retry_failed=True)
    assert (a["status"], b["status"]) == ("failed", "pending")
    assert b["retry_count"] == 1
    assert pipe["status"] == "running"

    pipe["status"] = "failed"
    b.update(status="failed", retry_count=2)
    assert not ex.resume_pipeline(pipe, retry_failed=True)
    assert pipe["status"] == "failed"


def test_transition_table():
    pl = {"status": "paused"}
    assert not transition(pl, "completed")
    assert transition(pl, "running") and pl["status"] == "running"
    assert transition(pl, "completed")
    assert not transition(pl, "running")
