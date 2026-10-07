"""Kelvin's desktop presence: one mood for the tray, plus the console banner."""
import asyncio
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm.kelvin_status import BADGE_COLORS, KelvinStatus, startup_banner, tray_icon_image


def test_idle_by_default():
    assert KelvinStatus().mood() == "idle"


def test_busy_sessions_and_wording():
    k = KelvinStatus()
    k.observe({"type": "thinking", "active": True, "session_id": "a"})
    assert k.mood() == "working" and k.describe() == "Kelvin: working"
    k.observe({"type": "thinking", "active": True, "session_id": "b"})
    assert k.describe() == "Kelvin: 2 sessions working"
    k.observe({"type": "thinking", "active": False, "session_id": "a"})
    k.observe({"type": "thinking", "active": False, "session_id": "b"})
    assert k.mood() == "idle"


def test_approval_outranks_everything_until_resolved():
    k = KelvinStatus()
    k.observe({"type": "thinking", "active": True, "session_id": "a"})
    k.observe({"type": "agent_error", "session_id": "a"})
    k.observe({"type": "approval_request", "approval": {"id": "r1", "description": "git push"}})
    assert k.mood() == "approval"
    assert k.describe() == "Kelvin: waiting for your approval"
    k.observe({"type": "approval_resolved", "approval": {"id": "r1"}})
    assert k.mood() == "error"


def test_done_and_error_fade_out():
    k = KelvinStatus()
    k.observe({"type": "message", "role": "assistant", "content": "Here you go"})
    now = __import__("time").time()
    assert k.mood(now) == "done"
    assert k.mood(now + 60) == "idle"
    k.observe({"type": "pipeline_update", "pipeline": {"status": "failed"}})
    assert k.mood(now) == "error"
    assert k.mood(now + 120) == "idle"


def test_listeners_hear_mood_changes_and_every_new_approval():
    k = KelvinStatus()
    heard = []
    k.subscribe(lambda mood, appr: heard.append((mood, appr and appr["description"])))
    k.observe({"type": "thinking", "active": True, "session_id": "a"})
    k.observe({"type": "thinking", "active": True, "session_id": "b"})  # same mood: no call
    k.observe({"type": "approval_request", "approval": {"id": "1", "description": "delete files"}})
    k.observe({"type": "approval_request", "approval": {"id": "2", "description": "git push"}})  # same mood, new approval
    assert heard == [("working", None), ("approval", "delete files"), ("approval", "git push")]


def test_bad_events_never_raise():
    k = KelvinStatus()
    k.observe({"type": "approval_request", "approval": None})
    k.observe({"type": "pipeline_update"})
    k.observe({})


def test_broadcast_feeds_kelvin_even_without_browsers(monkeypatch):
    import helm.broadcast as b
    import helm.state as _st
    fresh = KelvinStatus()
    monkeypatch.setattr(b, "_kelvin_status", fresh)
    monkeypatch.setattr(_st, "ws_clients", set())
    asyncio.run(b.broadcast({"type": "thinking", "active": True, "session_id": "x"}))
    assert fresh.mood() == "working"


def test_tray_icon_has_coloured_badge():
    for mood, colour in BADGE_COLORS.items():
        img = tray_icon_image(mood, size=64)
        assert img.size == (64, 64) and img.mode == "RGBA"
        corner = [img.getpixel((x, y))[:3] for x in range(32, 64) for y in range(32, 64)]
        assert corner.count(colour[:3]) > 40, mood  # badge colour clearly visible around Kelvin


def test_banner_only_on_a_real_console():
    class Tty(io.StringIO):
        def isatty(self):
            return True

    assert startup_banner("http://localhost:8000", io.StringIO()) is None
    out = Tty()
    text = startup_banner("http://localhost:8000", out)
    assert "http://localhost:8000" in out.getvalue() and text
    assert all(ord(c) < 128 for c in text.replace("\033", ""))
