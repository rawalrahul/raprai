"""Model picker for Claude: live model list, per-chat choice, mid-chat switching, what answered.

The behaviour these tests pin down was checked against the real Claude Code CLI (2.1.302):
  * its startup "initialize" control request returns the /model list: name, exact model, description
  * --continue with no --model keeps the conversation's last model; --model default resets it,
    but it also overrides the user's own setting (ANTHROPIC_MODEL), so it's only sent right after
    a chat switches back to Default, as the user's configured model when there is one
  * stream-json names the answering model on each assistant message
  * modelUsage also lists a Haiku helper, often with more tokens than the answer
  * effort: --effort takes low, medium, high, xhigh, max; the initialize reply lists per model
    supportsEffort and supportedEffortLevels; an unknown level is ignored with only a warning
  * an unknown model: exit 1, is_error, api_error_status 404, "There's an issue with the selected model"
  * an older exact version works and comes back dated (claude-opus-4-5 -> claude-opus-4-5-20251101);
    a retired one (claude-opus-4-1) is answered by a current model with no error
"""
import asyncio
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm import claude_models
from helm.ai_runner.claude import build_claude_cmd, model_answered, model_rejected, parse_claude_json_output

REJECTED = json.dumps({
    "type": "result", "subtype": "success", "is_error": True, "api_error_status": 404,
    "result": "There's an issue with the selected model (nope). It may not exist or you may not have access to it.",
    "modelUsage": {}, "usage": {"input_tokens": 0, "output_tokens": 0},
})

# Trimmed from the real reply of Claude Code 2.1.302 to its initialize request.
LEVELS = ["low", "medium", "high", "xhigh", "max"]
LIVE_MODELS = [
    {"value": "default", "resolvedModel": "claude-sonnet-5-5", "displayName": "Default (recommended)",
     "description": "Sonnet 5.5 · Efficient for routine tasks", "supportsEffort": True, "supportedEffortLevels": LEVELS},
    {"value": "sonnet", "resolvedModel": "claude-sonnet-5-5", "displayName": "Sonnet",
     "description": "Sonnet 5.5 · Efficient for routine tasks", "supportsEffort": True, "supportedEffortLevels": LEVELS},
    {"value": "fable", "resolvedModel": "claude-fable-5-1", "displayName": "Fable",
     "description": "Fable 5.1 · Most capable for your hardest and longest-running tasks · Requires usage credits",
     "supportsEffort": True, "supportedEffortLevels": LEVELS},
    {"value": "opus", "resolvedModel": "claude-opus-5-5", "displayName": "Opus",
     "description": "Opus 5.5 · Best for everyday, complex tasks", "supportsEffort": True, "supportedEffortLevels": LEVELS},
    {"value": "haiku", "resolvedModel": "claude-haiku-5-5", "displayName": "Haiku",
     "description": "Haiku 5.5 · Fastest for quick answers", "supportsEffort": False, "supportedEffortLevels": LEVELS},
]
# (Haiku is marked supportsEffort False here only to test that case; on the real account it takes effort too.)
INIT_REPLY = "\n".join([
    json.dumps({"type": "active_goal", "value": None}),
    json.dumps({"type": "control_response", "response": {"subtype": "success", "request_id": "rapr-models",
                "response": {"commands": [], "models": LIVE_MODELS, "account": {"subscriptionType": "max"}}}}),
])


def result(text="OK", usage=None):
    return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text,
                       "modelUsage": usage or {}, "usage": {"input_tokens": 3, "output_tokens": 1}})


