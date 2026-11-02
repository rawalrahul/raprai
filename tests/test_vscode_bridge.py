"""Copilot through VS Code's sign-in, by way of the RAPR Bridge extension (helm/vscode_bridge)."""
import json
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.mcp_server as mcp
from helm import vscode_bridge as vb

ROOT = Path(__file__).resolve().parent.parent
KEY = "k" * 64


@pytest.fixture
def bridge():
    """A stand-in for the extension: same file, same key check, same answers."""
    seen = []
    state = {"status": 200, "reply": {"text": "Looks good to me.", "model": {"id": "gpt-4.1"}}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self):
            return self.headers.get("Authorization") == f"Bearer {KEY}"

        def do_GET(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized", "message": "Wrong or missing key."})
            if self.path == "/health":
                return self._send(200, {"ok": True, "version": "0.1.0"})
            if self.path == "/models":
                return self._send(200, {"models": [{"id": "gpt-4.1", "family": "gpt-4.1"}]})
            self._send(404, {})

        def do_POST(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized", "message": "Wrong or missing key."})
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body)
            if state["status"] != 200:
                return self._send(state["status"], {"error": "no_permission", "message":
                                  'VS Code hasn\'t allowed RAPR Bridge to use Copilot yet. In VS Code, run '
                                  '"RAPR: Connect Copilot" (Ctrl+Shift+P) and press Allow.'})
            self._send(200, state["reply"])

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    vb.config_dir().mkdir(parents=True, exist_ok=True)
    vb.bridge_file().write_text(json.dumps({"port": server.server_address[1], "key": KEY, "pid": 1}))
    yield {"seen": seen, "state": state}
    server.shutdown()


def test_asks_copilot_through_the_bridge(bridge):
    assert vb.healthy() and vb.models()[0]["id"] == "gpt-4.1"
    assert vb.ask("Review this", model="gpt-4.1") == "Looks good to me."
    assert bridge["seen"] == [{"prompt": "Review this", "model": "gpt-4.1"}]


def test_without_vscode_it_says_what_to_do():
    assert not vb.healthy()
    with pytest.raises(vb.BridgeError, match="open VS Code"):
        vb.ask("hi")


def test_a_refusal_comes_back_in_the_bridges_words(bridge):
    bridge["state"]["status"] = 403
    with pytest.raises(vb.BridgeError, match="RAPR: Connect Copilot"):
        vb.ask("hi")


def test_the_helper_rapr_runs_prints_the_answer_or_the_reason(bridge):
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-m", "helm.ai_runner._vscode_bridge_cli"], input="Review this",
                       capture_output=True, text=True, env=env, cwd=ROOT, timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == "Looks good to me."
    bridge["state"]["status"] = 403
    r = subprocess.run([sys.executable, "-m", "helm.ai_runner._vscode_bridge_cli"], input="x",
                       capture_output=True, text=True, env=env, cwd=ROOT, timeout=30)
    assert r.returncode == 1 and r.stderr.startswith("(error: VS Code hasn't allowed")


def test_the_integration_shows_only_with_copilot_in_vscode(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("copilot_vscode", ROOT / "integrations" / "copilot_vscode.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert not mod.SHOW() and not mod.READY() and mod.ANSWERS_ONLY
    (tmp_path / ".vscode" / "extensions" / "github.copilot-chat-0.40.0").mkdir(parents=True)
    assert mod.SHOW()
    assert mod.build_command("x", model="gpt-4.1")[1:] == ["-m", "helm.ai_runner._vscode_bridge_cli", "--model", "gpt-4.1"]


def test_roles_that_edit_files_refuse_it(monkeypatch):
    import helm.state as _st
    monkeypatch.setattr(mcp, "agents", lambda: {"copilot_vscode": "Copilot (VS Code)", "codex": "Codex"})
    monkeypatch.setitem(_st.integrations, "copilot_vscode", {"answers_only": True})
    s = mcp.Server(out=None)

    def err(tool, **args):
        out = s.call_tool(tool, args)
        return out.get("isError"), out["content"][0]["text"]
    for tool, args in [("start_bakeoff", {"task": "t", "agents": ["copilot_vscode", "codex"]}),
                       ("start_relay", {"task": "t", "executor": "copilot_vscode", "reviewer": "codex"}),
                       ("start_relay", {"task": "t", "executor": "codex", "fixer": "copilot_vscode", "reviewer": "codex"}),
                       ("start_team", {"parts": [{"agent": "copilot_vscode", "task": "t"}]}),
                       ("ask_agent", {"agent": "copilot_vscode", "prompt": "p", "allow_edits": True})]:
        is_err, text = err(tool, **args)
        assert is_err and "can't edit files" in text, (tool, text)
    mcp._check_agent("copilot_vscode")      # answering is fine: second_opinion, ask_agent, planner, reviewer


def test_connect_installs_the_bridge_into_vscode(monkeypatch, tmp_path):
    ran = []
    monkeypatch.setattr(vb, "copilot_in_vscode", lambda: True)
    monkeypatch.setattr(vb, "installed", lambda: False)
    monkeypatch.setattr(vb, "code_cli", lambda: "/usr/bin/code")
    monkeypatch.setattr(vb.subprocess, "run", lambda cmd, **k: ran.append(cmd) or subprocess.CompletedProcess(cmd, 0, "ok", ""))
    text = mcp.Server(out=None).call_tool("connect_vscode_copilot", {})["content"][0]["text"]
    assert ran == [["/usr/bin/code", "--install-extension", str(vb.vsix_path()), "--force"]]
    assert "Installed the RAPR Bridge 0.1.0" in text and "RAPR: Connect Copilot" in text and "Reload Window" in text


def test_connect_without_the_code_command_says_how(monkeypatch):
    monkeypatch.setattr(vb, "copilot_in_vscode", lambda: True)
    monkeypatch.setattr(vb, "installed", lambda: False)
    monkeypatch.setattr(vb, "code_cli", lambda: None)
    out = mcp.Server(out=None).call_tool("connect_vscode_copilot", {})
    assert out["isError"] and "Install from VSIX" in out["content"][0]["text"]


def test_list_agents_offers_vscode_copilot_not_only_the_cli(monkeypatch):
    monkeypatch.setattr(mcp, "agents", lambda: {"codex": "Codex"})
    monkeypatch.setattr(mcp, "signed_out", lambda: [])
    monkeypatch.setattr("helm.editor_clis.has_extension", lambda prefix, home=None: prefix == "github.copilot-chat-")
    monkeypatch.setattr(mcp, "_found", lambda exe: False)
    text = mcp.Server(out=None).call_tool("list_agents", {})["content"][0]["text"]
    assert "connect_vscode_copilot" in text and "your VS Code sign-in" in text


def test_the_packaged_bridge_is_the_source_in_the_repo():
    """helm/vscode_bridge/rapr-bridge.vsix must be rebuilt when vscode-bridge/ changes:
    cd vscode-bridge && npx @vscode/vsce package --no-dependencies -o ../helm/vscode_bridge/rapr-bridge.vsix"""
    with zipfile.ZipFile(vb.vsix_path()) as z:
        assert z.read("extension/extension.js").decode() == (ROOT / "vscode-bridge" / "extension.js").read_text()
        packed = json.loads(z.read("extension/package.json"))
    source = json.loads((ROOT / "vscode-bridge" / "package.json").read_text())
    assert {k: packed[k] for k in source} == source
    assert vb.bundled_version() == source["version"]


@pytest.mark.skipif(not shutil.which("node"), reason="needs Node.js")
def test_the_extension_itself():
    r = subprocess.run(["node", "--test", "vscode-bridge/test/bridge.test.js"], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


# --- Under VS Code, and VS Code connected to WSL ----------------------------------------------

from helm import editor_clis as ec  # noqa: E402


def _ext(root, name, version, binary):
    d = root / f"{name}{version}" / "bin"
    d.mkdir(parents=True)
    exe = d / binary
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    return exe


def test_knows_when_vscode_started_it():
    assert not ec.under_vscode({})
    assert ec.under_vscode({"TERM_PROGRAM": "vscode"})
    assert ec.under_vscode({"VSCODE_IPC_HOOK_CLI": "/tmp/vscode-ipc.sock"})
    assert ec.under_vscode({"CLAUDE_CODE_ENTRYPOINT": "claude-vscode"})


@pytest.mark.skipif(os.name == "nt", reason="POSIX paths")
def test_under_vscode_the_extensions_claude_goes_first(tmp_path, monkeypatch):
    own = tmp_path / "usr-bin"
    own.mkdir()
    (own / "claude").write_text("#!/bin/sh\n")
    (own / "claude").chmod(0o755)
    monkeypatch.setenv("PATH", str(own))
    exe = _ext(tmp_path / ".vscode" / "extensions", "anthropic.claude-code-", "2.1.300", "claude")
    assert ec.add_to_path(tmp_path, prefer=False) == {}                  # outside VS Code: the install wins
    assert ec.add_to_path(tmp_path, prefer=True)["claude"] == str(exe)  # under VS Code: the extension's
    assert shutil.which("claude") == str(exe)


@pytest.mark.skipif(os.name == "nt", reason="POSIX paths")
def test_in_a_wsl_window_vscode_servers_copy_wins(tmp_path):
    local = _ext(tmp_path / ".vscode" / "extensions", "anthropic.claude-code-", "2.1.400", "claude")
    server = _ext(tmp_path / ".vscode-server" / "extensions", "anthropic.claude-code-", "2.1.300", "claude")
    assert ec.find_in_editors("claude", tmp_path, env={}) == local      # newest, when nothing says where
    assert ec.find_in_editors("claude", tmp_path, env={"VSCODE_AGENT_FOLDER": str(tmp_path / ".vscode-server")}) == server


def test_copilot_installed_only_on_windows_is_seen_from_wsl(tmp_path, monkeypatch):
    win = tmp_path / "mnt" / "c" / "Users" / "me" / ".vscode" / "extensions"
    (win / "github.copilot-chat-0.40.0").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "wsl-home")
    assert not ec.has_extension("github.copilot-chat-")
    monkeypatch.setattr(ec, "_windows_extension_roots", lambda: [win])
    assert ec.has_extension("github.copilot-chat-")


@pytest.mark.skipif(os.name == "nt", reason="VS Code Server runs on Linux")
def test_in_wsl_the_bridge_installs_with_vscode_servers_cli(tmp_path, monkeypatch):
    agent = tmp_path / ".vscode-server"
    for layout in ("bin/abc123/bin/remote-cli/code", "bin/abc123/bin/code-server"):
        p = agent / layout
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/sh\n")
        p.chmod(0o755)
    env = {"VSCODE_AGENT_FOLDER": str(agent)}
    assert vb.code_cli(env).endswith("bin/abc123/bin/code-server")                 # no VS Code attached
    env["VSCODE_IPC_HOOK_CLI"] = "/tmp/vscode-ipc.sock"
    assert vb.code_cli(env).endswith("bin/abc123/bin/remote-cli/code")             # attached: its remote `code`
    # Newer VS Code Server layout
    new = tmp_path / "s2" / "cli" / "servers" / "Stable-def" / "server" / "bin" / "code-server"
    new.parent.mkdir(parents=True)
    new.write_text("#!/bin/sh\n")
    new.chmod(0o755)
    assert vb.code_cli({"VSCODE_AGENT_FOLDER": str(tmp_path / "s2")}) == str(new)


def test_in_wsl_windows_code_launcher_is_not_used(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)          # no ~/.vscode-server
    monkeypatch.setattr(ec, "is_wsl", lambda: True)
    monkeypatch.setattr(vb.shutil, "which", lambda n: "/mnt/c/Program Files/Microsoft VS Code/bin/code" if n == "code" else None)
    monkeypatch.setattr(vb.sys, "platform", "linux")
    assert vb.code_cli({}) is None
