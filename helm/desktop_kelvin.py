"""
helm/desktop_kelvin.py — Kelvin on your desktop, like Codex Pets.

A small, frameless, always-on-top window showing an animated Kelvin that
follows what RAPR's AIs are doing (helm/kelvin_status.py). Users can:
  - drag Kelvin anywhere (position is remembered, across monitors)
  - click Kelvin for a little hop, or to open RAPR when an approval waits
  - double-click to open RAPR AI
  - right-click for a menu (status, Open RAPR AI, Hide Kelvin)

Visibility follows KELVIN_DESKTOP_PET ("1" by default), toggled from the tray
menu ("Kelvin on desktop") or Settings, so it can be brought back any time.

Built on Tkinter (bundled by build.bat's tk-inter plugin). The animation is
pre-rendered from frontend2/js/kelvin.js into sprite strips
frontend2/assets/kelvin/pet-<mood>.png by scripts/render_kelvin_assets.cjs.
Windows uses a colour-key for the transparent background; elsewhere Kelvin
sits on a small dark tile.
"""

import json
import logging
import os
import sys
import threading
from typing import Callable, Optional

from helm.paths import PROJECT_ROOT, user_data_dir

logger = logging.getLogger("helm")

ASSET_DIR = PROJECT_ROOT / "frontend2" / "assets" / "kelvin"
PET_W, PET_H = 160, 170
FRAME_MS = 75
KEY_COLOR = (255, 0, 254)          # colour-key for the transparent window background
KEY_HEX = "#ff00fe"
FALLBACK_BG = (24, 22, 20)        # non-Windows: Kelvin sits on a dark tile
ALPHA_CUTOFF = 110                # colour-key windows have no partial transparency
SLEEP_AFTER_SECONDS = 10 * 60
POKE_MS = 1200
DRAG_THRESHOLD = 4
PET_MOODS = ("idle", "working", "thinking", "approval", "done", "error", "sleeping")


def pet_enabled() -> bool:
    return os.environ.get("KELVIN_DESKTOP_PET", "1").strip().lower() not in ("0", "false", "no", "off")


def state_file():
    return user_data_dir() / "kelvin_desktop.json"


def load_position() -> Optional[tuple]:
    try:
        data = json.loads(state_file().read_text())
        return int(data["x"]), int(data["y"])
    except Exception:
        return None


def save_position(x: int, y: int) -> None:
    try:
        state_file().write_text(json.dumps({"x": int(x), "y": int(y)}))
    except Exception as exc:
        logger.debug("Could not save desktop Kelvin position: %s", exc)


def clamp_position(x: int, y: int, screen: tuple) -> tuple:
    """Keep at least part of Kelvin on screen (e.g. after a monitor was unplugged).

    screen = (left, top, width, height) of the whole virtual desktop.
    """
    left, top, width, height = screen
    margin = 40
    x = min(max(x, left - PET_W + margin), left + width - margin)
    y = min(max(y, top), top + height - margin)
    return x, y


def default_position(screen: tuple) -> tuple:
    """Bottom-right corner, above the taskbar."""
    left, top, width, height = screen
    return left + width - PET_W - 24, top + height - PET_H - 64


def pet_mood(status, now: Optional[float] = None) -> str:
    mood = status.mood(now)
    if mood == "idle" and status.idle_seconds(now) > SLEEP_AFTER_SECONDS:
        return "sleeping"
    if mood == "working" and not status.counts()["pipelines"]:
        return "thinking"   # sessions waiting on their AI; the gear is for running pipelines
    return mood


