"""Sharing a bake-off: results are kept without code, and Publish sends only what the preview shows."""
import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.arena as arena
import helm.bakeoff as bo
import helm.bakeoff_history as history
from helm.db_migrate import v12_add_bakeoff_results


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def db(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    v12_add_bakeoff_results(conn)
    monkeypatch.setattr(history, "_db", lambda: conn)
    return conn


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "proj"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "t")
    (r / "app.py").write_text("def add(a, b):\n    return a - b\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    return r


def finished(repo, tmp_path, task="fix the add bug in app.py"):
    b = bo.create(str(repo), task, ["claude", "codex"], test_command="python -c 'import app; assert app.add(1,2)==3'",
                  root=str(tmp_path / "work"))

    async def runner(ai, prompt, cwd):
        Path(cwd, "app.py").write_text("def add(a, b):\n    return a + b\n" if ai == "claude" else "x = 1\n")
        return "SECRET OUTPUT"
    asyncio.run(bo.run(b, runner))
    return b


def test_result_has_numbers_not_code(repo, tmp_path):
    b = finished(repo, tmp_path)
    bo.merge(b, [a.ai for a in b.attempts].index("claude"))
    r = bo.result(b)
    assert r["winner"] == "claude" and r["status"] == "merged"
    assert r["category"] == "bug fix" and r["language"] == "Python" and r["had_tests"]
    claude = next(a for a in r["attempts"] if a["ai"] == "claude")
    assert claude["winner"] and claude["tests_passed"] and claude["lines_added"] == 1 and claude["lines_removed"] == 1
    dumped = json.dumps(r)
    assert "return a + b" not in dumped and "SECRET OUTPUT" not in dumped and str(repo) not in dumped


def test_payload_leaves_out_the_task_unless_asked(repo, tmp_path):
    b = finished(repo, tmp_path)
    bo.merge(b, 0)
    r = bo.result(b)
    assert "task" not in arena.payload(r)
    p = arena.payload(r, include_task=True, task="  Fix   the bug  ", category="refactor")
    assert p["task"] == "Fix the bug" and p["category"] == "refactor"
    assert arena.payload(r, category="nonsense")["category"] == "bug fix"
    assert len(arena.payload(r, include_task=True, task="x" * 1000)["task"]) == arena.TASK_MAX
    assert set(p) == {"app_version", "category", "language", "had_tests", "winner", "attempts", "task"}


def test_share_text_puts_the_winner_first(repo, tmp_path):
    b = finished(repo, tmp_path)
    bo.merge(b, [a.ai for a in b.attempts].index("codex"))
    text = arena.share_text(bo.result(b))
    lines = text.splitlines()
    assert lines[1].startswith("🏆 codex") and "tests ❌" in lines[1]
    assert "fix the add bug" not in text
    assert "fix the add bug" in arena.share_text(bo.result(b), task="fix the add bug")


@pytest.mark.parametrize("task,category", [
    ("Fix the login crash", "bug fix"), ("Add a /health endpoint", "feature"),
    ("Refactor the router", "refactor"), ("Write pytest tests for utils", "tests"),
    ("Update the README", "docs"), ("hmm", "other"),
])
def test_guess_category(task, category):
    assert bo.guess_category(task) == category


def test_history_round_trip(db, repo, tmp_path):
    b = finished(repo, tmp_path)
    history.save(bo.result(b))
    bo.merge(b, 0)
    history.save(bo.result(b))
    history.set_arena_url(b.id, "https://www.raprai.com/arena/r/abc")
    got = history.get(b.id)
    assert got["status"] == "merged" and got["arena_url"].endswith("/abc")
    history.save(bo.result(b))   # saving again keeps the link
    assert history.get(b.id)["arena_url"].endswith("/abc")
    assert [r["id"] for r in history.recent()] == [b.id]
    assert history.between(b.created_at - 1, b.created_at + 1) and not history.between(0, 1)


def test_discarding_midway_is_not_reported_as_done(repo, tmp_path):
    b = bo.create(str(repo), "x", ["claude", "codex"], root=str(tmp_path / "work"))

    async def runner(ai, prompt, cwd):
        b.status = "discarded"
        return "ok"
    asyncio.run(bo.run(b, runner))
    assert b.status == "discarded"
    bo.cleanup(b)


def test_share_and_publish_routes(db, repo, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    import helm.web_routes.bakeoff_routes as routes

    async def runner(ai, prompt, cwd):
        Path(cwd, "app.py").write_text(f"# {ai}\n")
        return "ok"
    monkeypatch.setattr(routes, "_runner", lambda: runner)
    real_create = bo.create
    monkeypatch.setattr(bo, "create", lambda repo, task, ais, test_command=None: real_create(repo, task, ais, test_command=test_command, root=str(tmp_path / "w")))
    sent = []

    def fake_publish(body):
        sent.append(body)
        return {"id": "abc123", "url": "https://www.raprai.com/arena/r/abc123"}
    monkeypatch.setattr(arena, "publish", fake_publish)

    client = TestClient(webapp)
    bid = client.post("/api/bakeoff", json={"repo": str(repo), "task": "add logging", "ais": ["claude", "codex"]}).json()["id"]
    for _ in range(50):
        if client.get(f"/api/bakeoff/{bid}").json()["status"] == "done":
            break
        time.sleep(0.1)
    assert history.get(bid)["status"] == "done"   # kept as soon as it finishes

    share = client.get(f"/api/bakeoff/{bid}/share").json()
    assert share["can_publish"] is False
    assert client.post(f"/api/bakeoff/{bid}/publish", json={}).status_code == 400

    client.post(f"/api/bakeoff/{bid}/merge", json={"attempt": 1})
    share = client.get(f"/api/bakeoff/{bid}/share", params={"include_task": 1, "task": "Add logs", "category": "feature"}).json()
    assert share["payload"]["task"] == "Add logs" and '"Add logs"' in share["text"]
    share = client.get(f"/api/bakeoff/{bid}/share").json()
    assert share["can_publish"] and share["result"]["winner"] == "codex" and "task" not in share["payload"]

    r = client.post(f"/api/bakeoff/{bid}/publish", json={"include_task": False}).json()
    assert r["url"].endswith("/abc123") and "abc123" in r["text"]
    assert sent == [share["payload"]]   # exactly what the preview showed
    again = client.post(f"/api/bakeoff/{bid}/publish", json={}).json()
    assert again["already"] and len(sent) == 1
    assert client.get("/api/bakeoffs").json()["bakeoffs"][0]["arena_url"].endswith("/abc123")


def test_publish_reports_a_readable_error(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(requests, "post", boom)
    with pytest.raises(RuntimeError, match="couldn't reach the Arena"):
        arena.publish({})
