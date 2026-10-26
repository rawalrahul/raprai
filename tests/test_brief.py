"""Your brief: what needs you from every AI's apps, one-tap actions, and what your AIs can reach."""
import asyncio
import os
import sys
import time
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.approval as appr
import helm.audit as audit
import helm.brief as brief
import helm.reach as reach
import helm.state as _st


@pytest.fixture
def data(tmp_path, monkeypatch):
    import helm.paths as paths
    import helm.session_mgr as sm
    import helm.approval_rules as rules
    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(rules, "_path", lambda: tmp_path / "approval_rules.json")
    monkeypatch.setattr(audit, "_path", lambda: tmp_path / "audit.jsonl")
    monkeypatch.setattr(_st, "approval_queue", {}, raising=False)
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "session_counter", 0, raising=False)
    monkeypatch.setattr(_st, "focused_id", None, raising=False)
    monkeypatch.setattr(_st, "telegram_app", None, raising=False)
    monkeypatch.setattr(_st, "integrations", {"codex": {"name": "Codex", "emoji": "💻", "color": "#2c5"}},
                        raising=False)
    monkeypatch.setattr(sm, "get_history_messages", lambda pid: [])
    monkeypatch.setattr(sm, "save_cwd_to_log", lambda *a, **k: None)

    class _Term:
        def launch(self): pass
        def stop(self): pass
    monkeypatch.setattr(sm, "TerminalSession", _Term)

    async def quiet(*a, **k):
        return None
    import helm.broadcast as bc
    monkeypatch.setattr(bc, "broadcast", quiet)
    monkeypatch.setattr(bc, "push_state", quiet)
    import helm.heartbeat as hb
    monkeypatch.setattr(hb, "scan_pending_tasks", lambda **k: [])
    return tmp_path


def run(coro):
    return asyncio.run(coro)


# ── Reading the AI's answer ─────────────────────────────────────────────────

def test_items_are_found_inside_chatter():
    text = ('Checked Gmail.\n```json\n{"items": [{"title": "Reply to Dana", "why": "Contract due today",'
            ' "app": "Gmail", "urgency": "URGENT", "action": "Draft a reply", "link": "javascript:x"},'
            ' {"why": "no title"}]}\n```\nDone.')
    items, problem = brief.parse_items(text)
    assert problem == ""
    assert items == [{"title": "Reply to Dana", "why": "Contract due today", "app": "Gmail",
                      "urgency": "normal", "action": "Draft a reply", "link": ""}]


def test_nothing_and_problems_are_reported():
    assert brief.parse_items('{"items": []}') == ([], "")
    assert brief.parse_items('{"items": [], "problem": "No Gmail connector"}') == ([], "No Gmail connector")
    assert brief.parse_items("I couldn't do it")[1].startswith("The AI didn't answer")


# ── What your AIs can reach ─────────────────────────────────────────────────

def test_claude_and_gemini_lists():
    claude = ("Checking MCP server health…\n\n"
              "claude.ai Gmail: https://gmail.mcp.claude.com/mcp - ✓ Connected\n"
              "claude.ai Google Calendar: https://gcal.mcp.claude.com/mcp - ! Needs authentication\n"
              "github: npx -y @modelcontextprotocol/server-github - √ Connected\n"
              "notion: https://mcp.notion.com/mcp (HTTP) - × Failed to connect — 403 Forbidden\n")
    assert reach.parse_list(claude) == [
        {"name": "Gmail", "via": "claude.ai", "status": "connected"},
        {"name": "Google Calendar", "via": "claude.ai", "status": "needs sign-in"},
        {"name": "github", "via": "", "status": "connected"},
        {"name": "notion", "via": "", "status": "not connected"},
    ]
    gemini = "Configured MCP servers:\n\n✓ linear: https://mcp.linear.app/sse (sse) - Connected\n"
    assert reach.parse_list(gemini) == [{"name": "linear", "via": "", "status": "connected"}]


def test_codex_json_list():
    out = ('[{"name": "github", "enabled": true, "auth_status": "unsupported"},'
           ' {"name": "linear", "enabled": false, "auth_status": "unknown"}]\n'
           'WARNING: proceeding, even though we could not create PATH aliases: Refusing to create '
           'helper binaries under temporary dir "/tmp" (codex_home: AbsolutePathBuf("/tmp/x"))')
    assert reach.parse_codex_json(out) == [{"name": "github", "via": "", "status": "connected"},
                                           {"name": "linear", "via": "", "status": "off"}]
    assert reach.parse_codex_json("WARNING [x]\n" + out.split("\n")[0]) == reach.parse_codex_json(out)


