"""Group chats: background summaries (folder.py, summariser.py, validate.py, facts.py)."""
import asyncio

import helm.groupchat as gc
import helm.state as _st
from helm.groupchat_context import blocks, budget, folder, summariser, validate
from helm.groupchat_context import summarize_prompts as sp

from gc_env import chat  # the `env` fixture comes from conftest.py


def test_when_messages_get_folded(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, folder.KEEP_RECENT + folder.BATCH - 1)
    assert folder.plan(g) is None
    chat(g, 1, start=99)
    step = folder.plan(g)
    assert step["kind"] == "fold" and len(step["msgs"]) == folder.L1_MAX_MSGS
    assert step["msgs"][0]["content"].startswith("msg0")
    # Messages a member can't fit are folded even when there are few.
    g2 = gc.make_group("G2", "", [a])
    monkeypatch.setattr(budget, "budget_tokens", lambda m: 2000)
    chat(g2, 12, size=1500)
    assert len(folder.plan(g2)["msgs"]) >= folder.PRESSURE_MIN


def test_fold_writes_a_block_and_room_facts(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    env["add"]("s9", "Writer", "writer")
    monkeypatch.setenv("GROUP_SUMMARISER", "writer")
    g = gc.make_group("G", "", [a])
    chat(g, folder.KEEP_RECENT + folder.BATCH + 10)
    assert asyncio.run(gc.update_summary(g)) is True
    act = blocks.active(g)
    assert [b["level"] for b in act] == [1, 1]          # 30 due, at most 15 per block
    assert act[0]["topic"] == "early talk" and act[0]["summary"].startswith("- User: msg0")
    assert len(blocks.unfolded(g)) == folder.KEEP_RECENT
    assert g["facts"] == ["Budget is $500", "Alpha: write the tests"]
    assert any(e["type"] == "group_context" for e in env["events"])
    assert not g.get("_summarising")


def test_no_ai_answer_falls_back_to_a_plain_recap(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    _st.integrations["alpha"]["build_command"] = lambda prompt, model=None: ["no-such-ai-binary-xyz", prompt]
    g = gc.make_group("G", "", [a])
    chat(g, folder.KEEP_RECENT + folder.BATCH)
    assert asyncio.run(gc.update_summary(g)) is True
    b = blocks.active(g)[0]
    assert b["summary"].startswith("- User: msg0") and b["topic"] == ""
    assert len(b["summary"]) <= sp.SUMMARY_CHARS[1] + validate.KEEP_LINE_CHARS + 40


def test_old_level_one_blocks_merge_into_level_two(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    env["add"]("s9", "Writer", "writer")
    monkeypatch.setenv("GROUP_SUMMARISER", "writer")
    g = gc.make_group("G", "", [a])
    chat(g, 200, size=5)
    msgs = g["messages"]
    for i in range(folder.MERGE_TRIGGER + 1):
        part = msgs[i * 10:(i + 1) * 10]
        blocks.add(g, level=1, msg_ids=[m["id"] for m in part], first_ts=part[0]["timestamp"],
                   last_ts=part[-1]["timestamp"], summary=f"- part {i}")
    step = folder.plan(g)
    assert step["kind"] == "fold"            # unfolded messages come first…
    monkeypatch.setattr(folder, "BATCH", 10_000)
    step = folder.plan(g)
    assert step["kind"] == "merge" and step["level"] == 2   # …then merging
    assert [b["summary"] for b in step["blocks"]] == ["- part 0", "- part 1", "- part 2", "- part 3"]
    assert asyncio.run(folder.run(g)) is True
    act = blocks.active(g)
    assert act[0]["level"] == 2 and act[0]["summary"].startswith("- merged summary")
    assert len(act[0]["msg_ids"]) == 40 and act[0]["children"] == ["b1", "b2", "b3", "b4"]
    assert blocks.get(g, "b1")["active"] is False and blocks.get(g, "b1")["merged_into"] == act[0]["id"]


def test_cleared_meanwhile_drops_the_summary(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, folder.KEEP_RECENT + folder.BATCH)
    real = folder._write

    def clear_then_write(group, step):
        gc.clear_messages(group)
        return real(group, step)
    monkeypatch.setattr(folder, "_write", clear_then_write)
    assert asyncio.run(gc.update_summary(g)) is False
    assert not blocks.active(g) and g["messages"] == []


def test_summariser_prefers_claude_then_the_strongest_paid_ai(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    o = env["add"]("s2", "Local", "llama", ai="ollama")
    g = gc.make_group("G", "", [o, a])
    monkeypatch.setattr(summariser, "claude_installed", lambda: True)
    assert summariser.pick(g)["ai"] == "claude"
    monkeypatch.setattr(summariser, "claude_installed", lambda: False)
    assert summariser.pick(g)["ai"] == "alpha"                 # offline models never summarise
    _st.integrations["codex"] = env["integration"]("codex")
    assert summariser.pick(g)["ai"] == "codex"                 # set up, stronger, not in the group
    assert summariser.pick(g)["id"] == "summariser-codex"
    monkeypatch.setenv("GROUP_SUMMARISER", "alpha")
    assert summariser.pick(g)["id"] == "s1"                    # the member's own session


def test_repair_puts_back_exact_strings():
    src = ["Use `make_group` in helm/groupchat.py, budget $500, see https://x.dev/a and v1.2.3"]
    assert set(validate.key_strings(src)) >= {"make_group", "helm/groupchat.py", "$500",
                                              "https://x.dev/a", "v1.2.3"}
    fixed = validate.repair("- talked about groups", src)
    assert "Kept word for word:" in fixed and "helm/groupchat.py" in fixed
    assert validate.repair("- make_group in helm/groupchat.py costs $500 https://x.dev/a v1.2.3", src) \
        .count("Kept") == 0


def test_parse_reads_sections_and_tolerates_plain_text():
    topic, summary, facts = sp.parse("TOPIC: Logo\nSUMMARY:\n- blue\n- round\nFACTS:\n- Due Friday\n- (none)")
    assert (topic, summary, facts) == ("Logo", "- blue\n- round", ["Due Friday"])
    assert sp.parse("just a recap") == ("", "just a recap", [])
