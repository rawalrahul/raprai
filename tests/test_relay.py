"""Relays from the MCP server: plan with one AI, build with another, review, fix, review again."""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.mcp_server as mcp
from helm import relay


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "proj"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (r / "app.py").write_text("def add(a, b):\n    return a - b\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    return r


class FakeAIs:
    """'planner' plans (and scribbles a file it shouldn't), 'builder' fixes add() and later
    adds a test, 'critic' asks for a test the first time and approves the second."""

    def __init__(self, monkeypatch, agents=("planner", "builder", "critic")):
        self.calls = []
        self.gate = None          # set to a threading.Event to hold the builder until it's set
        monkeypatch.setattr(mcp, "agents", lambda: {a: a.title() for a in agents})
        monkeypatch.setattr(mcp, "run_agent", self.run)

    def run(self, agent, prompt, cwd, model=None, **kw):
        self.calls.append({"agent": agent, "prompt": prompt, "cwd": cwd, "edits": kw.get("edits")})
        if self.gate is not None and agent == "builder":
            self.gate.wait(10)
        if agent == "planner":
            Path(cwd, "notes.txt").write_text("planner was here")
            return "1. Make add() return a + b.\n2. Add a test."
        if agent == "builder":
            if "found problems" in prompt:
                Path(cwd, "test_app.py").write_text("from app import add\nassert add(1, 2) == 3\n")
                return "Added the test."
            Path(cwd, "app.py").write_text("def add(a, b):\n    return a + b\n")
            return "Fixed add()."
        if agent == "critic":
            reviews = sum(c["agent"] == "critic" for c in self.calls)
            Path(cwd, "app.py").write_text("reviewer scribble\n")
            return ("Looks right now.\nVERDICT: APPROVED" if reviews > 1
                    else "app.py:2 there's no test for add().\nVERDICT: CHANGES NEEDED")
        return "?"


def call(server, name, **args):
    out = server.call_tool(name, args)
    return out["content"][0]["text"], out.get("isError", False)


def wait(server, rid, seconds=20):
    end = time.time() + seconds
    while time.time() < end:
        text, _ = call(server, "relay_status", id=rid, wait_seconds=1)
        if "Still running" not in text:
            return text
    raise AssertionError("relay didn't finish: " + text)


def rid_of(text):
    return text.split("relay ", 1)[1].split()[0]


def worktrees(repo):
    return git(repo, "worktree", "list")


def test_plan_build_review_fix_review_then_merge(repo, monkeypatch):
    ais = FakeAIs(monkeypatch)
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "start_relay", task="add() is wrong", planner="planner", executor="builder",
                     reviewer="critic")
    assert not err and "planner plans, builder builds, critic reviews" in text
    rid = rid_of(text)
    report = wait(s, rid)

    assert [c["agent"] for c in ais.calls] == ["planner", "builder", "critic", "builder", "critic"]
    assert [c["edits"] for c in ais.calls] == [False, True, False, True, False]
    build, review1, fix, review2 = (c["prompt"] for c in ais.calls[1:])
    assert "Make add() return a + b" in build                 # the executor follows the plan
    assert "+    return a + b" in review1 and "notes.txt" not in review1   # the planner's scribble was undone
    assert "no test for add()" in fix                          # the fixer gets the review
    assert "test_app.py" in review2                            # the second review sees the fix
    assert all(c["cwd"] != str(repo) for c in ais.calls)

    assert f"Relay {rid}: done" in report and "approved" in report
    assert "## Plan: planner" in report and "## Fix: builder" in report
    assert (repo / "app.py").read_text() == "def add(a, b):\n    return a - b\n"   # untouched until merge

    text, err = call(s, "merge_relay", id=rid)
    assert not err and "2 file(s) changed" in text
    assert (repo / "app.py").read_text() == "def add(a, b):\n    return a + b\n"   # not the reviewer's scribble
    assert (repo / "test_app.py").exists() and not (repo / "notes.txt").exists()
    assert "rapr-mcp" not in worktrees(repo)


