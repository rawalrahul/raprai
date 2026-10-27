"""Asking before an AI acts in a connected app: the classifier, the gate, Claude's hook."""
import asyncio
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.approval as appr
import helm.approval_rules as rules
import helm.audit as audit
import helm.outward as outward
import helm.state as _st

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "helm" / "mcp" / "tool_gate_hook.py"


@pytest.fixture
def data(tmp_path, monkeypatch):
    import helm.paths as paths
    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(rules, "_path", lambda: tmp_path / "approval_rules.json")
    monkeypatch.setattr(audit, "_path", lambda: tmp_path / "audit.jsonl")
    monkeypatch.setattr(_st, "approval_queue", {}, raising=False)
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "telegram_app", None, raising=False)
    monkeypatch.delenv("OUTWARD_ACTIONS", raising=False)
    monkeypatch.delenv("OUTWARD_WAIT_MINUTES", raising=False)

    async def quiet(*a, **k):
        return None
    monkeypatch.setattr(appr, "broadcast_approval", quiet)
    monkeypatch.setattr(appr, "broadcast_resolution", quiet)
    return tmp_path


@pytest.mark.parametrize("name", [
    "mcp__claude_ai_Gmail__send_email",
    "mcp__slack__slack_post_message",
    "mcp__github__create_pull_request",
    "mcp__github__merge_pull_request",
    "mcp__linear__updateIssue",
    "google_workspace_gmail_users_messages_send",
    "mcp__stripe__create_refund",
    "mcp__notion__notion-append-block-children",
    "mcp__claude_ai_Google_Calendar__create_event",
])
def test_actions_that_change_things_are_outward(name):
    assert outward.is_outward(name)


@pytest.mark.parametrize("name", [
    "mcp__claude_ai_Gmail__search_threads",
    "mcp__github__list_pull_requests",
    "mcp__github__get_file_contents",
    "mcp__linear__listIssues",
    "google_workspace_gmail_users_messages_list",
    "mcp__claude_ai_Gmail__create_draft",          # a draft stays with you
    "mcp__postgres__query",
])
def test_reading_and_drafting_are_not(name):
    assert not outward.is_outward(name)


def test_description_names_the_ai_app_and_arguments():
    desc, details = outward.describe("mcp__claude_ai_Gmail__send_email",
                                     {"to": "bob@example.com", "subject": "Invoice  #12\n overdue"}, "claude")
    assert desc == "Claude wants to send email in Gmail"
    assert details[0] == "tool: mcp__claude_ai_Gmail__send_email"
    assert "to: bob@example.com" in details and "subject: Invoice #12 overdue" in details


def run(coro):
    return asyncio.run(coro)


def test_reading_runs_without_asking(data):
    assert run(outward.gate("mcp__github__list_issues", {}, "s1", "claude")) == (True, "")
    assert appr.pending() == []


def test_outward_action_waits_for_your_ok(data):
    async def scenario():
        task = asyncio.create_task(outward.gate("mcp__slack__post_message", {"text": "hi"}, "s1", "claude"))
        for _ in range(50):
            await asyncio.sleep(0.01)
            if appr.pending():
                break
        [req] = appr.pending()
        assert req["action"] == "outward_action" and "post message in Slack" in req["description"]
        appr.resolve(req["id"], "approved")
        return await task
    assert run(scenario()) == (True, "")


def test_declined_and_unanswered_actions_are_not_done(data, monkeypatch):
    async def answer(status):
        task = asyncio.create_task(outward.gate("mcp__github__merge_pull_request", {}, "s1"))
        await asyncio.sleep(0.05)
        appr.resolve(appr.pending()[0]["id"], status)
        return await task
    allowed, reason = run(answer("denied"))
    assert not allowed and "declined" in reason

    monkeypatch.setattr(outward, "wait_seconds", lambda: 0.05)
    allowed, reason = run(outward.gate("mcp__github__merge_pull_request", {}, "s1"))
    assert not allowed and "hasn't answered" in reason


def test_your_rules_decide_first(data):
    rules.save_rules([
        {"id": "slack-ok", "match": r"post message in slack", "action": "allow"},
        {"id": "no-merge", "match": r"merge", "action": "deny"},
        {"id": "db-ask", "match": r"postgres.*query", "action": "deny"},
    ])
    assert run(outward.gate("mcp__slack__post_message", {}, "s1")) == (True, "")
    assert run(outward.gate("mcp__github__merge_pull_request", {}, "s1"))[0] is False
    # a rule can hold back a tool that only reads, too
    assert run(outward.gate("mcp__postgres__query", {"sql": "select 1"}, "s1"))[0] is False
    applied = [e["rule"] for e in audit.read() if e["event"] == "rule_applied"]   # newest first
    assert applied == ["db-ask", "no-merge", "slack-ok"]


