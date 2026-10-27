"""Agent webhooks are called from outside RAPR, with no login.

The builder shows `POST <address>/api/agents/webhook/<token>`; the secret token
is the password. With a PIN set, the call used to be sent to /login instead.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient

import helm.state as _st


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    import helm.auth as auth
    salt, hashed = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", hashed)
    agent = {"id": "a1", "trigger": {"webhook": {"enabled": True, "token": "s3cret-token"}}}
    monkeypatch.setattr(_st, "agents", {"a1": agent})
    started = []

    async def fake_trigger(agent_id, trigger, input_data):
        started.append((agent_id, trigger, input_data))
        return {"id": "run-1"}
    import helm.web_routes.agent_routes as routes
    monkeypatch.setattr(routes, "trigger_agent_run", fake_trigger)
    routes._webhook_last_trigger.clear()
    from helm.web_routes import app as webapp
    return TestClient(webapp, follow_redirects=False), started


def test_the_right_token_starts_the_agent_without_a_login(client):
    c, started = client
    r = c.post("/api/agents/webhook/s3cret-token", content=b"new order #42")
    assert r.status_code == 200 and r.json() == {"ok": True, "run_id": "run-1"}
    assert started == [("a1", "webhook", "new order #42")]


def test_a_wrong_token_starts_nothing(client):
    c, started = client
    assert c.post("/api/agents/webhook/guess", content=b"x").status_code == 404
    assert started == []


def test_the_rest_of_the_agents_api_still_needs_a_login(client):
    c, _ = client
    r = c.get("/api/agents")
    assert r.status_code == 303 and r.headers["location"] == "/login"
