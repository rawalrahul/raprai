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
        assert bucket["agents"]["codex"] == {"name": "Codex", "calls": 2, "failed": 1, "seconds": 42.5, "tokens": 200}
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