def test_discover_counts_raprs_copies_once(data, monkeypatch):
    monkeypatch.setattr(reach, "rapr_servers", lambda: [{"name": "zapier", "via": "RAPR", "status": "connected"}])

    def scan(ai):
        if ai == "gemini":
            return None
        apps = [{"name": "zapier", "via": "", "status": "connected"}] if ai == "codex" else []
        apps.append({"name": f"{ai}-mail", "via": "", "status": "connected"})
        return {"ai": ai, "name": ai, "apps": apps, "error": ""}
    monkeypatch.setattr(reach, "scan_agent", scan)
    d = reach.discover(force=True)
    assert [a["ai"] for a in d["agents"]] == ["claude", "codex"]
    assert [x["name"] for x in d["agents"][1]["apps"]] == ["codex-mail"]
    assert reach.summary(d) == {"ais": 2, "apps": 3}
    assert (data / "reach.json").exists()
    monkeypatch.setattr(reach, "scan_agent", lambda ai: pytest.fail("cached answer expected"))
    reach._cache = {}
    assert reach.discover()["agents"] == d["agents"]


def test_suggestions_come_from_connected_apps(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)
    data = {"agents": [{"ai": "claude", "apps": [{"name": "Gmail", "via": "claude.ai", "status": "connected"},
                                                  {"name": "x", "via": "", "status": "off"}]},
                       {"ai": "codex", "apps": []}]}
    assert brief.suggestions(data) == [{"ai": "claude", "look_at": "my apps you're connected to: Gmail (claude.ai)"}]


# ── Putting it together ─────────────────────────────────────────────────────

def test_settings_are_checked(data):
    assert brief.load_settings()["enabled"] is True and brief.load_settings()["sources"] == []
    saved = brief.save_settings({"time": "07:30", "every_hours": 4,
                                 "sources": [{"ai": "claude", "look_at": "  my   Gmail "}]})
    assert saved["time"] == "07:30" and saved["sources"][0]["look_at"] == "my Gmail"
    assert brief.load_settings()["every_hours"] == 4
    for bad in ({"time": "7am"}, {"sources": [{"ai": "", "look_at": "x"}]},
                {"sources": [{"ai": "claude", "look_at": ""}]}):
        with pytest.raises(ValueError):
            brief.save_settings(bad)


def test_each_ai_looks_read_only_and_leaves_no_session(data, monkeypatch):
    import helm.ai_runner as ar
    seen = {}

    async def fake_process(text, source="web", session_id=None):
        s = _st.sessions[session_id]
        seen.update(read_only=s.get("read_only"), ai=s["ai"], source=source, cwd=s["cwd"], prompt=text)
        return '{"items": [{"title": "PR 12 waits for you", "urgency": "high", "action": "Review it"}]}'
    monkeypatch.setattr(ar, "process_message", fake_process)
    r = run(brief.run_source({"id": "s1", "ai": "codex", "look_at": "GitHub"}, 5))
    assert seen["read_only"] is True and seen["ai"] == "codex" and seen["source"] == "brief"
    assert "Look at GitHub" in seen["prompt"] and "Only look" in seen["prompt"]
    assert seen["cwd"] == str(data / "brief")
    assert _st.sessions == {}
    assert r["items"][0]["ai"] == "codex" and r["items"][0]["kind"] == "ai"


def test_brief_puts_approvals_first_and_numbers_items(data, monkeypatch):
    brief.save_settings({"sources": [{"ai": "claude", "look_at": "Gmail"}]})
    appr.create_request("s1", "outward_action", "Claude wants to send email in Gmail")
    brief.record_result({"id": "t1", "name": "Nightly tests", "ai": "codex", "cwd": "/p"}, "(error: tests failed)")

    async def fake_source(src, max_items):
        return {"source": src, "problem": "", "items": [
            {"kind": "ai", "ai": "claude", "title": "FYI newsletter", "urgency": "low", "action": "", "why": ""},
            {"kind": "ai", "ai": "claude", "title": "Reply to Dana", "urgency": "high", "action": "Draft it",
             "why": "due today", "app": "Gmail", "link": ""}]}
    monkeypatch.setattr(brief, "run_source", fake_source)
    b = run(brief.build("manual"))
    assert [(i["n"], i["kind"], i["title"][:14]) for i in b["items"]] == [
        (1, "approval", "Claude wants t"), (2, "ai", "Reply to Dana"),
        (3, "schedule", "Nightly tests "), (4, "ai", "FYI newsletter")]
    assert b["items"][2]["urgency"] == "high" and "failed" in b["items"][2]["title"]
    assert b["checked"] == [{"ai": "claude", "look_at": "Gmail", "found": 2, "problem": ""}]
    assert brief.latest()["id"] == b["id"]
    t = brief.text(b)
    assert "1. 🔴 Claude wants to send email in Gmail" in t and "2. 🔴 Reply to Dana (Gmail)" in t
    assert "Checked: Claude: Gmail; RAPR" in t and "/do <number>" in t


