"""
helm/desktop_kelvin.py — Kelvin on your desktop, like Codex Pets.

A small, frameless, always-on-top window showing an animated Kelvin that
follows what RAPR's AIs are doing (helm/kelvin_status.py). Users can:
  - drag Kelvin anywhere (position is remembered, across monitors)
  - click Kelvin for a little hop, or to open RAPR when an approval waits
  - double-click to open RAPR AI
  - scroll the mouse wheel over Kelvin to make him bigger or smaller
  - hover for a ✕ that hides him
  - right-click for a menu (status, Open RAPR AI, Size, Show, Hide for 1 hour, Hide)

KELVIN_DESKTOP_PET picks when Kelvin is on screen: "1" always (default),
"working" only while an AI is working or needs you, "0" never.
KELVIN_DESKTOP_SIZE is small, medium (default) or large. Both are also in the
tray menu ("Kelvin on desktop") and Settings, so he can be brought back any time.

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

SIZES = {"small": 0.5, "medium": 0.75, "large": 1.0}
SIZE_ORDER = ("small", "medium", "large")
DEFAULT_SIZE = "medium"
MODES = ("always", "working", "off")
MODE_LABELS = {"always": "Always", "working": "Only while AI works", "off": "Hidden"}
SNOOZE_SECONDS = 60 * 60
# Moods that bring Kelvin out in "working" mode ("done" lingers a few seconds, then he leaves).
BUSY_MOODS = ("working", "thinking", "approval", "error", "done")


def pet_mode() -> str:
    """always | working | off, from KELVIN_DESKTOP_PET."""
    raw = os.environ.get("KELVIN_DESKTOP_PET", "1").strip().lower()
    if raw in ("0", "false", "no", "off", "hidden"):
        return "off"
    if raw in ("working", "auto", "busy"):
        return "working"
    return "always"


def pet_enabled() -> bool:
    return pet_mode() != "off"


def pet_size() -> str:
    raw = os.environ.get("KELVIN_DESKTOP_SIZE", DEFAULT_SIZE).strip().lower()
    return raw if raw in SIZES else DEFAULT_SIZE


def pet_box(size: Optional[str] = None) -> tuple:
    """Window size in pixels for a Kelvin size."""
    f = SIZES[size or pet_size()]
    return round(PET_W * f), round(PET_H * f)


def next_size(size: str, step: int) -> str:
    i = SIZE_ORDER.index(size) + step
    return SIZE_ORDER[min(max(i, 0), len(SIZE_ORDER) - 1)]


def should_show(mode: str, mood: str, snoozed: bool) -> bool:
    """Is Kelvin on screen right now?"""
    if mode == "off":
        return False
    if mood == "approval":
        return True          # an approval waiting always gets a Kelvin, even when snoozed
    if snoozed:
        return False
    return mode == "always" or mood in BUSY_MOODS


def resize_anchor(x: int, y: int, old: tuple, new: tuple) -> tuple:
    """Keep the bottom-right corner where it was, so Kelvin grows up and left."""
    return x + old[0] - new[0], y + old[1] - new[1]


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


def clamp_position(x: int, y: int, screen: tuple, box: Optional[tuple] = None) -> tuple:
    """Keep at least part of Kelvin on screen (e.g. after a monitor was unplugged).

    screen = (left, top, width, height) of the whole virtual desktop.
    """
    left, top, width, height = screen
    w = (box or (PET_W, PET_H))[0]
    margin = 40
    x = min(max(x, left - w + margin), left + width - margin)
    y = min(max(y, top), top + height - margin)
    return x, y


def default_position(screen: tuple, box: Optional[tuple] = None) -> tuple:
    """Bottom-right corner, above the taskbar."""
    left, top, width, height = screen
    w, h = box or (PET_W, PET_H)
    return left + width - w - 24, top + height - h - 64


def pet_mood(status, now: Optional[float] = None) -> str:
    mood = status.mood(now)
    if mood == "idle" and status.idle_seconds(now) > SLEEP_AFTER_SECONDS:
        return "sleeping"
    if mood == "working" and not status.counts()["pipelines"]:
        return "thinking"   # sessions waiting on their AI; the gear is for running pipelines
    return mood


def load_strip(mood: str, box: Optional[tuple] = None):
    """Return the RGBA frames for one mood from its sprite strip, scaled to box."""
    from PIL import Image
    strip = Image.open(ASSET_DIR / f"pet-{mood}.png").convert("RGBA")
    count = max(1, strip.width // PET_W)
    frames = [strip.crop((i * PET_W, 0, (i + 1) * PET_W, PET_H)) for i in range(count)]
    if box and tuple(box) != (PET_W, PET_H):
        frames = [f.resize(box, Image.LANCZOS) for f in frames]
    return frames


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
                 transparent: Optional[bool] = None,
                 on_hidden: Optional[Callable[[str], None]] = None):
        self.status = status
        self.open_ui = open_ui
        self.set_enabled = set_enabled or (lambda on: os.environ.__setitem__("KELVIN_DESKTOP_PET", "1" if on else "0"))
        self.on_hidden = on_hidden or (lambda message: None)
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
        self._size = None
        self._snooze_until = 0.0

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
        # A small ✕ in the corner while the pointer is over Kelvin: one click hides him.
        self.close_btn = tk.Label(root, text="✕", font=("Segoe UI", 9, "bold"), fg="#f6efe3", bg="#1f1a14",
                                  padx=4, pady=0, cursor="hand2")
        self.close_btn.bind("<ButtonRelease-1>", lambda e: self._hide_by_user())

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Kelvin", state="disabled")
        self.menu.add_separator()
        self.menu.add_command(label="Open RAPR AI", command=self._open)
        self.size_var = tk.StringVar(master=root, value=pet_size())
        size_menu = tk.Menu(self.menu, tearoff=0)
        for name in SIZE_ORDER:
            size_menu.add_radiobutton(label=name.title(), value=name, variable=self.size_var,
                                      command=lambda n=name: set_pet_size(n))
        self.menu.add_cascade(label="Size (or scroll over Kelvin)", menu=size_menu)
        self.mode_var = tk.StringVar(master=root, value=pet_mode())
        show_menu = tk.Menu(self.menu, tearoff=0)
        for mode in ("always", "working"):
            show_menu.add_radiobutton(label=MODE_LABELS[mode], value=mode, variable=self.mode_var,
                                      command=lambda m=mode: set_pet_mode(m))
        self.menu.add_cascade(label="Show", menu=show_menu)
        self.menu.add_separator()
        self.menu.add_command(label="Hide for 1 hour", command=self._snooze)
        self.menu.add_command(label="Hide Kelvin", command=self._hide_by_user)

        for widget in (root, self.label):
            widget.bind("<ButtonPress-1>", self._on_press)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<Double-Button-1>", lambda e: self._open())
            widget.bind("<Button-3>", self._on_menu)
            widget.bind("<MouseWheel>", self._on_wheel)       # Windows / macOS
            widget.bind("<Button-4>", lambda e: self._resize_step(1))   # X11
            widget.bind("<Button-5>", lambda e: self._resize_step(-1))
        root.bind("<Enter>", lambda e: self.close_btn.place(relx=1.0, x=-2, y=2, anchor="ne"))
        root.bind("<Leave>", self._on_leave)

        self.root = root
        self._size = pet_size()
        box = pet_box(self._size)
        screen = _virtual_screen(root)
        x, y = load_position() or default_position(screen, box)
        x, y = clamp_position(x, y, screen, box)
        root.geometry(f"{box[0]}x{box[1]}+{x}+{y}")
        self._tick()

    # -- animation -----------------------------------------------------------

    def _frames_for(self, mood: str):
        if mood not in self._frames:
            from PIL import ImageTk
            bg = KEY_COLOR if self.transparent else FALLBACK_BG
            box = pet_box(self._size)
            self._frames[mood] = [ImageTk.PhotoImage(flatten(f, bg), master=self.root)
                                  for f in load_strip(mood, box)]
        return self._frames[mood]

    def _apply_size(self, size: str) -> None:
        """Switch to a new size, keeping the bottom-right corner in place."""
        old = pet_box(self._size)
        new = pet_box(size)
        self._size = size
        self._frames.clear()
        x, y = resize_anchor(self.root.winfo_x(), self.root.winfo_y(), old, new)
        x, y = clamp_position(x, y, _virtual_screen(self.root), new)
        self.root.geometry(f"{new[0]}x{new[1]}+{x}+{y}")
        save_position(x, y)
        try:
            self.size_var.set(size)
        except Exception:
            pass

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
            import time
            if pet_size() != self._size:
                self._apply_size(pet_size())
            mood = self.current_mood()
            want = should_show(pet_mode(), mood, time.time() < self._snooze_until)
            if want != self._shown:
                (self.root.deiconify if want else self.root.withdraw)()
                if want:
                    self.root.attributes("-topmost", True)
                self._shown = want
            if want:
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

    def _on_leave(self, e) -> None:
        # <Leave> also fires when moving onto the ✕ itself; only hide it once outside the window.
        x, y = self.root.winfo_pointerxy()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        if not (rx <= x < rx + self.root.winfo_width() and ry <= y < ry + self.root.winfo_height()):
            self.close_btn.place_forget()

    def _on_wheel(self, e) -> None:
        self._resize_step(1 if e.delta > 0 else -1)

    def _resize_step(self, step: int) -> None:
        # Step from the saved size: fast scrolling can outrun the next frame redraw.
        size = next_size(pet_size(), step)
        if size != pet_size():
            set_pet_size(size)

    def _snooze(self) -> None:
        import time
        self._snooze_until = time.time() + SNOOZE_SECONDS
        self.on_hidden("Kelvin is taking a 1 hour break. He'll still pop up if an AI needs your approval.")

    def _hide_by_user(self) -> None:
        self.close_btn.place_forget()
        self.set_enabled(False)
        self.on_hidden("Kelvin is hidden. Bring him back from the tray icon (Kelvin on desktop) or Settings.")


_instance: Optional[DesktopKelvin] = None


def start_desktop_kelvin(open_ui: Callable[[], None],
                         on_hidden: Optional[Callable[[str], None]] = None) -> Optional[DesktopKelvin]:
    """Start the floating Kelvin (Windows only for now)."""
    global _instance
    if sys.platform != "win32":
        return None
    if _instance is None:
        from helm.kelvin_status import status
        _instance = DesktopKelvin(status, open_ui, set_enabled=set_pet_enabled, on_hidden=on_hidden)
        _instance.start()
    return _instance


def _save_setting(key: str, value: str) -> None:
    os.environ[key] = value
    try:
        from helm.web_routes.app import update_env
        update_env(key, value)
    except Exception as exc:
        logger.debug("Could not save %s: %s", key, exc)


def set_pet_mode(mode: str) -> None:
    """always | working | off — remembered across restarts."""
    _save_setting("KELVIN_DESKTOP_PET", {"always": "1", "working": "working", "off": "0"}[mode])


def set_pet_enabled(on: bool) -> None:
    """Show or hide desktop Kelvin and remember the choice."""
    set_pet_mode("always" if on else "off")


def set_pet_size(size: str) -> None:
    if size in SIZES:
        _save_setting("KELVIN_DESKTOP_SIZE", size)
