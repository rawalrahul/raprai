"""A RAPR to send messages through, for tests of helm/ai_runner/core.py.

It watches RAPR only from the outside, so the tests keep working while that
code is moved around (docs/code-health-plan.md, track C):

- The AIs are stand-in command-line programs on PATH. Each records how it was
  started (arguments, piped prompt, folder) and replies with whatever the test
  set for it.
- What RAPR shows you is caught by a stand-in browser tab: every message it
  would send to the web UI.

    def test_something(rapr):
        rapr.reply("codex", "Done.")
        sess = rapr.session("codex")
        out = rapr.send("fix the bug", sess)
        assert rapr.calls("codex")[0]["stdin"] ...
"""
import asyncio
import json
import os
import sys

import pytest

FAKE_CLI = '''#!{py}
import json, os, select, sys
name = os.path.basename(sys.argv[0])
stdin = ""
if select.select([sys.stdin], [], [], 0.2)[0]:
    stdin = sys.stdin.read()
with open(os.environ["RAPR_FAKE_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps({{"ai": name, "argv": sys.argv[1:], "stdin": stdin, "cwd": os.getcwd(),
                        "session": os.environ.get("RAPR_SESSION_ID")}}) + "\\n")
spec = os.path.join(os.environ["RAPR_FAKE_DIR"], name + ".json")
reply = {{"text": "reply from " + name, "exit": 0}}
if os.path.exists(spec):
    with open(spec, encoding="utf-8") as f:
        reply.update(json.load(f))
sys.stdout.write(reply["text"])
sys.exit(reply["exit"])
'''

AIS = ("claude", "codex", "gemini")


class FakeTab:
    """A browser tab: records what RAPR sends to the web UI."""

    def __init__(self):
        self.sent = []

    async def send_text(self, payload):
        self.sent.append(json.loads(payload))


class Rapr:
    def __init__(self, root, tab):
        self.root = root
        self.tab = tab
        self.fake_dir = root / "fake"
        self.log = self.fake_dir / "calls.jsonl"

    # ── the AIs ───────────────────────────────────────────────────────────
    def reply(self, ai, text, exit=0):
        """What the stand-in *ai* prints next time (and every time after)."""
        (self.fake_dir / f"{ai}.json").write_text(json.dumps({"text": text, "exit": exit}))

    def claude_reply(self, text, input_tokens=None, output_tokens=None, cost=None, is_error=False):
        """Claude Code's --output-format json result."""
        data = {"type": "result", "result": text, "is_error": is_error}
        if input_tokens is not None:
            data["usage"] = {"input_tokens": input_tokens, "output_tokens": output_tokens}
        if cost is not None:
            data["total_cost_usd"] = cost
        self.reply("claude", json.dumps(data))

    def calls(self, ai=None):
        """How each stand-in AI was started, oldest first."""
        if not self.log.exists():
            return []
        calls = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [c for c in calls if ai is None or c["ai"] == ai]

    @staticmethod
    def prompt(call):
        """The prompt an AI got: piped in, or after -p / as the last argument."""
        if call["stdin"]:
            return call["stdin"]
        argv = call["argv"]
        if "-p" in argv:
            return argv[argv.index("-p") + 1]
        return argv[-1] if argv else ""

    # ── RAPR ──────────────────────────────────────────────────────────────
    def session(self, ai, **kw):
        from helm.session_mgr import make_session
        sess = make_session(ai, cwd=str(self.root / "project"), **kw)
        # An AI RAPR doesn't know becomes a shell session without a word.
        assert (sess["ai"] or "shell") == ai, f"asked for {ai}, got {sess['ai']}"
        return sess

    def send(self, text, sess=None, source="web"):
        from helm.ai_runner.core import process_message
        sid = sess["id"] if sess else None
        return asyncio.run(asyncio.wait_for(process_message(text, source=source, session_id=sid), 60))

    def messages(self, role=None):
        """Chat messages RAPR showed, as (role, content), oldest first."""
        return [(m["role"], m["content"]) for m in self.tab.sent
                if m.get("type") == "message" and (role is None or m["role"] == role)]

    def events(self, kind):
        return [m for m in self.tab.sent if m.get("type") == kind]


@pytest.fixture
def rapr(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("uses #! scripts as stand-in AIs")
    import helm.db as db
    import helm.skills as skills
    import helm.state as st
    from helm.integrations import load_integrations

    (tmp_path / "project").mkdir()
    (tmp_path / "data").mkdir()
    fake_dir = tmp_path / "fake"
    bindir = fake_dir / "bin"
    bindir.mkdir(parents=True)
    for ai in AIS:
        f = bindir / ai
        f.write_text(FAKE_CLI.format(py=sys.executable))
        f.chmod(0o755)

    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("RAPR_FAKE_DIR", str(fake_dir))
    monkeypatch.setenv("RAPR_FAKE_LOG", str(fake_dir / "calls.jsonl"))
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("RAPR_LIVE_PROGRESS", "0")      # the blocking run, not streaming
    monkeypatch.setenv("AI_MAX_RETRIES", "1")
    monkeypatch.setenv("AI_AUTO_SWITCH", "0")
    monkeypatch.setenv("PIPELINE_AUTO_SUGGEST", "0")
    for key in list(os.environ):
        if key.startswith(("BUDGET_", "COMPUTER_USE", "GEMINI_API", "GOOGLE_API")):
            monkeypatch.delenv(key)

    # Fresh RAPR state. Other tests share this thread's database connection,
    # so it's put back afterwards rather than closed.
    monkeypatch.setattr(st, "sessions", {})
    monkeypatch.setattr(st, "focused_id", None)
    monkeypatch.setattr(st, "usage_stats", {})
    monkeypatch.setattr(st, "usage_exact", {})
    monkeypatch.setattr(st, "chat_history", [])
    monkeypatch.setattr(st, "integrations", {})
    tab = FakeTab()
    monkeypatch.setattr(st, "ws_clients", {tab})
    monkeypatch.setattr(skills, "_primary_skills_dir", tmp_path / "skills")
    # "Is this CLI installed?" answers are cached per process; the stand-ins are new.
    import importlib
    import helm.ai_runner.core as core
    webapp = importlib.import_module("helm.web_routes.app")   # the module, not the FastAPI app
    monkeypatch.setattr(webapp, "_find_cli_cache", {})
    monkeypatch.setattr(core, "_availability_cache", {})
    monkeypatch.setattr(db, "_init_done", False)
    previous = getattr(db._local, "conn", None)
    db._local.conn = None
    db.init_db()
    load_integrations()

    yield Rapr(tmp_path, tab)

    mine = db._local.conn
    if mine is not None and mine is not previous:
        mine.close()
    db._local.conn = previous
