"""
helm/headless.py — Is RAPR running without a desktop? (servers, Docker, Linux VPS)

Headless mode skips everything that needs a screen or the Windows shell: the
system tray, desktop Kelvin, and keep-awake. Chat apps, the web UI, schedules,
Kelvin on Telegram and WhatsApp all keep working.

Turned on by RAPR_HEADLESS=1|true|yes. Linux with no display (no DISPLAY and no
WAYLAND_DISPLAY, as on a VPS or in Docker) is treated as headless automatically.
"""

import os
import sys

_TRUE = ("1", "true", "yes", "on")


def is_headless() -> bool:
    raw = os.environ.get("RAPR_HEADLESS", "").strip().lower()
    if raw:
        return raw in _TRUE
    if sys.platform.startswith("linux"):
        return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return False