def test_a_given_plan_skips_the_planner_and_uncommitted_work_comes_along(repo, monkeypatch):
    ais = FakeAIs(monkeypatch)
    (repo / "wip.py").write_text("x = 1\n")        # uncommitted: the copy starts from it
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "start_relay", task="fix add", plan="Just flip the sign.", executor="builder",
                     reviewer="critic", fix_rounds=0)
    assert not err
    report = wait(s, rid_of(text))
    assert [c["agent"] for c in ais.calls] == ["builder", "critic"]
    assert "Just flip the sign." in ais.calls[0]["prompt"]
    assert "wip.py" not in ais.calls[1]["prompt"]   # only the relay's own change is reviewed
    assert "still wants changes" in report and "The plan you gave" in report
    call(s, "merge_relay", id=rid_of(text))
    assert (repo / "app.py").read_text().endswith("a + b\n") and (repo / "wip.py").read_text() == "x = 1\n"


def test_no_change_fails_and_cleans_up(repo, monkeypatch):
    ais = FakeAIs(monkeypatch)
    ais.run = lambda *a, **k: "I'd rather not."
    monkeypatch.setattr(mcp, "run_agent", ais.run)
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "start_relay", task="t", executor="builder", reviewer="critic")
    report = wait(s, rid_of(text))
    assert ": failed" in report and "didn't change any files" in report
    text, err = call(s, "merge_relay", id=rid_of(text))
    assert err and "only a finished relay" in text
    time.sleep(0.2)
    assert "rapr-mcp" not in worktrees(repo)


def test_discard_stops_a_running_relay(repo, monkeypatch):
    ais = FakeAIs(monkeypatch)
    ais.gate = threading.Event()
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "start_relay", task="t", executor="builder", reviewer="critic")
    rid = rid_of(text)
    end = time.time() + 10   # the copy is made in the background first
    status, _ = call(s, "relay_status", id=rid, wait_seconds=0)
    while "builder is carrying out the task" not in status and time.time() < end:
        time.sleep(0.05)
        status, _ = call(s, "relay_status", id=rid, wait_seconds=0)
    assert "running" in status and "builder is carrying out the task" in status
    text, err = call(s, "discard_relay", id=rid)
    assert not err and "Discarded" in text
    ais.gate.set()
    end = time.time() + 10
    while "rapr-mcp" in worktrees(repo) and time.time() < end:
        time.sleep(0.1)
    assert "rapr-mcp" not in worktrees(repo)
    assert [c["agent"] for c in ais.calls] == ["builder"]     # it never went on to review
    assert (repo / "app.py").read_text().endswith("a - b\n")


def test_discard_while_the_project_is_still_being_copied(repo, monkeypatch):
    ais = FakeAIs(monkeypatch)
    gate = threading.Event()
    real = mcp.Scratch

    class SlowScratch(real):
        def __init__(self, folder):
            gate.wait(10)
            super().__init__(folder)
    monkeypatch.setattr(mcp, "Scratch", SlowScratch)
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "start_relay", task="t", executor="builder", reviewer="critic")
    rid = rid_of(text)
    status, _ = call(s, "relay_status", id=rid, wait_seconds=0)
    assert "copying the project" in status
    text, err = call(s, "discard_relay", id=rid)
    assert not err and "Discarded" in text
    gate.set()
    end = time.time() + 10
    time.sleep(0.3)
    while "rapr-mcp" in worktrees(repo) and time.time() < end:
        time.sleep(0.1)
    assert "rapr-mcp" not in worktrees(repo)
    assert ais.calls == []                                    # no AI was started


def test_closing_the_server_discards_open_relays(repo, monkeypatch):
    FakeAIs(monkeypatch)
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "start_relay", task="t", executor="builder", reviewer="critic", fix_rounds=0)
    wait(s, rid_of(text))
    assert "rapr-mcp" in worktrees(repo)
    s.close_relays()
    assert "rapr-mcp" not in worktrees(repo)


