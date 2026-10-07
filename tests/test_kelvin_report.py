"""/kelvin on Telegram and the optional daily check-in."""
import asyncio
import os
import sys
import time
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.kelvin_report as kr
import helm.kelvin_status as ks
import helm.state as _st


def _fresh_status(monkeypatch):
    st = ks.KelvinStatus()
    monkeypatch.setattr(ks, "status", st)
    return st


def test_report_when_quiet(monkeypatch):
    _fresh_status(monkeypatch)
    monkeypatch.setattr(_st, "scheduled_tasks", {}, raising=False)
    monkeypatch.setenv("KELVIN_KEEP_AWAKE", "working")
    text = kr.kelvin_report()
    assert text.startswith("🐧 Kelvin is on.")
    assert "Nothing running right now." in text
    assert "No schedules set." in text
    assert "Keep PC awake: while kelvin works" in text


def test_report_lists_work_approvals_and_next_schedule(monkeypatch):
    st = _fresh_status(monkeypatch)
    st.observe({"type": "thinking", "active": True, "session_id": "a"})
    st.observe({"type": "thinking", "active": True, "session_id": "b"})
    st.observe({"type": "pipeline_update", "pipeline": {"id": "p", "status": "running"}})
    st.observe({"type": "approval_request", "approval": {"id": "r", "description": "Claude wants to run: git push"}})
    now = time.time()
    monkeypatch.setattr(_st, "scheduled_tasks", {
        "1": {"name": "Inbox summary", "enabled": True, "next_run": now + 3600},
        "2": {"name": "Weekly report", "enabled": True, "next_run": now + 86400 * 3},
        "3": {"name": "Disabled one", "enabled": False, "next_run": now + 60},
    }, raising=False)
    text = kr.kelvin_report(now)
    assert "2 sessions working, 1 pipeline running" in text
    assert "Waiting for your approval: Claude wants to run: git push" in text
    assert "Next schedule: Inbox summary" in text


def test_uptime_formatting():
    assert kr._ago(59) == "0m"
    assert kr._ago(3 * 3600 + 12 * 60) == "3h 12m"
    assert kr._ago(2 * 86400 + 5 * 3600) == "2d 5h"


def test_checkin_time_parsing(monkeypatch):
    for raw, want in [("09:00", (9, 0)), ("21:30", (21, 30)), ("off", None), ("", None), ("25:00", None)]:
        monkeypatch.setenv("KELVIN_DAILY_CHECKIN", raw)
        assert kr.checkin_time() == want, raw


def test_checkin_once_per_day_after_the_time(monkeypatch):
    monkeypatch.setenv("KELVIN_DAILY_CHECKIN", "09:00")
    assert not kr.checkin_due(datetime(2026, 10, 7, 8, 59), None)
    assert kr.checkin_due(datetime(2026, 10, 7, 9, 0), None)
    assert not kr.checkin_due(datetime(2026, 10, 7, 9, 30), "2026-10-07")   # already sent today
    assert kr.checkin_due(datetime(2026, 10, 8, 9, 1), "2026-10-07")
    monkeypatch.setenv("KELVIN_DAILY_CHECKIN", "off")
    assert not kr.checkin_due(datetime(2026, 10, 8, 9, 1), None)


def test_tg_kelvin_replies_to_the_owner(monkeypatch):
    _fresh_status(monkeypatch)
    monkeypatch.setattr(_st, "scheduled_tasks", {}, raising=False)
    import helm.telegram_bot.auth as auth
    monkeypatch.setattr(auth, "ALLOWED_USER_IDS", [42])
    from helm.telegram_bot.commands import tg_kelvin
    replies = []

    async def reply_text(text, **kw):
        replies.append(text)

    update = SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=SimpleNamespace(id=42),
                             message=SimpleNamespace(reply_text=reply_text))
    asyncio.run(tg_kelvin(update, None))
    assert replies and replies[0].startswith("🐧 Kelvin is on.")


def test_tg_kelvin_refuses_strangers(monkeypatch):
    import helm.telegram_bot.auth as auth
    monkeypatch.setattr(auth, "ALLOWED_USER_IDS", [42])
    from helm.telegram_bot.commands import tg_kelvin
    replies = []

    async def reply_text(text, **kw):
        replies.append(text)

    update = SimpleNamespace(effective_user=SimpleNamespace(id=7), effective_chat=SimpleNamespace(id=7),
                             message=SimpleNamespace(reply_text=reply_text))
    asyncio.run(tg_kelvin(update, None))
    assert replies == ["⛔ Unauthorized."]
