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
