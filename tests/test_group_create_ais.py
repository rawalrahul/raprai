"""Creating a group by picking AIs: reuse an open session, or start one."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.groupchat as gc
import helm.state as _st


@pytest.fixture
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    import helm.session_mgr as sm
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "session_counter", 0, raising=False)
    monkeypatch.setattr(_st, "integrations", {"gemini": {"name": "Gemini", "emoji": "♊", "color": "#4af"}}, raising=False)
    monkeypatch.setattr(sm, "get_history_messages", lambda pid: [])
    monkeypatch.setattr(sm, "save_cwd_to_log", lambda *a, **k: None)
    monkeypatch.setattr(sm, "TerminalSession", lambda: object())
    monkeypatch.setattr(gc, "groups", {})
    monkeypatch.setattr(gc, "_loaded", True)
    monkeypatch.setattr(gc, "_store_path", lambda: tmp_path / "g.json")
    return TestClient(webapp)


def test_picking_ais_starts_sessions(client):
    r = client.post("/api/groups", json={"name": "Duo", "member_ais": ["claude", "gemini"]})
    assert r.status_code == 200, r.text
    g = r.json()["group"]
    assert [m["ai"] for m in g["members"]] == ["claude", "gemini"]
    assert len(_st.sessions) == 2                 # one session started per AI


def test_open_session_is_reused(client):
    import helm.session_mgr as sm
    existing = sm.make_session("gemini", cwd="/tmp")
    r = client.post("/api/groups", json={"member_ais": ["gemini"]})
    assert r.json()["group"]["members"][0]["session_id"] == existing["id"]
    assert len(_st.sessions) == 1


def test_unknown_ai_is_refused(client):
    r = client.post("/api/groups", json={"member_ais": ["nonsense"]})
    assert r.status_code == 400 and "isn't installed" in r.json()["error"]
    assert _st.sessions == {}


def test_nothing_picked(client):
    r = client.post("/api/groups", json={"name": "x"})
    assert r.status_code == 400 and "Pick at least one AI" in r.json()["error"]


def test_crew_from_ais_and_too_few_is_refused_before_starting_anything(client):
    r = client.post("/api/groups/from-crew", json={"crew_id": "code-review", "member_ais": ["claude"]})
    assert r.status_code == 400 and "needs 3 AIs" in r.json()["error"]
    assert _st.sessions == {}
    _st.integrations["codex"] = {"name": "Codex", "emoji": "🧠", "color": "#0a0"}
    r = client.post("/api/groups/from-crew", json={"crew_id": "code-review", "member_ais": ["claude", "codex", "gemini"]})
    assert r.status_code == 200, r.text
    roles = {m["role"]: m["ai"] for m in r.json()["group"]["members"]}
    assert roles == {"Author": "claude", "Reviewer": "codex", "Tester": "gemini"}
