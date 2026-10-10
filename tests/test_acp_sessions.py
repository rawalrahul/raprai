"""ACP agents as sessions: registry, a full turn through the agent, and naming."""
import asyncio
import os
import shlex
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.acp_agents as agents
import helm.acp_session as acp_session
import helm.state as _st

MOCK = f"{sys.executable} {os.path.join(os.path.dirname(__file__), 'mock_acp_agent.py')}"


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(agents, "_path", lambda: tmp_path / "acp_agents.json")
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    import helm.audit as audit
    monkeypatch.setattr(audit, "_path", lambda: tmp_path / "audit.jsonl")
    return tmp_path


def test_validation_and_save(data):
    agents.save([{"id": "mock", "name": "Mock", "command": MOCK}])
    a = agents.get("mock")
    assert a["command"] == shlex.split(MOCK)
    for bad in ({"id": "Bad Id", "name": "x", "command": "y"}, {"id": "a", "name": "", "command": "y"},
                {"id": "a", "name": "x", "command": ""}):
        with pytest.raises(ValueError):
            agents.validate(bad)
    with pytest.raises(ValueError, match="same id"):
        agents.save([{"id": "a", "name": "x", "command": "y"}, {"id": "a", "name": "z", "command": "w"}])


def test_a_turn_goes_through_the_agent(data):
    agents.save([{"id": "mock", "name": "Mock", "command": MOCK}])
    sess = {"id": "s1", "ai": "acp:mock", "cwd": str(data)}

    async def go():
        reply1 = await acp_session.run_turn(sess, "hello", "s1", "Mock")
        reply2 = await acp_session.run_turn(sess, "again", "s1", "Mock")   # same agent process
        await sess["_acp_client"].close()
        return reply1, reply2
    r1, r2 = asyncio.run(go())
    assert r1 == "you said: hello" and r2 == "you said: again"


def test_missing_agent_is_explained(data):
    agents.save([])
    reply = asyncio.run(acp_session.run_turn({"ai": "acp:gone", "cwd": str(data)}, "x", "s", "x"))
    assert "isn't set up" in reply


def test_session_is_named_after_its_agent(data, monkeypatch):
    agents.save([{"id": "mock", "name": "Mock agent", "command": MOCK, "emoji": "🧪"}])
    import helm.session_mgr as sm
    monkeypatch.setattr(sm, "get_history_messages", lambda pid: [])
    monkeypatch.setattr(sm, "save_cwd_to_log", lambda *a, **k: None)
    monkeypatch.setattr(sm, "TerminalSession", lambda: object())
    sess = sm.make_session("acp:mock", cwd=str(data))
    assert sess["name"].startswith("Mock agent #") and sess["emoji"] == "🧪"
    assert sess["ai"] == "acp:mock"
