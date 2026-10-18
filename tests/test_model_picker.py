"""Model picker for Claude: per-chat choice, mid-chat switching, what answered, and rejected models.

The behaviour these tests pin down was checked against the real Claude Code CLI:
  * --continue with no --model keeps the conversation's last model; --model default resets it
  * stream-json names the answering model on each assistant message
  * modelUsage also lists a Haiku helper, often with more tokens than the answer
  * an unknown model: exit 1, is_error, api_error_status 404, "There's an issue with the selected model"
"""
import asyncio
import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm.ai_runner.claude import build_claude_cmd, model_answered, model_rejected, parse_claude_json_output

REJECTED = json.dumps({
    "type": "result", "subtype": "success", "is_error": True, "api_error_status": 404,
    "result": "There's an issue with the selected model (nope). It may not exist or you may not have access to it.",
    "modelUsage": {}, "usage": {"input_tokens": 0, "output_tokens": 0},
})


def result(text="OK", usage=None):
    return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text,
                       "modelUsage": usage or {}, "usage": {"input_tokens": 3, "output_tokens": 1}})


# ── Command and output parsing ──────────────────────────────────────────────

def test_default_mid_chat_passes_claudes_own_default():
    assert "--model" not in build_claude_cmd("hi", has_history=False)
    cmd = build_claude_cmd("hi", has_history=True)
    assert cmd[cmd.index("--model") + 1] == "default" and "--continue" in cmd
    cmd = build_claude_cmd("hi", has_history=True, model="opus")
    assert cmd[cmd.index("--model") + 1] == "opus" and cmd.count("--model") == 1


def test_rejected_model_is_recognised():
    assert model_rejected(parse_claude_json_output(REJECTED))
    assert not model_rejected(parse_claude_json_output(result()))
    other_error = json.dumps({"type": "result", "is_error": True, "api_error_status": 429, "result": "rate limited"})
    assert not model_rejected(parse_claude_json_output(other_error))


def test_answering_model_ignores_the_haiku_helper():
    usage = {"claude-haiku-5-5": {"outputTokens": 17}, "claude-opus-5-5": {"outputTokens": 4}}
    parsed = parse_claude_json_output(result(usage=usage))
    assert model_answered(parsed, "opus") == "claude-opus-5-5"
    assert model_answered(parsed, None) == "claude-opus-5-5"        # the one that isn't the helper
    assert model_answered(parsed, "haiku") == "claude-haiku-5-5"
    assert model_answered(parse_claude_json_output(result(usage={"claude-sonnet-5-5": {}})), None) == "claude-sonnet-5-5"
    assert model_answered(parse_claude_json_output(REJECTED), "nope") is None


def test_claude_list_always_offers_haiku(monkeypatch):
    from helm.web_routes import helpers
    monkeypatch.setattr(helpers, "_claude_cli_aliases", lambda: ["fable", "opus", "sonnet"])
    monkeypatch.setattr(helpers, "_fetch_claude_model_ids", lambda: ["claude-opus-5-5", "opus"])
    assert helpers._fetch_claude_models() == ["fable", "opus", "sonnet", "haiku", "claude-opus-5-5"]
    monkeypatch.setattr(helpers, "_claude_cli_aliases", lambda: [])
    assert helpers._fetch_claude_models()[:3] == ["opus", "sonnet", "haiku"]


def test_catalog_options(monkeypatch):
    from helm import model_catalog
    monkeypatch.setattr(model_catalog, "_fetch", lambda ai: ["opus", "haiku", "claude-opus-5-5"])
    model_catalog._cache.clear()
    assert model_catalog.options("claude") == [
        {"id": None, "label": "Default"}, {"id": "opus", "label": "Opus"},
        {"id": "haiku", "label": "Haiku"}, {"id": "claude-opus-5-5", "label": "claude-opus-5-5"}]
    assert model_catalog.label("claude", None) == "Default"


# ── API: one chat's model, not every chat's ─────────────────────────────────