def test_check_ins_only_send_when_something_is_new(data, monkeypatch):
    sent = []

    async def fake_send(b):
        sent.append(b["trigger"])
        return []
    monkeypatch.setattr(brief, "send", fake_send)
    run(brief.run("check-in"))                       # nothing yet: stays quiet
    assert sent == []
    appr.create_request("s1", "outward_action", "Claude wants to post in Slack")
    run(brief.run("schedule"))
    run(brief.run("check-in"))                       # same as before: stays quiet
    appr.create_request("s1", "outward_action", "Codex wants to merge in GitHub")
    run(brief.run("check-in"))
    assert sent == ["schedule", "check-in"]
    brief._save_latest({"id": "b0", "created": time.time(), "checked": [], "items": []})
    run(brief.run("check-in"))                       # after an empty brief, anything is new
    assert sent == ["schedule", "check-in", "check-in"]


def test_tapping_an_item_hands_it_to_its_ai(data, monkeypatch):
    import helm.ai_runner as ar
    ran = []

    async def fake_process(text, source="web", session_id=None):
        ran.append((text, source, session_id))
        return "done"
    monkeypatch.setattr(ar, "process_message", fake_process)
    brief._save_latest({"id": "b1", "created": time.time(), "checked": [], "items": [
        {"n": 1, "kind": "approval", "ref": "appr-1", "title": "x", "status": "open"},
        {"n": 2, "kind": "ai", "ai": "codex", "title": "CI is red on main", "why": "3 tests fail",
         "app": "GitHub", "action": "Fix the failing tests", "link": "https://github.com/o/r/actions/1",
         "folder": "/proj", "status": "open"},
        {"n": 3, "kind": "ai", "ai": "nope", "title": "y", "action": "Do y", "status": "open"},
        {"n": 4, "kind": "ai", "ai": "claude", "title": "z", "action": "", "status": "open"}]})
    sess, prompt = run(brief.start_item(2, source="telegram"))
    assert sess["ai"] == "codex" and sess["cwd"] == "/proj" and _st.focused_id == sess["id"]
    assert prompt.startswith("Fix the failing tests") and "CI is red on main (GitHub)" in prompt
    assert "https://github.com/o/r/actions/1" in prompt
    assert brief.item(brief.latest(), 2)["status"] == "started"
    assert ran == []                                   # the chat app runs it and relays the reply
    assert run(brief.start_item(3))[0]["ai"] == "claude"   # unknown AI → Claude
    assert run(brief.start_item(1))[0] is None
    assert run(brief.start_item(4))[0] is None
    assert run(brief.start_item(9))[1].startswith("There's no item 9")


def test_chat_commands(data, monkeypatch):
    import helm.ai_runner as ar
    import helm.chat_router as cr

    async def fake_process(text, source="web", session_id=None):
        return "PR reviewed"
    monkeypatch.setattr(ar, "process_message", fake_process)
    brief._save_latest({"id": "b1", "created": time.time(), "checked": [], "items": [
        {"n": 1, "kind": "ai", "ai": "claude", "title": "Review PR 7", "action": "Review it", "status": "open"},
        {"n": 2, "kind": "ai", "ai": "claude", "title": "Old thing", "action": "x", "status": "open"}]})
    assert "1. 🟡 Review PR 7" in run(cr.handle("whatsapp", "/brief"))[0]
    assert run(cr.handle("whatsapp", "/skip 2")) == ["Dropped item 2."]
    replies = run(cr.handle("whatsapp", "/do 1"))
    assert "took item 1" in replies[0] and replies[1] == "PR reviewed"
    assert "Old thing" not in run(cr.handle("whatsapp", "/brief"))[0]


