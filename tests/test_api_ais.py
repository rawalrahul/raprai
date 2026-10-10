"""The API-based AIs (Groq, OpenRouter, GitHub Models, local servers) and session saving.

2.0.0 on a server: Groq answered "API 403 — error code: 1010" (Cloudflare refuses
requests without a User-Agent), GitHub Models failed with "Name or service not
known" (its old address was retired), and every save logged "Could not save last
state: Object of type Lock is not JSON serializable".
"""
import asyncio
import http.server
import json
import os
import sqlite3
import subprocess
import sys
import threading

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


@pytest.fixture
def fake_api():
    """A local OpenAI-style server that records each request's headers and body."""
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"path": self.path, "headers": dict(self.headers), "body": body})
            out = json.dumps({"choices": [{"message": {"content": "pong"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/v1", seen
    srv.shutdown()


def _run_cli(base_url, model="m", env_key="sk-test"):
    env = dict(os.environ, TEST_KEY=env_key)
    return subprocess.run(
        [sys.executable, "-m", "helm.ai_runner._openai_compat_cli",
         "--base-url", base_url, "--model", model, "--api-key-env", "TEST_KEY"],
        input="ping", capture_output=True, text=True, timeout=30, cwd=ROOT, env=env)


def test_api_request_has_a_user_agent(fake_api):
    url, seen = fake_api
    out = _run_cli(url)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "pong"
    h = {k.lower(): v for k, v in seen[0]["headers"].items()}
    assert seen[0]["path"] == "/v1/chat/completions"
    assert h["user-agent"].startswith("RAPR-AI/")
    assert "python-urllib" not in h["user-agent"].lower()
    assert h["authorization"] == "Bearer sk-test"
    assert seen[0]["body"]["messages"] == [{"role": "user", "content": "ping"}]


def test_github_models_uses_the_current_endpoint():
    from integrations import github_models as gm
    cmd = gm.build_command("hi")
    assert cmd[cmd.index("--base-url") + 1] == "https://models.github.ai/inference"
    assert cmd[cmd.index("--model") + 1] == "openai/gpt-4o-mini"
    # A model picked under its old short name still works.
    cmd = gm.build_command("hi", model="gpt-4o")
    assert cmd[cmd.index("--model") + 1] == "openai/gpt-4o"
    cmd = gm.build_command("hi", model="meta/Llama-3.3-70B-Instruct")
    assert cmd[cmd.index("--model") + 1] == "meta/Llama-3.3-70B-Instruct"
    assert "azure" not in " ".join(cmd)


def test_session_state_saves_with_a_lock_in_the_session(monkeypatch):
    import helm.db
    import helm.state as st
    from helm import history

    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE session_state (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
    monkeypatch.setattr(helm.db, "get_db", lambda: db)
    monkeypatch.setattr(st, "sessions", {
        "s1": {"ai": "groq", "cwd": "/tmp", "_lock": asyncio.Lock(),
               "extra": {"lock": threading.Lock()}},
    })
    warnings = []
    monkeypatch.setattr(history.logger, "warning", lambda *a: warnings.append(a))

    history.save_last_state()

    assert warnings == []
    saved = json.loads(db.execute(
        "SELECT value FROM session_state WHERE key='sessions'").fetchone()[0])
    assert saved == {"s1": {"ai": "groq", "cwd": "/tmp", "extra": {"lock": None}}}


@pytest.mark.skipif(sys.platform == "win32", reason="uses a #! launcher")
def test_open_interpreter_gets_the_whole_prompt(tmp_path, monkeypatch):
    """Open Interpreter has no --message option and its --stdin reads one line,
    so RAPR runs its Python API with the full prompt."""
    pkg = tmp_path / "site" / "interpreter"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "class _Llm: model = 'default'\n"
        "class _OI:\n"
        "    llm = _Llm(); auto_run = False\n"
        "    def chat(self, text, display=True):\n"
        "        return [{'role': 'user', 'type': 'message', 'content': text},\n"
        "                {'role': 'assistant', 'type': 'message',\n"
        "                 'content': f'{self.llm.model}|{self.auto_run}|{text!r}'}]\n"
        "interpreter = _OI()\n")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    launcher = bindir / "interpreter"
    launcher.write_text(f"#!{sys.executable}\nraise SystemExit('launcher should not run')\n")
    launcher.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])

    from integrations import open_interpreter as oi
    cmd = oi.build_command("ignored", model="gpt-4o")
    assert cmd[0] == sys.executable
    env = dict(os.environ, PYTHONPATH=str(tmp_path / "site"))
    out = subprocess.run(cmd, input="line one\nline two", capture_output=True,
                         text=True, timeout=30, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "gpt-4o|True|'line one\\nline two'"


def test_cli_ais_run_headless():
    from integrations import aider, amazon_q, cursor
    assert "--yes-always" in aider.build_command("p")
    q = amazon_q.build_command("do it")
    assert q[1:3] == ["chat", "--no-interactive"] and q[-1] == "do it"
    assert not amazon_q.STDIN_PROMPT
    c = cursor.build_command("do it", model="gpt-5")
    assert c[:2] == [c[0], "-p"] and "--trust" in c and c[-1] == "do it"
    assert c[c.index("--model") + 1] == "gpt-5"


def test_model_choice_is_saved_in_the_data_folder(tmp_path, monkeypatch):
    """/model for Claude, Codex and Gemini is kept in the user's data folder, so
    an app update (which replaces helm/config) doesn't forget it."""
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    from helm import model_prefs
    old = model_prefs._OLD_PREFS_PATH.read_text()
    model_prefs.set_model_pref("claude", "claude-haiku-4-5")
    assert model_prefs.get_model_pref("claude") == "claude-haiku-4-5"
    assert json.loads((tmp_path / "selected_models.json").read_text())["claude"] == "claude-haiku-4-5"
    assert model_prefs._OLD_PREFS_PATH.read_text() == old


def test_open_interpreter_in_rapr_python_counts_as_installed(monkeypatch):
    """Open Interpreter run through RAPR's own Python is a CLI, not an API key AI."""
    from helm.ai_runner import core
    import helm.state as st
    monkeypatch.setitem(st.integrations, "interpreter", {
        "build_command": lambda p, model=None: [sys.executable, "-c", "x", "", "1"],
        "env_vars": ["INTERPRETER_AUTO_FLAG"]})
    monkeypatch.delenv("INTERPRETER_AUTO_FLAG", raising=False)
    core._availability_cache.pop("interpreter", None)
    assert core.is_backend_available("interpreter")
    core._availability_cache.pop("interpreter", None)


@pytest.mark.skipif(sys.platform == "win32", reason="uses #! scripts as fake CLIs")
def test_model_lists_come_from_the_installed_clis(tmp_path, monkeypatch):
    """/model and Telegram's model picker list what the user's own Claude and
    Gemini CLIs accept, so new models show up when the CLIs update."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    claude = bindir / "claude"
    claude.write_text(
        "#!/bin/sh\n"
        "[ \"$1\" = --help ] || exit 1\n"
        "echo '  --model <model>     Model for the current session. Provide'\n"
        "echo \"                      an alias for the latest model (e.g. 'zeta', 'opus', or\"\n"
        "echo \"                      'sonnet') or a model's full name.\"\n")
    claude.chmod(0o755)
    bundle = tmp_path / "gemini-cli" / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "chunk.js").write_text(
        'var GEMINI_MODEL_ALIAS_AUTO = "auto";\nvar GEMINI_MODEL_ALIAS_ULTRA = "ultra";\n'
        'var GEMINI_MODEL_ALIAS_AUTO2 = "auto";\n')
    (bundle / "gemini.js").write_text("#!/usr/bin/env node\n")
    os.symlink(bundle / "gemini.js", bindir / "gemini")
    os.chmod(bundle / "gemini.js", 0o755)
    monkeypatch.setenv("PATH", str(bindir))
    monkeypatch.setenv("HOME", str(tmp_path))
    from helm.web_routes import helpers
    monkeypatch.setattr(helpers, "_npm_global_roots", lambda: [])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert helpers._fetch_claude_models()[:3] == ["zeta", "opus", "sonnet"]
    assert helpers._fetch_gemini_models() == ["auto", "ultra"]
    assert helpers._fetch_antigravity_models() == []   # agy isn't the gemini command
