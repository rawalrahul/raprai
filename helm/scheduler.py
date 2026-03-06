"""
helm/scheduler.py — Cron-based scheduled AI task runner.

Covers: natural_to_cron, next_cron_run, make_sched_task,
        load_scheduled_tasks, save_scheduled_tasks,
        run_scheduled_task, cron_runner, sched_tasks_payload.

Storage: SQLite `scheduled_tasks` table (via helm/db.py).
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional

import helm.state as _st
from helm.config import CHAT_LOG_DIR, CRONITER_OK, logger

if CRONITER_OK:
    from croniter import croniter as _Croniter

# ---------------------------------------------------------------------------
# Natural language → cron
# ---------------------------------------------------------------------------

def natural_to_cron(text: str) -> Optional[str]:
    """Convert natural language schedule description to a cron expression."""
    import re as _re
    t = text.strip().lower()

    _time_re = _re.compile(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?')
    m = _time_re.search(t)
    if not m:
        return None
    hour   = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm   = m.group(3)
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0

    _days = {
        "monday":0, "mon":0, "tuesday":1, "tue":1,
        "wednesday":2, "wed":2, "thursday":3, "thu":3,
        "friday":4, "fri":4, "saturday":5, "sat":5,
        "sunday":6, "sun":6,
    }

    if any(x in t for x in ("weekday", "week day", "every weekday", "workday")):
        return f"{minute} {hour} * * 1-5"
    if any(x in t for x in ("weekend",)):
        return f"{minute} {hour} * * 6,0"

    for day_name, day_num in _days.items():
        if day_name in t:
            return f"{minute} {hour} * * {day_num}"

    if any(x in t for x in ("every day", "daily", "each day", "everyday")):
        return f"{minute} {hour} * * *"

    if any(x in t for x in ("monthly", "every month", "each month", "once a month")):
        dom_m = _re.search(r"(\d{1,2})(?:st|nd|rd|th)?", t)
        dom = int(dom_m.group(1)) if dom_m else 1
        return f"{minute} {hour} {dom} * *"

    return None


_natural_to_cron = natural_to_cron  # legacy alias


def next_cron_run(cron_expr: str) -> Optional[float]:
    """Return the next fire time (Unix timestamp) for cron_expr, or None on error."""
    if not CRONITER_OK:
        return None
    try:
        return _Croniter(cron_expr, datetime.now()).get_next(float)
    except Exception:
        return None


_next_cron_run = next_cron_run  # legacy alias


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------

def make_sched_task(cron: str, ai: Optional[str], prompt: str,
                    cwd: Optional[str] = None, name: Optional[str] = None) -> dict:
    _st.sched_counter += 1
    tid = f"t{_st.sched_counter}"
    task = {
        "id":        tid,
        "name":      name or f"Task #{_st.sched_counter}",
        "ai":        ai,
        "cwd":       cwd or _st.last_cwd,
        "prompt":    prompt,
        "cron":      cron,
        "enabled":   True,
        "next_run":  next_cron_run(cron),
        "last_run":  None,
        "run_count": 0,
        "created":   time.time(),
    }
    # Also persist to DB immediately
    _st.scheduled_tasks[tid] = task
    _save_single_task(task)
    return task


_make_sched_task = make_sched_task  # legacy alias


def _save_single_task(task: dict) -> None:
    """Persist a single scheduled task to the database."""
    from helm.db import get_db
    try:
        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO scheduled_tasks
               (id, name, ai, cwd, prompt, cron, enabled, next_run,
                last_run, run_count, created)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task["id"],
                task.get("name", ""),
                task.get("ai"),
                task.get("cwd"),
                task.get("prompt", ""),
                task.get("cron", ""),
                1 if task.get("enabled", True) else 0,
                task.get("next_run"),
                task.get("last_run"),
                task.get("run_count", 0),
                task.get("created", 0),
            ),
        )
        db.commit()
    except Exception as e:
        logger.warning("Could not save task %s to DB: %s", task.get("id"), e)


def load_scheduled_tasks() -> None:
    """Load scheduled tasks from the SQLite database into state."""
    from helm.db import get_db
    try:
        db = get_db()
        rows = db.execute("SELECT * FROM scheduled_tasks").fetchall()
        tasks = {}
        max_counter = 0
        for row in rows:
            tid = row["id"]
            task = {
                "id":        tid,
                "name":      row["name"],
                "ai":        row["ai"],
                "cwd":       row["cwd"],
                "prompt":    row["prompt"],
                "cron":      row["cron"],
                "enabled":   bool(row["enabled"]),
                "next_run":  row["next_run"],
                "last_run":  row["last_run"],
                "run_count": row["run_count"],
                "created":   row["created"],
            }
            # Recompute next_run so they're correct after a restart
            if task["enabled"] and task["cron"]:
                task["next_run"] = next_cron_run(task["cron"])
            tasks[tid] = task
            # Track highest counter for new task IDs
            if tid.startswith("t"):
                try:
                    num = int(tid[1:])
                    if num > max_counter:
                        max_counter = num
                except ValueError:
                    pass
        _st.scheduled_tasks = tasks
        _st.sched_counter = max_counter
    except Exception as e:
        logger.warning("Could not load scheduled tasks: %s", e)


_load_scheduled_tasks = load_scheduled_tasks  # legacy alias


def save_scheduled_tasks() -> None:
    """Persist all scheduled tasks to the SQLite database."""
    from helm.db import get_db
    try:
        db = get_db()
        # Clear and re-insert all (simple and atomic)
        db.execute("DELETE FROM scheduled_tasks")
        for task in _st.scheduled_tasks.values():
            db.execute(
                """INSERT INTO scheduled_tasks
                   (id, name, ai, cwd, prompt, cron, enabled, next_run,
                    last_run, run_count, created)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task["id"],
                    task.get("name", ""),
                    task.get("ai"),
                    task.get("cwd"),
                    task.get("prompt", ""),
                    task.get("cron", ""),
                    1 if task.get("enabled", True) else 0,
                    task.get("next_run"),
                    task.get("last_run"),
                    task.get("run_count", 0),
                    task.get("created", 0),
                ),
            )
        db.commit()
    except Exception as e:
        logger.warning("Could not save scheduled tasks: %s", e)


