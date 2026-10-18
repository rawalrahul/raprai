"""
helm/bakeoff_history.py — Finished bake-offs, kept so they can be shared later
and counted in the monthly recap.

Only the result is kept (see bakeoff.result): who took part, how long each
took, how much it changed, whether the tests passed and which one you merged.
The diffs and the AIs' output are not.
"""

from __future__ import annotations

import json
from typing import Optional


def _db():
    from helm.db import get_db
    return get_db()


def save(result: dict) -> None:
    """Insert or update a bake-off's result, keeping its Arena link if it has one."""
    db = _db()
    db.execute(
        """INSERT INTO bakeoff_results (id, created_at, status, winner_ai, result_json)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET status = excluded.status,
               winner_ai = excluded.winner_ai, result_json = excluded.result_json""",
        (result["id"], result["created_at"], result["status"], result.get("winner"),
         json.dumps(result, ensure_ascii=False)),
    )
    db.commit()


def _row(row) -> dict:
    d = json.loads(row["result_json"])
    d["arena_url"] = row["arena_url"]
    return d


def get(bid: str) -> Optional[dict]:
    row = _db().execute("SELECT * FROM bakeoff_results WHERE id = ?", (bid,)).fetchone()
    return _row(row) if row else None


def recent(limit: int = 20) -> list[dict]:
    rows = _db().execute("SELECT * FROM bakeoff_results ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def between(start: float, end: float) -> list[dict]:
    rows = _db().execute(
        "SELECT * FROM bakeoff_results WHERE created_at >= ? AND created_at < ? ORDER BY created_at",
        (start, end)).fetchall()
    return [_row(r) for r in rows]


def set_arena_url(bid: str, url: str) -> None:
    db = _db()
    db.execute("UPDATE bakeoff_results SET arena_url = ? WHERE id = ?", (url, bid))
    db.commit()
