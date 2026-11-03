"""Group chats: getting detail back from summaries (recall.py, mcp_tools.py, archive.py)."""
import asyncio

import helm.groupchat as gc
from helm.groupchat_context import archive, blocks, budget, mcp_tools, recall

from gc_env import chat  # the `env` fixture comes from conftest.py


def _fold(g, msgs, summary):
    return blocks.add(g, level=1, msg_ids=[m["id"] for m in msgs], first_ts=msgs[0]["timestamp"],
                      last_ts=msgs[-1]["timestamp"], summary=summary)


def _replies_after(g, user_text):
    i = next(i for i, m in enumerate(g["messages"]) if m.get("content") == user_text)
    return [m["content"] for m in g["messages"][i + 1:] if m["role"] == "member"]


async def _wait_idle(group, timeout=20):
    for _ in range(int(timeout / 0.05)):
        await asyncio.sleep(0.05)
        if not group.get("_turn"):
            return
    raise AssertionError("room turn did not finish")


def test_parse_request():
    assert recall.parse_request("(recall b3)") == {"blocks": ["b3"]}
    assert recall.parse_request(" (recall B3, b5) ") == {"blocks": ["b3", "b5"]}
    assert recall.parse_request("(recall: stripe webhook)") == {"query": "stripe webhook"}
    assert recall.parse_request("(recall the pricing talk)") == {"query": "the pricing talk"}
    assert recall.parse_request("I recall b3 said so") is None
    assert recall.parse_request("(pass)") is None


def test_messages_survive_trimming_in_the_archive(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    monkeypatch.setattr(gc, "MAX_STORED_MESSAGES", 5)
    gc.append_message(g, gc.make_message("user", "the code is SECRET-42"))
    first = g["messages"][0]["id"]
    chat(g, 10)
    assert first not in {m["id"] for m in g["messages"]}
    assert archive.lookup(g, [first])[0]["content"] == "the code is SECRET-42"
    gc.forget_group(g["id"])
    assert archive.lookup(g, [first]) == [None]


def test_groups_from_before_the_archive_are_backfilled_on_load(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("Old", "", [a])
    g["messages"].append(gc.make_message("user", "made before the archive"))   # not archived
    gc.save_groups()
    gc.groups.clear()
    gc._loaded = False
    gc.load_groups()
    first = g["messages"][0]["id"]
    assert archive.load(g["id"])[first]["content"] == "made before the archive"


def test_search_and_expand(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    gc.append_message(g, gc.make_message("user", "Stripe webhook secret goes in config/payments.toml"))
    chat(g, 9)
    _fold(g, g["messages"][:10], "- payments talk")
    hits = recall.search(g, "where does the stripe webhook secret go?")
    assert hits and hits[0]["block"] == "b1" and "payments.toml" in hits[0]["message"]["content"]
    text = recall.expand_blocks(g, ["b1", "b9"])
    assert "[b1 · 10 messages, word for word]" in text and "config/payments.toml" in text
    assert "[b9: no such summary]" in text
    assert "nothing earlier" in recall.answer_search(g, "kubernetes")


def test_small_member_gets_matching_details_automatically(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    gc.append_message(g, gc.make_message("user", "Stripe webhook secret goes in config/payments.toml"))
    chat(g, 29, size=300, start=1)
    _fold(g, g["messages"][:15], "- payments and other things")
    gc.append_message(g, gc.make_message("user", "remind me where the stripe webhook secret goes"))
    monkeypatch.setattr(budget, "budget_tokens", lambda m: 2_200)
    p = gc.build_prompt(g, g["members"][0])
    assert "- payments and other things" in p
    assert "Earlier messages that may matter" in p and "[from b1] User: Stripe webhook" in p


def test_member_that_asks_is_run_again_with_the_messages(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "recaller", stdin=True)
    g = gc.make_group("G", "", [a])
    gc.append_message(g, gc.make_message("user", "the code is SECRET-42"))
    chat(g, 9, start=1)
    _fold(g, g["messages"][:10], "- a code was shared")

    async def run():
        await gc.send_user_message(g, "what was the code?")
        await _wait_idle(g)
    asyncio.run(run())
    replies = _replies_after(g, "what was the code?")
    assert replies[0] == "got it: SECRET-42"
    assert not any("(recall" in r for r in replies)


def test_asking_twice_counts_as_a_pass(env):
    a = env["add"]("s1", "Alpha", "nested-recall", stdin=True)
    g = gc.make_group("G", "", [a])
    chat(g, 10)
    _fold(g, g["messages"][:10], "- stuff")

    async def run():
        await gc.send_user_message(g, "go")
        await _wait_idle(g)
    asyncio.run(run())
    assert _replies_after(g, "go") == []


def test_mcp_tools_read_the_saved_group(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("Payments", "", [a])
    gc.append_message(g, gc.make_message("user", "Stripe webhook secret goes in config/payments.toml"))
    chat(g, 5, start=1)
    _fold(g, g["messages"][:6], "- payments")
    gc.save_groups()
    out = mcp_tools.tool_group_recall({"group": g["id"], "blocks": ["b1"]})
    assert "config/payments.toml" in out
    out = mcp_tools.tool_group_search({"group": "payments", "query": "stripe webhook"})
    assert "[from b1] User: Stripe webhook" in out
    assert "No group chat" in mcp_tools.tool_group_search({"group": "nope", "query": "x"})
    from helm import mcp_server
    assert {"group_search", "group_recall"} <= set(mcp_server.TOOLS)
