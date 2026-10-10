"""
helm/tray.py — System tray icon for RAPR AI (Windows).

Provides a tray icon with menu: Open UI, Status, Quit.
Hides the console window on startup so the user doesn't accidentally close it.
"""

import os
import shutil
import subprocess
import sys
import ctypes
import webbrowser
import threading
import logging

from helm.subprocess_utils import hidden_kwargs

logger = logging.getLogger("helm.tray")

# ---------------------------------------------------------------------------
# Console window management (Windows only)
# ---------------------------------------------------------------------------

def hide_console():
    """Hide the console window on Windows."""
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            SW_HIDE = 0
            user32.ShowWindow(hwnd, SW_HIDE)
            logger.info("Console window hidden")
    except Exception as exc:
        logger.warning("Could not hide console window: %s", exc)


def show_console():
    """Show the console window on Windows (for debugging)."""
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            SW_SHOW = 5
            user32.ShowWindow(hwnd, SW_SHOW)
            logger.info("Console window shown")
    except Exception as exc:
        logger.warning("Could not show console window: %s", exc)


# ---------------------------------------------------------------------------
# System tray icon
# ---------------------------------------------------------------------------

_tray_icon = None
_shutdown_event = None


def _load_icon():
    """Load the tray icon from the current RAPR logo asset."""
    try:
        from PIL import Image
        from helm.paths import PROJECT_ROOT
        logo_path = PROJECT_ROOT / "rapr-logo.png"
        if logo_path.exists():
            img = Image.open(str(logo_path))
            # Resize to standard tray icon size
            img = img.resize((64, 64), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
            return img
        else:
            # Fallback: create a simple colored square
            img = Image.new("RGBA", (64, 64), (106, 99, 255, 255))
            return img
    except ImportError:
        logger.warning("Pillow not installed — using default tray icon")
        return None
    except Exception as exc:
        logger.warning("Could not load tray icon: %s", exc)
        return None


def start_tray(port: int, shutdown_callback=None):
    """
    Start the system tray icon in a background thread.

    Args:
        port: The actual port the web server is running on.
        shutdown_callback: Callable to invoke for graceful shutdown.
    """
    global _tray_icon, _shutdown_event

    try:
        import pystray
        from pystray import MenuItem, Menu
    except ImportError:
        logger.info("pystray not installed — skipping system tray icon. "
                     "Install with: pip install pystray")
        return

    logo_image = _load_icon()
    if logo_image is None:
        logger.warning("No icon image available — skipping tray")
        return

    # Kelvin sits next to the logo as a small badge whose colour shows what
    # the agents are doing (see helm/kelvin_status.py).
    from helm.kelvin_status import status as kelvin, tray_icon_image

    def _icon_for(mood):
        try:
            return tray_icon_image(mood, logo=logo_image)
        except Exception as exc:
            logger.warning("Kelvin tray badge unavailable: %s", exc)
            return logo_image

    icon_image = _icon_for(kelvin.mood())

    url = f"http://localhost:{port}"

    def _open_app_mode(target_url):
        """Open URL in Chrome/Edge app mode (standalone window), fallback to browser."""
        if sys.platform == "win32":
            for browser_path in [
                shutil.which("chrome"),
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                shutil.which("msedge"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ]:
                if browser_path and os.path.isfile(browser_path):
                    try:
                        subprocess.Popen([browser_path, f"--app={target_url}"], **hidden_kwargs())
                        return
                    except Exception:
                        continue
        webbrowser.open(target_url)

    def on_open_ui(icon, item):
        _open_app_mode(url)

    def on_show_console(icon, item):
        show_console()

    def _is_autostart_enabled():
        """Check if RAPR AI is set to start on Windows login."""
        if sys.platform != "win32":
            return False
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "RAPR AI")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def on_toggle_autostart(icon, item):
        """Toggle start-on-login via Windows Registry Run key."""
        if sys.platform != "win32":
            return
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
            if _is_autostart_enabled():
                # Remove autostart
                try:
                    winreg.DeleteValue(key, "RAPR AI")
                    logger.info("Autostart disabled")
                except FileNotFoundError:
                    pass
            else:
                # Add autostart — use the current executable path
                exe_path = sys.executable
                if exe_path.endswith("python.exe") or exe_path.endswith("pythonw.exe"):
                    # Running from source — use pythonw + web_app.py
                    from helm.paths import PROJECT_ROOT
                    exe_path = f'"{sys.executable}" "{PROJECT_ROOT / "web_app.py"}"'
                else:
                    # Running as compiled .exe
                    exe_path = f'"{exe_path}"'
                winreg.SetValueEx(key, "RAPR AI", 0, winreg.REG_SZ, exe_path)
                logger.info("Autostart enabled: %s", exe_path)
            winreg.CloseKey(key)
        except Exception as exc:
            logger.warning("Could not toggle autostart: %s", exc)

    def on_quit(icon, item):
        logger.info("Quit requested from system tray")
        icon.stop()
        if shutdown_callback:
            shutdown_callback()
        else:
            # Force exit if no callback provided
            os._exit(0)

    from helm.keep_awake import MODES as _awake_modes, MODE_LABELS as _awake_labels, \
        current_mode as _awake_mode, set_mode as _awake_set

    def _set_awake(mode):
        def _handler(icon, item):
            try:
                _awake_set(mode)
                icon.update_menu()
            except Exception as exc:
                logger.warning("Could not change keep-awake mode: %s", exc)
        return _handler

    from helm.desktop_kelvin import (
        MODE_LABELS as _pet_mode_labels, SIZE_ORDER as _pet_sizes,
        pet_mode as _pet_mode, pet_size as _pet_size,
        set_pet_mode, set_pet_size, start_desktop_kelvin,
    )

    def _set_pet(fn, value):
        def _handler(icon, item):
            fn(value)
            icon.update_menu()
        return _handler

    _pet_menu = Menu(*(
        [MenuItem(_pet_mode_labels[m], _set_pet(set_pet_mode, m), radio=True,
                  checked=(lambda m: lambda item: _pet_mode() == m)(m))
         for m in ("always", "working", "off")]
        + [Menu.SEPARATOR]
        + [MenuItem(z.title(), _set_pet(set_pet_size, z), radio=True,
                    checked=(lambda z: lambda item: _pet_size() == z)(z))
           for z in _pet_sizes]
    ))

    menu = Menu(
        MenuItem(f"RAPR AI — {url}", on_open_ui, default=True),
        MenuItem(lambda item: kelvin.describe(), on_open_ui, enabled=False),
        Menu.SEPARATOR,
        MenuItem("Open in Browser", on_open_ui),
        MenuItem("Show Console", on_show_console),
        MenuItem("Kelvin on desktop", _pet_menu),
        MenuItem("Keep PC awake", Menu(*[
            MenuItem(_awake_labels[m], _set_awake(m), radio=True,
                     checked=(lambda m: lambda item: _awake_mode() == m)(m))
            for m in _awake_modes
        ])),
        MenuItem("Start on Login", on_toggle_autostart,
                 checked=lambda item: _is_autostart_enabled()),
        Menu.SEPARATOR,
        MenuItem("Quit RAPR AI", on_quit),
    )

    _tray_icon = pystray.Icon(
        name="rapr-ai",
        icon=icon_image,
        title=f"RAPR AI — Running on {url}",
        menu=menu,
    )

    def _on_kelvin(mood, new_approval):
        icon = _tray_icon
        if icon is None:
            return
        try:
            icon.icon = _icon_for(mood)
            icon.title = f"RAPR AI — {kelvin.describe()}"[:127]
            icon.update_menu()
            if new_approval and getattr(icon, "HAS_NOTIFICATION", True):
                icon.notify(new_approval["description"][:200], "Kelvin needs your approval")
        except Exception as exc:
            logger.debug("Kelvin tray update failed: %s", exc)

    kelvin.subscribe(_on_kelvin)

    def _tick():
        # Lets timed moods (done, error) fade back to idle without new events.
        while _tray_icon is not None:
            kelvin.tick()
            threading.Event().wait(2.0)

    threading.Thread(target=_tick, daemon=True, name="kelvin-tray-tick").start()

    def _setup(icon):
        icon.visible = True
        try:
            from helm.kelvin_tips import first_run_tip
            threading.Event().wait(2.0)  # give Windows a moment to show the icon first
            first_run_tip(notify)
        except Exception as exc:
            logger.debug("First-run tip failed: %s", exc)

    def _run_tray():
        try:
            _tray_icon.run(setup=_setup)
        except Exception as exc:
            logger.warning("Tray icon error: %s", exc)

    tray_thread = threading.Thread(target=_run_tray, daemon=True, name="tray-icon")
    tray_thread.start()

    # Kelvin on the desktop: a draggable, always-on-top companion (Windows).
    try:
        start_desktop_kelvin(lambda: _open_app_mode(url),
                             on_hidden=lambda message: notify("Kelvin", message))
    except Exception as exc:
        logger.info("Desktop Kelvin not started: %s", exc)
    logger.info("System tray icon started")


def notify(title: str, message: str) -> bool:
    """Show a Windows notification from the tray icon (no-op if the tray isn't running)."""
    icon = _tray_icon
    if icon is None or not getattr(icon, "HAS_NOTIFICATION", True):
        return False
    try:
        icon.notify(message, title)
        return True
    except Exception as exc:
        logger.debug("Tray notification failed: %s", exc)
        return False


def stop_tray():
    """Stop the tray icon if running."""
    global _tray_icon
    if _tray_icon:
        try:
            _tray_icon.stop()
        except Exception:
            pass
        _tray_icon = None
