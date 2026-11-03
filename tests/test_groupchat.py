"""Group chats: several AIs answering in one conversation."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.groupchat as gc
import helm.state as _st


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


# ── Context: budgets, pins, clearing (more in test_gc_context_*.py) ────────

def _chat(g, n, size=10, start=0):
    for i in range(start, start + n):
        who = None if i % 2 == 0 else g["members"][-1]
        role = "user" if who is None else "member"
        gc.append_message(g, gc.make_message(role, f"msg{i} " + "x" * size, who))


def test_long_claude_prompts_go_over_stdin(monkeypatch):
    from helm.ai_runner.claude import CLAUDE_STDIN_CHARS
    from helm.council.runner import _build_cmd_for_session
    short, long_ = "hi", "y" * (CLAUDE_STDIN_CHARS + 1)
    cmd, stdin, _ = _build_cmd_for_session({"ai": "claude"}, short)
    assert cmd[-2:] == ["-p", short] and stdin is None
    cmd, stdin, _ = _build_cmd_for_session({"ai": "claude"}, long_)
    assert cmd[-1] == "-p" and long_ not in cmd and stdin == long_


def test_pins_are_always_in_the_prompt(env, monkeypatch):
    from helm.groupchat_context import budget
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    gc.append_message(g, gc.make_message("user", "Budget is $500, hard limit"))
    first = g["messages"][0]["id"]
    monkeypatch.setattr(budget, "budget_tokens", lambda m: 2000)
    _chat(g, 30, size=900)
    assert gc.pin_message(g, first) is None
    assert gc.pin_message(g, first) is None                 # pinning twice is fine
    assert len(g["pinned"]) == 1
    p = gc.build_prompt(g, g["members"][0])
    assert "Pinned by the user" in p and "User: Budget is $500, hard limit" in p
    assert gc.context_info(g)["pinned"] == 1
    assert gc.pin_message(g, "gm-nope") == "Message not found"
    gc.unpin_message(g, first)
    assert "Budget is $500" not in gc.build_prompt(g, g["members"][0])


def test_pin_limit_and_clear(env):
    from helm.groupchat_context import archive, blocks
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    _chat(g, gc.MAX_PINS + 1)
    for m in g["messages"][:gc.MAX_PINS]:
        assert gc.pin_message(g, m["id"]) is None
    assert "At most" in gc.pin_message(g, g["messages"][-1]["id"])
    blocks.add(g, level=1, msg_ids=[g["messages"][0]["id"]], first_ts=0, last_ts=0, summary="s")
    g["facts"] = ["x"]
    assert archive.path(g["id"]).exists()
    gc.clear_messages(g)
    assert g["messages"] == [] and g["pinned"] == [] and "blocks" not in g and "facts" not in g
    assert not archive.path(g["id"]).exists()
    assert "context" in gc.client_view(g) and "_cleared" not in gc.client_view(g)
