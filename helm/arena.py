"""
helm/arena.py — Share a bake-off result on RAPR Arena (raprai.com/arena).

Nothing is sent unless you press Publish. What is sent is exactly what
`payload` returns, and the share dialog shows it to you first: which AIs took
part, how long each took, how many files and lines it changed, whether your
tests passed and which one you merged. Never your code, your folder or what
the AIs said. The task itself is only included if you tick the box, and you
can edit it first.

Published results go into a public leaderboard of which AI wins which kind of
task, and each one gets its own page you can link to.
"""

from __future__ import annotations

import os
import re

from helm.bakeoff import CATEGORIES

TASK_MAX = 280
_NAME = re.compile(r"[^A-Za-z0-9 ._:/+-]")


def arena_url() -> str:
    return (os.environ.get("ARENA_URL") or "https://www.raprai.com").rstrip("/")


def _name(value, limit: int = 60):
    if not value:
        return None
    return _NAME.sub("", str(value))[:limit] or None


def payload(result: dict, include_task: bool = False, task: str | None = None,
            category: str | None = None) -> dict:
    """The exact body sent to the Arena for a finished bake-off."""
    from helm.version import APP_VERSION
    body = {
        "app_version": APP_VERSION,
        "category": category if category in CATEGORIES else result["category"],
        "language": result.get("language"),
        "had_tests": bool(result.get("had_tests")),
        "winner": result.get("winner"),
        "attempts": [{
            "ai": _name(a["ai"], 40),
            "model": _name(a.get("model")),
            "seconds": a["seconds"],
            "files_changed": a["files_changed"],
            "lines_added": a["lines_added"],
            "lines_removed": a["lines_removed"],
            "tests_passed": a["tests_passed"],
            "failed": a["failed"],
            "winner": a["winner"],
        } for a in result["attempts"]],
    }
    if include_task:
        text = " ".join((task if task is not None else result["task"]).split())[:TASK_MAX]
        if text:
            body["task"] = text
    return body


def _secs(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}m{s % 60:02d}s" if s >= 60 else f"{s}s"


def share_text(result: dict, task: str | None = None, url: str | None = None) -> str:
    """A short post about the result, for copying anywhere. The task is only mentioned if given."""
    lines = ["🧪 AI bake-off on RAPR AI"]
    task = " ".join((task or "").split())
    if task:
        lines[0] += f': "{task[:120]}{"…" if len(task) > 120 else ""}"'
    ranked = sorted(result["attempts"], key=lambda a: (not a["winner"], a["failed"], a["seconds"]))
    for a in ranked:
        bits = ["failed" if a["failed"] else _secs(a["seconds"])]
        if not a["failed"]:
            bits.append(f'{a["files_changed"]} file{"s" if a["files_changed"] != 1 else ""}')
            if a["tests_passed"] is not None:
                bits.append("tests ✅" if a["tests_passed"] else "tests ❌")
        lines.append(f'{"🏆" if a["winner"] else "•"} {a["ai"]}: {" · ".join(bits)}')
    if not result.get("winner"):
        lines.append("No winner merged this time.")
    lines.append(url or "Run your own: https://raprai.com")
    return "\n".join(lines)


def publish(body: dict) -> dict:
    """Send a result to the Arena. Returns {"id", "url"}; raises RuntimeError with a readable reason."""
    import requests
    from helm.version import APP_VERSION
    try:
        r = requests.post(f"{arena_url()}/api/arena", json=body, timeout=20,
                          headers={"User-Agent": f"RAPR-AI/{APP_VERSION}"})
    except requests.RequestException as exc:
        raise RuntimeError(f"couldn't reach the Arena ({exc.__class__.__name__})") from exc
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code != 200 or not data.get("url"):
        raise RuntimeError(data.get("error") or f"the Arena answered {r.status_code}")
    return {"id": data.get("id"), "url": data["url"]}