def load_strip(mood: str):
    """Return the RGBA frames for one mood from its sprite strip."""
    from PIL import Image
    strip = Image.open(ASSET_DIR / f"pet-{mood}.png").convert("RGBA")
    count = max(1, strip.width // PET_W)
    return [strip.crop((i * PET_W, 0, (i + 1) * PET_W, PET_H)) for i in range(count)]


def flatten(frame, background=KEY_COLOR):
    """Flatten an RGBA frame onto a solid background, with a hard alpha cut.

    Colour-key transparency is all-or-nothing, so soft edges and the drop
    shadow are dropped instead of being blended into a magenta fringe.
    """
    from PIL import Image
    bg = Image.new("RGB", frame.size, background)
    mask = frame.getchannel("A").point(lambda a: 255 if a >= ALPHA_CUTOFF else 0)
    bg.paste(frame.convert("RGB"), (0, 0), mask)
    return bg


def _virtual_screen(root) -> tuple:
    if sys.platform == "win32":
        try:
            import ctypes
            m = ctypes.windll.user32.GetSystemMetrics
            return m(76), m(77), m(78), m(79)  # SM_X/YVIRTUALSCREEN, SM_CX/CYVIRTUALSCREEN
        except Exception:
            pass
    return 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()


class DesktopKelvin:
    """The floating Kelvin window. Tk lives entirely on its own thread."""

    def __init__(self, status, open_ui: Callable[[], None],
                 set_enabled: Optional[Callable[[bool], None]] = None,
                 transparent: Optional[bool] = None):
        self.status = status
        self.open_ui = open_ui
        self.set_enabled = set_enabled or (lambda on: os.environ.__setitem__("KELVIN_DESKTOP_PET", "1" if on else "0"))
        self.transparent = (sys.platform == "win32") if transparent is None else transparent
        self.root = None
        self.ready = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._frames: dict = {}
        self._mood = None
        self._frame = 0
        self._poke_until = 0.0
        self._press = None
        self._dragged_to = None
        self._shown = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="desktop-kelvin")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        try:
            self._build()
            self.ready.set()
            self.root.mainloop()
        except Exception as exc:
            logger.warning("Desktop Kelvin unavailable: %s", exc)
            self.ready.set()
        finally:
            # Tk objects must be released on the thread that created them,
            # or Tcl aborts when Python later collects them elsewhere.
            import gc
            self._frames.clear()
            self.label = self.menu = self.root = None
            gc.collect()

    def _build(self) -> None:
        import tkinter as tk

        tk.NoDefaultRoot()  # keep no hidden global reference to this thread's Tk
        root = tk.Tk()
        root.withdraw()
        root.title("Kelvin")
        root.overrideredirect(True)          # no title bar, no taskbar button
        root.attributes("-topmost", True)
        bg_hex = KEY_HEX if self.transparent else "#%02x%02x%02x" % FALLBACK_BG
        root.configure(bg=bg_hex)
        if self.transparent:
            root.attributes("-transparentcolor", KEY_HEX)
        self.label = tk.Label(root, bd=0, highlightthickness=0, bg=bg_hex, cursor="hand2")
        self.label.pack()

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Kelvin", state="disabled")
        self.menu.add_separator()
        self.menu.add_command(label="Open RAPR AI", command=self._open)
        self.menu.add_command(label="Hide Kelvin (show again from the tray)", command=self._hide_by_user)

        for widget in (root, self.label):
            widget.bind("<ButtonPress-1>", self._on_press)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<Double-Button-1>", lambda e: self._open())
            widget.bind("<Button-3>", self._on_menu)

        self.root = root
        screen = _virtual_screen(root)
        x, y = load_position() or default_position(screen)
        x, y = clamp_position(x, y, screen)
        root.geometry(f"{PET_W}x{PET_H}+{x}+{y}")
        self._tick()

    # -- animation -----------------------------------------------------------

    def _frames_for(self, mood: str):
        if mood not in self._frames:
            from PIL import ImageTk
            bg = KEY_COLOR if self.transparent else FALLBACK_BG
            self._frames[mood] = [ImageTk.PhotoImage(flatten(f, bg), master=self.root) for f in load_strip(mood)]
        return self._frames[mood]

    def current_mood(self, now: Optional[float] = None) -> str:
        import time
        now = now or time.time()
        if now < self._poke_until:
            return "done"
        return pet_mood(self.status, now)

    def _tick(self) -> None:
        if self._stop.is_set():
            self.root.quit()
            self.root.destroy()
            return
        try:
            want = pet_enabled()
            if want != self._shown:
                (self.root.deiconify if want else self.root.withdraw)()
                if want:
                    self.root.attributes("-topmost", True)
                self._shown = want
            if want:
                mood = self.current_mood()
                if mood != self._mood:
                    self._mood, self._frame = mood, 0
                frames = self._frames_for(mood)
                self.label.configure(image=frames[self._frame % len(frames)])
                self._frame += 1
        except Exception as exc:
            logger.debug("Desktop Kelvin frame failed: %s", exc)
        self.root.after(FRAME_MS, self._tick)

    # -- interaction ---------------------------------------------------------

    def _on_press(self, e) -> None:
        self._press = (e.x_root, e.y_root, self.root.winfo_x(), self.root.winfo_y(), False)

    def _on_drag(self, e) -> None:
        if not self._press:
            return
        x0, y0, wx, wy, moved = self._press
        dx, dy = e.x_root - x0, e.y_root - y0
        if not moved and abs(dx) + abs(dy) < DRAG_THRESHOLD:
            return
        self._press = (x0, y0, wx, wy, True)
        self._dragged_to = (wx + dx, wy + dy)
        self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def _on_release(self, e) -> None:
        press, self._press = self._press, None
        if not press:
            return
        if press[4]:
            save_position(*self._dragged_to)
        elif self.status.mood() == "approval":
            self._open()                      # Kelvin is asking: take the user to it
        else:
            import time
            self._poke_until = time.time() + POKE_MS / 1000

    def _on_menu(self, e) -> None:
        try:
            self.menu.entryconfigure(0, label=self.status.describe())
        except Exception:
            pass
        self.menu.tk_popup(e.x_root, e.y_root)

    def _open(self) -> None:
        try:
            self.open_ui()
        except Exception as exc:
            logger.warning("Could not open RAPR AI: %s", exc)

    def _hide_by_user(self) -> None:
        self.set_enabled(False)


_instance: Optional[DesktopKelvin] = None


def start_desktop_kelvin(open_ui: Callable[[], None]) -> Optional[DesktopKelvin]:
    """Start the floating Kelvin (Windows only for now)."""
    global _instance
    if sys.platform != "win32":
        return None
    if _instance is None:
        from helm.kelvin_status import status
        _instance = DesktopKelvin(status, open_ui, set_enabled=set_pet_enabled)
        _instance.start()
    return _instance


def set_pet_enabled(on: bool) -> None:
    """Show or hide desktop Kelvin and remember the choice."""
    value = "1" if on else "0"
    os.environ["KELVIN_DESKTOP_PET"] = value
    try:
        from helm.web_routes.app import update_env
        update_env("KELVIN_DESKTOP_PET", value)
    except Exception as exc:
        logger.debug("Could not save desktop Kelvin setting: %s", exc)