def test_allow_setting_stops_asking_but_rules_still_apply(data, monkeypatch):
    monkeypatch.setenv("OUTWARD_ACTIONS", "allow")
    assert run(outward.gate("mcp__slack__post_message", {}, "s1")) == (True, "")
    rules.save_rules([{"id": "no-merge", "match": "merge", "action": "deny"}])
    assert run(outward.gate("mcp__github__merge_pull_request", {}, "s1"))[0] is False


def test_read_only_runs_never_act(data):
    _st.sessions["s9"] = {"id": "s9", "ai": "codex", "read_only": True}
    allowed, reason = run(outward.gate("mcp__claude_ai_Gmail__send_email", {}, "s9"))
    assert not allowed and "suggested action" in reason
    assert appr.pending() == []                       # nobody is asked at 7am
    assert run(outward.gate("mcp__claude_ai_Gmail__search_threads", {}, "s9")) == (True, "")


def test_claude_gets_the_hook_only_when_rapr_can_answer(data, monkeypatch):
    monkeypatch.setattr(_st, "gate_url", "", raising=False)
    assert outward.claude_hook_settings("s1") is None
    monkeypatch.setattr(_st, "gate_url", "http://127.0.0.1:8123", raising=False)
    settings = json.loads(outward.claude_hook_settings("s1"))
    [entry] = settings["hooks"]["PreToolUse"]
    assert entry["matcher"] == "mcp__.*"
    hook = entry["hooks"][0]
    assert hook["type"] == "command" and hook["timeout"] > 600
    assert "tool_gate_hook.py" in hook["command"] and "http://127.0.0.1:8123 s1 " in hook["command"]
    monkeypatch.setenv("OUTWARD_ACTIONS", "allow")
    assert outward.claude_hook_settings("s1") is None   # nothing would ever ask


def test_claude_command_carries_the_settings():
    from helm.ai_runner.claude import build_claude_cmd
    cmd = build_claude_cmd("hi", False, auto_approve=True, settings='{"hooks":{}}')
    assert cmd[cmd.index("--settings") + 1] == '{"hooks":{}}'
    assert "--settings" not in build_claude_cmd("hi", False)


class _Gate(BaseHTTPRequestHandler):
    answers = {}
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Gate.seen.append((self.path, self.headers.get("Authorization"), body))
        out = json.dumps(_Gate.answers.get(body["tool_name"], {"allowed": True})).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def _hook(url, event, env=None):
    return subprocess.run([sys.executable, str(HOOK), url, "s4", "30"], input=json.dumps(event),
                          capture_output=True, text=True, timeout=30,
                          env={**os.environ, "MCP_BEARER_TOKEN": "tok", **(env or {})})


def test_hook_asks_rapr_and_blocks_what_you_decline():
    server = HTTPServer(("127.0.0.1", 0), _Gate)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    _Gate.answers = {"mcp__slack__post_message": {"allowed": False, "reason": "The user declined."}}
    try:
        ok = _hook(url, {"tool_name": "mcp__github__list_issues", "tool_input": {"repo": "x"}})
        assert ok.returncode == 0
        path, auth, body = _Gate.seen[-1]
        assert path == "/mcp/gate" and auth == "Bearer tok"
        assert body == {"tool_name": "mcp__github__list_issues", "tool_input": {"repo": "x"}, "session_id": "s4"}

        no = _hook(url, {"tool_name": "mcp__slack__post_message", "tool_input": {}})
        assert no.returncode == 2 and "The user declined." in no.stderr
    finally:
        server.shutdown()
        server.server_close()

    # RAPR gone: the action is not done
    gone = _hook(url, {"tool_name": "mcp__slack__post_message", "tool_input": {}})
    assert gone.returncode == 2 and "couldn't be reached" in gone.stderr


def test_gate_endpoint(data, monkeypatch):
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    client = TestClient(webapp)
    r = client.post("/mcp/gate", json={"tool_name": "mcp__github__list_issues", "tool_input": {}, "session_id": "-"})
    assert r.json() == {"allowed": True, "reason": ""}
    rules.save_rules([{"id": "no-mail", "match": "send email in gmail", "action": "deny"}])
    r = client.post("/mcp/gate", json={"tool_name": "mcp__claude_ai_Gmail__send_email",
                                       "tool_input": {"to": "a@b.c"}, "session_id": "s1"})
    assert r.json()["allowed"] is False


def test_hook_calls_pass_the_security_middleware():
    """The real app adds CSRF and rate limits (web_app.py); the hook has no cookie and calls often."""
    import helm.security as sec
    assert any("/mcp/gate".startswith(p) for p in sec._CSRF_EXEMPT)
    assert any("/mcp/gate".startswith(p) for p in sec._RATE_LIMIT_EXEMPT)
    from helm.web_routes.app import _MCP_PREFIXES      # localhost + bearer token, like /mcp/call
    assert "/mcp/gate" in _MCP_PREFIXES
