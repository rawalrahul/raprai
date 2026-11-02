"""Copilot through the RAPR Bridge as an agent: the tools RAPR runs for it, the loop, and the
MCP tools handing it real work (helm/vscode_bridge/agent.py)."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.mcp_server as mcp
from helm.vscode_bridge import agent

ROOT = Path(__file__).resolve().parent.parent



@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    (p / "app.py").write_text("def add(a, b):\n    return a - b\n")
    (p / "pkg").mkdir()
    (p / "pkg" / "util.py").write_text("X = 1\n")
    return p


def scripted(*steps):
    """A stand-in for Copilot: each step is (text, [tool calls]); records what it was sent."""
    sent = []

    def chat(messages, tools, model=None):
        sent.append({"messages": [dict(m) for m in messages], "tools": [t["name"] for t in tools]})
        text, calls = steps[min(len(sent), len(steps)) - 1]
        return {"text": text, "toolCalls": [{"callId": f"c{len(sent)}-{i}", "name": n, "input": a}
                                            for i, (n, a) in enumerate(calls)]}
    chat.sent = sent
    return chat


def results(chat, step):
    """The tool results Copilot got back before its step `step` (1-based)."""
    return [r["content"] for r in chat.sent[step - 1]["messages"][-1].get("toolResults", [])]


# --- the tools -------------------------------------------------------------------------------

def test_each_job_gets_only_its_tools():
    names = lambda mode: [t["name"] for t in agent.tools_for(mode)]  # noqa: E731
    assert names(agent.READ) == ["list_files", "read_file", "search_files"]
    assert names(agent.EDIT) == names(agent.READ) + ["write_file", "edit_file"]
    assert names(agent.RUN) == names(agent.EDIT) + ["run_command"]


def test_reading_listing_and_searching(proj):
    assert "app.py" in agent.run_tool("list_files", {}, proj, agent.READ).splitlines()
    assert "pkg/util.py" in agent.run_tool("list_files", {"depth": 2}, proj, agent.READ)
    assert agent.run_tool("read_file", {"path": "app.py", "start_line": 2, "end_line": 2}, proj, agent.READ) == "2:     return a - b"
    assert agent.run_tool("search_files", {"pattern": r"return a\s*-"}, proj, agent.READ) == "app.py:2:     return a - b"


def test_editing_needs_the_exact_text_once(proj):
    assert agent.run_tool("edit_file", {"path": "app.py", "old_text": "a - b", "new_text": "a + b"}, proj, agent.EDIT) == "edited app.py"
    assert "a + b" in (proj / "app.py").read_text()
    assert "appears 0 times" in agent.run_tool("edit_file", {"path": "app.py", "old_text": "nope", "new_text": "x"}, proj, agent.EDIT)
    agent.run_tool("write_file", {"path": "new/dir/f.txt", "content": "hi"}, proj, agent.EDIT)
    assert (proj / "new" / "dir" / "f.txt").read_text() == "hi"


def test_a_job_cant_use_tools_beyond_it(proj):
    assert "isn't allowed" in agent.run_tool("write_file", {"path": "x", "content": "y"}, proj, agent.READ)
    assert "isn't allowed" in agent.run_tool("run_command", {"command": "echo hi"}, proj, agent.EDIT)
    assert not (proj / "x").exists()


def test_paths_stay_inside_the_project(proj, tmp_path):
    (tmp_path / "secret.txt").write_text("s")
    for args in ({"path": "../secret.txt"}, {"path": str(tmp_path / "secret.txt")}, {"path": "pkg/../../secret.txt"}):
        assert "outside the project" in agent.run_tool("read_file", args, proj, agent.RUN), args
    assert "outside the project" in agent.run_tool("write_file", {"path": "../evil.txt", "content": "x"}, proj, agent.RUN)
    assert not (tmp_path / "evil.txt").exists()
    (proj / ".git").mkdir()
    assert ".git" in agent.run_tool("write_file", {"path": ".git/hooks/pre-commit", "content": "x"}, proj, agent.RUN)


def test_commands_run_in_the_project(proj):
    out = agent.run_tool("run_command", {"command": f'"{sys.executable}" -c "import os; print(os.getcwd())"'}, proj, agent.RUN)
    assert out.startswith("exit code 0") and str(proj) in out
    assert agent.run_tool("run_command", {"command": f'"{sys.executable}" -c "raise SystemExit(3)"'}, proj, agent.RUN).startswith("exit code 3")


def test_unknown_tools_and_bad_input_go_back_as_errors(proj):
    assert agent.run_tool("format_disk", {}, proj, agent.RUN).startswith("error:")
    assert agent.run_tool("read_file", None, proj, agent.READ).startswith("error:")


# --- the loop --------------------------------------------------------------------------------

def test_copilot_fixes_a_bug_and_runs_the_tests(proj):
    chat = scripted(
        ("Let me look.", [("read_file", {"path": "app.py"})]),
        ("", [("edit_file", {"path": "app.py", "old_text": "a - b", "new_text": "a + b"}),
              ("run_command", {"command": f'"{sys.executable}" -c "import app; assert app.add(2, 3) == 5"'})]),
        ("Fixed add() to add; the check passes.", []),
    )
    answer = agent.run("Fix add()", str(proj), agent.RUN, chat=chat)
    assert answer == "Fixed add() to add; the check passes."
    assert "a + b" in (proj / "app.py").read_text()
    assert "return a - b" in results(chat, 2)[0]
    assert results(chat, 3) == ["edited app.py", "exit code 0 (no output)"]
    first = chat.sent[0]["messages"][0]["content"]
    assert "run commands" in first and first.endswith("Fix add()")
    assert chat.sent[0]["tools"][-1] == "run_command"


def test_the_loop_stops_after_its_steps(proj):
    chat = scripted(("still looking", [("list_files", {})]))
    answer = agent.run("Loop forever", str(proj), agent.READ, chat=chat, max_steps=3)
    assert len(chat.sent) == 3 and "stopped Copilot after 3 steps" in answer


# --- through the MCP tools, end to end (subprocess, HTTP, the fake bridge) ---------------------

@pytest.fixture
def copilot_ready(monkeypatch):
    """Copilot (VS Code) set up as RAPR would load it."""
    import helm.state as _st
    spec = importlib.util.spec_from_file_location("copilot_vscode", ROOT / "integrations" / "copilot_vscode.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mcp._load()
    monkeypatch.setitem(_st.integrations, "copilot_vscode", {
        "name": mod.NAME, "build_command": mod.build_command, "stdin_prompt": True, "env_vars": [],
        "process_env": {}, "ready": None, "answers_only": False})
    monkeypatch.setattr(mcp, "agents", lambda: {"copilot_vscode": "Copilot (VS Code)", "codex": "Codex"})


def _script(steps):
    """For the fake bridge: reply to each /chat by how many tool results came back so far."""
    def reply(body):
        n = sum(1 for m in body.get("messages", []) if m.get("toolResults"))
        text, calls = steps[min(n, len(steps) - 1)]
        return {"text": text, "model": {"id": "gpt-4.1"},
                "toolCalls": [{"callId": f"c{n}-{i}", "name": c, "input": a} for i, (c, a) in enumerate(calls)]}
    return reply


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_ask_agent_delegates_to_copilot_in_a_copy(proj, bridge, copilot_ready):
    _git(proj, "init", "-q")
    _git(proj, "-c", "user.email=t@e.x", "-c", "user.name=t", "commit", "-qm", "init", "--allow-empty")
    bridge["state"]["script"] = _script([
        ("", [("edit_file", {"path": "app.py", "old_text": "a - b", "new_text": "a + b"}),
              ("run_command", {"command": "git status --short"})]),
        ("Fixed it.", []),
    ])
    out = mcp.Server(out=None, cwd=str(proj)).call_tool("ask_agent", {"agent": "copilot_vscode", "prompt": "Fix add()"})
    text = out["content"][0]["text"]
    assert not out.get("isError"), text
    assert "Fixed it." in text and "+    return a + b" in text          # its change comes back as a diff
    assert "return a - b" in (proj / "app.py").read_text()               # the project itself is untouched
    first = bridge["seen"][0]
    assert [t["name"] for t in first["tools"]][-1] == "run_command"     # in a copy it may run commands
    assert bridge["seen"][1]["messages"][-1]["toolResults"][1]["content"].startswith("exit code 0")


def test_with_allow_edits_copilot_edits_the_project_but_runs_nothing(proj, bridge, copilot_ready):
    bridge["state"]["script"] = _script([
        ("", [("edit_file", {"path": "app.py", "old_text": "a - b", "new_text": "a + b"}),
              ("run_command", {"command": "echo hi"})]),
        ("Done.", []),
    ])
    out = mcp.Server(out=None, cwd=str(proj)).call_tool(
        "ask_agent", {"agent": "copilot_vscode", "prompt": "Fix add()", "allow_edits": True})
    assert "Done." in out["content"][0]["text"]
    assert "a + b" in (proj / "app.py").read_text()
    assert "run_command" not in [t["name"] for t in bridge["seen"][0]["tools"]]
    assert "isn't allowed" in bridge["seen"][1]["messages"][-1]["toolResults"][1]["content"]


def test_second_opinion_lets_copilot_read_but_not_write(proj, bridge, copilot_ready):
    _git(proj, "init", "-q")
    _git(proj, "add", "-A")
    _git(proj, "-c", "user.email=t@e.x", "-c", "user.name=t", "commit", "-qm", "init")
    (proj / "app.py").write_text("def add(a, b):\n    return a * b\n")
    bridge["state"]["script"] = _script([("", [("read_file", {"path": "pkg/util.py"})]),
                                         ("add() multiplies: a bug.", [])])
    out = mcp.Server(out=None, cwd=str(proj)).call_tool("second_opinion", {"agent": "copilot_vscode"})
    assert "add() multiplies: a bug." in out["content"][0]["text"]
    assert [t["name"] for t in bridge["seen"][0]["tools"]] == ["list_files", "read_file", "search_files"]
    assert "return a * b" in bridge["seen"][0]["messages"][0]["content"]       # the diff is in the task


def test_an_old_bridge_asks_to_be_updated(proj, bridge, copilot_ready):
    bridge["state"]["version"] = "0.1.0"
    out = mcp.Server(out=None, cwd=str(proj)).call_tool("ask_agent", {"agent": "copilot_vscode", "prompt": "x"})
    assert out.get("isError") and "connect_vscode_copilot" in out["content"][0]["text"]


def test_connect_updates_an_older_bridge(monkeypatch):
    from helm import vscode_bridge as vb
    ran = []
    monkeypatch.setattr(vb, "copilot_in_vscode", lambda fresh=False: True)
    monkeypatch.setattr(vb, "find_copilot", lambda *a, **k: [{"how": "extension", "side": "WSL", "path": "x"}])
    monkeypatch.setattr(vb, "installed", lambda: True)
    monkeypatch.setattr(vb, "installed_version", lambda: "0.1.0")
    monkeypatch.setattr(vb, "code_cli", lambda env=None: "/usr/bin/code")
    monkeypatch.setattr(vb.subprocess, "run", lambda cmd, **k: ran.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))
    text = mcp.Server(out=None).call_tool("connect_vscode_copilot", {})["content"][0]["text"]
    assert len(ran) == 1 and "from 0.1.0 to 0.2.0" in text


def test_the_installed_version_comes_from_its_folder(tmp_path, monkeypatch):
    from helm import vscode_bridge as vb
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for v in ("0.1.0", "0.2.0"):
        (tmp_path / ".vscode-server" / "extensions" / f"raprai.rapr-bridge-{v}").mkdir(parents=True)
    assert vb.installed_version() == "0.2.0" and not vb.outdated()
    assert json.loads(json.dumps(vb.bundled_version())) == "0.2.0"
