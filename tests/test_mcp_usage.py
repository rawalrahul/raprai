"""The usage ribbon's numbers: what `rapr mcp` records for each AI run (helm/mcp_usage.py)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.mcp_server as mcp
from helm import mcp_usage


def test_runs_add_up_today_and_in_total():
    mcp_usage.record("codex", 30, prompt="x" * 400, reply="y" * 400, name="Codex")
    mcp_usage.record("codex", 12.5, prompt="p", reply="", ok=False, name="Codex")
    mcp_usage.record("claude", 60, prompt="q" * 40, reply="r" * 40, name="Claude Code")
    data = json.loads(Path(os.environ["RAPR_MCP_USAGE_FILE"]).read_text())
    for bucket in (data["today"], data["total"]):
        assert bucket["calls"] == 3 and bucket["failed"] == 1 and bucket["seconds"] == 102.5
        assert bucket["tokens"] == 200 + 0 + 20
        assert bucket["agents"]["codex"] == {"name": "Codex", "calls": 2, "failed": 1, "seconds": 42.5,
                                             "tokens": 200, "estimated": 200, "cost_usd": 0.0}
    assert data["last"]["agent"] == "claude" and data["last"]["ok"] is True


def test_today_starts_over_on_a_new_day():
    mcp_usage.record("codex", 30, name="Codex")
    path = Path(os.environ["RAPR_MCP_USAGE_FILE"])
    data = json.loads(path.read_text())
    data["day"] = "2000-01-01"
    path.write_text(json.dumps(data))
    mcp_usage.record("codex", 5, name="Codex")
    data = mcp_usage.load()
    assert data["today"]["calls"] == 1 and data["total"]["calls"] == 2


def test_a_broken_file_is_started_again():
    Path(os.environ["RAPR_MCP_USAGE_FILE"]).write_text("{not json")
    mcp_usage.record("codex", 1, name="Codex")
    assert mcp_usage.load()["total"]["calls"] == 1


def test_the_usage_tool_reads_like_the_ribbon():
    s = mcp.Server(out=None)
    text = s.call_tool("usage", {})["content"][0]["text"]
    assert "no AI has been run" in text
    mcp_usage.record("codex", 125, prompt="x" * 4000, reply="", name="Codex")
    text = s.call_tool("usage", {})["content"][0]["text"]
    assert "today: 1 call, 2m 05s of AI time, ~1.0k tokens" in text
    assert "- Codex: 1 call" in text and "Last: Codex took 2m 05s" in text


def test_run_agent_counts_each_run(monkeypatch, tmp_path):
    import helm.council.runner as runner
    monkeypatch.setattr(runner, "_build_cmd_for_session", lambda sess, prompt: (["fake"], None, None))
    replies = iter(["all good", "(error: not signed in)"])
    monkeypatch.setattr(runner, "_run_subprocess_blocking", lambda *a, **k: next(replies))
    assert mcp.run_agent("codex", "hello", str(tmp_path)) == "all good"
    try:
        mcp.run_agent("codex", "hello", str(tmp_path))
    except mcp.ToolError:
        pass
    today = mcp_usage.load()["today"]
    assert today["calls"] == 2 and today["failed"] == 1


# --- Plan limits, as each AI reports them -------------------------------------------------

CLAUDE_STREAM = "\n".join([
    '{"type":"system","subtype":"init"}',
    json.dumps({"type": "rate_limit_event", "rate_limit_info": {
        "status": "allowed_warning", "rateLimitType": "seven_day", "utilization": 0.88, "resetsAt": 1793606400,
        "unifiedWindows": {"five_hour": {"utilization": 0.61, "resetsAt": 1793528400},
                           "seven_day": {"utilization": 0.88, "resetsAt": 1793606400}}}}),
    json.dumps({"type": "result", "subtype": "success", "result": "hi there", "total_cost_usd": 0.092,
                "usage": {"input_tokens": 2, "output_tokens": 18, "cache_creation_input_tokens": 11123,
                          "cache_read_input_tokens": 13462}}),
])


def test_claude_stream_gives_the_plan_windows_exact_tokens_and_cost(monkeypatch):
    monkeypatch.setattr(mcp_usage.time, "time", lambda: 1793500000)
    result, tokens, cost = mcp_usage.claude_stream_result(CLAUDE_STREAM)
    assert json.loads(result)["result"] == "hi there" and tokens == 24605 and cost == 0.092
    wins = mcp_usage.limits()["claude"]["windows"]
    assert [(w["label"], w["pct"]) for w in wins] == [("5h", 61.0), ("week", 88.0)]


def test_a_window_past_its_reset_reads_zero():
    mcp_usage.set_limits("claude", "Claude", [{"key": "five_hour", "label": "5h", "pct": 70.0, "resets_at": 1}], "test")
    assert mcp_usage.limits()["claude"]["windows"][0]["pct"] == 0.0


def _rollout(home, minutes=300, rate=True):
    d = home / "sessions" / "2026" / "11" / "01"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "rollout-2026-11-01T10-00-00-abc.jsonl"
    lines = ['{"type":"session_meta","payload":{}}']
    payload = {"type": "token_count", "info": {"total_token_usage": {"total_tokens": 5321}}}
    if rate:
        payload["rate_limits"] = {
            "primary": {"used_percent": 12.0, "window_minutes": minutes, "resets_at": 4102444800},
            "secondary": {"used_percent": 40.5, "window_minutes": 10080, "resets_in_seconds": 3600}}
    lines.append(json.dumps({"type": "event_msg", "payload": payload}))
    f.write_text("\n".join(lines) + "\n")
    return f


def test_a_codex_runs_tokens_come_from_its_session_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    _rollout(tmp_path / "codex")
    assert mcp_usage.codex_run_tokens(0) == 5321
    assert "codex" not in mcp_usage.limits()      # windows come from Codex itself (app-server), live


def test_run_agent_runs_claude_in_stream_mode_and_keeps_its_numbers(monkeypatch, tmp_path):
    import helm.council.runner as runner
    seen = {}
    monkeypatch.setattr(runner, "_build_cmd_for_session",
                        lambda sess, prompt: (["claude", "--output-format", "json", "-p", prompt], None, {}))

    def run(cmd, *a, **k):
        seen["cmd"] = cmd
        return CLAUDE_STREAM
    monkeypatch.setattr(runner, "_run_subprocess_blocking", run)
    monkeypatch.setattr(mcp_usage.time, "time", lambda: 1793500000)
    assert mcp.run_agent("claude", "hello", str(tmp_path)) == "hi there"
    assert "stream-json" in seen["cmd"] and "--verbose" in seen["cmd"]
    today = mcp_usage.load()["today"]
    # On a plan (it reported plan windows) Claude's cost is a list price: not counted as spent.
    assert today["tokens"] == 24605 and today["estimated"] == 0 and today["cost_usd"] == 0
    assert mcp_usage.limits()["claude"]["windows"][0]["pct"] == 61.0


def test_the_usage_tool_shows_plan_usage_first(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "none"))
    mcp_usage.set_limits("claude", "Claude", [{"key": "five_hour", "label": "5h", "pct": 61.0,
                                               "resets_at": 4102444800}], "test")
    text = mcp.Server(out=None).call_tool("usage", {})["content"][0]["text"]
    assert text.startswith("Plan usage (subscriptions), as each AI reports it:\n- Claude: 5h 61% (resets in")


def test_the_app_shows_the_plan_share_not_an_estimate(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "none"))
    import asyncio
    from helm.web_routes import usage_routes
    mcp_usage.set_limits("claude", "Claude", [
        {"key": "five_hour", "label": "5h", "pct": 61.0, "resets_at": 4102444800},
        {"key": "seven_day", "label": "week", "pct": 88.0, "resets_at": 4102444800}], "test")
    data = json.loads(asyncio.run(usage_routes.get_usage()).body)
    claude = data["ais"]["claude"]
    assert claude["pct_used"] == 88.0 and claude["source"] == "plan" and len(claude["limits"]) == 2


# --- Plan or API key: never mixed ------------------------------------------------------------

def test_claude_says_plan_or_api_key_in_its_init_line(monkeypatch):
    for k in mcp_usage.CLAUDE_API_ENV:
        monkeypatch.delenv(k, raising=False)
    assert mcp_usage.claude_mode({"apiKeySource": "none"}) == mcp_usage.PLAN
    assert mcp_usage.claude_mode({"apiKeySource": "ANTHROPIC_API_KEY"}) == mcp_usage.API
    assert mcp_usage.claude_mode({}) is None
    assert mcp_usage.claude_mode({"apiKeySource": "none"}, {"CLAUDE_CODE_USE_BEDROCK": "1"}) == mcp_usage.API


def test_switching_claude_to_an_api_key_drops_its_plan_windows(monkeypatch):
    for k in mcp_usage.CLAUDE_API_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(mcp_usage.time, "time", lambda: 1793500000)
    mcp_usage.claude_stream_result(CLAUDE_STREAM)
    assert "claude" in mcp_usage.limits()
    api_run = "\n".join([json.dumps({"type": "system", "subtype": "init", "apiKeySource": "ANTHROPIC_API_KEY"}),
                         json.dumps({"type": "result", "result": "ok", "total_cost_usd": 0.5, "usage": {"output_tokens": 10}})])
    mcp_usage.claude_stream_result(api_run)
    assert "claude" not in mcp_usage.limits() and mcp_usage.billing("claude") == mcp_usage.API


def test_money_counts_only_on_an_api_key():
    mcp_usage.set_billing("claude", "Claude", mcp_usage.PLAN, "test")
    mcp_usage.record("claude", 5, tokens=100, cost_usd=0.9, name="Claude Code")      # a list price
    mcp_usage.set_billing("codex", "Codex", mcp_usage.API, "test")
    mcp_usage.record("codex", 5, tokens=100, cost_usd=0.25, name="Codex")
    today = mcp_usage.load()["today"]
    assert today["agents"]["claude"]["cost_usd"] == 0 and today["agents"]["codex"]["cost_usd"] == 0.25
    text = mcp_usage.summary()
    assert "On an API key (billed per token, no 5-hour or weekly limits):\n- Codex: $0.25 today" in text


def test_the_app_shows_no_plan_or_cap_for_an_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "none"))
    monkeypatch.delenv("USAGE_CAP_MIN_CLAUDE", raising=False)
    monkeypatch.delenv("USAGE_CAP_MIN_DEFAULT", raising=False)
    import asyncio
    from helm.web_routes import usage_routes
    mcp_usage.set_limits("claude", "Claude", [{"key": "five_hour", "label": "5h", "pct": 61.0, "resets_at": 4102444800}], "t")
    plan = json.loads(asyncio.run(usage_routes.get_usage()).body)["ais"]["claude"]
    assert plan["billing"] == "plan" and plan["cost_is_spent"] is False and plan["limits"]
    mcp_usage.set_billing("claude", "Claude", mcp_usage.API, "t")
    api = json.loads(asyncio.run(usage_routes.get_usage()).body)["ais"]["claude"]
    assert api["billing"] == "api" and api["limits"] == [] and api["pct_used"] is None and api["cap_min"] is None
