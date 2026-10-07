"""The web UI's Kelvin mascot shows an error only when the backend says a run failed for good."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.ai_runner.core as core
import helm.state as _st

FAILURE = "(error: claude CLI not found on PATH)"


async def _noop(*args, **kwargs):
    return None


def _run_dispatch(monkeypatch, outputs, fallbacks=()):
    """Run _dispatch_with_recovery with _run_single_ai returning `outputs` in order."""
    events, calls = [], iter(outputs)

    async def fake_broadcast(data):
        events.append(data)

    async def fake_run_single_ai(*args, **kwargs):
        return next(calls)

    async def no_sleep(_):
        return None

    monkeypatch.setattr("helm.broadcast.broadcast", fake_broadcast)
    monkeypatch.setattr("helm.broadcast.save_message_to_log", lambda *a, **k: None)
    monkeypatch.setattr("helm.broadcast.save_last_state", lambda *a, **k: None)
    monkeypatch.setattr(core, "push_state", _noop)
    monkeypatch.setattr(core, "_run_single_ai", fake_run_single_ai)
    monkeypatch.setattr(core, "_find_available_ais", lambda ai: list(fallbacks))
    monkeypatch.setattr(core.asyncio, "sleep", no_sleep)
    monkeypatch.setenv("AI_MAX_RETRIES", "1")

    sess = {"id": "s1", "name": "Test", "emoji": "🐧", "ai": "claude"}
    monkeypatch.setitem(_st.sessions, "s1", sess)
    asyncio.run(core._dispatch_with_recovery(
        "claude", sess, "hi", "hi", ".", None, "web", "s1", None, None,
    ))
    return events


def _errors(events):
    return [e for e in events if e.get("type") == "agent_error"]


def test_error_event_when_no_fallback(monkeypatch):
    errs = _errors(_run_dispatch(monkeypatch, [FAILURE]))
    assert len(errs) == 1
    assert errs[0]["session_id"] == "s1"
    assert "claude" in errs[0]["message"]


def test_error_event_when_auto_switch_disabled(monkeypatch):
    monkeypatch.setenv("AI_AUTO_SWITCH", "0")
    assert len(_errors(_run_dispatch(monkeypatch, [FAILURE]))) == 1


def test_error_event_when_every_fallback_fails(monkeypatch):
    errs = _errors(_run_dispatch(monkeypatch, [FAILURE, FAILURE, FAILURE], fallbacks=["gemini", "codex"]))
    assert len(errs) == 1


def test_no_error_event_when_fallback_succeeds(monkeypatch):
    events = _run_dispatch(monkeypatch, [FAILURE, "Here is your answer."], fallbacks=["gemini"])
    assert _errors(events) == []


def test_error_event_when_fallback_raises(monkeypatch):
    def outputs():
        yield FAILURE
        raise RuntimeError("gemini exploded")
    errs = _errors(_run_dispatch(monkeypatch, outputs(), fallbacks=["gemini"]))
    assert len(errs) == 1 and "gemini exploded" in errs[0]["message"]


def test_no_error_event_on_success(monkeypatch):
    assert _errors(_run_dispatch(monkeypatch, ["All done."])) == []