@pytest.fixture(autouse=True)
def no_claude_settings(monkeypatch, tmp_path):
    """Keep the real ~/.claude settings and ANTHROPIC_* out of every test."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    for k in ("ANTHROPIC_MODEL", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    from helm import model_catalog
    model_catalog._cache.clear()
    yield home
    model_catalog._cache.clear()


# ── Command and output parsing ──────────────────────────────────────────────

def test_command_only_names_a_model_when_given_one():
    assert "--model" not in build_claude_cmd("hi", has_history=False)
    assert "--model" not in build_claude_cmd("hi", has_history=True)       # the user's own setting applies
    cmd = build_claude_cmd("hi", has_history=True, model="opus")
    assert cmd[cmd.index("--model") + 1] == "opus" and "--continue" in cmd


def test_rejected_model_is_recognised():
    assert model_rejected(parse_claude_json_output(REJECTED))
    assert not model_rejected(parse_claude_json_output(result()))
    other_error = json.dumps({"type": "result", "is_error": True, "api_error_status": 429, "result": "rate limited"})
    assert not model_rejected(parse_claude_json_output(other_error))


def test_answering_model_ignores_the_haiku_helper():
    usage = {"claude-haiku-5-5": {"outputTokens": 17}, "claude-opus-5-5": {"outputTokens": 4}}
    parsed = parse_claude_json_output(result(usage=usage))
    assert model_answered(parsed, "opus") == "claude-opus-5-5"
    assert model_answered(parsed, None) == "claude-opus-5-5"
    assert model_answered(parsed, "haiku") == "claude-haiku-5-5"
    assert model_answered(parse_claude_json_output(REJECTED), "nope") is None


def test_replaced_only_counts_exact_versions():
    assert claude_models.replaced("claude-opus-4-1", "claude-opus-5-5")
    assert not claude_models.replaced("claude-opus-4-5", "claude-opus-4-5-20251101")
    assert not claude_models.replaced("claude-opus-4-5", "claude-opus-4-5")
    assert not claude_models.replaced("opus", "claude-opus-5-5")
    assert not claude_models.replaced("sonnet[1m]", "claude-sonnet-5-5")
    assert not claude_models.replaced(None, "claude-opus-5-5")


# ── Where the list comes from ───────────────────────────────────────────────

def test_parse_initialize_reply():
    models = claude_models.parse_initialize("not json\n" + INIT_REPLY)
    assert [m["value"] for m in models] == ["default", "sonnet", "fable", "opus", "haiku"]
    assert models[3] == {"value": "opus", "resolved": "claude-opus-5-5", "name": "Opus",
                         "description": "Opus 5.5 · Best for everyday, complex tasks", "efforts": LEVELS}
    assert models[4]["efforts"] == []                     # supportsEffort false: no levels offered
    assert claude_models.parse_initialize("") == []


FAKE_INIT = r'''#!{python}
import json, os, sys
args = sys.argv[1:]
open(os.environ["FAKE_LOG"], "a").write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")
if "--no-session-persistence" in args and os.environ.get("OLD_CLI"):
    print("error: unknown option '--no-session-persistence'", file=sys.stderr); sys.exit(1)
req = json.loads(sys.stdin.readline())
assert req["request"]["subtype"] == "initialize"
print(open(os.environ["FAKE_REPLY"]).read())
'''


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
@pytest.mark.parametrize("old_cli", [False, True])
def test_live_models_asks_the_installed_cli(tmp_path, monkeypatch, old_cli):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(FAKE_INIT.replace("{python}", sys.executable))
    exe.chmod(0o755)
    reply = tmp_path / "reply.jsonl"
    reply.write_text(INIT_REPLY)
    log = tmp_path / "log.jsonl"
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.setenv("FAKE_REPLY", str(reply))
    if old_cli:
        monkeypatch.setenv("OLD_CLI", "1")
    monkeypatch.chdir(tmp_path)
    models = claude_models.live_models()
    assert [m["value"] for m in models][:2] == ["default", "sonnet"]
    calls = [json.loads(l) for l in log.read_text().splitlines()]
    assert "--input-format" in calls[0]["args"] and "--no-session-persistence" in calls[0]["args"]
    assert all("rapr-claude-models-" in c["cwd"] for c in calls)   # never in a project folder
    assert len(calls) == (2 if old_cli else 1)


def test_live_models_without_claude(monkeypatch):
    monkeypatch.setattr(claude_models, "_claude_exe", lambda: None)
    assert claude_models.live_models() == []


def test_all_versions_from_the_models_api(monkeypatch):
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            seen["key"], seen["path"] = self.headers.get("x-api-key"), self.path
            body = json.dumps({"data": [{"id": "claude-opus-5-5", "display_name": "Claude Opus 5.5"},
                                        {"id": "claude-opus-4-5-20251101", "display_name": "Claude Opus 4.5"}]})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert claude_models.all_versions() == []                     # no key: nothing asked
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{srv.server_port}")
        got = claude_models.all_versions()
        assert got[1] == {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5"}
        assert seen["key"] == "sk-test-123" and seen["path"].startswith("/v1/models")
    finally:
        srv.shutdown()


def test_configured_model_follows_claude_codes_order(tmp_path, monkeypatch, no_claude_settings):
    proj = tmp_path / "proj"
    (proj / ".claude").mkdir(parents=True)
    assert claude_models.configured_model(str(proj)) is None
    (no_claude_settings / ".claude").mkdir()
    (no_claude_settings / ".claude" / "settings.json").write_text(json.dumps({"model": "opus"}))
    assert claude_models.configured_model(str(proj)) == "opus"
    (proj / ".claude" / "settings.json").write_text(json.dumps({"model": "sonnet"}))
    assert claude_models.configured_model(str(proj)) == "sonnet"
    (proj / ".claude" / "settings.local.json").write_text(json.dumps({"model": "haiku"}))
    assert claude_models.configured_model(str(proj)) == "haiku"
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-5")
    assert claude_models.configured_model(str(proj)) == "claude-opus-4-5"


def test_picker_options_show_versions_and_older_ones(monkeypatch):
    from helm import model_catalog
    monkeypatch.setattr(claude_models, "live_models", lambda: claude_models.parse_initialize(INIT_REPLY))
    monkeypatch.setattr(claude_models, "all_versions", lambda: [
        {"id": "claude-opus-5-5", "name": "Claude Opus 5.5"},                      # same as Opus: not repeated
        {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5"}])
    opts = model_catalog.options("claude")
    assert opts[0]["id"] is None and opts[0]["label"] == "Default" and opts[0]["sub"] == "Sonnet 5.5"
    assert [(o["id"], o.get("sub")) for o in opts[1:5]] == [
        ("sonnet", "Sonnet 5.5"), ("fable", "Fable 5.1"), ("opus", "Opus 5.5"), ("haiku", "Haiku 5.5")]
    assert "Requires usage credits" in opts[2]["title"]
    assert opts[5] == {"id": "claude-opus-4-5-20251101", "label": "Claude Opus 4.5",
                       "sub": "claude-opus-4-5-20251101", "group": "Older versions", "efforts": []}
    assert opts[0]["efforts"] == LEVELS and model_catalog.efforts_for("claude", "opus") == LEVELS
    assert model_catalog.efforts_for("claude", "haiku") == []
    assert model_catalog.efforts_for("claude", "my-custom-model") == []
    assert len(opts) == 6
    from helm.web_routes import helpers
    assert helpers._fetch_claude_models() == ["sonnet", "fable", "opus", "haiku", "claude-opus-4-5-20251101"]


def test_picker_falls_back_to_help_names(monkeypatch):
    from helm import model_catalog
    from helm.web_routes import helpers
    monkeypatch.setattr(claude_models, "live_models", lambda: [])
    monkeypatch.setattr(claude_models, "all_versions", lambda: [])
    monkeypatch.setattr(claude_models, "help_effort_levels", lambda: ["low", "high"])
    monkeypatch.setattr(helpers, "_claude_cli_aliases", lambda: ["fable", "opus", "sonnet"])
    assert model_catalog.model_ids("claude") == ["fable", "opus", "sonnet", "haiku"]
    assert model_catalog.efforts_for("claude", None) == ["low", "high"]


HELP_TEXT = """  --effort <level>                      Effort level for the current session
                                        (low, medium, high, xhigh, max)
  --environment <environment_id>        Create a new cloud session"""


def test_help_effort_levels(monkeypatch):
    import subprocess as sp
    monkeypatch.setattr(claude_models, "_claude_exe", lambda: "claude")
    monkeypatch.setattr(sp, "run", lambda *a, **k: sp.CompletedProcess(a, 0, HELP_TEXT, ""))
    assert claude_models.help_effort_levels() == LEVELS


# ── API: one chat's model, not every chat's ─────────────────────────────────

@pytest.fixture
def api(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import helm.state as st
    import helm.model_prefs as prefs
    from helm.web_routes import app as webapp
    monkeypatch.setattr(prefs, "_prefs_path", lambda: tmp_path / "selected_models.json")
    monkeypatch.setattr(prefs, "_OLD_PREFS_PATH", tmp_path / "old.json")
    monkeypatch.setattr(claude_models, "live_models", lambda: claude_models.parse_initialize(INIT_REPLY))
    monkeypatch.setattr(claude_models, "all_versions", lambda: [])
    sent = []

    async def no_push(*a, **k):
        sent.append(a)
    import helm.broadcast as bc
    monkeypatch.setattr(bc, "push_state", no_push)
    monkeypatch.setattr(bc, "push_message", no_push)
    saved = dict(st.sessions)
    st.sessions.clear()
    st.sessions.update({
        "a": {"id": "a", "ai": "claude", "model": None},
        "b": {"id": "b", "ai": "claude", "model": "opus"},
        "o": {"id": "o", "ai": "ollama", "model": None},
    })
    yield TestClient(webapp), st, prefs, sent
    st.sessions.clear()
    st.sessions.update(saved)


def test_switching_one_chat_leaves_the_others(api):
    client, st, prefs, sent = api
    r = client.put("/api/sessions/a/model", json={"model": "sonnet"})
    assert r.status_code == 200 and r.json()["model"] == "sonnet"
    assert st.sessions["a"]["model"] == "sonnet" and st.sessions["b"]["model"] == "opus"
    assert prefs.get_model_pref("claude") == "sonnet"            # new Claude chats start with it
    assert any("Sonnet 5.5" in str(a) for a in sent)             # the chat is told, with the version
    d = client.get("/api/models/claude?session=a").json()
    assert d["selected"] == "sonnet" and d["options"][0]["id"] is None and d["options"][3]["sub"] == "Opus 5.5"
    assert client.get("/api/models/claude?session=b").json()["selected"] == "opus"
    assert client.put("/api/sessions/a/model", json={"model": "claude-opus-4-5"}).json()["model"] == "claude-opus-4-5"
    assert client.put("/api/sessions/a/model", json={"model": None}).json()["model"] is None
    assert st.sessions["a"]["model"] is None and prefs.get_model_pref("claude") is None


def test_new_chat_default_doesnt_touch_open_chats(api):
    client, st, prefs, _ = api
    assert client.put("/api/models/claude", json={"model": "haiku"}).json()["ok"]
    assert st.sessions["b"]["model"] == "opus" and st.sessions["a"]["model"] is None
    assert client.get("/api/models/claude").json()["selected"] == "haiku"


def test_effort_per_chat(api):
    client, st, prefs, sent = api
    r = client.put("/api/sessions/a/effort", json={"effort": "xhigh"})
    assert r.status_code == 200 and st.sessions["a"]["effort"] == "xhigh"
    assert st.sessions["b"].get("effort") is None and prefs.get_effort_pref("claude") == "xhigh"
    assert client.get("/api/models/claude?session=a").json()["effort"] == "xhigh"
    bad = client.put("/api/sessions/a/effort", json={"effort": "ultra"})
    assert bad.status_code == 400 and "low, medium, high, xhigh, max" in bad.json()["error"]
    assert "effort" not in prefs.get_all_prefs() and "claude:effort" not in prefs.get_all_prefs()
    # Haiku (in this fixture) takes no effort: switching to it resets the level, and says so.
    client.put("/api/sessions/a/model", json={"model": "haiku"})
    assert st.sessions["a"]["effort"] is None and prefs.get_effort_pref("claude") is None
    assert any("effort is back to Default" in str(a) for a in sent)
    assert client.put("/api/sessions/a/effort", json={"effort": "high"}).status_code == 400
    assert client.put("/api/sessions/a/effort", json={"effort": None}).json()["effort"] is None


def test_bad_requests(api):
    client, st, *_ = api
    assert client.put("/api/sessions/zz/model", json={"model": "opus"}).status_code == 404
    assert client.put("/api/sessions/o/model", json={"model": "llama3"}).status_code == 400   # not offered yet
    assert client.put("/api/sessions/a/model", json={"model": "two words"}).status_code == 400
    assert st.sessions["a"]["model"] is None


def test_new_chat_starts_with_the_remembered_model(api, tmp_path):
    client, st, prefs, _ = api
    prefs.set_model_pref("claude", "haiku")
    prefs.set_effort_pref("claude", "max")
    from helm.session_mgr import make_session
    sess = make_session("claude", cwd=str(tmp_path))
    try:
        assert sess["model"] == "haiku" and sess["effort"] == "max"
    finally:
        st.sessions.pop(sess["id"], None)


# ── The real message path, with a stand-in `claude` CLI ─────────────────────

FAKE_CLAUDE = r'''#!{python}
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_CLAUDE_LOG"], "a") as f:
    f.write(json.dumps(args) + "\n")
model = args[args.index("--model") + 1] if "--model" in args else None
stream = "stream-json" in args
if model in os.environ.get("FAKE_CLAUDE_REJECT", "nope").split(","):
    msg = {"type": "assistant", "message": {"model": "<synthetic>", "content": [{"type": "text", "text": "There's an issue with the selected model"}]}}
    res = {"type": "result", "is_error": True, "api_error_status": 404,
           "result": "There's an issue with the selected model (%s). It may not exist or you may not have access to it." % model}
    print(json.dumps(msg) if stream else "", flush=True)
    print(json.dumps(res))
    sys.exit(1)
name = {"opus": "claude-opus-5-5", "haiku": "claude-haiku-5-5",
        "claude-opus-4-5": "claude-opus-4-5-20251101",
        "claude-opus-4-1": "claude-opus-5-5"}.get(model, "claude-sonnet-5-5")   # 4-1 is retired: swapped
if stream:
    print(json.dumps({"type": "system", "subtype": "init", "model": name}))
    print(json.dumps({"type": "assistant", "message": {"model": name, "content": [{"type": "text", "text": "OK"}]}}))
print(json.dumps({"type": "result", "is_error": False, "result": "OK from " + name,
                  "modelUsage": {name: {"outputTokens": 1}, "claude-haiku-5-5": {"outputTokens": 9}},
                  "usage": {"input_tokens": 1, "output_tokens": 1}}))
'''


@pytest.fixture
def run_claude(tmp_path, monkeypatch):
    """Send messages through RAPR's real Claude path, with a stand-in `claude` on PATH.
    Returns say(text) -> output, plus the recorded CLI calls and system messages."""
    import helm.ai_runner.core as core
    import helm.model_prefs as prefs
    from helm.ai_runner import streaming
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(FAKE_CLAUDE.replace("{python}", sys.executable))
    exe.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    # The model list comes from the recorded live reply, so only messages reach the fake CLI.
    monkeypatch.setattr(claude_models, "live_models", lambda: claude_models.parse_initialize(INIT_REPLY))
    monkeypatch.setattr(claude_models, "all_versions", lambda: [])
    streaming._stream_disabled.clear()
    streaming._stream_failures.clear()
    monkeypatch.setattr(prefs, "_prefs_path", lambda: tmp_path / "selected_models.json")
    msgs = []

    async def record(role, content, **k):
        msgs.append((role, content))

    async def nothing(*a, **k):
        return None
    monkeypatch.setattr(core, "push_message", record)
    monkeypatch.setattr(core, "push_state", nothing)
    monkeypatch.setattr(core, "push_thinking", nothing)
    monkeypatch.setattr(core, "inject_mcp_context", lambda t, **k: t)
    monkeypatch.setattr(core, "auto_create_skill_template", lambda *a, **k: None)
    cwd = tmp_path / "proj"
    cwd.mkdir()

    class Run:
        def __init__(self):
            self.msgs = msgs
            self.cwd = cwd

        def calls(self):
            return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []

        def say(self, sess, text):
            return asyncio.run(core._run_single_ai("claude", sess, text, text, str(cwd), None, "web", sess["id"],
                                                   lambda c: {}, nothing))

        def session(self, model=None, history=()):
            return {"id": "t", "ai": "claude", "model": model, "cwd": str(cwd),
                    "claude_msgs": list(history), "proc": None}
    return Run()


def model_flag(call):
    return call[call.index("--model") + 1] if "--model" in call else None


def effort_flag(call):
    return call[call.index("--effort") + 1] if "--effort" in call else None


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_message_path_sends_effort_only_when_the_model_takes_it(run_claude, monkeypatch):
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "1")
    sess = run_claude.session(model="opus")
    run_claude.say(sess, "hi")
    assert effort_flag(run_claude.calls()[-1]) is None          # Default: nothing sent
    sess["effort"] = "xhigh"
    run_claude.say(sess, "hi")
    assert effort_flag(run_claude.calls()[-1]) == "xhigh"
    sess["model"] = "haiku"                                     # takes no effort (in this fixture)
    run_claude.say(sess, "hi")
    assert effort_flag(run_claude.calls()[-1]) is None
    sess["model"], sess["effort"] = "opus", "ultra"             # a level Claude Code doesn't list
    run_claude.say(sess, "hi")
    assert effort_flag(run_claude.calls()[-1]) is None


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
@pytest.mark.parametrize("live_progress", ["1", "0"])
def test_message_path_switches_mid_chat(run_claude, monkeypatch, live_progress):
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", live_progress)
    sess = run_claude.session(model="opus")
    out = run_claude.say(sess, "first")
    assert "OK from claude-opus-5-5" in out and sess["model_used"] == "claude-opus-5-5"
    first = run_claude.calls()[-1]
    assert model_flag(first) == "opus" and "--continue" not in first

    sess["model"] = "haiku"                                     # switch mid-chat
    out = run_claude.say(sess, "second")
    assert "claude-haiku-5-5" in out and "--continue" in run_claude.calls()[-1]

    sess["model"] = None                                        # back to Default mid-chat
    run_claude.say(sess, "third")
    assert model_flag(run_claude.calls()[-1]) == "default"      # spelled out once, so --continue doesn't keep Haiku
    run_claude.say(sess, "fourth")
    assert model_flag(run_claude.calls()[-1]) is None           # after that, the user's own setting applies again


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_default_means_the_users_configured_model(run_claude, monkeypatch):
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "0")
    monkeypatch.setenv("ANTHROPIC_MODEL", "haiku")
    sess = run_claude.session(history=["earlier"])              # never touched the picker
    run_claude.say(sess, "hi")
    assert model_flag(run_claude.calls()[-1]) is None           # nothing overrides their setting
    sess["model"] = "opus"
    run_claude.say(sess, "hi")
    sess["model"] = None
    run_claude.say(sess, "hi")
    assert model_flag(run_claude.calls()[-1]) == "haiku"        # Default = their setting, not Claude's


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
@pytest.mark.parametrize("live_progress", ["1", "0"])
def test_refused_model_goes_back_to_default(run_claude, monkeypatch, live_progress, tmp_path):
    import helm.model_prefs as prefs
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", live_progress)
    prefs.set_model_pref("claude", "nope")
    sess = run_claude.session(model="nope", history=["earlier"])
    out = run_claude.say(sess, "hi")
    calls = run_claude.calls()
    assert [model_flag(c) for c in calls] == ["nope", "default"]   # refused, then sent once more on Default
    assert sess["model"] is None and prefs.get_model_pref("claude") is None
    assert "OK from claude-sonnet-5-5" in out
    assert any(r == "system" and "can't use the model `nope`" in c for r, c in run_claude.msgs)


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_swapped_version_is_reported_once(run_claude, monkeypatch):
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "1")
    sess = run_claude.session(model="claude-opus-4-1")
    run_claude.say(sess, "hi")
    run_claude.say(sess, "again")
    notes = [c for r, c in run_claude.msgs if r == "system" and "answered with" in c]
    assert len(notes) == 1 and "claude-opus-4-1" in notes[0] and "claude-opus-5-5" in notes[0]
    sess["model"] = "claude-opus-4-5"                           # a real older version: answered by itself
    run_claude.say(sess, "hi")
    assert sess["model_used"] == "claude-opus-4-5-20251101"
    assert len([c for r, c in run_claude.msgs if r == "system" and "answered with" in c]) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_older_claude_without_default_is_retried_quietly(run_claude, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_REJECT", "nope,default")
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "0")
    sess = run_claude.session(history=["earlier"])
    sess["_ran_with_model"] = "opus"                            # just switched back to Default
    out = run_claude.say(sess, "hi")
    assert [model_flag(c) for c in run_claude.calls()] == ["default", None]
    assert "OK from" in out and not any(r == "system" for r, _ in run_claude.msgs)
