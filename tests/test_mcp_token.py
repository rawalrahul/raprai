"""The token the AIs RAPR starts use to call /mcp/call and /mcp/gate.

It's made fresh at every start and never saved. Older .env files still hold a
saved one; if a reload put that back, every tool call and approval check from
an AI would be refused.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    import helm.auth as auth
    salt, hashed = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", hashed)
    (tmp_path / ".env").write_text(f"PIN_SALT={salt}\nPIN_HASH={hashed}\nMCP_BEARER_TOKEN=old-saved-token\n")
    import importlib
    app_module = importlib.import_module("helm.web_routes.app")
    from helm.web_routes import app as webapp
    return webapp, app_module


def test_a_saved_token_never_replaces_the_live_one(app_with_pin):
    _, app_module = app_with_pin
    app_module.reload_env()
    assert os.environ["MCP_BEARER_TOKEN"] == app_module.MCP_BEARER_TOKEN != "old-saved-token"


def test_an_ai_on_this_computer_reaches_the_gate_with_the_live_token(app_with_pin, monkeypatch):
    webapp, app_module = app_with_pin
    monkeypatch.setattr(app_module, "_is_localhost", lambda request: True)   # TestClient isn't 127.0.0.1
    local = TestClient(webapp)
    body = {"tool_name": "mcp__github__list_issues", "tool_input": {}, "session_id": "-"}
    ok = local.post("/mcp/gate", json=body, headers={"Authorization": f"Bearer {app_module.MCP_BEARER_TOKEN}"})
    assert ok.status_code == 200 and ok.json()["allowed"] is True
    stale = local.post("/mcp/gate", json=body, headers={"Authorization": "Bearer old-saved-token"})
    assert stale.status_code == 401


def test_browser_control_is_gone(app_with_pin):
    webapp, _ = app_with_pin
    assert "/ws/chrome" not in {getattr(r, "path", "") for r in webapp.routes}
