"""
Subprocess utilities — hide console windows on Windows.

Every subprocess call in the app MUST use the helpers exported here
(or at minimum pass the kwargs from ``hidden_kwargs()``) so that
no cmd.exe / conhost window flashes on screen.

Usage
-----
    from helm.subprocess_utils import hidden_kwargs

    subprocess.run(["git", "status"], **hidden_kwargs(), capture_output=True)
    subprocess.Popen(["chrome", "--app=http://..."], **hidden_kwargs())
"""

from __future__ import annotations

import subprocess
import sys

__all__ = ["hidden_kwargs", "CREATE_NO_WINDOW"]

# On Windows: suppress console window for child processes.
# On other platforms: no-op (empty dict).
if sys.platform == "win32":
    CREATE_NO_WINDOW = 0x08000000   # same as subprocess.CREATE_NO_WINDOW

    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = 0  # SW_HIDE

    def hidden_kwargs() -> dict:
        """Return kwargs that suppress the console window on Windows."""
        return {
            "creationflags": CREATE_NO_WINDOW,
            "startupinfo": _STARTUPINFO,
        }
else:
    CREATE_NO_WINDOW = 0

    def hidden_kwargs() -> dict:
        """No-op on non-Windows platforms."""
        return {}
