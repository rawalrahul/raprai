"""How each kind of AI is run: helm/ai_runner/core.py _run_single_ai.

These pin down today's behaviour before that code is split into one runner per
AI type (docs/code-health-plan.md, steps C1 and C3). They watch RAPR from the
outside (tests/core_harness.py), so moving the code shouldn't break them.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest  # noqa: E402

import helm.state as st  # noqa: E402
from helm.ai_runner.core import _SAFETY_PREAMBLE  # noqa: E402


# ── Claude Code ───────────────────────────────────────────────────────────

def test_claude_gets_the_prompt_and_its_answer_is_shown(rapr):
    rapr.claude_reply("Hi from Claude")
    sess = rapr.session("claude")
    out = rapr.send("PINEAPPLE", sess)
    assert out == "Hi from Claude"
    [call] = rapr.calls("claude")
    argv = call["argv"]
    assert argv[argv.index("--output-format") + 1] == "json"
    assert rapr.prompt(call).endswith(_SAFETY_PREAMBLE + "PINEAPPLE")
    assert "--dangerously-skip-permissions" in argv
    assert "--continue" not in argv                          # first message: a new chat
    assert "--settings" not in argv                           # no web server to ask you
    assert ("assistant", "Hi from Claude") in rapr.messages()


def test_claude_asks_before_acting_while_the_web_server_runs(rapr, monkeypatch):
    monkeypatch.setattr(st, "gate_url", "http://127.0.0.1:9/mcp/gate", raising=False)
    rapr.claude_reply("ok")
    sess = rapr.session("claude")
    rapr.send("hello", sess)
    argv = rapr.calls("claude")[0]["argv"]
    hook = json.loads(argv[argv.index("--settings") + 1])["hooks"]["PreToolUse"][0]
    assert hook["matcher"] == "mcp__.*"
    assert "tool_gate_hook.py" in hook["hooks"][0]["command"]
    assert sess["id"] in hook["hooks"][0]["command"]


def test_claude_continues_the_conversation_and_uses_the_model(rapr):
    rapr.claude_reply("ok")
    sess = rapr.session("claude", model="claude-test-9")
    rapr.send("one", sess)
    rapr.send("two", sess)
    first, second = rapr.calls("claude")
    assert "--continue" not in first["argv"] and "--continue" in second["argv"]
    assert second["argv"][second["argv"].index("--model") + 1] == "claude-test-9"
    assert sess["claude_msgs"] == ["one", "two"]


def test_claude_tokens_and_cost_are_counted(rapr):
    from helm.pipeline.cost import calculate_cost
    rapr.claude_reply("ok", input_tokens=1200, output_tokens=345, cost=0.0123)
    rapr.send("hello", rapr.session("claude"))
    stats = st.usage_stats["claude"]
    assert stats["tokens_in"] == 1200 and stats["tokens_out"] == 345
    assert stats["tokens_source"] == "actual"
    # Today usage stats price the tokens with RAPR's own table; the cost Claude
    # reports only reaches the learning system.
    assert stats["cost_usd"] == pytest.approx(calculate_cost("claude", 1200, 345))


def test_claude_gets_your_name_and_instructions(rapr):
    (rapr.root / "data" / "user_prefs.json").write_text(json.dumps(
        {"user_name": "Asha", "custom_instructions": "Answer in haiku."}))
    rapr.claude_reply("ok")
    rapr.send("hello", rapr.session("claude"))
    prompt = rapr.prompt(rapr.calls("claude")[0])
    assert "The user's name is Asha." in prompt and "Answer in haiku." in prompt
    assert prompt.index("Asha") < prompt.index(_SAFETY_PREAMBLE)


class FakeMCP:
    """One running MCP server (a file-system one) for Claude to use."""

    def __init__(self, tmp):
        self.tmp = tmp
        self.exported = []

    def has_running_servers(self):
        return True

    def _get_subprocess_servers(self):
        return {"fs": {"command": "fs-server"}}

    def export_claude_mcp_config(self, cwd):
        path = self.tmp / f"mcp-{len(self.exported)}.json"
        path.write_text("{}")
        self.exported.append(path)
        return str(path)

    def get_text_tool_descriptions(self):
        return "fs.read_file(path): read a file"


@pytest.fixture
def mcp_server(rapr, monkeypatch):
    import helm.mcp as mcp
    import helm.mcp.manager as manager
    fake = FakeMCP(rapr.root)
    monkeypatch.setattr(mcp, "get_manager", lambda: fake)
    monkeypatch.setattr(manager, "get_manager", lambda: fake)
    return fake


def test_claude_gets_mcp_servers_natively_and_as_text(rapr, mcp_server):
    rapr.claude_reply("Read it.", input_tokens=10, output_tokens=5)
    out = rapr.send("read the readme", rapr.session("claude"))
    assert out == "Read it."
    [call] = rapr.calls("claude")
    argv = call["argv"]
    assert argv[argv.index("--mcp-config") + 1] == str(mcp_server.exported[0])
    assert "fs.read_file(path)" in rapr.prompt(call)
    assert not mcp_server.exported[0].exists()                # temp config cleaned up
    assert st.usage_stats["claude"]["tokens_in"] == 10


def test_a_cli_ai_gets_mcp_tools_as_text(rapr, mcp_server):
    rapr.reply("codex", "ok")
    rapr.send("read the readme", rapr.session("codex"))
    [call] = rapr.calls("codex")
    assert "fs.read_file(path)" in rapr.prompt(call)
    assert "--mcp-config" not in call["argv"]


def test_claude_with_computer_use_runs_through_the_tool_loop(rapr, monkeypatch):
    import helm.builtin_tools as bt
    monkeypatch.setattr(bt, "is_computer_use_enabled", lambda: True)
    rapr.claude_reply("Nothing to click.", input_tokens=7, output_tokens=3)
    out = rapr.send("hello", rapr.session("claude"))
    assert out == "Nothing to click."
    assert rapr.prompt(rapr.calls("claude")[0]).startswith("[MCP TOOLS]")
    assert st.usage_stats["claude"]["tokens_out"] == 3


@pytest.fixture
def live_progress(monkeypatch):
    import helm.ai_runner.streaming as streaming
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "1")
    monkeypatch.setattr(streaming, "_stream_disabled", {})


def test_claudes_live_progress_shows_its_steps(rapr, live_progress):
    step = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}
    result = {"type": "result", "result": "Listed it.", "is_error": False}
    rapr.reply("claude", json.dumps(step) + "\n" + json.dumps(result) + "\n")
    sess = rapr.session("claude")
    out = rapr.send("list the files", sess)
    assert out == "Listed it."
    [call] = rapr.calls("claude")
    assert call["argv"][call["argv"].index("--output-format") + 1] == "stream-json"
    steps = [e for e in rapr.events("activity") if e.get("phase") == "step"]
    assert steps and steps[0]["session_id"] == sess["id"] and steps[0]["n"] == 1


def test_if_claudes_live_progress_fails_it_runs_normally(rapr, live_progress):
    rapr.reply("claude", "not a stream")                    # no result event
    out = rapr.send("hello", rapr.session("claude"))
    assert out == "not a stream"
    first, second = rapr.calls("claude")
    assert first["argv"][first["argv"].index("--output-format") + 1] == "stream-json"
    assert second["argv"][second["argv"].index("--output-format") + 1] == "json"


# ── Other command-line AIs (Codex, Gemini, …) ─────────────────────────────

def test_a_cli_ai_remembers_the_last_three_exchanges(rapr):
    sess = rapr.session("codex")
    for i in range(5):
        rapr.reply("codex", f"answer {i}")
        rapr.send(f"question {i}", sess)
    last = rapr.prompt(rapr.calls("codex")[-1])
    assert last.startswith("[Prior conversation in this session]\n")
    assert "User: question 1\nAssistant: answer 1" in last
    assert "User: question 3\nAssistant: answer 3" in last
    assert "question 0" not in last                           # only the last three
    assert "[Current request]\n" in last and last.endswith("question 4")
    assert len(sess["_integration_history"]) == 5


def test_cli_history_keeps_ten_exchanges(rapr):
    sess = rapr.session("codex")
    for i in range(12):
        rapr.send(f"q{i}", sess)
    assert [h["q"] for h in sess["_integration_history"]] == [f"q{i}" for i in range(2, 12)]


def test_a_failing_cli_ai_isnt_shown_as_an_answer(rapr):
    rapr.reply("codex", "", exit=1)
    sess = rapr.session("codex")
    out = rapr.send("hello", sess)
    assert out == "(codex exited 1)"
    assert not any(role == "assistant" for role, _ in rapr.messages())
    assert any("failed after 1 attempts" in c for _, c in rapr.messages("system"))
    assert "_integration_history" not in sess


def test_an_error_exit_with_text_is_shown_as_the_reply(rapr):
    """Today a non-zero exit only counts as a failure without output, or when
    the text looks like a CLI problem (not found, auth, network…)."""
    rapr.reply("codex", "I couldn't finish: the tests fail.", exit=1)
    out = rapr.send("hello", rapr.session("codex"))
    assert out == "I couldn't finish: the tests fail."
    assert ("assistant", out) in rapr.messages()


def test_gemini_explains_googles_cutoff(rapr):
    rapr.reply("gemini", "Error: IneligibleTier for this account")
    out = rapr.send("hello", rapr.session("gemini"))
    assert "Google no longer serves the Gemini CLI for personal Google accounts" in out


def test_with_computer_use_on_the_ai_is_told_about_its_tools(rapr, monkeypatch):
    import helm.builtin_tools as bt
    monkeypatch.setattr(bt, "is_computer_use_enabled", lambda: True)
    rapr.reply("codex", "No tools needed.")
    out = rapr.send("hello", rapr.session("codex"))
    assert out == "No tools needed."
    prompt = rapr.prompt(rapr.calls("codex")[0])
    assert prompt.startswith("[MCP TOOLS]")
    assert len(rapr.calls("codex")) == 1                      # no tool call, so one turn


# ── Ollama, the shell and native computer use ─────────────────────────────

def test_ollama_answers_through_its_agent(rapr, monkeypatch):
    import helm.ai_runner.ollama as ollama
    seen = {}

    async def agent(sess, text, source, sid):
        seen["text"] = text
        return "Hi from Ollama"
    monkeypatch.setattr(ollama, "_run_ollama_agent", agent)
    out = rapr.send("PINEAPPLE", rapr.session("ollama"))
    assert out == "Hi from Ollama"
    assert seen["text"].endswith(_SAFETY_PREAMBLE + "PINEAPPLE")
    assert ("assistant", "Hi from Ollama") in rapr.messages()


def test_a_failed_ollama_turn_starts_the_next_one_fresh(rapr, monkeypatch):
    import helm.ai_runner.ollama as ollama

    async def agent(sess, text, source, sid):
        sess["ollama_messages"] = [{"role": "user", "content": text}]
        return "(error: connection refused)"
    monkeypatch.setattr(ollama, "_run_ollama_agent", agent)
    sess = rapr.session("ollama")
    out = rapr.send("hello", sess)
    assert out == "(error: connection refused)"
    assert "ollama_messages" not in sess


@pytest.fixture
def quick_shell(monkeypatch):
    """The shell's output is done after 0.5s of quiet (30s by default)."""
    from helm.terminal import TerminalSession
    monkeypatch.setattr(TerminalSession.drain, "__defaults__", (0.5, 20.0, 20.0))


