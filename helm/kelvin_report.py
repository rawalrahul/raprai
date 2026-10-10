"""
helm/kelvin_report.py — "Is Kelvin on?" for Telegram.

  /kelvin            replies with a short status report (uptime, what's
                     running, approvals waiting, next schedule, keep-awake).
                     No reply means RAPR is off or the PC is asleep.
  daily check-in     optional (KELVIN_DAILY_CHECKIN="HH:MM", empty = off):
                     the same report sent once a day at that local time.
"""

import asyncio
import os
import platform
import time
from datetime import datetime
from typing import Optional

import helm.state as _st
from helm.config import logger


def _ago(seconds: float) -> str:
    seconds = int(max(0, seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def next_schedule(now: Optional[float] = None) -> Optional[tuple]:
    """(name, timestamp) of the next enabled scheduled task, if any."""
    now = now or time.time()
    upcoming = [
        (t.get("name") or "Scheduled task", t["next_run"])
        for t in (_st.scheduled_tasks or {}).values()
        if t.get("enabled") and t.get("next_run") and t["next_run"] >= now - 60
    ]
    return min(upcoming, key=lambda x: x[1]) if upcoming else None


def kelvin_report(now: Optional[float] = None) -> str:
    from helm.kelvin_status import status
    from helm import keep_awake
    from helm.desktop_kelvin import pet_enabled

    now = now or time.time()
    c = status.counts()
    lines = [f"🐧 Kelvin is on. RAPR AI has been running for {_ago(now - status.started_at)} on {platform.node() or 'this PC'}."]

    if c["approvals"]:
        first = c["approval_texts"][0][:120]
        more = f" (+{c['approvals'] - 1} more)" if c["approvals"] > 1 else ""
        lines.append(f"✋ Waiting for your approval: {first}{more}")
    work = []
    if c["busy"]:
        work.append(f"{c['busy']} session{'s' if c['busy'] != 1 else ''} working")
    if c.get("groups"):
        work.append(f"{c['groups']} group chat{'s' if c['groups'] != 1 else ''} answering")
    if c["pipelines"]:
        work.append(f"{c['pipelines']} pipeline{'s' if c['pipelines'] != 1 else ''} running")
    lines.append("⚙️ " + (", ".join(work) if work else "Nothing running right now."))

    nxt = next_schedule(now)
    if nxt:
        when = datetime.fromtimestamp(nxt[1])
        day = "today" if when.date() == datetime.fromtimestamp(now).date() else when.strftime("%a %d %b")
        lines.append(f"⏰ Next schedule: {nxt[0]} at {when.strftime('%H:%M')} {day}")
    else:
        lines.append("⏰ No schedules set.")

    lines.append(f"☕ {keep_awake.describe()}")
    lines.append(f"🖥️ Desktop Kelvin: {'shown' if pet_enabled() else 'hidden'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Optional daily check-in
# ---------------------------------------------------------------------------

def checkin_time() -> Optional[tuple]:
    raw = os.environ.get("KELVIN_DAILY_CHECKIN", "").strip()
    try:
        hh, mm = raw.split(":")
        hh, mm = int(hh), int(mm)
        if 0 <= hh < 24 and 0 <= mm < 60:
            return hh, mm
    except Exception:
        pass
    return None


def checkin_due(now: datetime, last_sent_day: Optional[str]) -> bool:
    at = checkin_time()
    if not at:
        return False
    today = now.strftime("%Y-%m-%d")
    return last_sent_day != today and (now.hour, now.minute) >= at


async def daily_checkin_loop(poll_seconds: float = 30.0) -> None:
    """Send the Kelvin report to Telegram once a day at KELVIN_DAILY_CHECKIN."""
    from helm.ai_runner import forward_to_telegram
    # Don't fire for a time that already passed before RAPR started today.
    start = datetime.now()
    at = checkin_time()
    last_sent = start.strftime("%Y-%m-%d") if at and (start.hour, start.minute) > at else None
    while True:
        await asyncio.sleep(poll_seconds)
        try:
            now = datetime.now()
            if checkin_due(now, last_sent):
                last_sent = now.strftime("%Y-%m-%d")
                greeting = "Good morning from Kelvin!" if now.hour < 12 else "Daily check-in from Kelvin"
                await forward_to_telegram(f"{greeting}\n\n{kelvin_report()}")
        except Exception as exc:
            logger.warning("Kelvin daily check-in failed: %s", exc)
