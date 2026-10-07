"""Tips that explain RAPR keeps running: shown sparingly, never nagging."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.kelvin_tips as tips


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(tips, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(tips, "_shown_closed_this_run", False)
    shown = []
    return shown, lambda title, msg: shown.append(title)


def test_first_run_tip_only_once_ever(monkeypatch, tmp_path):
    shown, notify = _fresh(monkeypatch, tmp_path)
    assert tips.first_run_tip(notify) is True
    assert tips.first_run_tip(notify) is False
    assert shown == ["Kelvin is here"]


def test_window_closed_tip_once_per_run_and_three_times_total(monkeypatch, tmp_path):
    shown, notify = _fresh(monkeypatch, tmp_path)
    for run in range(5):
        monkeypatch.setattr(tips, "_shown_closed_this_run", False)   # a new app start
        tips.window_closed_tip(notify)
        tips.window_closed_tip(notify)                               # closed again same run
    assert shown == ["RAPR AI is still running"] * tips.WINDOW_CLOSED_MAX


def test_no_tip_if_a_window_reconnects(monkeypatch, tmp_path):
    shown, notify = _fresh(monkeypatch, tmp_path)
    t = tips.schedule_window_closed_check(lambda: True, notify, delay=0.05)
    t.join(1)
    assert shown == []


def test_tip_when_no_window_comes_back(monkeypatch, tmp_path):
    shown, notify = _fresh(monkeypatch, tmp_path)
    t = tips.schedule_window_closed_check(lambda: False, notify, delay=0.05)
    t.join(1)
    assert shown == ["RAPR AI is still running"]


def test_tray_notify_without_tray_is_harmless():
    import helm.tray as tray
    assert tray.notify("x", "y") is False
