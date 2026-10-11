"""Codex models: only offer what your sign-in can use, and recover when Codex
refuses one.

A user signed in with ChatGPT had "gpt-5.4-mini" saved as their Codex model, and
every message failed with "The 'gpt-5.4-mini' model is not supported when using
Codex with a ChatGPT account." """
import asyncio
import base64
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def _jwt(claims: dict) -> str:
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b({'alg': 'none'})}.{b(claims)}.sig"


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (tmp_path / ".codex").mkdir()
    cache = {"models": [
        {"slug": "gpt-6-sol", "visibility": "list", "supported_in_api": True,
         "available_in_plans": ["plus", "pro"]},
        {"slug": "gpt-6-pro", "visibility": "list", "supported_in_api": True,
         "available_in_plans": ["pro"]},
        {"slug": "gpt-5.4-mini", "visibility": "list", "supported_in_api": True,
         "available_in_plans": []},
        {"slug": "codex-internal", "visibility": "hide", "supported_in_api": True},
        {"slug": "chatgpt-only", "visibility": "list", "supported_in_api": False,
         "available_in_plans": ["plus"]},
    ]}
    (tmp_path / ".codex" / "models_cache.json").write_text(json.dumps(cache))
    return tmp_path


def _sign_in(home, plan=None, api_key=False):
    if api_key:
        auth = {"OPENAI_API_KEY": "sk-test", "tokens": None}
    else:
        claims = {"https://api.openai.com/auth": {"chatgpt_plan_type": plan}} if plan else {}
        auth = {"tokens": {"id_token": _jwt(claims), "access_token": "x"}}
    (home / ".codex" / "auth.json").write_text(json.dumps(auth))


def test_chatgpt_plus_sees_only_its_plans_models(home):
    from helm.web_routes.helpers import codex_cached_models
    _sign_in(home, plan="plus")
    assert codex_cached_models() == ["gpt-6-sol", "chatgpt-only"]


def test_api_key_sees_api_models(home):
    from helm.web_routes.helpers import codex_cached_models
    _sign_in(home, api_key=True)
    assert codex_cached_models() == ["gpt-6-sol", "gpt-6-pro", "gpt-5.4-mini"]


def test_unknown_plan_is_not_filtered(home):
    from helm.web_routes.helpers import codex_cached_models
    _sign_in(home)
    assert "gpt-6-pro" in codex_cached_models()


def test_saved_model_the_plan_cant_use_is_skipped(home):
    from helm.session_mgr import codex_model_offered
    _sign_in(home, plan="plus")
    assert codex_model_offered("gpt-6-sol")
    assert not codex_model_offered("gpt-5.4-mini")


def test_no_cache_means_no_second_guessing(tmp_path, monkeypatch):
    from helm.session_mgr import codex_model_offered
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert codex_model_offered("anything")


FAKE_CODEX = '''#!{py}
import json, sys
sys.stdin.read()
if "--model" in sys.argv:
    sys.stderr.write('ERROR: {{"type":"error","status":400,"error":{{"type":"invalid_request_error",'
                     '"message":"The \\'gpt-5.4-mini\\' model is not supported when using Codex '
                     'with a ChatGPT account."}}}}\\n')
    sys.exit(1)
if "--json" in sys.argv:
    print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message", "text": "Hello from default"}}}}))
else:
    print("Hello from default")
'''


def test_rejected_model_is_dropped_and_the_message_retried(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("uses a #! script as a stand-in Codex")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    f = bindir / "codex"
    f.write_text(FAKE_CODEX.format(py=sys.executable))
    f.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    import helm.state as st
    from helm.db import init_db
    from helm.integrations import load_integrations
    from helm.model_prefs import get_model_pref, set_model_pref
    from helm.session_mgr import make_session
    from helm.ai_runner.core import process_message
    init_db()
    st.integrations.clear()
    load_integrations()
    set_model_pref("codex", "gpt-5.4-mini")
    sess = make_session("codex", cwd=str(tmp_path))
    assert sess["model"] == "gpt-5.4-mini"

    out = asyncio.run(asyncio.wait_for(process_message("Hi", session_id=sess["id"]), 60))
    assert "Hello from default" in out
    assert sess["model"] is None
    assert not get_model_pref("codex")


def test_skill_is_picked_from_the_users_words_not_the_safety_rule():
    """"Hi" got the file-organizer skill: the file-safety rule added in front of
    every message mentions files and folders."""
    import helm.skills as sk
    from helm.ai_runner.core import _SAFETY_PREAMBLE
    sk.reload_registry()
    if "file-organizer" not in sk._registry:
        pytest.skip("bundled skills not found")
    prompt = _SAFETY_PREAMBLE + "Hi"
    assert sk.detect_skill(prompt) == "file-organizer"          # the old behaviour
    assert sk.inject_skill_prefix(prompt, ai="codex", match_text="Hi") == prompt
    out = sk.inject_skill_prefix(_SAFETY_PREAMBLE + "organize files in my downloads folder",
                                 ai="codex", match_text="organize files in my downloads folder")
    assert "HQ SKILL: file-organizer" in out


def test_codex_config_stays_valid_toml_with_windows_paths(tmp_path, monkeypatch):
    """RAPR copies MCP servers into ~/.codex/config.toml. Unescaped Windows paths
    ("C:\\Users\\…") made the file invalid, which breaks Codex itself."""
    import tomllib
    from helm.mcp.manager import MCPManager
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    (tmp_path / ".codex").mkdir()
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.write_text('model = "gpt-6-sol"\n')
    m = MCPManager()
    servers = {"fs": {"command": r"C:\Users\me\AppData\Roaming\npm\npx.cmd",
                      "args": ["-y", r"C:\Users\me\Desktop"],
                      "env": {"TOKEN": 'a"b\\c', "ODD KEY": "x"}},
               "my.server": {"command": "uvx"}}
    monkeypatch.setattr(m, "_get_subprocess_servers", lambda: servers)
    m.sync_native_mcp_configs()
    m.sync_native_mcp_configs()                        # a second sync replaces, not duplicates
    data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    assert data["model"] == "gpt-6-sol"
    fs = data["mcp_servers"]["fs"]
    assert fs["command"] == r"C:\Users\me\AppData\Roaming\npm\npx.cmd"
    assert fs["args"] == ["-y", r"C:\Users\me\Desktop"]
    assert fs["env"] == {"TOKEN": 'a"b\\c', "ODD KEY": "x"}
    assert data["mcp_servers"]["my.server"]["command"] == "uvx"
