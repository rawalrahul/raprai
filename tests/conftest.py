"""Fixtures shared by the tests in this folder."""
from core_harness import rapr  # noqa: F401  (a RAPR to send messages through)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _mcp_usage_in_tmp(tmp_path, monkeypatch):
    """AIs run in tests count toward a throwaway usage file, not ~/.config/rapr (helm/mcp_usage.py)."""
    monkeypatch.setenv("RAPR_MCP_USAGE_FILE", str(tmp_path / "mcp-usage.json"))
    monkeypatch.setenv("RAPR_USAGE_READERS", "0")   # no asking real AI accounts for their usage
    monkeypatch.setenv("RAPR_CONFIG_DIR", str(tmp_path / "rapr-config"))   # no real RAPR Bridge
    import helm.vscode_bridge as _vb
    monkeypatch.setattr(_vb, "_found_cache", (0.0, None))      # each test looks for Copilot afresh
    # Run from a VS Code terminal or not, the tests see the same: not under VS Code.
    for var in ("TERM_PROGRAM", "CLAUDE_CODE_ENTRYPOINT", "VSCODE_PID", "VSCODE_IPC_HOOK",
                "VSCODE_IPC_HOOK_CLI", "VSCODE_AGENT_FOLDER", "VSCODE_CWD"):
        monkeypatch.delenv(var, raising=False)


# --- A stand-in for the RAPR Bridge extension (helm/vscode_bridge), shared by the tests ---------
import json as _json  # noqa: E402
import threading as _threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402

BRIDGE_KEY = "k" * 64


@pytest.fixture
def bridge():
    """A stand-in for the extension: same file, same key check, same answers."""
    seen = []
    # script: Copilot's reply to each request, given the request (an agent run: tool calls, then text).
    state = {"status": 200, "version": "0.2.0", "script": None,
             "reply": {"text": "Looks good to me.", "toolCalls": [], "model": {"id": "gpt-4.1"}}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, body):
            data = _json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self):
            return self.headers.get("Authorization") == f"Bearer {BRIDGE_KEY}"

        def do_GET(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized", "message": "Wrong or missing key."})
            if self.path == "/health":
                return self._send(200, {"ok": True, "version": state["version"], "features": ["chat", "tools"]})
            if self.path == "/models":
                return self._send(200, {"models": [{"id": "gpt-4.1", "family": "gpt-4.1"}]})
            self._send(404, {})

        def do_POST(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized", "message": "Wrong or missing key."})
            body = _json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            if state["status"] != 200:
                return self._send(state["status"], {"error": "no_permission", "message":
                                  'VS Code hasn\'t allowed RAPR Bridge to use Copilot yet. In VS Code, run '
                                  '"RAPR: Connect Copilot" (Ctrl+Shift+P) and press Allow.'})
            self._send(200, state["script"](body) if state["script"] else state["reply"])

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    _threading.Thread(target=server.serve_forever, daemon=True).start()
    _vb_config_dir().mkdir(parents=True, exist_ok=True)
    _vb_bridge_file().write_text(_json.dumps({"port": server.server_address[1], "key": BRIDGE_KEY, "pid": 1}))
    yield {"seen": seen, "state": state}
    server.shutdown()




def _vb_config_dir():
    from helm import vscode_bridge
    return vscode_bridge.config_dir()


def _vb_bridge_file():
    from helm import vscode_bridge
    return vscode_bridge.bridge_file()
