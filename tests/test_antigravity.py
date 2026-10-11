"""Antigravity (agy), Google's replacement for the Gemini CLI on personal accounts.

Checked against agy 1.3.3 on Windows: `agy -p "say hi"` answers and exits; agy
does not read a piped prompt (it tried to run a tool for it instead); `agy models`
prints "<id>   <label>" lines; --output-format stream-json prints events keyed
by "event". The fake agy below replays that real output.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Real `agy -p "say hi" --output-format stream-json` output (tools list trimmed).
REAL_STREAM = [
    {"event": "init", "conversation_id": "a55c", "init": {"cwd": "C:\\\\x", "tools": ["view_file"],
                                                          "permission_mode": "request-review"}},
    {"event": "step_update", "step_update": {"conversation_id": "a55c", "step_index": 0,
                                             "state": "DONE", "step_type": "user_input"}},
    {"event": "step_update", "step_update": {"conversation_id": "a55c", "step_index": 1,
                                             "state": "ACTIVE", "step_type": "agent_response",
                                             "text_delta": "Hi! How can I help you today?"}},
    {"event": "step_update", "step_update": {"conversation_id": "a55c", "step_index": 1,
                                             "state": "DONE", "step_type": "agent_response",
                                             "text_delta": "\n"}},
    {"event": "result", "result": {"conversation_id": "a55c", "status": "SUCCESS",
                                   "response": "Hi! How can I help you today?\n", "num_turns": 1}},
]

FAKE_AGY = '''#!{py}
import json, sys
args = sys.argv[1:]
open({log!r}, "a").write(json.dumps(args) + "\\n")
if args[:1] == ["models"]:
    print("gemini-3.8-flash-high     Gemini 3.8 Flash (High)")
    print("gemini-3.1-pro-high       Gemini 3.1 Pro (High)")
    print("claude-sonnet-4-6         Claude Sonnet 4.6 (Thinking)")
    sys.exit(0)
prompt = args[args.index("-p") + 1]
if "--output-format" in args:
    for ev in {stream!r}:
        print(json.dumps(ev))
else:
    print("agy says: " + prompt[:40])
'''


@pytest.fixture
def fake_agy(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("uses a #! script as the fake agy")
    log = tmp_path / "argv.log"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    agy = bindir / "agy"
    agy.write_text(FAKE_AGY.format(py=sys.executable, log=str(log), stream=REAL_STREAM))
    agy.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("AGY_APPROVAL_FLAG", raising=False)
    return agy, log


def test_prompt_goes_on_the_command_line(fake_agy):
    agy, _ = fake_agy
    from integrations import antigravity as ag
    assert ag.STDIN_PROMPT is False
    cmd = ag.build_command("say hi", model="gemini-3.1-pro-high")
    assert cmd[0] == str(agy)
    assert cmd[cmd.index("-p") + 1] == "say hi"
    assert cmd[cmd.index("--model") + 1] == "gemini-3.1-pro-high"
    assert "--dangerously-skip-permissions" in cmd
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert out.stdout.strip() == "agy says: say hi"


def test_long_prompt_is_passed_as_a_file(fake_agy):
    from integrations import antigravity as ag
    long = "x" * (ag._MAX_ARG_PROMPT + 10)
    cmd = ag.build_command(long)
    short = cmd[cmd.index("-p") + 1]
    assert len(short) < 500
    path = short.split("in the file ", 1)[1].split(" (", 1)[0]
    assert open(path, encoding="utf-8").read() == long
    assert cmd[cmd.index("--add-dir") + 1] == os.path.dirname(path)
    os.remove(path)


def test_stream_reader_understands_agy(fake_agy):
    from helm.ai_runner.streaming import run_agy_stream
    from integrations import antigravity as ag
    events = []
    sess = {}
    text = run_agy_stream(ag.build_command("say hi"), os.getcwd(), sess, events.append, timeout=30)
    assert text == "Hi! How can I help you today?"
    assert events[-1] == {"phase": "done"}


def test_models_come_from_agy(fake_agy, monkeypatch):
    import helm.state as st
    from helm.web_routes import helpers
    from integrations import antigravity as ag
    monkeypatch.setitem(st.integrations, "antigravity", {"build_command": ag.build_command})
    assert helpers._fetch_antigravity_models() == [
        "gemini-3.8-flash-high", "gemini-3.1-pro-high", "claude-sonnet-4-6"]


def test_gemini_is_hidden_unless_its_cli_is_installed(tmp_path, monkeypatch):
    """New installs offer Antigravity; Gemini appears only where its CLI exists."""
    import helm.state as st
    import importlib
    from helm import integrations
    webapp = importlib.import_module("helm.web_routes.app")   # the module, not the FastAPI app
    monkeypatch.setattr(st, "integrations", {})
    monkeypatch.setattr(webapp, "_find_cli", lambda name: False)
    integrations.load_integrations()
    assert "gemini" not in st.integrations
    assert "antigravity" in st.integrations
    monkeypatch.setattr(webapp, "_find_cli", lambda name: name == "gemini")
    st.integrations.clear()
    integrations.load_integrations()
    assert "gemini" in st.integrations


def test_setup_wizard_offers_antigravity_not_gemini():
    from helm.setup_wizard import _SETUP_HTML
    assert "Antigravity" in _SETUP_HTML and "checkAntigravity" in _SETUP_HTML
    assert "npm install -g @google/gemini-cli" not in _SETUP_HTML
    assert "GEMINI_API_KEY" not in _SETUP_HTML
