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
    """Load the tray icon from logo.png."""
    try:
        from PIL import Image
        from helm.paths import PROJECT_ROOT
        logo_path = PROJECT_ROOT / "logo.png"
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

    icon_image = _load_icon()
    if icon_image is None:
        logger.warning("No icon image available — skipping tray")
        return

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
                        subprocess.Popen([browser_path, f"--app={target_url}"])
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

    menu = Menu(
        MenuItem(f"RAPR AI — {url}", on_open_ui, default=True),
        Menu.SEPARATOR,
        MenuItem("Open in Browser", on_open_ui),
        MenuItem("Show Console", on_show_console),
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

    def _run_tray():
        try:
            _tray_icon.run()
        except Exception as exc:
            logger.warning("Tray icon error: %s", exc)

    tray_thread = threading.Thread(target=_run_tray, daemon=True, name="tray-icon")
    tray_thread.start()
    logger.info("System tray icon started")


def stop_tray():
    """Stop the tray icon if running."""
    global _tray_icon
    if _tray_icon:
        try:
            _tray_icon.stop()
        except Exception:
            pass
        _tray_icon = None
