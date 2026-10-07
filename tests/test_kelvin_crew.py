"""'Call the Kelvin crew' re-runs the last big task as a parallel pipeline."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.web_routes.chat_ws as chat_ws


def _setup(monkeypatch):
    messages, started, killed = [], [], []

    async def fake_push_message(role, content, **kw):
        messages.append(content)

    async def fake_push_thinking(*a, **kw):
        return None

    async def fake_process_message(text, source="web", session_id=None):
        started.append((text, session_id))
        return ""

    monkeypatch.setattr(chat_ws, "push_message", fake_push_message)
    monkeypatch.setattr(chat_ws, "push_thinking", fake_push_thinking)
    monkeypatch.setattr(chat_ws, "process_message", fake_process_message)
    monkeypatch.setattr(chat_ws, "kill_session_proc", lambda sess: killed.append(sess["id"]))
    return messages, started, killed


async def _call_and_settle(sess):
    ok = await chat_ws.call_kelvin_crew(sess)
    await asyncio.sleep(0)  # let the scheduled pipeline task run
    return ok


def test_without_a_remembered_task_nothing_starts(monkeypatch):
    messages, started, killed = _setup(monkeypatch)
    sess = {"id": "s1", "_lock": asyncio.Lock()}
    assert asyncio.run(_call_and_settle(sess)) is False
    assert started == [] and killed == []
    assert "no recent task" in messages[0]


def test_idle_session_starts_pipeline_with_the_same_prompt(monkeypatch):
    messages, started, killed = _setup(monkeypatch)
    sess = {"id": "s1", "_lock": asyncio.Lock(), "crew_prompt": "Research, build and test the page"}
    assert asyncio.run(_call_and_settle(sess)) is True
    assert started == [("/pipeline Research, build and test the page", "s1")]
    assert killed == []
    assert "crew_prompt" not in sess


def test_busy_session_is_stopped_before_the_crew_starts(monkeypatch):
    messages, started, killed = _setup(monkeypatch)

    async def scenario():
        lock = asyncio.Lock()
        sess = {"id": "s1", "_lock": lock, "crew_prompt": "Big task"}
        await lock.acquire()
        # The solo run notices the kill and releases its lock shortly after.
        asyncio.get_running_loop().call_later(0.3, lock.release)
        return await _call_and_settle(sess)

    assert asyncio.run(scenario()) is True
    assert killed == ["s1"]
    assert started == [("/pipeline Big task", "s1")]
    assert any("Stopped the solo run" in m for m in messages)


def test_crew_gives_up_if_the_solo_run_will_not_stop(monkeypatch):
    messages, started, killed = _setup(monkeypatch)
    monkeypatch.setattr(chat_ws, "CREW_WAIT_SECONDS", 0.4)

    async def scenario():
        lock = asyncio.Lock()
        await lock.acquire()
        sess = {"id": "s1", "_lock": lock, "crew_prompt": "Big task"}
        ok = await _call_and_settle(sess)
        return ok, sess

    ok, sess = asyncio.run(scenario())
    assert ok is False
    assert started == []
    assert sess["crew_prompt"] == "Big task"  # still there, so the user can try again
    assert "hasn't stopped yet" in messages[-1]
