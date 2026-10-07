"""
helm/kelvin_tips.py — short Windows notifications that explain RAPR is always on.

  first-run tip     once ever: where Kelvin lives and how to keep it visible
  window-closed tip when the last RAPR window closes: RAPR keeps running
                    (shown at most WINDOW_CLOSED_MAX times so it never nags)

State is kept in kelvin_tips.json in the user data folder.
"""

import json
import logging
import threading
from typing import Callable, Optional

from helm.paths import user_data_dir

logger = logging.getLogger("helm")

WINDOW_CLOSED_MAX = 3
WINDOW_CLOSED_DELAY = 6.0   # ignore page reloads and quick reconnects

FIRST_RUN = ("Kelvin is here",
             "RAPR AI runs in your system tray, next to the clock. Click ^ and drag Kelvin onto the "
             "taskbar to keep it in view. You can also drag desktop Kelvin anywhere on screen.")
WINDOW_CLOSED = ("RAPR AI is still running",
                 "Your AIs, schedules and Telegram keep working. Open RAPR again from the tray or "
                 "double-click Kelvin. Quit from the tray menu.")

_shown_closed_this_run = False


def _state_path():
    return user_data_dir() / "kelvin_tips.json"


def _load() -> dict:
    try:
        return json.loads(_state_path().read_text())
    except Exception:
        return {}


def _save(state: dict) -> None:
    try:
        _state_path().write_text(json.dumps(state))
    except Exception as exc:
        logger.debug("Could not save Kelvin tips state: %s", exc)


def first_run_tip(notify: Callable[[str, str], None]) -> bool:
    state = _load()
    if state.get("first_run"):
        return False
    notify(*FIRST_RUN)
    state["first_run"] = True
    _save(state)
    return True


def window_closed_tip(notify: Callable[[str, str], None]) -> bool:
    """Call when the last browser window disconnects (after the reconnect grace period)."""
    global _shown_closed_this_run
    if _shown_closed_this_run:
        return False
    state = _load()
    count = int(state.get("window_closed", 0))
    if count >= WINDOW_CLOSED_MAX:
        return False
    notify(*WINDOW_CLOSED)
    state["window_closed"] = count + 1
    _save(state)
    _shown_closed_this_run = True
    return True


def schedule_window_closed_check(has_clients: Callable[[], bool], notify: Optional[Callable[[str, str], None]] = None,
                                 delay: float = WINDOW_CLOSED_DELAY) -> threading.Timer:
    """After `delay` seconds, show the tip only if no RAPR window reconnected."""
    if notify is None:
        from helm.tray import notify as notify  # noqa: PLW0127 - tray owns the notification area

    def _check():
        try:
            if not has_clients():
                window_closed_tip(notify)
        except Exception as exc:
            logger.debug("Window-closed tip failed: %s", exc)

    timer = threading.Timer(delay, _check)
    timer.daemon = True
    timer.start()
    return timer
