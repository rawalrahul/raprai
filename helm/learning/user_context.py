"""
helm/learning/user_context.py — First-run OS/resolution/browser/DPI detection.

Writes helm/learning/user_context.json on first import if missing.
Subsequent imports load from the cached file.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

_LEARNING_DIR = Path(__file__).parent
_CONTEXT_PATH = _LEARNING_DIR / "user_context.json"

# Module-level cache
_ctx: dict | None = None


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _detect_resolution() -> dict:
    """Return primary screen resolution and DPI scale."""
    try:
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            # Physical pixels (requires DPI awareness already set by builtin_tools)
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            # DPI for primary monitor
            try:
                shcore = ctypes.windll.shcore
                dpi_x = ctypes.c_uint(0)
                dpi_y = ctypes.c_uint(0)
                shcore.GetDpiForMonitor(
                    user32.MonitorFromPoint(ctypes.c_int(0), ctypes.c_int(0), 2),
                    0,  # MDT_EFFECTIVE_DPI
                    ctypes.byref(dpi_x),
                    ctypes.byref(dpi_y),
                )
                dpi = dpi_x.value
            except Exception:
                dpi = 96
            scale = round(dpi / 96.0, 2)
            return {"width": w, "height": h, "dpi": dpi, "scale": scale}
    except Exception:
        pass
    # Fallback via tkinter (cross-platform)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return {"width": w, "height": h, "dpi": 96, "scale": 1.0}
    except Exception:
        pass
    return {"width": 1920, "height": 1080, "dpi": 96, "scale": 1.0}


def _detect_default_browser() -> str:
    """Return name of default browser (best-effort)."""
    try:
        if sys.platform == "win32":
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
            ) as k:
                prog_id, _ = winreg.QueryValueEx(k, "ProgId")
            pid = prog_id.lower()
            for name, key in [
                ("chrome", "chrome"), ("firefox", "firefox"),
                ("edge", "edge"), ("brave", "brave"), ("opera", "opera"),
            ]:
                if key in pid:
                    return name
            return prog_id
    except Exception:
        pass
    # Unix fallback
    for cmd in ["xdg-settings get default-web-browser", "defaults read com.apple.LaunchServices"]:
        try:
            import subprocess
            r = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=3)
            if r.returncode == 0 and r.stdout.strip():
                out = r.stdout.strip().lower()
                for name in ["chrome", "firefox", "safari", "edge", "brave"]:
                    if name in out:
                        return name
        except Exception:
            pass
    return "unknown"


def _detect_default_terminal() -> str:
    for t in ["wt", "windowsterminal", "cmd", "powershell", "bash", "zsh", "gnome-terminal", "iterm"]:
        if shutil.which(t):
            return t
    return "unknown"


def _detect_os() -> dict:
    import platform
    return {
        "system": platform.system(),
        "version": platform.version(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def _count_monitors() -> int:
    try:
        if sys.platform == "win32":
            import ctypes
            return ctypes.windll.user32.GetSystemMetrics(80)  # SM_CMONITORS
    except Exception:
        pass
    return 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_and_save() -> dict:
    """Run all detections and write user_context.json. Returns context dict."""
    from datetime import datetime, timezone
    ctx: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "os": _detect_os(),
        "screen": _detect_resolution(),
        "monitor_count": _count_monitors(),
        "default_browser": _detect_default_browser(),
        "default_terminal": _detect_default_terminal(),
        # User preferences — set via /learning/context PUT
        "prefer_speed_vs_quality": 0.5,   # 0=pure speed, 1=pure quality
        "trusted_ai": None,
        "avoid_apps": [],
    }
    try:
        tmp = _CONTEXT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        if _CONTEXT_PATH.exists():
            _CONTEXT_PATH.unlink()
        tmp.rename(_CONTEXT_PATH)
    except Exception:
        pass
    return ctx


def load_context() -> dict:
    """Load user_context.json (create if missing). Cached after first load."""
    global _ctx
    if _ctx is not None:
        return _ctx
    if _CONTEXT_PATH.exists():
        try:
            _ctx = json.loads(_CONTEXT_PATH.read_text(encoding="utf-8"))
            return _ctx
        except Exception:
            pass
    _ctx = detect_and_save()
    return _ctx


def update_context(updates: dict) -> dict:
    """Merge updates into user_context.json and return new state."""
    global _ctx
    ctx = load_context()
    ctx.update(updates)
    from datetime import datetime, timezone
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        tmp = _CONTEXT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        if _CONTEXT_PATH.exists():
            _CONTEXT_PATH.unlink()
        tmp.rename(_CONTEXT_PATH)
        _ctx = ctx
    except Exception:
        pass
    return ctx


def get_context_block() -> str:
    """Return a short text block for injection into AI prompts."""
    try:
        ctx = load_context()
        screen = ctx.get("screen", {})
        res = f"{screen.get('width', '?')}x{screen.get('height', '?')}@{screen.get('scale', 1.0)}x"
        browser = ctx.get("default_browser", "unknown")
        os_info = ctx.get("os", {}).get("system", "Windows")
        return (
            f"[USER ENVIRONMENT]\n"
            f"OS: {os_info} | Screen: {res} | Browser: {browser}\n"
            f"[END USER ENVIRONMENT]\n"
        )
    except Exception:
        return ""


# First-run: create on import if missing
if not _CONTEXT_PATH.exists():
    try:
        detect_and_save()
    except Exception:
        pass
