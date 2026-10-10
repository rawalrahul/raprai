"""Desktop Kelvin: the draggable, always-on-top companion (logic that needs no screen)."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.desktop_kelvin as dk
from helm.kelvin_status import KelvinStatus

SCREEN = (0, 0, 1920, 1080)


def test_every_mood_has_a_sprite_strip():
    for mood in dk.PET_MOODS:
        frames = dk.load_strip(mood)
        assert len(frames) >= 8, mood
        assert frames[0].size == (dk.PET_W, dk.PET_H)


def test_default_position_is_bottom_right_above_taskbar():
    x, y = dk.default_position(SCREEN)
    assert 1920 - dk.PET_W - 40 < x < 1920 - dk.PET_W
    assert y + dk.PET_H < 1080 - 40


def test_clamp_brings_kelvin_back_when_a_monitor_disappears():
    # Saved on a second monitor to the right that is no longer connected.
    x, y = dk.clamp_position(3500, 400, SCREEN)
    assert x <= 1920 - 40 and y == 400
    x, y = dk.clamp_position(-900, -300, SCREEN)
    assert x >= -dk.PET_W + 40 and y == 0
    assert dk.clamp_position(800, 500, SCREEN) == (800, 500)


def test_clamp_respects_monitors_left_of_primary():
    virtual = (-1920, 0, 3840, 1080)
    assert dk.clamp_position(-1500, 300, virtual) == (-1500, 300)


def test_position_is_remembered(monkeypatch, tmp_path):
    monkeypatch.setattr(dk, "user_data_dir", lambda: tmp_path)
    assert dk.load_position() is None
    dk.save_position(321, 654)
    assert dk.load_position() == (321, 654)


def test_mood_mapping():
    st = KelvinStatus()
    assert dk.pet_mood(st) == "idle"
    st.observe({"type": "thinking", "active": True, "session_id": "a"})
    assert dk.pet_mood(st) == "thinking"
    st.observe({"type": "pipeline_update", "pipeline": {"id": "p", "status": "running"}})
    assert dk.pet_mood(st) == "working"
    st.observe({"type": "approval_request", "approval": {"id": "r", "description": "x"}})
    assert dk.pet_mood(st) == "approval"


def test_kelvin_dozes_off_when_nothing_happens():
    st = KelvinStatus()
    st.observe({"type": "message", "role": "assistant"})
    later = time.time() + dk.SLEEP_AFTER_SECONDS + 5
    assert dk.pet_mood(st, later) == "sleeping"


def test_flatten_uses_hard_edges_for_the_colour_key():
    from PIL import Image
    frame = Image.new("RGBA", (4, 1))
    frame.putdata([(10, 20, 30, 255), (10, 20, 30, 200), (0, 0, 0, 60), (0, 0, 0, 0)])
    flat = list(dk.flatten(frame).getdata())
    assert flat[0] == (10, 20, 30) and flat[1] == (10, 20, 30)   # solid enough: kept
    assert flat[2] == dk.KEY_COLOR and flat[3] == dk.KEY_COLOR   # faint shadow/edge: see-through


def test_enabled_by_default_and_can_be_hidden(monkeypatch):
    monkeypatch.delenv("KELVIN_DESKTOP_PET", raising=False)
    assert dk.pet_enabled()
    monkeypatch.setenv("KELVIN_DESKTOP_PET", "0")
    assert not dk.pet_enabled()


def test_set_pet_enabled_persists(monkeypatch):
    import importlib
    app = importlib.import_module("helm.web_routes.app")
    saved = {}
    monkeypatch.setattr(app, "update_env", lambda k, v: saved.__setitem__(k, v))
    dk.set_pet_enabled(False)
    assert saved == {"KELVIN_DESKTOP_PET": "0"} and not dk.pet_enabled()
    dk.set_pet_enabled(True)
    assert dk.pet_enabled()
    monkeypatch.delenv("KELVIN_DESKTOP_PET")


def test_only_starts_on_windows(monkeypatch):
    monkeypatch.setattr(dk.sys, "platform", "linux")
    monkeypatch.setattr(dk, "_instance", None)
    assert dk.start_desktop_kelvin(lambda: None) is None


# ── Size and visibility ──────────────────────────────────────────────────────

def test_modes(monkeypatch):
    for raw, mode in (("1", "always"), ("true", "always"), ("working", "working"), ("auto", "working"),
                      ("0", "off"), ("off", "off")):
        monkeypatch.setenv("KELVIN_DESKTOP_PET", raw)
        assert dk.pet_mode() == mode, raw
    monkeypatch.delenv("KELVIN_DESKTOP_PET")
    assert dk.pet_mode() == "always"


def test_should_show():
    assert dk.should_show("always", "idle", False)
    assert not dk.should_show("always", "idle", True)             # hidden for an hour
    assert dk.should_show("always", "approval", True)             # ...but approvals still show him
    assert not dk.should_show("working", "idle", False)
    assert not dk.should_show("working", "sleeping", False)
    for mood in ("thinking", "working", "approval", "error", "done"):
        assert dk.should_show("working", mood, False), mood
    assert not dk.should_show("off", "approval", False)


def test_sizes(monkeypatch):
    monkeypatch.delenv("KELVIN_DESKTOP_SIZE", raising=False)
    assert dk.pet_size() == "medium"
    monkeypatch.setenv("KELVIN_DESKTOP_SIZE", "huge")
    assert dk.pet_size() == "medium"
    assert dk.pet_box("large") == (dk.PET_W, dk.PET_H)
    assert dk.pet_box("small") == (dk.PET_W // 2, dk.PET_H // 2)
    assert dk.next_size("medium", 1) == "large" and dk.next_size("large", 1) == "large"
    assert dk.next_size("medium", -1) == "small" and dk.next_size("small", -1) == "small"
    frames = dk.load_strip("idle", dk.pet_box("small"))
    assert frames[0].size == dk.pet_box("small")


def test_resize_keeps_bottom_right_corner():
    old, new = dk.pet_box("large"), dk.pet_box("small")
    x, y = dk.resize_anchor(1000, 800, old, new)
    assert (x + new[0], y + new[1]) == (1000 + old[0], 800 + old[1])


def test_mode_and_size_are_saved(monkeypatch, tmp_path):
    import importlib
    app = importlib.import_module("helm.web_routes.app")
    saved = {}
    monkeypatch.setattr(app, "update_env", lambda k, v: saved.__setitem__(k, v))
    dk.set_pet_mode("working")
    dk.set_pet_size("small")
    assert saved == {"KELVIN_DESKTOP_PET": "working", "KELVIN_DESKTOP_SIZE": "small"}
    assert dk.pet_mode() == "working" and dk.pet_size() == "small"
    dk.set_pet_enabled(True)
    assert dk.pet_mode() == "always"
    monkeypatch.delenv("KELVIN_DESKTOP_SIZE")
    monkeypatch.delenv("KELVIN_DESKTOP_PET")
