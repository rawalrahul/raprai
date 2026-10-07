"""Keep the PC awake while Kelvin's AIs work (Windows SetThreadExecutionState)."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.keep_awake as ka
from helm.kelvin_status import KelvinStatus


def _keeper(active, mode):
    calls = []
    k = ka.KeepAwake(lambda: active[0], setter=lambda on: calls.append(on) or True,
                     mode=lambda: mode[0], poll=0.05)
    return k, calls


def test_working_mode_follows_activity():
    active, mode = [False], ["working"]
    k, calls = _keeper(active, mode)
    k.apply_once()
    assert calls == [] and not k.holding           # nothing to hold yet
    active[0] = True
    k.apply_once()
    assert calls == [True] and k.holding
    k.apply_once()
    assert calls == [True]                          # no repeated calls while unchanged
    active[0] = False
    k.apply_once()
    assert calls == [True, False] and not k.holding


def test_always_and_off_modes():
    active, mode = [False], ["always"]
    k, calls = _keeper(active, mode)
    k.apply_once()
    assert calls == [True]
    mode[0] = "off"
    active[0] = True
    k.apply_once()
    assert calls == [True, False]


def test_thread_releases_on_stop():
    active, mode = [True], ["working"]
    k, calls = _keeper(active, mode)
    k.start()
    time.sleep(0.15)
    k.stop()
    k._thread.join(1)
    assert calls[0] is True and calls[-1] is False and not k.holding


def test_unknown_mode_falls_back_to_working(monkeypatch):
    monkeypatch.setenv("KELVIN_KEEP_AWAKE", "banana")
    assert ka.current_mode() == "working"
    monkeypatch.delenv("KELVIN_KEEP_AWAKE")
    assert ka.current_mode() == "working"


def test_set_mode_persists_and_validates(monkeypatch):
    saved = {}
    import importlib
    app = importlib.import_module("helm.web_routes.app")  # the module, not the FastAPI object
    monkeypatch.setattr(app, "update_env", lambda k, v: saved.__setitem__(k, v))
    monkeypatch.setattr(ka, "_instance", None)
    ka.set_mode("always")
    assert saved == {"KELVIN_KEEP_AWAKE": "always"} and os.environ["KELVIN_KEEP_AWAKE"] == "always"
    try:
        ka.set_mode("forever")
        assert False, "should reject unknown modes"
    except ValueError:
        pass
    monkeypatch.delenv("KELVIN_KEEP_AWAKE")


def test_kelvin_status_counts_running_pipelines_and_approvals_as_active():
    k = KelvinStatus()
    assert not k.active()
    k.observe({"type": "pipeline_update", "pipeline": {"id": "p1", "status": "running"}})
    assert k.active()
    k.observe({"type": "pipeline_update", "pipeline": {"id": "p1", "status": "completed"}})
    assert not k.active()
    k.observe({"type": "approval_request", "approval": {"id": "a", "description": "x"}})
    assert k.active()


def test_noop_off_windows():
    if sys.platform != "win32":
        assert ka._default_setter(True) is False
