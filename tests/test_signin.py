"""Not offering an AI whose command-line tool says it isn't signed in."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.mcp_server as mcp
import helm.signin as signin

AUTH_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK",
            "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY", "OPENAI_API_KEY", "CODEX_API_KEY")


@pytest.fixture
def clean(monkeypatch, tmp_path):
    for name in AUTH_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    monkeypatch.setattr(signin, "_cache", {})
    monkeypatch.setattr(signin, "_exe", lambda name: f"/bin/{name}")
    calls = []

    def answer(replies):
        def run(exe, *args):
            calls.append((exe, *args))
            reply = replies[os.path.basename(exe)]
            if isinstance(reply, Exception):
                raise reply
            return reply
        monkeypatch.setattr(signin, "_run", run)
    return answer, calls


def test_claude_reads_loggedin_from_auth_status(clean):
    answer, _ = clean
    answer({"claude": (1, 'warning: something\n{"loggedIn": false, "authMethod": "none"}\n')})
    assert signin.claude() is False
    answer({"claude": (0, json.dumps({"loggedIn": True, "email": "a@b.c"}))})
    assert signin.claude() is True


def test_claude_unclear_answers_keep_it_listed(clean):
    answer, _ = clean
    answer({"claude": (1, "error: unknown command 'auth'")})        # an older Claude Code
    assert signin.claude() is None and signin.signed_in("claude")
    signin._cache.clear()
    answer({"claude": TimeoutError()})
    assert signin.signed_in("claude")


def test_claude_api_key_needs_no_sign_in(clean, monkeypatch):
    _, calls = clean
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert signin.claude() is True and not calls


def test_codex_sign_in_from_its_file_key_or_status(clean, monkeypatch, tmp_path):
    answer, calls = clean
    answer({"codex": (1, "Not logged in\n")})
    assert signin.codex() is False
    answer({"codex": (0, "Logged in using ChatGPT\n")})
    assert signin.codex() is True
    calls.clear()
    (tmp_path / "codex").mkdir()
    (tmp_path / "codex" / "auth.json").write_text(json.dumps({"tokens": {"id_token": "x"}}))
    assert signin.codex() is True and not calls                     # the file is enough
    (tmp_path / "codex" / "auth.json").unlink()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert signin.codex() is True and not calls


def test_answers_are_cached(clean):
    answer, calls = clean
    answer({"codex": (1, "Not logged in")})
    assert signin.status("codex") is False and signin.status("codex") is False
    assert len(calls) == 1
    assert signin.status("copilot") is None                         # no check: never hidden


def test_list_agents_skips_and_explains_signed_out_tools(monkeypatch):
    import helm.state as st
    mcp._load()
    monkeypatch.setattr(mcp, "_agents_cache", (0.0, {}))
    monkeypatch.setattr(mcp, "_found", lambda exe: exe in ("claude", "codex"))
    monkeypatch.setattr(signin, "_cache", {"claude": (True, 1e18), "codex": (False, 1e18)})
    monkeypatch.setattr(signin.time, "monotonic", lambda: 1e18)
    assert "codex" in st.integrations
    have = mcp.agents()
    assert "claude" in have and "codex" not in have
    text = mcp.Server(out=None).call_tool("list_agents", {})["content"][0]["text"]
    assert "- claude (Claude Code)" in text
    assert "codex is installed but not signed in: run `codex login`" in text


def test_grok_from_its_login_file_or_key(clean, monkeypatch, tmp_path):
    monkeypatch.setattr(signin.Path, "home", lambda: tmp_path)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    assert signin.grok() is False
    (tmp_path / ".grok").mkdir()
    (tmp_path / ".grok" / "auth.json").write_text('{"token": "x"}')
    assert signin.grok() is True
    (tmp_path / ".grok" / "auth.json").write_text("{}")            # after `grok logout`
    assert signin.grok() is False
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    assert signin.grok() is True
    monkeypatch.setattr(signin, "_exe", lambda name: None)         # not installed: nothing to say
    assert signin.grok() is None


def test_kiro_from_whoami(clean):
    answer, calls = clean
    answer({"kiro-cli": (1, "Not logged in\n")})
    assert signin.kiro() is False
    answer({"kiro-cli": (0, '{"accountType": "BuilderId", "email": "a@b.c"}')})
    assert signin.kiro() is True
    answer({"kiro-cli": (2, "error: unexpected")})
    assert signin.kiro() is None
    assert calls[0][1:] == ("whoami",)


def test_tools_without_a_check_are_never_hidden(clean):
    for name in ("copilot", "antigravity", "gemini", "opencode", "kilocode", "qwen_code", "droid"):
        assert signin.status(name) is None and signin.signed_in(name)
