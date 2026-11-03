"""Group chats: one view of the shared history per member (render.py, fit.py)."""
import helm.groupchat as gc
from helm.groupchat_context import blocks, budget, render

from gc_env import chat  # the `env` fixture comes from conftest.py


def _fold(g, msgs, summary, level=1, children=None):
    return blocks.add(g, level=level, msg_ids=[m["id"] for m in msgs],
                      first_ts=msgs[0]["timestamp"], last_ts=msgs[-1]["timestamp"],
                      summary=summary, topic="t", children=children)


def _budgets(monkeypatch, by_name):
    monkeypatch.setattr(budget, "budget_tokens", lambda m: by_name[m["name"]])


def test_prompt_frames_the_room(env):
    a = env["add"]("s1", "Alpha", "alpha")
    b = env["add"]("s2", "Beta", "beta")
    g = gc.make_group("Launch", "Plan the launch", [a, b])
    gc.append_message(g, gc.make_message("user", "what first?"))
    gc.append_message(g, gc.make_message("member", "pricing page", g["members"][1]))
    p = gc.build_prompt(g, g["members"][0])
    assert p.startswith('[Group chat: "Launch" - with the user, Beta (beta)]')
    assert "Plan the launch" in p and "User: what first?" in p and "Beta: pricing page" in p
    assert "(pass)" in p and "(recall" not in p        # nothing summarised: no recall hint
    assert "You: pricing page" in gc.build_prompt(g, g["members"][1])


def test_big_window_reads_summarised_parts_word_for_word_small_one_reads_summaries(env, monkeypatch):
    a = env["add"]("s1", "Big", "alpha")
    b = env["add"]("s2", "Small", "beta")
    g = gc.make_group("G", "", [a, b])
    chat(g, 40, size=400)
    _fold(g, g["messages"][:15], "- early part, summarised")
    _fold(g, g["messages"][15:30], "- middle part, summarised")
    _budgets(monkeypatch, {"Big": 200_000, "Small": 2_500})
    big, info_big = render.build(g, g["members"][0])
    small, info_small = render.build(g, g["members"][1])
    assert "msg0 " in big and "summarised" not in big and info_big["expanded"] == 2
    assert "early part, summarised" in small and "msg0 " not in small
    assert "[b1 · summary of 15 messages · t]" in small and "(recall b1)" in small
    assert info_small["summaries"] == 2 and info_small["tokens"] <= 2_500


def test_spare_room_opens_the_newest_summary_first(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, 30, size=1000)
    _fold(g, g["messages"][:10], "- OLDEST")
    _fold(g, g["messages"][10:20], "- NEWER")
    # Room for the open messages, one opened summary, and the other as a summary.
    _budgets(monkeypatch, {"Alpha": 7_000})
    p, info = render.build(g, g["members"][0])
    assert "- OLDEST" in p and "- NEWER" not in p and "msg15 " in p and info["expanded"] == 1
    assert p.index("- OLDEST") < p.index("msg15 ")


def test_level_two_opens_into_level_one_before_raw(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, 24, size=1500)
    one = _fold(g, g["messages"][:10], "- L1 one")
    two = _fold(g, g["messages"][10:20], "- L1 two")
    msgs = g["messages"][:20]
    _fold(g, msgs, "- L2 both", level=2, children=[one["id"], two["id"]])
    assert [b["id"] for b in blocks.active(g)] == ["b3"]
    _budgets(monkeypatch, {"Alpha": 3_500})
    p = gc.build_prompt(g, g["members"][0])
    assert "- L1 one" in p and "- L1 two" in p and "- L2 both" not in p


def test_too_small_shortens_then_hides_oldest_messages(env, monkeypatch):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, 10, size=5000)
    _budgets(monkeypatch, {"Alpha": 12_000})
    p = gc.build_prompt(g, g["members"][0])
    assert "msg9 " + "x" * 5000 in p and "chars cut" in p          # newest whole, older cut
    _budgets(monkeypatch, {"Alpha": 2_000})
    p, info = render.build(g, g["members"][0])
    assert "earlier messages not shown" in p and "msg9" in p and "msg0 " not in p
    assert info["hidden"] > 0 and gc.context_info(g)["pct"] > 50


def test_marker_shows_what_is_new_since_the_member_spoke(env):
    a = env["add"]("s1", "Alpha", "alpha")
    b = env["add"]("s2", "Beta", "beta")
    g = gc.make_group("G", "", [a, b])
    alpha = g["members"][0]
    gc.append_message(g, gc.make_message("user", "q1"))
    gc.append_message(g, gc.make_message("member", "a1", alpha))
    gc.append_message(g, gc.make_message("user", "q2"))
    p = gc.build_prompt(g, alpha)
    assert p.index("You: a1") < p.index("--- new since your last message ---") < p.index("User: q2")
    assert "--- new since" not in gc.build_prompt(g, g["members"][1])


def test_facts_and_pins_come_after_the_history(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, 4)
    g["facts"] = ["Deadline: Friday"]
    gc.pin_message(g, g["messages"][0]["id"])
    p = gc.build_prompt(g, g["members"][0])
    assert p.index("msg3") < p.index("Room facts") < p.index("Pinned by the user") < p.index("Write your next")


def test_meter_lists_every_member(env, monkeypatch):
    a = env["add"]("s1", "Big", "alpha")
    b = env["add"]("s2", "Small", "beta")
    g = gc.make_group("G", "", [a, b])
    chat(g, 10, size=2000)
    _budgets(monkeypatch, {"Big": 200_000, "Small": 3_000})
    info = gc.context_info(g)
    assert [m["name"] for m in info["members"]] == ["Big", "Small"]
    assert info["tightest"] == g["members"][1]["id"] and info["budget"] == 3_000


def test_old_single_summary_becomes_a_legacy_block(env):
    a = env["add"]("s1", "Alpha", "alpha")
    g = gc.make_group("G", "", [a])
    chat(g, 6)
    g["summary"], g["summary_upto"] = "- User wants a blue logo", g["messages"][3]["id"]
    blocks.migrate_legacy_summary(g)
    assert "summary" not in g and blocks.active(g)[0]["legacy"]
    p = gc.build_prompt(g, g["members"][0])
    assert "- User wants a blue logo" in p and "msg3" not in p and "msg4" in p
    # The boundary already trimmed: everything left is newer than the summary.
    g2 = gc.make_group("G2", "", [a])
    chat(g2, 3)
    g2["summary"], g2["summary_upto"] = "- old", "gm-gone"
    blocks.migrate_legacy_summary(g2)
    assert len(blocks.unfolded(g2)) == 3
