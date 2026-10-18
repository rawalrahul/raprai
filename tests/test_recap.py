"""Monthly recap: worked out locally from chat history, group chats and bake-offs."""
import json
import os
import sqlite3
import sys
from datetime import date, datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.bakeoff_history as history
import helm.recap as recap
from helm.db import _SCHEMA_SQL
from helm.db_migrate import v12_add_bakeoff_results


@pytest.fixture
def db(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA_SQL)
    v12_add_bakeoff_results(conn)
    monkeypatch.setattr(recap, "_db", lambda: conn)
    monkeypatch.setattr(history, "_db", lambda: conn)
    monkeypatch.setattr(recap, "_groups", lambda: [])
    monkeypatch.setattr(recap, "_label", lambda ai: ai.title())
    return conn


def msg(conn, when, role, ai=None, content="x" * 400, session="s1", project="p1", source=None):
    conn.execute(
        "INSERT INTO messages (history_id, type, role, content, ai, session_id, timestamp, extra) VALUES (?, 'message', ?, ?, ?, ?, ?, ?)",
        (project, role, content, ai, session, when, json.dumps({"source": source}) if source else None))


def test_empty_month(db):
    r = recap.build("2026-09")
    assert r["empty"] and r["mvp"] is None and r["month_label"] == "September 2026"


def test_counts_streaks_and_the_mvp(db):
    for day in (3, 4, 5, 9):
        msg(db, f"2026-10-{day:02d}T23:15:00", "user", session="s1")
        msg(db, f"2026-10-{day:02d}T23:16:00", "assistant", ai="claude", session="s1")
    msg(db, "2026-10-09T23:20:00", "user", session="s2", source="telegram", project="p2")
    msg(db, "2026-10-09T23:21:00", "assistant", ai="codex", session="s2", project="p2")
    msg(db, "2026-10-09T23:22:00", "assistant", ai="shell", session="s2")
    msg(db, "2026-11-01T10:00:00", "user")   # next month: not counted
    r = recap.build("2026-10")
    assert r["messages_sent"] == 5 and r["replies"] == 5
    assert r["mvp"]["ai"] == "claude" and r["mvp"]["replies"] == 4
    assert r["active_days"] == 4 and r["longest_streak"] == 3
    assert r["busiest_day"]["date"] == "2026-10-09" and r["top_hour"] == 23
    assert r["projects"] == 2 and r["from_chat_apps"] == 1
    assert r["api_value_usd"] > 0 and r["saved_usd"] == 0
    assert r["persona"] == "Night Owl"


def test_local_ai_work_counts_as_saved(db):
    for i in range(3):
        msg(db, f"2026-10-0{i + 1}T10:00:00", "user", session="o", content="y" * 4000)
        msg(db, f"2026-10-0{i + 1}T10:01:00", "assistant", ai="ollama", session="o", content="z" * 4000)
    r = recap.build("2026-10")
    assert r["free_share"] == 1.0 and r["saved_usd"] > 0 and r["api_value_usd"] == 0
    assert r["persona"] == "Local Hero" and r["ais"][0]["free"]


def test_group_chats_and_bakeoffs_are_included(db, monkeypatch):
    ts = datetime(2026, 10, 12, 8, 0).timestamp()
    monkeypatch.setattr(recap, "_groups", lambda: [{"messages": [
        {"role": "user", "content": "hi", "timestamp": ts, "source": "whatsapp"},
        {"role": "member", "author_ai": "gemini", "content": "hello", "timestamp": ts + 5},
        {"role": "member", "author_ai": "claude", "content": "hey", "timestamp": ts + 9},
    ]}])
    for i, winner in enumerate(["codex", "codex", "claude"]):
        history.save({"id": f"b{i}", "created_at": ts + i, "status": "merged", "winner": winner, "attempts": []})
    r = recap.build("2026-10")
    assert r["group_chats"] == 1 and r["group_messages"] == 3 and r["from_chat_apps"] == 1
    assert r["bakeoffs"] == 3 and r["bakeoff_wins"] == {"codex": 2, "claude": 1}
    assert r["persona"] == "The Judge"
    assert recap.first_month() is None


def test_month_bounds():
    assert recap.month_bounds("2026-12") == (date(2026, 12, 1), date(2027, 1, 1))
    assert recap.month_bounds(None)[0] == date.today().replace(day=1)


def test_route_checks_the_month(db):
    from fastapi.testclient import TestClient
    from helm.web_routes import app as webapp
    client = TestClient(webapp)
    assert client.get("/api/recap?month=2026-13").status_code == 400
    msg(db, "2026-10-03T10:00:00", "user")
    d = client.get("/api/recap?month=2026-10").json()
    assert d["messages_sent"] == 1 and d["first_month"] == "2026-10"
