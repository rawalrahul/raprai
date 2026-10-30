"""RAPR as an MCP server: the stdio protocol, second opinions in a throwaway copy, bake-offs."""
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.mcp_server as mcp

ROOT = Path(__file__).resolve().parent.parent


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


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


@pytest.fixture
def fake_agents(monkeypatch):
    """Two fake AIs. 'editor' also rewrites app.py wherever it runs; prompts are recorded."""
    seen = []

    def run(agent, prompt, cwd, model=None, **kw):
        seen.append({"agent": agent, "prompt": prompt, "cwd": cwd, "edits": kw.get("edits", False)})
        if agent == "editor":
            Path(cwd, "app.py").write_text("def add(a, b):\n    return a + b\n")
        return f"{agent} says hi"
    monkeypatch.setattr(mcp, "agents", lambda: {"editor": "Editor", "reader": "Reader"})
    monkeypatch.setattr(mcp, "run_agent", run)
    return seen


def call(server, name, **args):
    out = server.call_tool(name, args)
    return out["content"][0]["text"], out.get("isError", False)


def test_second_opinion_reviews_uncommitted_work_without_touching_it(repo, fake_agents):
    (repo / "app.py").write_text("def add(a, b):\n    return a * b\n")
    (repo / "new.py").write_text("print('new')\n")
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "second_opinion", agent="editor", focus="the math")
    assert not err and "editor says hi" in text and "uncommitted changes" in text
    p = fake_agents[0]["prompt"]
    assert "return a * b" in p and "+print('new')" in p and "the math" in p
    assert fake_agents[0]["cwd"] != str(repo)
    assert (repo / "app.py").read_text() == "def add(a, b):\n    return a * b\n"   # the edit landed in the copy only
    assert "rapr-mcp" not in subprocess.run(["git", "worktree", "list"], cwd=repo, capture_output=True, text=True).stdout


def test_second_opinion_falls_back_to_the_last_commit(repo, fake_agents):
    (repo / "app.py").write_text("def add(a, b):\n    return a + b\n")
    git(repo, "commit", "-qam", "fix add")
    text, err = call(mcp.Server(out=None, cwd=str(repo)), "second_opinion", agent="reader")
    assert not err and "the last commit" in text
    assert "fix add" in fake_agents[0]["prompt"] and "return a + b" in fake_agents[0]["prompt"]


def test_second_opinion_needs_git_and_changes(tmp_path, repo, fake_agents):
    text, err = call(mcp.Server(out=None, cwd=str(tmp_path)), "second_opinion", agent="reader")
    assert err and "isn't a git repository" in text
    text, err = call(mcp.Server(out=None, cwd=str(repo)), "second_opinion", agent="reader")
    assert err and "no changes" in text


def test_ask_agent_returns_changes_as_a_diff_unless_edits_are_allowed(repo, fake_agents):
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "ask_agent", agent="editor", prompt="fix add")
    assert not err and "not applied" in text and "+    return a + b" in text
    assert "a - b" in (repo / "app.py").read_text()
    text, err = call(s, "ask_agent", agent="editor", prompt="fix add", allow_edits=True)
    assert not err and "edits allowed" in text and "a + b" in (repo / "app.py").read_text()


def test_ask_agent_in_a_plain_folder(tmp_path, fake_agents):
    (tmp_path / "app.py").write_text("x")
    text, err = call(mcp.Server(out=None, cwd=str(tmp_path)), "ask_agent", agent="editor", prompt="hi")
    assert not err and (tmp_path / "app.py").read_text() == "x"


def test_unknown_agent_and_missing_args(repo, fake_agents):
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "ask_agent", agent="nope", prompt="hi")
    assert err and "Installed: editor, reader" in text
    text, err = call(s, "ask_agent", agent="editor")
    assert err and "Missing: prompt" in text


def test_bakeoff_round_trip(repo, fake_agents, monkeypatch, tmp_path):
    import helm.bakeoff as bakeoff
    real_create = bakeoff.create
    monkeypatch.setattr(bakeoff, "create", lambda r, t, a, test_command=None: real_create(r, t, a, test_command=test_command, root=str(tmp_path / "w")))
    saved = []
    monkeypatch.setattr(mcp, "_save", lambda b: saved.append(b.status))
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "start_bakeoff", task="fix add", agents=["editor", "reader"],
                     test_command='python -c "import app; assert app.add(1,2)==3"')
    assert not err
    bid = next(iter(s.bakeoffs))
    text, err = call(s, "bakeoff_status", id=bid, wait_seconds=30)
    assert "done" in text and "tests passed" in text and "tests FAILED" in text and "+    return a + b" in text
    text, err = call(s, "merge_bakeoff", id=bid, agent="editor")
    assert not err and "a + b" in (repo / "app.py").read_text()
    assert saved == ["done", "merged"]
    text, err = call(s, "bakeoff_status", id="zzz")
    assert err and "No bake-off" in text


