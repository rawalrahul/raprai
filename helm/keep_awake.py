"""
helm/keep_awake.py — stop Windows from sleeping while Kelvin's AIs are working.

Mode comes from KELVIN_KEEP_AWAKE (Settings, tray menu):
  working  (default) stay awake while sessions are busy, a pipeline runs, or
           an approval is waiting
  always   stay awake the whole time RAPR runs (for true always-on)
  off      let Windows sleep as usual

Only the computer is kept awake; the screen can still turn off. Closing a
laptop lid follows the Windows "lid close action" setting and may still sleep.
Uses SetThreadExecutionState, which needs no admin rights and is released
automatically if RAPR exits. On macOS it runs the built-in `caffeinate -i`
tied to RAPR's process (so it ends if RAPR exits). Elsewhere this is a no-op.
"""

import os
import sys
import threading
from typing import Callable, Optional

from helm.config import logger

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

MODES = ("working", "always", "off")
MODE_LABELS = {"working": "While Kelvin works", "always": "Always", "off": "Off"}
POLL_SECONDS = 5.0


def current_mode() -> str:
    mode = os.environ.get("KELVIN_KEEP_AWAKE", "working").strip().lower()
    return mode if mode in MODES else "working"


_caffeinate = None   # macOS: the running `caffeinate` process while awake


def _mac_setter(awake: bool) -> bool:
    global _caffeinate
    import subprocess
    if awake:
        if _caffeinate is None or _caffeinate.poll() is not None:
            # -i: no idle sleep; -w: stop by itself if RAPR's process goes away.
            _caffeinate = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        return True
    if _caffeinate is not None:
        _caffeinate.terminate()
        _caffeinate = None
    return True


def _default_setter(awake: bool) -> bool:
    if sys.platform == "darwin":
        try:
            return _mac_setter(awake)
        except Exception:
            return False
    if sys.platform != "win32":
        return False
    import ctypes
    flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if awake else 0)
    return bool(ctypes.windll.kernel32.SetThreadExecutionState(flags))


class KeepAwake:
    """Owns the execution state on one long-lived thread (Windows tracks it per thread)."""

    def __init__(self, is_active: Callable[[], bool], setter: Callable[[bool], bool] = _default_setter,
                 mode: Callable[[], str] = current_mode, poll: float = POLL_SECONDS):
        self._is_active = is_active
        self._setter = setter
        self._mode = mode
        self._poll = poll
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.holding = False

    def wanted(self) -> bool:
        mode = self._mode()
        if mode == "always":
            return True
        if mode == "off":
            return False
        return bool(self._is_active())

    def apply_once(self) -> None:
        want = self.wanted()
        if want != self.holding:
            try:
                self._setter(want)
                self.holding = want
                logger.info("Keep-awake %s (mode=%s)", "on" if want else "off", self._mode())
            except Exception as exc:
                logger.warning("Keep-awake update failed: %s", exc)

    def poke(self) -> None:
        """Re-check now (e.g. after a mood change or a settings change)."""
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            self.apply_once()
            self._wake.wait(self._poll)
            self._wake.clear()
        if self.holding:
            try:
                self._setter(False)
            except Exception:
                pass
            self.holding = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="kelvin-keep-awake")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()


_instance: Optional[KeepAwake] = None


def start_keep_awake() -> KeepAwake:
    """Start the app-wide keeper, driven by Kelvin's view of what is running."""
    global _instance
    if _instance is None:
        from helm.kelvin_status import status
        _instance = KeepAwake(status.active)
        status.subscribe(lambda mood, appr: _instance.poke())
        _instance.start()
    return _instance


def set_mode(mode: str) -> None:
    """Change the mode, persist it to .env, and apply it immediately."""
    if mode not in MODES:
        raise ValueError(mode)
    os.environ["KELVIN_KEEP_AWAKE"] = mode
    try:
        from helm.web_routes.app import update_env
        update_env("KELVIN_KEEP_AWAKE", mode)
    except Exception as exc:
        logger.warning("Could not save keep-awake mode: %s", exc)
    if _instance:
        _instance.poke()


def describe() -> str:
    mode = current_mode()
    holding = bool(_instance and _instance.holding)
    if mode == "off":
        return "Keep PC awake: off"
    return f"Keep PC awake: {MODE_LABELS[mode].lower()} ({'awake now' if holding else 'idle, sleep allowed'})"
