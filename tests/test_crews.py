"""Crews: group chats where each AI has a role."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.crews as crews
import helm.groupchat as gc
import helm.state as _st


def sess(sid, ai):
    return {"id": sid, "ai": ai, "name": f"{ai} #{sid}", "cwd": "/tmp", "model": None,
            "emoji": "🤖", "color": "#123"}


def test_every_crew_is_well_formed():
    ids = [c["id"] for c in crews.CREWS]
    assert len(ids) == len(set(ids))
    for c in crews.CREWS:
        assert len(c["roles"]) >= 2
        for r in c["roles"]:
            assert r["name"] and r["prompt"] and r["prefers"]


def test_roles_get_their_preferred_ai_when_available():
    crew = crews.get("code-review")
    pairs = crews.assign(crew, [sess("1", "gemini"), sess("2", "codex"), sess("3", "claude")])
    by_role = {r["name"]: s["ai"] for r, s in pairs}
    assert by_role["Author"] == "claude"
    assert by_role["Reviewer"] == "codex"
    assert by_role["Tester"] == "gemini"


def test_each_session_is_used_once_even_without_preferences():
    crew = crews.get("research")
    pairs = crews.assign(crew, [sess("1", "mystery"), sess("2", "other"), sess("3", "third")])
    assert len(pairs) == 3
    assert len({s["id"] for _, s in pairs}) == 3


def test_not_enough_sessions_is_explained():
    with pytest.raises(ValueError, match="needs 3 AI sessions"):
        crews.assign(crews.get("launch"), [sess("1", "claude")])


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(gc, "groups", {})
    monkeypatch.setattr(gc, "_loaded", True)
    monkeypatch.setattr(gc, "_store_path", lambda: tmp_path / "g.json")

    async def nobroadcast(ev):
        pass
    monkeypatch.setattr(gc, "_broadcast", nobroadcast)


def test_group_from_crew_carries_roles_into_prompts(env):
    crew = crews.get("launch")
    s = [sess("1", "claude"), sess("2", "gemini"), sess("3", "ollama")]
    pairs = crews.assign(crew, s)
    g = gc.make_group(crew["name"], crew["about"], [sess_ for _, sess_ in pairs],
                      roles=[(r["name"], r["prompt"]) for r, _ in pairs])
    member = g["members"][0]
    assert member["role"] == "Copywriter"
    prompt = gc.build_prompt(g, member)
    assert "Your role in this group: You write the announcement" in prompt


def test_plain_group_has_no_role_line(env):
    g = gc.make_group("Plain", "", [sess("1", "claude")])
    assert "Your role" not in gc.build_prompt(g, g["members"][0])


def test_crew_endpoint_creates_a_group(env, monkeypatch):
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    monkeypatch.setattr(_st, "sessions", {"1": sess("1", "claude"), "2": sess("2", "codex"),
                                          "3": sess("3", "gemini")}, raising=False)
    client = TestClient(webapp)
    r = client.post("/api/groups/from-crew", json={"crew_id": "code-review", "session_ids": ["1", "2", "3"]})
    assert r.status_code == 200, r.text
    g = r.json()["group"]
    assert g["name"] == "Code review"
    assert [m["role"] for m in g["members"]] == ["Author", "Reviewer", "Tester"]
    r = client.post("/api/groups/from-crew", json={"crew_id": "nope", "session_ids": ["1"]})
    assert "error" in r.json()
    r = client.post("/api/groups/from-crew", json={"crew_id": "launch", "session_ids": ["1"]})
    assert "needs 3 AI sessions" in r.json()["error"]
