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
    # Same prompt budget on every OS (Windows' command line is much shorter).
    monkeypatch.setattr(gc, "ARGV_MAX_CHARS_WINDOWS", gc.ARGV_MAX_CHARS_POSIX)
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


# ── Context: budget, summary, pins ──────────────────────────────────────────

def _chat(g, n, size=10, start=0):
    for i in range(start, start + n):
        who = None if i % 2 == 0 else g["members"][-1]
        role = "user" if who is None else "member"
        gc.append_message(g, gc.make_message(role, f"msg{i} " + "x" * size, who))


def test_old_long_messages_are_shortened_newest_kept_whole(env):
    a = env["add"]("s1", "Alpha", "alpha")
    b = env["add"]("s2", "Beta", "beta")
    g = gc.make_group("G", "", [a, b])
    _chat(g, 10, size=5000)
    p = gc.build_prompt(g, g["members"][0])
    assert "msg9 " + "x" * 5000 in p                 # newest: in full
    assert "msg0 " + "x" * 5000 not in p             # old: shortened…
    assert "chars cut" in p                          # …and says so


def test_messages_that_dont_fit_the_budget_are_counted(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    monkeypatch.setattr(gc, "MAX_PROMPT_TOKENS", 2000)     # ~8000 chars
    _chat(g, 20, size=900)
    p = gc.build_prompt(g, g["members"][0])
    assert len(p) <= 2000 * gc.CHARS_PER_TOKEN + 500
    assert "earlier messages not shown" in p
    assert "msg19" in p and "msg0 " not in p
    info = gc.context_info(g)
    assert info["hidden"] > 0 and info["pct"] > 50


def test_command_line_members_get_a_tighter_budget(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    m = g["members"][0]
    roomy = gc.prompt_budget_tokens(m)
    _st.integrations["alpha"]["stdin_prompt"] = True
    assert gc.prompt_budget_tokens(m) >= roomy
    _st.integrations["alpha"]["stdin_prompt"] = False
    monkeypatch.setattr(gc, "ARGV_MAX_CHARS_POSIX", 8000)
    monkeypatch.setattr(gc, "ARGV_MAX_CHARS_WINDOWS", 8000)
    assert gc.prompt_budget_tokens(m) == 2000


def test_long_claude_prompts_go_over_stdin():
    sess = {"ai": "claude"}
    short, long_ = "hi", "y" * (gc.STDIN_PROMPT_CHARS + 1)
    assert gc.use_stdin_if_long(sess, ["claude", "-p", short], None, short) == (["claude", "-p", short], None)
    assert gc.use_stdin_if_long(sess, ["claude", "-p", long_], None, long_) == (["claude", "-p"], long_)
    other = {"ai": "codex"}
    assert gc.use_stdin_if_long(other, ["codex", long_], None, long_) == (["codex", long_], None)


def test_summary_replaces_folded_messages_in_the_prompt(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    _chat(g, 6)
    g["summary"] = "- User wants a blue logo"
    g["summary_upto"] = g["messages"][3]["id"]
    p = gc.build_prompt(g, g["members"][0])
    assert "Summary of the earlier conversation:\n- User wants a blue logo" in p
    assert "msg3" not in p and "msg4" in p and "msg5" in p
    assert p.index("Summary of the earlier") < p.index("msg4")
    info = gc.context_info(g)
    assert info["summarised"] == 4 and info["has_summary"]
    # Boundary trimmed from storage: everything left is newer than the summary.
    del g["messages"][:4]
    assert [m["content"][:4] for m in gc._unsummarised(g)] == ["msg4", "msg5"]


def test_when_messages_get_folded(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    _chat(g, gc.SUMMARY_KEEP_RECENT + gc.SUMMARY_BATCH - 1)
    assert gc.messages_to_fold(g) == []
    _chat(g, 1, start=99)
    fold = gc.messages_to_fold(g)
    assert len(fold) == gc.SUMMARY_BATCH and fold[0]["content"].startswith("msg0")
    # Messages that don't fit a member's prompt are folded even when there are few.
    g2 = gc.make_group("G2", "", [a])
    monkeypatch.setattr(gc, "MAX_PROMPT_TOKENS", 2000)
    _chat(g2, 12, size=1500)
    assert len(gc.messages_to_fold(g2)) >= gc.SUMMARY_MIN_FOLD


def test_update_summary_uses_a_member_and_falls_back_to_a_digest(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    _chat(g, gc.SUMMARY_KEEP_RECENT + gc.SUMMARY_BATCH)
    assert asyncio.run(gc.update_summary(g)) is True
    assert g["summary"] == "alpha says hi"            # what the fake AI wrote
    assert g["summary_count"] == gc.SUMMARY_BATCH
    assert len(gc._unsummarised(g)) == gc.SUMMARY_KEEP_RECENT
    assert "msg0" not in gc.build_prompt(g, g["members"][0])
    assert any(e["type"] == "group_context" for e in env["events"])

    # The AI can't run: a plain digest of the folded messages is kept instead.
    _st.integrations["alpha"]["build_command"] = lambda prompt, model=None: ["no-such-ai-binary-xyz", prompt]
    _chat(g, gc.SUMMARY_BATCH, start=100)
    assert asyncio.run(gc.update_summary(g)) is True
    assert g["summary"].startswith("alpha says hi\n- User: msg10")
    assert len(g["summary"]) <= gc.SUMMARY_MAX_CHARS


def test_summary_is_dropped_if_the_chat_was_cleared_meanwhile(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    _chat(g, gc.SUMMARY_KEEP_RECENT + gc.SUMMARY_BATCH)
    real = gc._summarise_blocking

    def clear_then_summarise(group, msgs):
        gc.clear_messages(group)
        return real(group, msgs)
    gc._summarise_blocking = clear_then_summarise
    try:
        assert asyncio.run(gc.update_summary(g)) is False
    finally:
        gc._summarise_blocking = real
    assert not g.get("summary") and g["messages"] == []


def test_pins_are_always_in_the_prompt(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    gc.append_message(g, gc.make_message("user", "Budget is $500, hard limit"))
    first = g["messages"][0]["id"]
    monkeypatch.setattr(gc, "MAX_PROMPT_TOKENS", 2000)
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
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    _chat(g, gc.MAX_PINS + 1)
    for m in g["messages"][:gc.MAX_PINS]:
        assert gc.pin_message(g, m["id"]) is None
    assert "At most" in gc.pin_message(g, g["messages"][-1]["id"])
    g["summary"], g["summary_upto"] = "s", g["messages"][0]["id"]
    gc.clear_messages(g)
    assert g["messages"] == [] and g["pinned"] == [] and "summary" not in g
    assert "context" in gc.client_view(g) and "_cleared" not in gc.client_view(g)