def test_a_plain_folder(tmp_path, monkeypatch):
    FakeAIs(monkeypatch)
    folder = tmp_path / "plain"
    folder.mkdir()
    (folder / "app.py").write_text("def add(a, b):\n    return a - b\n")
    (folder / "old.txt").write_text("stays\n")
    s = mcp.Server(out=None, cwd=str(folder))
    text, _ = call(s, "start_relay", task="t", planner="planner", executor="builder", reviewer="critic")
    report = wait(s, rid_of(text))
    assert "changed: app.py" in report and "notes.txt" not in report
    call(s, "merge_relay", id=rid_of(text))
    assert (folder / "app.py").read_text().endswith("a + b\n") and (folder / "test_app.py").exists()
    assert (folder / "old.txt").exists() and not (folder / "notes.txt").exists()


def test_roles_are_checked_up_front(repo, monkeypatch):
    FakeAIs(monkeypatch)
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "start_relay", task="t", executor="builder", reviewer="nobody")
    assert err and "'nobody' isn't available" in text
    text, err = call(s, "start_relay", task="t", executor="builder")
    assert err and "Pick a reviewer" in text
    text, err = call(s, "start_relay", task="t", executor="builder", planner="planner")
    assert not err and "planner plans" in text and "planner reviews" in text
    call(s, "discard_relay", id=rid_of(text))


def test_verdict():
    assert relay.verdict("ok\nVERDICT: APPROVED") is True
    assert relay.verdict("**VERDICT:** changes needed") is False
    assert relay.verdict("VERDICT: CHANGES NEEDED\n...\nVERDICT: APPROVED") is True
    assert relay.verdict("Looks good") is None


def test_claude_may_edit_files_when_its_role_needs_it(monkeypatch):
    import helm.council.runner as runner
    seen = []
    monkeypatch.setattr(runner, "_run_subprocess_blocking", lambda cmd, *a, **k: seen.append((cmd, k)) or "ok")
    mcp.run_agent("claude", "do it", ".", edits=True, timeout=42)
    mcp.run_agent("claude", "look", ".")
    (edit_cmd, kw), (look_cmd, _) = seen
    assert edit_cmd[:3] == ["claude", "--permission-mode", "acceptEdits"] and kw["timeout"] == 42
    assert "--permission-mode" not in look_cmd


def test_grok_command(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("grok_integration", Path(__file__).parent.parent / "integrations" / "grok.py")
    grok = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grok)
    monkeypatch.delenv("GROK_ARGS", raising=False)
    cmd = grok.build_command("fix it", model="grok-code")
    assert cmd[0].startswith("grok") and cmd[-2:] == ["-p", "fix it"]
    assert "--always-approve" in cmd and cmd[cmd.index("--model") + 1] == "grok-code"
    long = grok.build_command("x" * 30_000)
    path = long[-1].split("in the file ", 1)[1].split(" (too long", 1)[0]
    assert Path(path).read_text(encoding="utf-8") == "x" * 30_000


def test_what_the_tests_leave_behind_is_not_merged(repo, monkeypatch):
    FakeAIs(monkeypatch)
    s = mcp.Server(out=None, cwd=str(repo))
    make_cache = "import os; os.makedirs('__pycache__'); open('__pycache__/app.pyc', 'w').write('x')"
    text, _ = call(s, "start_relay", task="t", executor="builder", reviewer="critic", fix_rounds=0,
                   test_command=f'"{sys.executable}" -c "{make_cache}"')
    report = wait(s, rid_of(text))
    assert "): passed" in report and "__pycache__" not in report.split("Files changed")[1]
    merged, _ = call(s, "merge_relay", id=rid_of(text))
    assert "1 file(s) changed" in merged and not (repo / "__pycache__").exists()
