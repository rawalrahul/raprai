"""Group chats from Telegram and WhatsApp, WhatsApp commands, and Kelvin during group chats."""
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

import helm.groupchat as gc
import helm.groupchat_channels as gch
import helm.state as _st


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(_st, "integrations", {}, raising=False)
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "focused_id", None, raising=False)
    monkeypatch.setattr(gc, "groups", {})
    monkeypatch.setattr(gc, "active_groups", {})
    monkeypatch.setattr(gc, "_channel_senders", {})
    monkeypatch.setattr(gc, "_loaded", True)
    monkeypatch.setattr(gc, "_store_path", lambda: tmp_path / "group_chats.json")
    events = []

    async def fake_broadcast(ev):
        events.append(ev)
    monkeypatch.setattr(gc, "_broadcast", fake_broadcast)

    # Room turns are exercised in test_groupchat.py; here just record that one started.
    turns = []

    async def fake_turn(gid, token):
        turns.append(gid)
    monkeypatch.setattr(gc, "run_room_turn", fake_turn)

    def add(sid, name, ai="claude", created=0):
        _st.sessions[sid] = {"id": sid, "ai": ai, "name": name, "cwd": str(tmp_path), "model": None,
                             "emoji": "🤖", "color": "#123", "created": created, "status": "running"}
        return _st.sessions[sid]

    add("s1", "Claude #1", "claude", 1)
    add("s2", "Gemini #2", "gemini", 2)
    _st.sessions["s3"] = {"id": "s3", "ai": None, "name": "Shell #3", "created": 3, "status": "running"}
    return SimpleNamespace(events=events, turns=turns, add=add, tmp=tmp_path)


def run(coro):
    return asyncio.run(coro)


# ── Shared /group commands ───────────────────────────────────────────────────

def test_group_new_lists_only_ai_sessions(env):
    text = run(gch.handle_command("telegram", "new"))
    assert "1. 🤖 Claude #1" in text and "2. 🤖 Gemini #2" in text
    assert "Shell" not in text


def test_create_enter_who_leave(env):
    text = run(gch.handle_command("whatsapp", "new Launch: 1 2"))
    g = next(iter(gc.groups.values()))
    assert g["name"] == "Launch" and [m["session_id"] for m in g["members"]] == ["s1", "s2"]
    assert gc.active_groups["whatsapp"] == g["id"]
    assert "You're in \"Launch\"" in text

    assert "Claude #1" in run(gch.handle_command("whatsapp", "who"))
    assert "← you're here" in run(gch.handle_command("whatsapp", ""))
    assert "Left \"Launch\"" in run(gch.handle_command("whatsapp", "leave"))
    assert "whatsapp" not in gc.active_groups
    # Enter again by number and by name.
    run(gch.handle_command("whatsapp", "1"))
    assert gc.active_groups["whatsapp"] == g["id"]
    gc.set_active_group("whatsapp", None)
    run(gch.handle_command("whatsapp", "launch"))
    assert gc.active_groups["whatsapp"] == g["id"]


def test_unknown_group_and_empty_states(env):
    assert "no group chats yet" in run(gch.handle_command("telegram", ""))
    assert "No group matches" in run(gch.handle_command("telegram", "nope"))
    assert "not in a group" in run(gch.handle_command("telegram", "leave"))


def test_messages_relay_to_other_channels_not_back_to_sender(env):
    sent = {"telegram": [], "whatsapp": []}

    def sender(ch):
        async def _s(group, text):
            sent[ch].append(text)
        return _s
    gc.register_channel("telegram", sender("telegram"))
    gc.register_channel("whatsapp", sender("whatsapp"))
    g = gc.make_group("Team", "", [_st.sessions["s1"], _st.sessions["s2"]])
    gc.set_active_group("telegram", g["id"])
    gc.set_active_group("whatsapp", g["id"])

    assert run(gch.send_to_active_group("telegram", "hello from my phone")) is True
    assert env.turns == [g["id"]]
    assert g["messages"][-1]["source"] == "telegram"
    assert sent["telegram"] == []                     # not echoed to its own app
    assert sent["whatsapp"] == ["🧑 You (from Telegram):\nhello from my phone"]

    # A member reply goes to every app in the group.
    msg = gc.make_message("member", "hi!", g["members"][0])
    run(gc._relay(g, msg))
    assert sent["telegram"][-1] == "🤖 Claude #1:\nhi!"
    assert sent["whatsapp"][-1] == "🤖 Claude #1:\nhi!"


