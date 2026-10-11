"""New AIs: Claude Code / Codex on local Ollama models, OpenCode, Droid, Qwen Code
and Copilot CLI. Their flags were read from each CLI's own --help (claude 2.1.296,
codex 0.162.1, opencode 1.19.0, droid 0.238.0, qwen 0.25.0, copilot 1.0.95), and
each was run against a stand-in server to confirm it reads a piped prompt.

Here a stand-in binary echoes its argv, its stdin and two env vars, and the
message goes through RAPR's real path (process_message)."""
import asyncio
import importlib
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

ECHO = '''#!{py}
import json, os, sys
print(json.dumps({{"argv": sys.argv[1:], "stdin": sys.stdin.read(),
                  "base": os.environ.get("ANTHROPIC_BASE_URL"),
                  "token": os.environ.get("ANTHROPIC_AUTH_TOKEN")}}))
'''

CASES = {
    # key: (binary, flags that must be there)
    "claude_ollama": ("claude", ["-p", "--model", "--dangerously-skip-permissions", "--settings"]),
    "codex_ollama":  ("codex", ["exec", "--oss", "--local-provider", "ollama", "--sandbox"]),
    "opencode":      ("opencode", ["run", "--auto"]),
    "droid":         ("droid", ["exec", "--auto", "medium"]),
    "qwen_code":     ("qwen", ["--yolo"]),
    "copilot":       ("copilot", ["--allow-all-tools", "-s"]),
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("uses #! scripts as stand-in CLIs")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for binary, _ in CASES.values():
        f = bindir / binary
        f.write_text(ECHO.format(py=sys.executable))
        f.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    return tmp_path


def _run(key, text, tmp_path, model=None):
    import helm.state as st
    from helm.db import init_db
    from helm.integrations import load_integrations
    from helm.session_mgr import make_session
    from helm.ai_runner.core import process_message
    init_db()
    st.integrations.clear()
    load_integrations()
    sess = make_session(key, cwd=str(tmp_path), model=model)
    return asyncio.run(asyncio.wait_for(process_message(text, session_id=sess["id"]), 60))


@pytest.mark.parametrize("key", list(CASES))
def test_prompt_and_flags_reach_the_cli(env, key):
    out = _run(key, "PINEAPPLE task", env)
    data = json.loads(out[out.index("{"):out.rindex("}") + 1])
    assert "PINEAPPLE task" in data["stdin"]            # prompt piped in, not on the command line
    assert not any("PINEAPPLE" in a for a in data["argv"])
    for flag in CASES[key][1]:
        assert flag in data["argv"], (key, flag, data["argv"])
    if key == "claude_ollama":
        assert data["base"] == "http://127.0.0.1:11434" and data["token"] == "ollama"
        assert data["argv"][data["argv"].index("--model") + 1] == "qwen3-coder"


def test_model_choice_is_passed(env):
    out = _run("codex_ollama", "hi", env, model="qwen3-coder:30b")
    data = json.loads(out[out.index("{"):out.rindex("}") + 1])
    assert data["argv"][data["argv"].index("-m") + 1] == "qwen3-coder:30b"


def test_claude_is_never_pointed_at_a_remote_ollama(monkeypatch):
    """Claude Code may send the user's Claude token to ANTHROPIC_BASE_URL."""
    monkeypatch.setenv("OLLAMA_HOST", "http://example.com:11434")
    import integrations.claude_ollama as co
    co = importlib.reload(co)
    assert co.PROCESS_ENV["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:11434"
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11500")
    co = importlib.reload(co)
    assert co.PROCESS_ENV["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:11500"


def test_claude_background_models_map_to_the_local_model(env):
    import integrations.claude_ollama as co
    cmd = co.build_command("x", model="qwen3-coder:30b")
    settings = json.loads(open(cmd[cmd.index("--settings") + 1]).read())
    assert set(settings["env"].values()) == {"qwen3-coder:30b"}