def test_bakeoff_status_answers_inside_codex_tool_timeout(tmp_path, monkeypatch):
    """Codex gives up on a tool after 60 seconds, so one status call never waits that long."""
    from types import SimpleNamespace
    clock = [0.0]
    monkeypatch.setattr(mcp, "time", SimpleNamespace(monotonic=lambda: clock[0],
                                                     sleep=lambda sec: clock.__setitem__(0, clock[0] + sec)))
    s = mcp.Server(out=None, cwd=str(tmp_path))
    s.bakeoffs["b1"] = SimpleNamespace(id="b1", status="running", task="fix add", test_command=None,
                                       attempts=[SimpleNamespace(ai="codex", seconds=0)])
    for asked in ({}, {"wait_seconds": 240}):
        clock[0] = 0.0
        text, err = call(s, "bakeoff_status", id="b1", **asked)
        assert not err and "still working" in text and "Call bakeoff_status again" in text
        assert clock[0] < 60
    schema = mcp.TOOLS["bakeoff_status"][0]["inputSchema"]["properties"]["wait_seconds"]
    assert schema["default"] <= schema["maximum"] < 60


@pytest.fixture
def fake_claude(tmp_path):
    """A stand-in `claude` command on PATH that answers like Claude Code's JSON output."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import json, os, sys
        prompt = sys.argv[sys.argv.index("-p") + 1]
        open("touched_by_claude.txt", "w").write("x")
        print(json.dumps({{"result": "FAKE REVIEW cwd=" + os.getcwd() + " saw=" + str("return a * b" in prompt)}}))
    """))
    exe.chmod(0o755)
    return bindir


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_stdio_end_to_end(repo, fake_claude, tmp_path):
    """The real entry point, over stdin/stdout, running a (fake) claude CLI."""
    (repo / "app.py").write_text("def add(a, b):\n    return a * b\n")
    env = dict(os.environ, PATH=f"{fake_claude}{os.pathsep}{os.environ['PATH']}", RAPR_DATA_DIR=str(tmp_path / "data"))
    proc = subprocess.Popen([sys.executable, str(ROOT / "rapr_mcp.py")], cwd=repo, env=env, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def send(msg):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def recv():
        line = proc.stdout.readline()
        assert line, proc.stderr.read()
        return json.loads(line)   # every stdout line must be JSON-RPC: no stray prints

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        init = recv()
        assert init["id"] == 1 and init["result"]["serverInfo"]["name"] == "rapr-ai"
        assert init["result"]["protocolVersion"] == "2025-06-18" and "tools" in init["result"]["capabilities"]
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in recv()["result"]["tools"]}
        assert {"list_agents", "second_opinion", "ask_agent", "start_bakeoff", "bakeoff_status"} <= names
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_agents", "arguments": {}}})
        assert "claude (Claude Code)" in recv()["result"]["content"][0]["text"]
        send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
              "params": {"name": "second_opinion", "arguments": {"agent": "claude"}}})
        send({"jsonrpc": "2.0", "id": 5, "method": "ping"})   # answered while the review runs
        got = {}
        deadline = time.time() + 60
        while len(got) < 2 and time.time() < deadline:
            m = recv()
            got[m["id"]] = m
        assert got[5]["result"] == {}
        review = got[4]["result"]
        assert not review.get("isError"), review
        text = review["content"][0]["text"]
        assert "FAKE REVIEW" in text and "saw=True" in text and f"cwd={repo}" not in text
        assert not (repo / "touched_by_claude.txt").exists()
        send({"jsonrpc": "2.0", "id": 6, "method": "bogus"})
        assert recv()["error"]["code"] == -32601
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)


def test_a_byte_order_mark_before_a_message_is_ignored():
    """Windows PowerShell puts a BOM in front of text it pipes to a program."""
    import io
    out = io.StringIO()
    mcp.Server(out=out).serve(io.StringIO('\ufeff{"jsonrpc":"2.0","id":7,"method":"ping"}\n'))
    assert json.loads(out.getvalue()) == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_local_model_ais_are_listed_only_while_their_server_answers(monkeypatch):
    """claude_ollama used to be listed whenever `claude` was installed, and local_ai always
    (its command is Python), even with no Ollama or local server on the computer."""
    import http.server
    import socket
    import threading
    import helm.state as st

    mcp._load()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        free = sock.getsockname()[1]
    monkeypatch.setenv("OLLAMA_HOST", f"127.0.0.1:{free}")
    monkeypatch.setenv("LOCAL_AI_URL", f"http://127.0.0.1:{free}")
    monkeypatch.setattr(mcp, "_found", lambda exe: True)   # as if claude and codex are installed
    for key in ("claude_ollama", "codex_ollama", "local_ai"):
        assert not mcp._ready(key, st.integrations[key]), key

    class Answer(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Answer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        monkeypatch.setenv("OLLAMA_HOST", f"127.0.0.1:{port}")
        monkeypatch.setenv("LOCAL_AI_URL", f"http://127.0.0.1:{port}")
        for key in ("claude_ollama", "codex_ollama", "local_ai"):
            assert mcp._ready(key, st.integrations[key]), key
    finally:
        server.shutdown()
