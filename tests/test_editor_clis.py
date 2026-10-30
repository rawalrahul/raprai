"""Claude Code and Codex that came only with a VS Code (or Cursor, Windsurf…) extension."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.editor_clis as ec

EXE = ".exe" if sys.platform == "win32" else ""


def make(home: Path, rel: str) -> Path:
    p = home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("")
    p.chmod(0o755)
    return p


def test_finds_the_newest_extension_copy(tmp_path):
    make(tmp_path, f".vscode/extensions/anthropic.claude-code-2.1.9-win32-x64/resources/native-binary/claude{EXE}")
    new = make(tmp_path, f".vscode/extensions/anthropic.claude-code-2.1.10-win32-x64/resources/native-binary/claude{EXE}")
    make(tmp_path, f".vscode/extensions/anthropic.claude-code-2.1.10-win32-x64/node_modules/x/claude{EXE}")
    assert ec.find_in_editors("claude", tmp_path) == new


def test_finds_codex_in_cursor_and_ignores_other_tools(tmp_path):
    codex = make(tmp_path, f".cursor/extensions/openai.chatgpt-26.5.1-linux-x64/bin/linux-x86_64/codex{EXE}")
    make(tmp_path, f".cursor/extensions/openai.chatgpt-26.5.1-linux-x64/bin/linux-x86_64/codex-helper{EXE}")
    assert ec.find_in_editors("codex", tmp_path) == codex
    assert ec.find_in_editors("claude", tmp_path) is None
    assert ec.find_in_editors("gemini", tmp_path) is None


def test_prefers_this_machines_build(tmp_path, monkeypatch):
    base = ".vscode/extensions/openai.chatgpt-26.5.1/bin"
    arm = make(tmp_path, f"{base}/macos-aarch64/codex{EXE}")
    intel = make(tmp_path, f"{base}/macos-x86_64/codex{EXE}")
    monkeypatch.setattr(ec.platform, "machine", lambda: "arm64")
    assert ec.find_in_editors("codex", tmp_path) == arm
    monkeypatch.setattr(ec.platform, "machine", lambda: "x86_64")
    assert ec.find_in_editors("codex", tmp_path) == intel


def test_add_to_path_only_when_not_installed(tmp_path, monkeypatch):
    claude = make(tmp_path, f".vscode/extensions/anthropic.claude-code-2.1.10/resources/native-binary/claude{EXE}")
    make(tmp_path, f".vscode/extensions/openai.chatgpt-26.5.1/bin/linux-x86_64/codex{EXE}")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(ec, "_on_path", lambda name: name == "codex")   # codex installed on its own
    assert ec.add_to_path(tmp_path) == {"claude": str(claude)}
    assert os.environ["PATH"].split(os.pathsep) == [str(tmp_path / "empty"), str(claude.parent)]


def test_no_editors_no_change(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/nowhere")
    monkeypatch.setattr(ec, "_on_path", lambda name: False)
    assert ec.add_to_path(tmp_path) == {}
    assert os.environ["PATH"] == "/nowhere"
