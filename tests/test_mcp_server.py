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
    monkeypatch.setattr(bakeoff, "create", lambda r, t, a, **kw: real_create(r, t, a, root=str(tmp_path / "w"), **kw))
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
        args = sys.argv[1:]
        i = args.index("-p")
        # Like Claude Code: piped stdin is read, and is the prompt when none is given. (Had it
        # inherited the MCP server's stdin, this would eat the client's messages.)
        piped = sys.stdin.read()
        via_stdin = i + 1 >= len(args)
        prompt = piped if via_stdin else args[i + 1]
        open("touched_by_claude.txt", "w").write("x")
        print(json.dumps({{"result": "FAKE REVIEW cwd=" + os.getcwd() + " saw=" + str("return a * b" in prompt)
                          + " stdin=" + str(via_stdin)}}))
    """))
    exe.chmod(0o755)
    return bindir


@pytest.mark.skipif(sys.platform == "win32", reason="uses a shebang script as a fake CLI")
def test_stdio_end_to_end(repo, fake_claude, tmp_path):
    """The real entry point, over stdin/stdout, running a (fake) claude CLI."""
    # A change big enough that the review prompt goes to claude over stdin.
    (repo / "app.py").write_text("def add(a, b):\n    return a * b\n" + "# padding line\n" * 600)
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
        assert "FAKE REVIEW" in text and "saw=True" in text and "stdin=True" in text and f"cwd={repo}" not in text
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
    for key in ("ollama", "claude_ollama", "codex_ollama", "local_ai"):
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
        for key in ("ollama", "claude_ollama", "codex_ollama", "local_ai"):
            assert mcp._ready(key, st.integrations[key]), key
    finally:
        server.shutdown()


@pytest.fixture
def team_agents(monkeypatch):
    """AIs whose task is "write FILE: TEXT"; they write that file wherever they run."""
    prompts = []

    def run(agent, prompt, cwd, model=None, **kw):
        prompts.append(prompt)
        task = prompt.split("Your part")[1].split("\n")[1]
        name, text = task.removeprefix("write ").split(": ", 1)
        Path(cwd, name).write_text(text + "\n")
        return f"{agent} wrote {name}"
    monkeypatch.setattr(mcp, "agents", lambda: {"claude": "Claude Code", "codex": "Codex"})
    monkeypatch.setattr(mcp, "run_agent", run)
    return prompts


def wait_team(s, team_id):
    for _ in range(100):
        text, _ = call(s, "team_status", id=team_id, wait_seconds=1, include_diffs=False)
        if "working" not in text.splitlines()[0]:
            return text
    raise AssertionError("team never finished")


def test_team_parts_run_separately_and_merge_with_your_own_work(repo, team_agents):
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "start_team", plan="Split the app in two",
                     parts=[{"agent": "claude", "task": "write api.py: API = 1"},
                            {"agent": "codex", "task": "write ui.py: UI = 2"}])
    assert not err, text
    team_id = text.split()[2]
    (repo / "app.py").write_text("def add(a, b):\n    return a + b\n")   # the user's own part
    report = wait_team(s, team_id)
    assert "Part 1: claude, done" in report and "Part 2: codex, done" in report
    assert not (repo / "api.py").exists()          # nothing applied before merging
    assert all("Split the app in two" in prompt for prompt in team_agents)
    claude_prompt = next(prompt for prompt in team_agents if "write api.py" in prompt.split("Your part")[1][:40])
    assert "part 2 (codex): write ui.py" in claude_prompt

    text, err = call(s, "merge_team", id=team_id)
    assert not err, text
    assert (repo / "api.py").read_text() == "API = 1\n"
    assert (repo / "ui.py").read_text() == "UI = 2\n"
    assert "a + b" in (repo / "app.py").read_text()
    assert not any(Path(p.scratch.root).exists() for p in s.teams[team_id].parts)


def test_team_part_that_clashes_is_kept_back(repo, team_agents):
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "start_team", parts=[{"agent": "claude", "task": "write app.py: X = 1"},
                                           {"agent": "codex", "task": "write app.py: X = 2"}])
    team_id = text.split()[2]
    report = wait_team(s, team_id)
    assert "app.py (parts 1, 2)" in report
    text, _ = call(s, "merge_team", id=team_id)
    assert "part 1 (claude): 1 file(s)" in text and "part 2 (codex) not merged" in text
    assert (repo / "app.py").read_text() == "X = 1\n"
    assert s.teams[team_id].parts[1].status == "conflict"
    call(s, "discard_team", id=team_id)
    assert not Path(s.teams[team_id].parts[1].scratch.root).exists()


def test_team_in_a_plain_folder_wont_overwrite_your_changes(tmp_path, team_agents):
    (tmp_path / "notes.txt").write_text("old\n")
    s = mcp.Server(out=None, cwd=str(tmp_path))
    text, _ = call(s, "start_team", parts=[{"agent": "claude", "task": "write notes.txt: from claude"},
                                           {"agent": "codex", "task": "write extra.txt: from codex"}])
    team_id = text.split()[2]
    wait_team(s, team_id)
    (tmp_path / "notes.txt").write_text("mine\n")   # changed after the copies were made
    text, _ = call(s, "merge_team", id=team_id)
    assert "part 1 (claude) not merged: notes.txt" in text
    assert (tmp_path / "notes.txt").read_text() == "mine\n"
    assert (tmp_path / "extra.txt").read_text() == "from codex\n"


def test_team_checks_its_parts(repo, team_agents):
    s = mcp.Server(out=None, cwd=str(repo))
    assert call(s, "start_team", parts=[])[1]
    text, err = call(s, "start_team", parts=[{"agent": "nobody", "task": "x"}])
    assert err and "isn't available" in text
    text, err = call(s, "start_team", parts=[{"agent": "claude", "task": ""}])
    assert err and "Part 1 needs" in text
    text, err = call(s, "merge_team", id="team-nope")
    assert err


def test_start_relay_and_team_answer_before_the_copy_is_made(repo, team_agents, monkeypatch):
    """A big project can take longer to copy than an MCP client waits for a tool."""
    import threading
    gate = threading.Event()
    real = mcp.Scratch

    class SlowScratch(real):
        def __init__(self, folder):
            gate.wait(10)
            super().__init__(folder)
    monkeypatch.setattr(mcp, "Scratch", SlowScratch)
    s = mcp.Server(out=None, cwd=str(repo))
    start = time.monotonic()
    text, err = call(s, "start_relay", task="write a.py: A = 1", executor="claude", reviewer="codex",
                     fix_rounds=0)
    assert not err, text
    text, err = call(s, "start_team", parts=[{"agent": "claude", "task": "write api.py: API = 1"}])
    assert not err, text
    assert time.monotonic() - start < 3
    gate.set()
    report = wait_team(s, text.split()[2])
    assert "Part 1: claude, done" in report


def test_a_relay_whose_copy_fails_says_so(repo, team_agents, monkeypatch):
    def broken(folder):
        raise OSError("disk full")
    monkeypatch.setattr(mcp, "Scratch", broken)
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "start_relay", task="x", executor="claude", reviewer="codex")
    relay_id = text.split()[2]
    for _ in range(50):
        text, _ = call(s, "relay_status", id=relay_id, wait_seconds=1)
        if "failed" in text:
            break
    assert "failed" in text and "disk full" in text


def test_agents_are_checked_once_a_minute(monkeypatch):
    import helm.state as st
    mcp._load()
    calls = []
    monkeypatch.setattr(mcp, "_agents_cache", (0.0, {}))
    monkeypatch.setattr(mcp, "_found", lambda exe: False)
    monkeypatch.setattr(mcp, "_ready", lambda key, info: calls.append(key) or key == "codex")
    assert mcp.agents() == {"codex": st.integrations["codex"]["name"]}
    n = len(calls)
    mcp.agents()
    mcp._check_agent("codex")
    assert len(calls) == n                      # answered from the cache


def test_loading_the_ais_does_not_import_the_web_app():
    """It took seconds (the Gemini check imported the whole app) and timed out MCP clients."""
    code = ("import sys; sys.path.insert(0, '.'); import helm.mcp_server as m; m._load(); "
            "print('helm.web_routes' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.stdout.strip().splitlines()[-1] == "False", out.stderr[-2000:]


def test_list_agents_explains_copilot_chat_is_not_a_cli(monkeypatch, tmp_path):
    import helm.editor_clis as ec
    (tmp_path / ".vscode" / "extensions" / "github.copilot-chat-0.40.0").mkdir(parents=True)
    monkeypatch.setattr(ec.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(mcp, "agents", lambda: {"claude": "Claude Code"})
    monkeypatch.setattr(mcp, "signed_out", lambda: [])
    monkeypatch.setattr(mcp, "_found", lambda exe: False)
    text = mcp.Server(out=None).call_tool("list_agents", {})["content"][0]["text"]
    assert "npm install -g @github/copilot" in text
    monkeypatch.setattr(mcp, "agents", lambda: {"claude": "Claude Code", "copilot": "Copilot"})
    text = mcp.Server(out=None).call_tool("list_agents", {})["content"][0]["text"]
    assert "npm install" not in text


# ── Robustness: failures, output size, cancellation, progress, cleanup ──────

def test_shared_runner_never_hands_the_ai_our_stdin_and_reports_errors(tmp_path):
    from helm.council.runner import _extract_text, _run_subprocess_blocking, failed
    # The child sees an empty stdin (not ours), so it can't eat an MCP client's messages.
    out = _run_subprocess_blocking([sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"],
                                   str(tmp_path), None)
    assert out == "''"
    # No output and a failing exit: the error text, not "(no output)".
    out = _run_subprocess_blocking([sys.executable, "-c", "import sys; sys.stderr.write('not logged in'); sys.exit(3)"],
                                   str(tmp_path), None)
    assert out == "(error: not logged in)" and failed(out)
    assert _extract_text(json.dumps({"is_error": True, "result": "Credit balance is too low"})) \
        == "(error: Credit balance is too low)"
    assert not failed("Looks good")


def test_run_agent_raises_when_the_ai_does_not_answer(monkeypatch):
    import helm.council.runner as runner
    monkeypatch.setattr(runner, "_build_cmd_for_session", lambda sess, prompt: (["x"], None, {}))
    for reply, says in [("(timed out)", "didn't finish within 5 minutes"),
                        ("(error: not logged in)", "didn't answer: error: not logged in")]:
        monkeypatch.setattr(runner, "_run_subprocess_blocking", lambda *a, reply=reply, **k: reply)
        with pytest.raises(mcp.ToolError, match=says):
            mcp.run_agent("codex", "hi", ".", timeout=300)
    # Saying nothing isn't failing: it may have edited files. The reply is just empty.
    monkeypatch.setattr(runner, "_run_subprocess_blocking", lambda *a, **k: "(no output)")
    assert mcp.run_agent("codex", "hi", ".") == ""


def test_long_answers_are_cut_and_saved_to_a_file(monkeypatch, tmp_path):
    monkeypatch.setattr(mcp, "OUTPUT_LIMIT", 1000)
    monkeypatch.setattr(mcp, "output_dir", lambda: tmp_path / "out")
    text = "".join(f"line {i}\n" for i in range(1000))
    out = mcp.fit_output("ask_agent", text)
    assert len(out) < 1300 and out.startswith("line 0\n") and "cut here" in out
    saved = list((tmp_path / "out").glob("ask_agent-*.md"))
    assert len(saved) == 1 and saved[0].read_text() == text and str(saved[0]) in out
    assert mcp.fit_output("x", "short") == "short"


def _server(out):
    class Out:
        def write(self, s):
            out.extend(json.loads(line) for line in s.splitlines() if line)

        def flush(self):
            pass
    return Out()


def test_cancelling_a_request_stops_its_ai_and_sends_no_answer(repo, monkeypatch):
    import helm.council.runner as runner
    monkeypatch.setattr(mcp, "agents", lambda: {"slow": "Slow"})
    monkeypatch.setattr(runner, "_build_cmd_for_session",
                        lambda sess, prompt: ([sys.executable, "-c", "import time; time.sleep(60)"], None, {}))
    sent: list = []
    s = mcp.Server(out=_server(sent), cwd=str(repo))
    s.handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
              "params": {"name": "ask_agent", "arguments": {"agent": "slow", "prompt": "hi"}}})
    for _ in range(600):   # up to 30s: slow runners
        if mcp._live:
            break
        time.sleep(0.05)
    assert mcp._live, "the AI never started"
    t0 = time.time()
    s.handle({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 7}})
    for _ in range(600):   # up to 30s: slow runners
        if not mcp._live and not s._pending:
            break
        time.sleep(0.05)
    assert not mcp._live and time.time() - t0 < 5          # killed, not left to run 60s
    assert [m for m in sent if m.get("id") == 7] == []      # a cancelled request gets no answer
    # Cancelling something already answered is ignored.
    s.cancel(99)
    assert 99 not in s._cancelled


def test_progress_notifications_while_a_tool_works(repo, monkeypatch):
    monkeypatch.setattr(mcp, "PROGRESS_EVERY", 0.05)
    monkeypatch.setattr(mcp, "agents", lambda: {"x": "X"})
    monkeypatch.setattr(mcp, "run_agent", lambda *a, **k: time.sleep(0.4) or "done")
    sent: list = []
    s = mcp.Server(out=_server(sent), cwd=str(repo))
    s.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "ask_agent", "arguments": {"agent": "x", "prompt": "hi"}, "_meta": {"progressToken": "tok"}}})
    for _ in range(600):   # up to 30s: slow runners
        if any(m.get("id") == 3 for m in sent):
            break
        time.sleep(0.05)
    progress = [m for m in sent if m.get("method") == "notifications/progress"]
    assert progress and all(p["params"]["progressToken"] == "tok" for p in progress)
    assert [p["params"]["progress"] for p in progress] == sorted({p["params"]["progress"] for p in progress})
    answer = next(m for m in sent if m.get("id") == 3)
    assert "done" in answer["result"]["content"][0]["text"]
    n = len([m for m in sent if m.get("method") == "notifications/progress"])
    time.sleep(0.2)
    assert len([m for m in sent if m.get("method") == "notifications/progress"]) == n   # stopped


def test_status_is_short_while_running_and_full_when_done(repo, fake_agents, monkeypatch, tmp_path):
    import threading
    import helm.bakeoff as bakeoff
    real_create = bakeoff.create
    monkeypatch.setattr(bakeoff, "create", lambda r, t, a, **kw: real_create(r, t, a, root=str(tmp_path / "w"), **kw))
    monkeypatch.setattr(mcp, "_save", lambda b: None)
    gate = threading.Event()

    def run(agent, prompt, cwd, model=None, **kw):
        if agent == "reader":
            gate.wait(10)
        Path(cwd, "app.py").write_text("def add(a, b):\n    return a + b\n")
        return agent + " says " + "blah " * 200
    monkeypatch.setattr(mcp, "run_agent", run)
    s = mcp.Server(out=None, cwd=str(repo))
    call(s, "start_bakeoff", task="fix add", agents=["editor", "reader"])
    bid = next(iter(s.bakeoffs))
    end = time.time() + 30   # copies are slow to make on Windows; wait for the editor's diff itself
    while not s.bakeoffs[bid].attempts[0].diff and time.time() < end:
        time.sleep(0.05)
    assert s.bakeoffs[bid].attempts[0].diff, "the editor never finished"
    text, _ = call(s, "bakeoff_status", id=bid, wait_seconds=0)
    assert "Still running" in text and "Diff:" not in text and len(text) < 1200
    text, _ = call(s, "bakeoff_status", id=bid, wait_seconds=0, include_diffs=True)
    assert "Diff:" in text                                  # asked for: shown anyway
    gate.set()
    text, _ = call(s, "bakeoff_status", id=bid, wait_seconds=10)
    assert "Still running" not in text and text.count("Diff:") == 2


def test_closing_the_server_removes_bakeoff_copies_and_branches(repo, fake_agents, monkeypatch, tmp_path):
    import helm.bakeoff as bakeoff
    real_create = bakeoff.create
    monkeypatch.setattr(bakeoff, "create", lambda r, t, a, **kw: real_create(r, t, a, root=str(tmp_path / "w"), **kw))
    monkeypatch.setattr(mcp, "_save", lambda b: None)
    s = mcp.Server(out=None, cwd=str(repo))
    call(s, "start_bakeoff", task="fix add", agents=["editor", "reader"])
    bid = next(iter(s.bakeoffs))
    call(s, "bakeoff_status", id=bid, wait_seconds=10)
    assert "bakeoff/" in subprocess.run(["git", "branch"], cwd=repo, capture_output=True, text=True).stdout
    s.serve([])   # the client goes away
    assert s.bakeoffs[bid].status == "discarded"
    assert "bakeoff/" not in subprocess.run(["git", "branch"], cwd=repo, capture_output=True, text=True).stdout
    assert len(subprocess.run(["git", "worktree", "list"], cwd=repo, capture_output=True, text=True).stdout.splitlines()) == 1


def test_bakeoff_works_on_and_merges_onto_uncommitted_work(repo, monkeypatch, tmp_path):
    import helm.bakeoff as bakeoff
    real_create = bakeoff.create
    monkeypatch.setattr(bakeoff, "create", lambda r, t, a, **kw: real_create(r, t, a, root=str(tmp_path / "w"), **kw))
    monkeypatch.setattr(mcp, "_save", lambda b: None)
    # The user's work in progress: an edit and a new file, neither committed.
    (repo / "app.py").write_text("def add(a, b):\n    return a - b\n\n\ndef sub(a, b):\n    return a - b\n")
    (repo / "notes.md").write_text("wip\n")
    seen = {}

    def run(agent, prompt, cwd, model=None, **kw):
        seen[agent] = (Path(cwd, "app.py").read_text(), Path(cwd, "notes.md").exists())
        if agent == "editor":
            Path(cwd, "app.py").write_text(Path(cwd, "app.py").read_text().replace("return a - b\n\n", "return a + b\n\n", 1))
        return "ok"
    monkeypatch.setattr(mcp, "agents", lambda: {"editor": "E", "reader": "R"})
    monkeypatch.setattr(mcp, "run_agent", run)
    s = mcp.Server(out=None, cwd=str(repo))
    call(s, "start_bakeoff", task="fix add", agents=["editor", "reader"])
    bid = next(iter(s.bakeoffs))
    text, _ = call(s, "bakeoff_status", id=bid, wait_seconds=10)
    assert all("def sub" in app and notes for app, notes in seen.values())   # they saw the work in progress
    assert "1 file(s) changed, +1 −1" in text                               # only the AI's own change
    text, err = call(s, "merge_bakeoff", id=bid, agent="editor")
    assert not err and "on top of your own uncommitted work" in text
    app = (repo / "app.py").read_text()
    assert "return a + b" in app and "def sub" in app and (repo / "notes.md").exists()


# ── Answering within the client's time limit (Codex: 60s) ───────────────────

def test_a_slow_ask_answers_with_an_id_and_agent_status_brings_the_reply(repo, monkeypatch):
    import threading
    monkeypatch.setattr(mcp, "ANSWER_WAIT", 0.2)
    monkeypatch.setattr(mcp, "agents", lambda: {"slow": "Slow"})
    gate = threading.Event()
    monkeypatch.setattr(mcp, "run_agent", lambda *a, **k: gate.wait(10) and "the answer")
    (repo / "app.py").write_text("def add(a, b):\n    return a * b\n")   # something to review
    s = mcp.Server(out=None, cwd=str(repo))
    t0 = time.time()
    text, err = call(s, "second_opinion", agent="slow")
    assert not err and "still working" in text and time.time() - t0 < 5
    jid = text.split("id '", 1)[1].split("'")[0]
    text, err = call(s, "agent_status", id=jid, wait_seconds=0)
    assert not err and "still working" in text
    gate.set()
    text, err = call(s, "agent_status", id=jid, wait_seconds=10)
    assert not err and "Second opinion from slow" in text and "the answer" in text
    text, err = call(s, "agent_status", id=jid)               # given once, then gone
    assert err and "already given" in text


def test_a_quick_ask_answers_directly_and_errors_stay_errors(repo, monkeypatch):
    monkeypatch.setattr(mcp, "agents", lambda: {"x": "X"})

    def boom(*a, **k):
        raise mcp.ToolError("x didn't answer: not logged in")
    monkeypatch.setattr(mcp, "run_agent", boom)
    s = mcp.Server(out=None, cwd=str(repo))
    text, err = call(s, "ask_agent", agent="x", prompt="hi")
    assert err and "not logged in" in text and not s.jobs


def test_cancel_agent_stops_a_running_ask(repo, monkeypatch):
    import helm.council.runner as runner
    monkeypatch.setattr(mcp, "ANSWER_WAIT", 0.2)
    monkeypatch.setattr(mcp, "agents", lambda: {"slow": "Slow"})
    monkeypatch.setattr(runner, "_build_cmd_for_session",
                        lambda sess, prompt: ([sys.executable, "-c", "import time; time.sleep(60)"], None, {}))
    s = mcp.Server(out=None, cwd=str(repo))
    text, _ = call(s, "ask_agent", agent="slow", prompt="hi")
    jid = text.split("id '", 1)[1].split("'")[0]
    for _ in range(600):
        if mcp._live:
            break
        time.sleep(0.05)
    t0 = time.time()
    text, err = call(s, "cancel_agent", id=jid)
    assert not err and "Stopped slow's question" in text and time.time() - t0 < 10
    assert not mcp._live and jid not in s.jobs
    assert "rapr-mcp" not in subprocess.run(["git", "worktree", "list"], cwd=repo, capture_output=True, text=True).stdout
