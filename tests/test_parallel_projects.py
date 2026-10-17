"""Choosing another project while the AI is working starts a second session there,
so both run in parallel instead of the next message waiting on the busy one."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.state as _st
import helm.ai_runner.helpers as helpers


@pytest.fixture
def env(tmp_path, monkeypatch):
    import helm.session_mgr as sm
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "session_counter", 0, raising=False)
    monkeypatch.setattr(_st, "focused_id", None, raising=False)
    monkeypatch.setattr(_st, "last_cwd", str(tmp_path), raising=False)
    monkeypatch.setattr(_st, "integrations", {}, raising=False)
    monkeypatch.setattr(sm, "get_history_messages", lambda pid: [])
    monkeypatch.setattr(sm, "save_cwd_to_log", lambda *a, **k: None)
    monkeypatch.setattr(sm, "TerminalSession", lambda: object())
    monkeypatch.setattr(helpers, "save_cwd_to_log", lambda *a, **k: None)
    monkeypatch.setattr(helpers, "save_last_state", lambda: None)
    messages = []
    async def noop(*a, **k):
        return None
    async def fake_push_message(role, text, **k):
        messages.append((k.get("session_id"), text))
    monkeypatch.setattr(helpers, "push_state", noop)
    monkeypatch.setattr(helpers, "push_message", fake_push_message)
    monkeypatch.setattr(helpers, "tg_update_focus", noop)
    a = tmp_path / "project-a"
    b = tmp_path / "project-b"
    a.mkdir()
    b.mkdir()
    return a, b, messages


def _session(folder):
    from helm.session_mgr import make_session
    s = make_session("claude", cwd=str(folder))
    _st.focused_id = s["id"]
    return s


def test_idle_session_moves_to_the_chosen_project(env):
    a, b, _ = env
    s = _session(a)
    assert asyncio.run(helpers.change_cwd(str(b)))
    assert s["cwd"] == str(b.resolve())
    assert _st.focused_id == s["id"] and len(_st.sessions) == 1


def test_busy_session_keeps_its_folder_and_a_new_one_starts(env):
    a, b, messages = env
    s = _session(a)
    s["busy"] = True
    s["model"] = "opus"
    assert asyncio.run(helpers.change_cwd(str(b)))
    assert s["cwd"] == str(a)
    new = _st.sessions[_st.focused_id]
    assert new["id"] != s["id"]
    assert new["ai"] == "claude" and new["model"] == "opus"
    assert new["cwd"] == str(b.resolve())
    assert messages and messages[-1][0] == new["id"]


def test_locked_session_counts_as_busy(env):
    a, b, _ = env
    s = _session(a)

    async def go():
        await s["_lock"].acquire()
        return await helpers.change_cwd(str(b))

    assert asyncio.run(go())
    assert s["cwd"] == str(a) and _st.focused_id != s["id"]
