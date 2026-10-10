"""Group chats: several AIs answering in one conversation."""
import asyncio
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

import helm.groupchat as gc
import helm.state as _st


# A fake AI CLI: `python fake_ai.py <behaviour> <prompt>` prints a reply.
FAKE_AI = textwrap.dedent('''
    import sys, time
    mode, prompt = sys.argv[1], sys.argv[2]
    if mode == "pass":
        print("(pass)")
    elif mode == "slow":
        time.sleep(30)
        print("too late")
    elif mode == "pinger":
        # Answers the user once, asking Beta to weigh in; passes afterwards.
        print("(pass)" if "Alpha asks @Beta" in prompt.split("Write your next")[0] else "Alpha asks @Beta to check")
    elif mode == "echo-last":
        convo = prompt.split("Write your next")[0].strip().splitlines()
        last = [l for l in convo if l.strip() and not l.startswith("---")][-1]
        print("Beta saw -> " + last)
    else:
        print(mode + " says hi")
''')


@pytest.fixture
def env(tmp_path, monkeypatch):
    script = tmp_path / "fake_ai.py"
    script.write_text(FAKE_AI)

    def integration(mode):
        return {"name": mode, "emoji": "🤖", "color": "#123456",
                "build_command": lambda prompt, model=None: [sys.executable, str(script), mode, prompt]}

    monkeypatch.setattr(_st, "integrations", {}, raising=False)
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(gc, "groups", {})
    monkeypatch.setattr(gc, "_loaded", True)
    monkeypatch.setattr(gc, "_store_path", lambda: tmp_path / "group_chats.json")
    events = []

    async def fake_broadcast(ev):
        events.append(ev)
    monkeypatch.setattr(gc, "_broadcast", fake_broadcast)

    def add_session(sid, name, mode):
        _st.integrations[mode] = integration(mode)
        _st.sessions[sid] = {"id": sid, "ai": mode, "name": name, "cwd": str(tmp_path),
                             "model": None, "emoji": "🤖", "color": "#123456"}
        return _st.sessions[sid]

    return {"add": add_session, "events": events, "tmp": tmp_path}


async def _wait_idle(group, timeout=20):
    for _ in range(int(timeout / 0.05)):
        await asyncio.sleep(0.05)
        if not group.get("_turn"):
            return
    raise AssertionError("room turn did not finish")


def _replies(group):
    return [(m["author_name"], m["content"]) for m in group["messages"] if m["role"] == "member"]


def test_parse_mentions():
    members = [{"id": "a", "name": "Claude #1"}, {"id": "b", "name": "Gemini Pro"}]
    assert gc.parse_mentions("hey @claude what do you think", members) == ["a"]
    assert gc.parse_mentions("@GeminiPro and @Claude#1", members) == ["a", "b"]
    assert gc.parse_mentions("@gemini", members) == ["b"]
    assert gc.parse_mentions("ask @everyone", members) == ["a", "b"]
    assert gc.parse_mentions("email me at bob@claude.com", members) == []
    assert gc.parse_mentions("no mentions", members) == []


def test_pass_detection():
    for s in ("(pass)", "pass", " (PASS) ", "pass."):
        assert gc.PASS_RE.match(s)
    assert not gc.PASS_RE.match("I'll pass on that, but here is why")


def test_everyone_answers_without_mentions(env):
    a = env["add"]("s1", "Alpha", "alpha")
    b = env["add"]("s2", "Beta", "beta")
    g = gc.make_group("Team", "", [a, b])

    async def run():
        await gc.send_user_message(g, "hello team")
        await _wait_idle(g)
    asyncio.run(run())

    # Round 1: both answer. Round 2: each sees the other's reply and answers
    # again (fake AIs never pass); capped by MAX_ROUNDS.
    replies = _replies(g)
    assert replies[:2] == [("Alpha", "alpha says hi"), ("Beta", "beta says hi")]
    assert len(replies) <= gc.MAX_REPLIES
    assert g["status"] == "idle"
    assert any(e["type"] == "group_status" and e["status"] == "running" for e in env["events"])
    assert (env["tmp"] / "group_chats.json").exists()


def test_mention_picks_who_answers(env):
    a = env["add"]("s1", "Alpha", "alpha")
    b = env["add"]("s2", "Beta", "beta")
    g = gc.make_group("Team", "", [a, b])

    async def run():
        await gc.send_user_message(g, "@Beta only you please")
        await _wait_idle(g)
    asyncio.run(run())
    assert _replies(g) == [("Beta", "beta says hi")]


def test_member_can_pull_in_another(env):
    a = env["add"]("s1", "Alpha", "pinger")
    b = env["add"]("s2", "Beta", "echo-last")
    g = gc.make_group("Team", "", [a, b])

    async def run():
        await gc.send_user_message(g, "@Alpha start")
        await _wait_idle(g)
    asyncio.run(run())
    replies = _replies(g)
    assert replies[0] == ("Alpha", "Alpha asks @Beta to check")
    assert replies[1] == ("Beta", "Beta saw -> Alpha: Alpha asks @Beta to check")


def test_pass_says_nothing_and_ends_turn(env):
    a = env["add"]("s1", "Alpha", "pass")
    b = env["add"]("s2", "Beta", "pass")
    g = gc.make_group("Quiet", "", [a, b])

    async def run():
        await gc.send_user_message(g, "anyone?")
        await _wait_idle(g)
    asyncio.run(run())
    assert _replies(g) == []
    assert [m["role"] for m in g["messages"]] == ["user"]


def test_stop_kills_running_reply(env):
    a = env["add"]("s1", "Alpha", "slow")
    g = gc.make_group("Slow", "", [a])

    async def run():
        await gc.send_user_message(g, "take your time")
        await asyncio.sleep(1.0)
        assert g["status"] == "running"
        await gc.stop_group(g)
        await asyncio.sleep(1.0)
    asyncio.run(run())
    assert _replies(g) == []
    assert g["status"] == "idle"


def test_closed_session_uses_snapshot(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("Solo", "", [a])
    del _st.sessions["s1"]  # session closed; the integration is still installed

    async def run():
        await gc.send_user_message(g, "still there?")
        await _wait_idle(g)
    asyncio.run(run())
    assert _replies(g) == [("Alpha", "alpha says hi")]


def test_prompt_frames_the_room(env):
    a = env["add"]("s1", "Alpha", "alpha")
    b = env["add"]("s2", "Beta", "beta")
    g = gc.make_group("Launch", "Plan the launch", [a, b])
    gc.append_message(g, gc.make_message("user", "what first?"))
    gc.append_message(g, gc.make_message("member", "pricing page", g["members"][1]))
    p = gc.build_prompt(g, g["members"][0])
    assert p.startswith('[Group chat: "Launch" - with the user, Beta (beta)]')
    assert "Plan the launch" in p
    assert "User: what first?" in p and "Beta: pricing page" in p
    assert "(pass)" in p
    # The member sees its own earlier messages as "You".
    assert "You: pricing page" in gc.build_prompt(g, g["members"][1])


def test_groups_persist(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("Keep", "", [a])
    gc.append_message(g, gc.make_message("user", "remember me"))
    gc.save_groups()
    gc.groups.clear()
    gc._loaded = False
    gc.load_groups()
    assert gc.groups[g["id"]]["messages"][0]["content"] == "remember me"
    assert gc.groups[g["id"]]["status"] == "idle"