@pytest.fixture
def api(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import helm.state as st
    import helm.model_prefs as prefs
    from helm import model_catalog
    from helm.web_routes import app as webapp
    monkeypatch.setattr(prefs, "_prefs_path", lambda: tmp_path / "selected_models.json")
    monkeypatch.setattr(prefs, "_OLD_PREFS_PATH", tmp_path / "old.json")
    monkeypatch.setattr(model_catalog, "_fetch", lambda ai: ["opus", "sonnet", "haiku"])
    model_catalog._cache.clear()
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
    assert any("Sonnet" in str(a) for a in sent)                 # the chat is told
    d = client.get("/api/models/claude?session=a").json()
    assert d["selected"] == "sonnet" and d["options"][0] == {"id": None, "label": "Default"}
    assert client.get("/api/models/claude?session=b").json()["selected"] == "opus"
    assert client.put("/api/sessions/a/model", json={"model": None}).json()["model"] is None
    assert st.sessions["a"]["model"] is None and prefs.get_model_pref("claude") is None


def test_new_chat_default_doesnt_touch_open_chats(api):
    client, st, prefs, _ = api
    assert client.put("/api/models/claude", json={"model": "haiku"}).json()["ok"]
    assert st.sessions["b"]["model"] == "opus" and st.sessions["a"]["model"] is None
    assert client.get("/api/models/claude").json()["selected"] == "haiku"


def test_bad_requests(api):
    client, st, *_ = api
    assert client.put("/api/sessions/zz/model", json={"model": "opus"}).status_code == 404
    assert client.put("/api/sessions/o/model", json={"model": "llama3"}).status_code == 400   # not offered yet
    assert client.put("/api/sessions/a/model", json={"model": "two words"}).status_code == 400
    assert st.sessions["a"]["model"] is None


def test_new_chat_starts_with_the_remembered_model(api, tmp_path):
    client, st, prefs, _ = api
    prefs.set_model_pref("claude", "haiku")
    from helm.session_mgr import make_session
    sess = make_session("claude", cwd=str(tmp_path))
    try:
        assert sess["model"] == "haiku"
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
if model in ("nope", "default") and os.environ.get("FAKE_CLAUDE_REJECT", "nope").split(",").count(model):
    msg = {"type": "assistant", "message": {"model": "<synthetic>", "content": [{"type": "text", "text": "There's an issue with the selected model"}]}}
    res = {"type": "result", "is_error": True, "api_error_status": 404,
           "result": "There's an issue with the selected model (%s). It may not exist or you may not have access to it." % model}
    print(json.dumps(msg) if stream else "", flush=True)
    print(json.dumps(res))
    sys.exit(1)
name = {"opus": "claude-opus-5-5", "haiku": "claude-haiku-5-5"}.get(model, "claude-sonnet-5-5")
if stream:
    print(json.dumps({"type": "system", "subtype": "init", "model": name}))
    print(json.dumps({"type": "assistant", "message": {"model": name, "content": [{"type": "text", "text": "OK"}]}}))
print(json.dumps({"type": "result", "is_error": False, "result": "OK from " + name,
                  "modelUsage": {name: {"outputTokens": 1}, "claude-haiku-5-5": {"outputTokens": 9}},
                  "usage": {"input_tokens": 1, "output_tokens": 1}}))
'''


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(FAKE_CLAUDE.replace("{python}", sys.executable))
    exe.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    return lambda: [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
@pytest.mark.parametrize("live_progress", ["1", "0"])
def test_message_path_switch_and_rejection(fake_claude, tmp_path, monkeypatch, live_progress):
    import helm.ai_runner.core as core
    import helm.model_prefs as prefs
    from helm.ai_runner import streaming
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", live_progress)
    streaming._stream_disabled.clear()
    streaming._stream_failures.clear()
    monkeypatch.setattr(prefs, "_prefs_path", lambda: tmp_path / "selected_models.json")
    msgs = []

    async def record(role, content, **k):
        msgs.append((role, content))

    async def nothing(*a, **k):
        return None
    for name in ("push_message", "push_state", "push_thinking"):
        monkeypatch.setattr(core, name, record if name == "push_message" else nothing)
    monkeypatch.setattr(core, "inject_mcp_context", lambda t, **k: t)
    monkeypatch.setattr(core, "auto_create_skill_template", lambda *a, **k: None)

    async def diff(*a, **k):
        return None
    cwd = tmp_path / "proj"
    cwd.mkdir()
    sess = {"id": "t1", "ai": "claude", "model": "opus", "cwd": str(cwd), "claude_msgs": [], "proc": None}

    def say(text):
        return asyncio.run(core._run_single_ai("claude", sess, text, text, str(cwd), None, "web", "t1",
                                               lambda c: {}, diff))

    out = say("first")
    calls = fake_claude()
    assert "OK from claude-opus-5-5" in out and sess["model_used"] == "claude-opus-5-5"
    assert calls[-1][calls[-1].index("--model") + 1] == "opus" and "--continue" not in calls[-1]

    sess["model"] = "haiku"                                     # switch mid-chat
    out = say("second")
    assert "claude-haiku-5-5" in out and sess["model_used"] == "claude-haiku-5-5"
    assert "--continue" in fake_claude()[-1]

    sess["model"] = None                                        # back to Default mid-chat
    say("third")
    last = fake_claude()[-1]
    assert last[last.index("--model") + 1] == "default" and sess["model_used"] == "claude-sonnet-5-5"

    prefs.set_model_pref("claude", "nope")
    sess["model"] = "nope"                                      # a model Claude refuses
    n = len(fake_claude())
    out = say("fourth")
    calls = fake_claude()[n:]
    assert len(calls) == 2                                      # refused, then sent once more
    assert calls[0][calls[0].index("--model") + 1] == "nope"
    assert calls[1][calls[1].index("--model") + 1] == "default"
    assert sess["model"] is None and prefs.get_model_pref("claude") is None
    assert "OK from claude-sonnet-5-5" in out
    assert any(r == "system" and "can't use the model `nope`" in c for r, c in msgs)


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_older_claude_without_default_is_retried_quietly(fake_claude, tmp_path, monkeypatch):
    import helm.ai_runner.core as core
    monkeypatch.setenv("FAKE_CLAUDE_REJECT", "nope,default")
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "0")
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
    async def diff(*a, **k):
        return None
    cwd = tmp_path / "proj"
    cwd.mkdir()
    sess = {"id": "t2", "ai": "claude", "model": None, "cwd": str(cwd), "claude_msgs": ["earlier"], "proc": None}
    out = asyncio.run(core._run_single_ai("claude", sess, "hi", "hi", str(cwd), None, "web", "t2",
                                          lambda c: {}, diff))
    calls = fake_claude()
    assert "--model" not in calls[-1] and "OK from" in out
    assert not any(r == "system" for r, _ in msgs)              # nothing misleading shown
