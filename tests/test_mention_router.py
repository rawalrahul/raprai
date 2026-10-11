"""@mention an AI at the start of a message to start it, or to bring it into a
group chat with the session you're working in (same folder)."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.groupchat as gc
import helm.state as _st
import helm.mention_router as mr
from helm.ai_runner.core import process_message as REAL_PROCESS_MESSAGE


@pytest.fixture
def env(tmp_path, monkeypatch):
    import helm.session_mgr as sm
    import helm.broadcast as bc
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "session_counter", 0, raising=False)
    monkeypatch.setattr(_st, "focused_id", None, raising=False)
    monkeypatch.setattr(_st, "last_cwd", str(tmp_path), raising=False)
    monkeypatch.setattr(_st, "chat_history", [], raising=False)
    monkeypatch.setattr(_st, "integrations", {
        "codex": {"name": "Codex", "emoji": "💻", "color": "#2a2"},
        "antigravity": {"name": "Antigravity", "emoji": "🪐", "color": "#55f"},
        "interpreter": {"name": "Open Interpreter", "emoji": "🖥️", "color": "#888"},
        "droid": {"name": "Droid", "emoji": "🤖", "color": "#66f"},
    }, raising=False)
    monkeypatch.setattr(sm, "get_history_messages", lambda pid: [])
    monkeypatch.setattr(sm, "save_cwd_to_log", lambda *a, **k: None)
    monkeypatch.setattr(sm, "TerminalSession", lambda: object())
    monkeypatch.setattr(gc, "groups", {})
    monkeypatch.setattr(gc, "active_groups", {})
    monkeypatch.setattr(gc, "_loaded", True)
    monkeypatch.setattr(gc, "_store_path", lambda: tmp_path / "g.json")
    turns = []
    async def fake_turn(gid, token):
        turns.append(gid)
    monkeypatch.setattr(gc, "run_room_turn", fake_turn)
    async def noop(*a, **k):
        return None
    for name in ("push_state", "push_message"):
        monkeypatch.setattr(bc, name, noop)
    monkeypatch.setattr(gc, "_broadcast", noop)
    monkeypatch.setattr(mr, "_ready", lambda key: key != "droid")   # Droid isn't installed
    sent = []
    async def fake_process(text, source="web", session_id=None):
        sent.append((session_id, text))
        return f"reply from {session_id}"
    import helm.ai_runner.core as core
    monkeypatch.setattr(core, "process_message", fake_process)
    return tmp_path, sent


def run(coro):
    return asyncio.run(coro)


def _claude_session(folder, worked_in=None):
    from helm.session_mgr import make_session
    s = make_session("claude", cwd=str(folder))
    _st.focused_id = s["id"]
    if worked_in:
        s["last_task_cwd"] = str(worked_in)
    return s


def test_mention_with_nothing_open_starts_that_ai(env):
    tmp, sent = env
    reply = run(mr.route("@codex fix the tests", "telegram"))
    sess = _st.sessions[_st.focused_id]
    assert sess["ai"] == "codex" and sess["cwd"] == str(tmp)
    assert sent == [(sess["id"], "fix the tests")] and reply == f"reply from {sess['id']}"
    assert gc.groups == {}


def test_mention_alone_just_starts_it(env):
    tmp, sent = env
    reply = run(mr.route("@codex", "web"))
    assert "started" in reply and sent == []


def test_mention_from_an_active_session_makes_a_group_with_context(env):
    tmp, sent = env
    claude = _claude_session(tmp, worked_in=tmp)
    _st.chat_history += [
        {"role": "user", "content": "build /health", "session_id": claude["id"]},
        {"role": "assistant", "content": "done, in routes/health.py", "session_id": claude["id"]},
        {"role": "assistant", "content": "other session", "session_id": "s99"},
    ]
    reply = run(mr.route("@codex review it", "telegram"))
    assert len(gc.groups) == 1
    g = next(iter(gc.groups.values()))
    assert [m["ai"] for m in g["members"]] == ["claude", "codex"]
    assert g["members"][0]["session_id"] == claude["id"]          # the same Claude session
    texts = [(m["role"], m["content"]) for m in g["messages"]]
    assert texts == [("user", "build /health"), ("member", "done, in routes/health.py"),
                     ("user", "@codex review it")]
    assert gc.active_groups["telegram"] == g["id"]                 # Telegram is now in the group
    assert g["started_session_ids"] == [g["members"][1]["session_id"]]
    assert "group chat" in reply and sent == []


def test_next_mention_adds_to_the_same_group(env):
    tmp, _ = env
    _claude_session(tmp)
    run(mr.route("@codex review it", "web"))
    run(mr.route("@antigravity and you?", "web"))
    assert len(gc.groups) == 1
    g = next(iter(gc.groups.values()))
    assert [m["ai"] for m in g["members"]] == ["claude", "codex", "antigravity"]


def test_moved_to_another_folder_starts_a_separate_session(env):
    tmp, sent = env
    other = tmp / "other"
    other.mkdir()
    claude = _claude_session(other, worked_in=tmp)   # worked in tmp, then moved to other
    run(mr.route("@codex fix it", "web"))
    assert gc.groups == {}
    codex = _st.sessions[_st.focused_id]
    assert codex["ai"] == "codex" and codex["cwd"] == str(other) and codex["id"] != claude["id"]


def test_mentioning_the_open_ai_is_a_normal_message(env):
    tmp, _ = env
    _claude_session(tmp)
    assert run(mr.route("@claude carry on", "web")) is None


@pytest.mark.parametrize("text", [
    "ask @codex later", "@john hello", "@codex @john hi", "@open the file please",
    "mail me@codex.dev", "", "plain text",
])
def test_not_routed(env, text):
    assert run(mr.route(text, "web")) is None
    assert gc.groups == {} and _st.sessions == {}


def test_not_from_agents_or_schedules(env):
    assert run(mr.route("@codex hi", "schedule")) is None


def test_ai_not_set_up_is_explained(env):
    reply = run(mr.route("@droid hi", "web"))
    assert "isn't set up" in reply and _st.sessions == {}


def test_two_mentions_with_nothing_open_start_a_group(env):
    tmp, _ = env
    run(mr.route("@codex @antigravity compare approaches", "whatsapp"))
    g = next(iter(gc.groups.values()))
    assert [m["ai"] for m in g["members"]] == ["codex", "antigravity"]
    assert gc.active_groups["whatsapp"] == g["id"]


def test_in_a_group_a_new_ai_mention_adds_it(env):
    tmp, _ = env
    run(mr.route("@codex @antigravity start", "web"))
    g = next(iter(gc.groups.values()))
    run(gc.send_user_message(g, "@claude what do you think?", source="web"))
    assert [m["ai"] for m in g["members"]] == ["codex", "antigravity", "claude"]
    run(gc.send_user_message(g, "@codex again", source="web"))          # already a member
    assert len(g["members"]) == 3


def test_process_message_uses_the_router(env, monkeypatch):
    async def fake_route(text, channel):
        return "routed" if text.startswith("@") else None
    monkeypatch.setattr(mr, "route", fake_route)
    assert run(REAL_PROCESS_MESSAGE("@codex hi", source="web")) == "routed"