_save_scheduled_tasks = save_scheduled_tasks  # legacy alias


async def run_scheduled_task(task: dict) -> None:
    """Execute one scheduled task in a temporary session and report via Telegram."""
    from helm.session_mgr import make_session
    from helm.ai_runner import process_message
    from helm.broadcast import push_message

    logger.info("Running scheduled task %s: %s", task["id"], task["name"])

    sess = make_session(task["ai"], cwd=task.get("cwd"))

    # Announce start
    announce = f"⏰ *{task['name']}* starting..."
    await push_message("system", announce, source="schedule", session_id=sess["id"])
    if _st.telegram_app and _st.telegram_chat_id:
        try:
            await _st.telegram_app.bot.send_message(
                chat_id=_st.telegram_chat_id, text=announce, parse_mode="Markdown"
            )
        except Exception:
            pass

    # Run the prompt
    await process_message(task["prompt"], source="schedule", session_id=sess["id"])

    task["run_count"] = task.get("run_count", 0) + 1
    task["last_run"]  = time.time()
    save_scheduled_tasks()

    # Clean up ephemeral session
    sess["terminal"].stop()
    if sess["id"] in _st.sessions:
        # Cache CWD so late-arriving messages still log to the right file
        _st.deleted_session_cwds[sess["id"]] = sess.get("cwd") or _st.last_cwd
        del _st.sessions[sess["id"]]
    from helm.broadcast import push_state
    await push_state()


_run_scheduled_task = run_scheduled_task  # legacy alias


async def cron_runner() -> None:
    """Background loop: fires scheduled tasks when they're due (checks every 30 s)."""
    while True:
        await asyncio.sleep(30)
        now = time.time()
        for task in list(_st.scheduled_tasks.values()):
            if not task.get("enabled"):
                continue
            nxt = task.get("next_run")
            if nxt and now >= nxt:
                task["next_run"] = next_cron_run(task["cron"])
                task["last_run"] = now
                save_scheduled_tasks()
                asyncio.create_task(run_scheduled_task(task))


_cron_runner = cron_runner  # legacy alias


def sched_tasks_payload() -> list[dict]:
    """JSON-safe list of scheduled tasks for the web UI."""
    out = []
    for t in _st.scheduled_tasks.values():
        nr = datetime.fromtimestamp(t["next_run"]).strftime("%Y-%m-%d %H:%M") if t.get("next_run") else "—"
        lr = datetime.fromtimestamp(t["last_run"]).strftime("%Y-%m-%d %H:%M") if t.get("last_run") else "never"
        out.append({**{k: v for k, v in t.items() if k not in ("next_run", "last_run")},
                    "next_run_fmt": nr, "last_run_fmt": lr,
                    "next_run": t.get("next_run"), "last_run": t.get("last_run")})
    return out


_sched_tasks_payload = sched_tasks_payload  # legacy alias