def test_telegram_buttons_fit(data):
    b = {"items": [{"n": 1, "kind": "approval", "ref": "appr-1234abcd", "title": "x", "status": "open"},
                   {"n": 12, "kind": "ai", "ai": "codex", "title": "y", "action": "do", "status": "open"},
                   {"n": 13, "kind": "ai", "ai": "claude", "title": "z", "action": "", "status": "open"}]}
    kb = brief.telegram_keyboard(b)
    data_ = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert data_ == ["brief:ok:appr-1234abcd", "brief:no:appr-1234abcd", "brief:do:12", "brief:skip:12"]
    assert all(len(d.encode()) <= 64 for d in data_)
    assert "Hand to Codex" in kb.inline_keyboard[1][0].text


# ── When it runs ────────────────────────────────────────────────────────────

def test_slots_and_missed_runs():
    s = {"enabled": True, "time": "08:00", "every_hours": 4}
    day = datetime(2026, 10, 26, 6, 0)
    assert [t.strftime("%H:%M") for t in brief.slots(day, s)] == ["08:00", "12:00", "16:00", "20:00"]
    assert brief.due_slot(day, s, "") is None                                   # too early
    assert brief.due_slot(datetime(2026, 10, 26, 8, 0, 30), s, "").hour == 8
    assert brief.due_slot(datetime(2026, 10, 26, 8, 1), s, "2026-10-26 08:00") is None   # already ran
    assert brief.due_slot(datetime(2026, 10, 26, 10, 30), s, "").hour == 8      # PC was asleep at 8
    assert brief.due_slot(datetime(2026, 10, 26, 11, 30), {**s, "every_hours": 0}, "") is None  # too late
    assert brief.due_slot(datetime(2026, 10, 26, 9), {**s, "enabled": False}, "") is None


def test_needs_endpoint(data):
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    client = TestClient(webapp)
    appr.create_request("s1", "outward_action", "Claude wants to post in Slack")
    brief.record_result({"id": "t1", "name": "Digest", "ai": "claude"}, "All good")
    brief._save_latest({"id": "b1", "created": time.time(), "checked": [], "items": [
        {"n": 1, "kind": "approval", "ref": "a", "title": "dup", "status": "open"},
        {"n": 2, "kind": "ai", "title": "Reply to Dana", "status": "open"},
        {"n": 3, "kind": "ai", "title": "gone", "status": "dismissed"}]})
    d = client.get("/api/needs").json()
    assert [a["description"] for a in d["approvals"]] == ["Claude wants to post in Slack"]
    assert [i["title"] for i in d["brief"]["items"]] == ["Reply to Dana"]
    assert d["results"][0]["name"] == "Digest" and d["results"][0]["failed"] is False
    assert client.post("/api/brief/item/2/skip").json() == {"ok": True}
    assert client.put("/api/brief/settings", json={"time": "nope"}).status_code == 400


def test_mcp_clients_can_read_the_latest_brief(data):
    import helm.mcp_server as mcp
    assert "No brief yet" in mcp.tool_latest_brief({}, None)
    brief._save_latest({"id": "b1", "created": time.time(), "checked": [], "items": [
        {"n": 1, "kind": "ai", "ai": "claude", "title": "Reply to Dana", "app": "Gmail", "status": "open"}]})
    out = mcp.tool_latest_brief({}, None)
    assert "1. 🟡 Reply to Dana (Gmail)" in out and "/do <number>" in out
    assert mcp.TOOLS["latest_brief"][0]["annotations"]["readOnlyHint"] is True


def test_a_brief_look_runs_once_on_the_ai_you_picked(monkeypatch):
    """Codex's answer about a rate-limit PR reads like a CLI error; it must not be
    retried or handed to Claude, which has other apps."""
    import helm.ai_runner.core as core
    calls = []

    async def fake_run(ai, *args, **kwargs):
        calls.append(ai)
        return '{"items": [{"title": "PR #212 adds rate-limit middleware"}]}'

    async def nothing(*a, **k):
        return None
    monkeypatch.setattr(core, "_run_single_ai", fake_run)
    monkeypatch.setattr(core, "_find_available_ais", lambda ai: ["claude"])
    monkeypatch.setattr(core.asyncio, "sleep", nothing)
    monkeypatch.setattr(core, "push_message", nothing)
    monkeypatch.setattr(core, "push_agent_error", nothing)
    monkeypatch.setitem(_st.integrations, "codex", {"name": "Codex"})
    assert core._is_failure('{"items": [{"title": "PR #212 adds rate-limit middleware"}]}')   # why it matters
    sess = {"id": "s1", "ai": "codex", "read_only": True}
    out, used = asyncio.run(core._dispatch_with_recovery(
        "codex", sess, "look", "look", ".", None, "brief", "s1", None, None))
    assert used == "codex" and calls == ["codex"] and "rate-limit" in out