def test_the_shell_runs_the_command(rapr, quick_shell):
    sess = rapr.session("shell")
    try:
        out = rapr.send("echo PINEAPPLE-$((40+2))", sess)
    finally:
        sess["terminal"].stop()
    assert "PINEAPPLE-42" in out
    assert ("assistant", out) in rapr.messages()
    assert rapr.calls() == []


def test_a_stopped_shell_says_so(rapr, quick_shell):
    sess = rapr.session("shell")
    sess["terminal"].stop()
    out = rapr.send("echo hi", sess)
    assert out == "Terminal stopped. Stop and restart this session."
    assert ("system", out) in rapr.messages()


def test_native_computer_use_skips_the_cli(rapr, monkeypatch):
    import helm.computer_runners as cr
    import helm.computer_runners.base as base
    import helm.computer_runners.claude_native as native
    monkeypatch.setattr(cr, "should_use_tier2", lambda ai: ai == "claude")
    monkeypatch.setattr(base, "primary_display_size", lambda: (1280, 800))

    async def run(text, cwd, sid, w, h, model=None):
        return f"clicked around on a {w}x{h} screen"
    monkeypatch.setattr(native, "run", run)
    out = rapr.send("open the calculator", rapr.session("claude"))
    assert out == "clicked around on a 1280x800 screen"
    assert rapr.calls("claude") == []


def test_if_native_computer_use_breaks_the_cli_takes_over(rapr, monkeypatch):
    import helm.computer_runners as cr

    def broken(ai):
        raise RuntimeError("no display")
    monkeypatch.setattr(cr, "should_use_tier2", broken)
    rapr.claude_reply("CLI answer")
    assert rapr.send("hello", rapr.session("claude")) == "CLI answer"
