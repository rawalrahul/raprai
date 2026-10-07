"""
helm/kelvin_status.py — Kelvin on the desktop.

Watches the same events the web UI gets (helm.broadcast calls observe()) and
boils them down to one mood for the whole app:

    approval > error > working > done > idle

The tray (helm/tray.py) subscribes to show a Kelvin badge next to the RAPR
logo, a status line in its menu, and a Windows notification when an approval
is waiting. The startup banner for console launches also lives here.
"""

import os
import sys
import threading
import time
from typing import Callable, Optional

from helm.paths import PROJECT_ROOT

ASSET_DIR = PROJECT_ROOT / "frontend2" / "assets" / "kelvin"

MOODS = ("idle", "working", "approval", "done", "error")
DONE_SECONDS = 8
ERROR_SECONDS = 30

# Badge background per mood: idle navy, working amber, approval blue, done green, error red.
BADGE_COLORS = {
    "idle": (58, 71, 96, 255),
    "working": (242, 179, 61, 255),
    "approval": (91, 156, 245, 255),
    "done": (52, 211, 153, 255),
    "error": (248, 113, 113, 255),
}


class KelvinStatus:
    """Thread-safe summary of what RAPR's agents are doing right now."""

    def __init__(self):
        self._lock = threading.Lock()
        self._busy: set[str] = set()
        self._approvals: dict[str, str] = {}
        self._done_until = 0.0
        self._error_until = 0.0
        self._listeners: list[Callable[[str, Optional[dict]], None]] = []
        self._last_mood = "idle"

    # -- input ---------------------------------------------------------------

    def observe(self, data: dict) -> None:
        """Feed every broadcast payload here. Never raises."""
        try:
            self._observe(data)
        except Exception:
            pass

    def _observe(self, data: dict) -> None:
        kind = data.get("type")
        now = time.time()
        new_approval = None
        with self._lock:
            if kind == "thinking":
                sid = data.get("session_id") or "_"
                if data.get("active"):
                    self._busy.add(sid)
                else:
                    self._busy.discard(sid)
            elif kind == "approval_request":
                req = data.get("approval") or {}
                rid = str(req.get("id") or len(self._approvals))
                self._approvals[rid] = req.get("description") or "An action needs your approval"
                new_approval = {"id": rid, "description": self._approvals[rid]}
            elif kind == "approval_resolved":
                req = data.get("approval") or {}
                self._approvals.pop(str(req.get("id")), None)
            elif kind == "agent_error":
                self._error_until = now + ERROR_SECONDS
            elif kind == "message" and data.get("role") == "assistant":
                self._done_until = now + DONE_SECONDS
                self._error_until = 0.0
            elif kind == "pipeline_update":
                status = (data.get("pipeline") or {}).get("status")
                if status == "completed":
                    self._done_until = now + DONE_SECONDS
                elif status == "failed":
                    self._error_until = now + ERROR_SECONDS
            else:
                return
        self._notify(new_approval)

    # -- output --------------------------------------------------------------

    def mood(self, now: Optional[float] = None) -> str:
        now = now or time.time()
        with self._lock:
            if self._approvals:
                return "approval"
            if now < self._error_until:
                return "error"
            if self._busy:
                return "working"
            if now < self._done_until:
                return "done"
            return "idle"

    def describe(self, now: Optional[float] = None) -> str:
        mood = self.mood(now)
        with self._lock:
            busy, approvals = len(self._busy), len(self._approvals)
        if mood == "approval":
            return "Kelvin: waiting for your approval" if approvals == 1 else f"Kelvin: {approvals} approvals waiting"
        if mood == "error":
            return "Kelvin: something went wrong"
        if mood == "working":
            return "Kelvin: working" if busy == 1 else f"Kelvin: {busy} sessions working"
        if mood == "done":
            return "Kelvin: done"
        return "Kelvin: idle"

    def subscribe(self, fn: Callable[[str, Optional[dict]], None]) -> None:
        """fn(mood, new_approval_or_None) runs whenever the mood changes or an approval arrives."""
        self._listeners.append(fn)

    def tick(self) -> None:
        """Call periodically so timed moods (done, error) expire on screen."""
        self._notify(None)

    def _notify(self, new_approval: Optional[dict]) -> None:
        mood = self.mood()
        if mood == self._last_mood and new_approval is None:
            return
        self._last_mood = mood
        for fn in list(self._listeners):
            try:
                fn(mood, new_approval)
            except Exception:
                pass


status = KelvinStatus()


# ---------------------------------------------------------------------------
# Tray icon: RAPR logo with a Kelvin badge in the corner
# ---------------------------------------------------------------------------

def tray_icon_image(mood: str, logo=None, size: int = 64):
    """Return a PIL image: the RAPR logo with a coloured Kelvin badge (bottom right)."""
    from PIL import Image, ImageDraw

    if logo is None:
        logo_path = PROJECT_ROOT / "rapr-logo.png"
        logo = Image.open(logo_path).convert("RGBA") if logo_path.exists() else Image.new("RGBA", (size, size), (106, 99, 255, 255))
    base = logo.convert("RGBA").resize((size, size), Image.LANCZOS)

    badge = int(size * 0.56)
    x0, y0 = size - badge, size - badge
    ring = max(2, size // 32)
    draw = ImageDraw.Draw(base)
    draw.ellipse((x0, y0, size - 1, size - 1), fill=(15, 13, 11, 255))  # dark outline ring
    draw.ellipse((x0 + ring, y0 + ring, size - 1 - ring, size - 1 - ring), fill=BADGE_COLORS.get(mood, BADGE_COLORS["idle"]))

    face_path = ASSET_DIR / f"tray-{mood}.png"
    if face_path.exists():
        face = Image.open(face_path).convert("RGBA")
        inner = badge - 2 * ring
        face = face.resize((inner, inner), Image.LANCZOS)
        mask = Image.new("L", (inner, inner), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, inner - 1, inner - 1), fill=255)
        clipped = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
        clipped.paste(face, (0, 0), Image.composite(face.getchannel("A"), mask, mask))
        base.alpha_composite(clipped, (x0 + ring, y0 + ring))
    return base


# ---------------------------------------------------------------------------
# Startup banner (only when RAPR is launched from a real console)
# ---------------------------------------------------------------------------

BANNER = "\n".join([
    '       (@)',
    '   .-"""""""-.',
    '  /===========\\',
    '  |  o     o  |',
    '  |     v     |',
    "   \\ '-...-' /",
    "    '-.___.-'",
])


def startup_banner(url: str, stream=None) -> Optional[str]:
    """Print a small ASCII Kelvin with the app URL. Plain ASCII so any console can show it."""
    stream = stream or sys.stdout
    try:
        if stream is None or not stream.isatty():
            return None
    except Exception:
        return None
    art = BANNER
    color = not os.environ.get("NO_COLOR") and (sys.platform != "win32" or os.environ.get("WT_SESSION"))
    amber, dim, reset = ("\033[38;2;242;179;61m", "\033[2m", "\033[0m") if color else ("", "", "")
    text = (
        f"{amber}{art}{reset}\n\n"
        f"   RAPR AI is running at {url}\n"
        f"   {dim}Kelvin is keeping an eye on your sessions.{reset}\n"
    )
    try:
        stream.write(text + "\n")
        stream.flush()
    except Exception:
        return None
    return text