def test_active_group_persists_and_clears_on_delete(env):
    g = gc.make_group("Team", "", [_st.sessions["s1"]])
    gc.set_active_group("telegram", g["id"])
    gc.groups.clear(); gc.active_groups.clear(); gc._loaded = False
    gc.load_groups()
    assert gc.active_groups["telegram"] == g["id"]


# ── Telegram ─────────────────────────────────────────────────────────────────

class _Msg:
    def __init__(self, text=""):
        self.text = text
        self.replies = []
        self.chat = SimpleNamespace(id=42, send_action=self._noop)

    async def _noop(self, *_a, **_k):
        pass

    async def reply_text(self, text, **kw):
        self.replies.append((text, kw.get("reply_markup")))


def _update(text=""):
    return SimpleNamespace(message=_Msg(text), effective_user=SimpleNamespace(id=7),
                           effective_chat=SimpleNamespace(id=42))


class _Query:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=7)
        self.message = SimpleNamespace(chat=SimpleNamespace(id=42))
        self.edits = []

    async def answer(self, *a, **k):
        pass

    async def edit_message_text(self, text, **kw):
        self.edits.append((text, kw.get("reply_markup")))

    async def edit_message_reply_markup(self, reply_markup=None):
        self.edits.append((None, reply_markup))


def _buttons(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


@pytest.fixture
def tg(env, monkeypatch):
    pytest.importorskip("telegram")
    import helm.telegram_bot.groups as tgg
    import helm.telegram_bot.auth as auth
    monkeypatch.setattr(auth, "ALLOWED_USER_IDS", {7})
    monkeypatch.setattr(tgg, "ALLOWED_USER_IDS", {7})
    return tgg


def test_tg_group_lists_and_picker_creates_group(env, tg):
    up = _update()
    ctx = SimpleNamespace(args=[], user_data={})
    run(tg.tg_group(up, ctx))
    text, markup = up.message.replies[-1]
    assert "no group chats yet" in text
    assert "gc:new" in _buttons(markup)

    q = _Query("gc:new")
    run(tg.group_callback(SimpleNamespace(callback_query=q), ctx))
    assert "Tick the AI sessions" in q.edits[-1][0]
    assert set(_buttons(q.edits[-1][1])) >= {"gc:t:s1", "gc:t:s2", "gc:mk"}
    for data in ("gc:t:s1", "gc:t:s2"):
        run(tg.group_callback(SimpleNamespace(callback_query=_Query(data)), ctx))
    q = _Query("gc:mk")
    run(tg.group_callback(SimpleNamespace(callback_query=q), ctx))
    g = next(iter(gc.groups.values()))
    assert {m["session_id"] for m in g["members"]} == {"s1", "s2"}
    assert gc.active_groups["telegram"] == g["id"]
    assert "gc:leave" in _buttons(q.edits[-1][1])


def test_tg_text_goes_to_group_and_stop_leave(env, tg):
    g = gc.make_group("Team", "", [_st.sessions["s1"], _st.sessions["s2"]])
    up = _update("what do you both think?")
    assert run(tg.handle_group_text(up, up.message.text)) is False   # not in a group yet
    gc.set_active_group("telegram", g["id"])
    assert run(tg.handle_group_text(up, up.message.text)) is True
    assert g["messages"][-1]["content"] == "what do you both think?"
    assert env.turns == [g["id"]]

    up = _update("stop")
    run(tg.handle_group_text(up, "stop"))
    assert "Stopped" in up.message.replies[-1][0]
    up = _update("leave")
    run(tg.handle_group_text(up, "leave"))
    assert "Left" in up.message.replies[-1][0]
    assert "telegram" not in gc.active_groups


def test_tg_open_group_button(env, tg):
    g = gc.make_group("Team", "", [_st.sessions["s1"]])
    q = _Query(f"gc:open:{g['id']}")
    run(tg.group_callback(SimpleNamespace(callback_query=q), SimpleNamespace(user_data={})))
    assert gc.active_groups["telegram"] == g["id"]
    assert "You're in \"Team\"" in q.edits[-1][0]


# ── WhatsApp ─────────────────────────────────────────────────────────────────

def test_whatsapp_authorization():
    from helm.whatsapp_bridge import is_authorized
    me = {"919800000001", "123456789012345"}            # phone JID user + LID user
    allowed = {"919811111111"}
    assert is_authorized("919800000001", ["919800000001"], True, False, me, allowed)       # Message yourself
    assert is_authorized("123456789012345", ["123456789012345"], True, False, me, allowed)  # self chat by LID
    assert not is_authorized("919822222222", ["919800000001"], True, False, me, allowed)   # you, writing to a friend
    assert is_authorized("919811111111", ["919811111111"], False, False, me, allowed)      # allowed number
    assert is_authorized("777", ["777", "919811111111"], False, False, me, allowed)        # LID sender, phone in SenderAlt
    assert not is_authorized("919833333333", ["919833333333"], False, False, me, allowed)  # stranger
    assert not is_authorized("1203@g", ["919811111111"], False, True, me, allowed)         # groups ignored


def test_whatsapp_echo_guard_and_chunks():
    import helm.whatsapp_bridge as wa
    wa._sent_texts.clear()
    wa._sent_texts.append((1000.0, "🤖 Claude #1:\nhi"))
    assert wa.is_echo("🤖 Claude #1:\nhi", now=1100.0)
    assert not wa.is_echo("🤖 Claude #1:\nhi", now=2000.0)
    assert not wa.is_echo("something else", now=1100.0)
    assert wa.chunks("x" * 7001, 3500) == ["x" * 3500, "x" * 3500, "x"]


def test_whatsapp_commands(env, monkeypatch):
    import helm.whatsapp_bridge as wa
    import helm.broadcast as bc

    async def noop(*a, **k):
        pass
    monkeypatch.setattr(bc, "push_state", noop)

    assert "RAPR AI" in run(wa.handle_text("/help"))[0]
    assert "1. 🤖 Claude #1" in run(wa.handle_text("/sessions"))[0]
    assert "No session is focused" in run(wa.handle_text("hello"))[0]
    assert "Now talking to 🤖 Gemini #2" in run(wa.handle_text("/use 2"))[0]
    assert _st.focused_id == "s2"
    assert "Unknown AI" in run(wa.handle_text("/new nonsense"))[0]

    calls = []

    async def fake_process(text, source="web", session_id=None):
        calls.append((text, source))
        return "done!"
    import helm.ai_runner as air
    monkeypatch.setattr(air, "process_message", fake_process)
    assert run(wa.handle_text("fix the bug")) == ["done!"]
    assert calls == [("fix the bug", "whatsapp")]

    # Group chat from WhatsApp: create, then plain text goes to the group, not a session.
    assert "You're in" in run(wa.handle_text("/group new 1 2"))[0]
    assert run(wa.handle_text("both of you, review this")) == []
    g = gc.active_group("whatsapp")
    assert g["messages"][-1]["source"] == "whatsapp"
    assert calls == [("fix the bug", "whatsapp")]
    # Switching session leaves the group.
    assert "left the group chat" in run(wa.handle_text("/use 1"))[0]
    assert gc.active_group("whatsapp") is None


def test_whatsapp_unavailable_is_reported(monkeypatch, tmp_path):
    """No neonize on the machine: start() reports it instead of crashing."""
    import builtins
    import helm.whatsapp_bridge as wa
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("neonize"):
            raise ImportError("no neonize")
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(wa, "_client", None)
    monkeypatch.setattr(wa, "_dir", lambda: tmp_path)
    st = run(wa.start())
    assert st["status"] == "error" and st["available"] is False
    assert "isn't available" in st["error"]
    wa.state.update(status="off", error=None, available=None)


# ── Kelvin during group chats ────────────────────────────────────────────────

def test_kelvin_works_while_a_group_answers():
    import helm.kelvin_status as ks
    st = ks.KelvinStatus()
    st.observe({"type": "group_status", "group_id": "g1", "status": "running", "speaking": "m1"})
    assert st.mood() == "working"
    assert st.active() is True                       # keeps the PC awake
    assert st.counts()["groups"] == 1
    assert st.describe() == "Kelvin: group chat answering"
    st.observe({"type": "thinking", "active": True, "session_id": "s1"})
    assert st.describe() == "Kelvin: 1 session + 1 group chat working"
    st.observe({"type": "thinking", "active": False, "session_id": "s1"})
    st.observe({"type": "group_status", "group_id": "g1", "status": "idle", "speaking": None})
    assert st.mood() == "done"
    assert st.active() is False


def test_kelvin_report_mentions_group_chats(monkeypatch):
    import helm.kelvin_status as ks
    import helm.kelvin_report as kr
    st = ks.KelvinStatus()
    monkeypatch.setattr(ks, "status", st)
    monkeypatch.setattr(_st, "scheduled_tasks", {}, raising=False)
    st.observe({"type": "group_status", "group_id": "g1", "status": "running"})
    assert "1 group chat answering" in kr.kelvin_report()


def test_group_status_event_carries_roster(env):
    g = gc.make_group("Team", "", [_st.sessions["s1"]])
    run(gc._set_status(g, "running", g["members"][0]["id"]))
    ev = env.events[-1]
    assert ev["type"] == "group_status" and ev["name"] == "Team"
    assert ev["members"][0]["ai"] == "claude"
