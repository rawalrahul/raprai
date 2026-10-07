"""
helm/kelvin_stickers.py — Kelvin mood stickers on Telegram (opt-in).

Off by default. Users turn it on in Settings (TELEGRAM_KELVIN_STICKERS=1).
Stickers are sent only at moments that matter, so the chat stays readable:
  - approval  alongside an approval request
  - error     when a run fails for good (after retries and fallbacks)
  - done      when a long task or a whole pipeline finishes

Images live in frontend2/assets/kelvin/ and are regenerated with
scripts/render_kelvin_assets.cjs.
"""

import asyncio
import os
from typing import Optional

import helm.state as _st
from helm.config import logger
from helm.paths import PROJECT_ROOT

STICKER_DIR = PROJECT_ROOT / "frontend2" / "assets" / "kelvin"
MOODS = ("done", "error", "approval", "working", "idle")
LONG_TASK_SECONDS = 60
# Sub-runs (pipeline steps, Agent Builder nodes) report through their parent instead.
QUIET_SOURCES = ("pipeline", "agent")

# Telegram returns a file_id after the first upload; reuse it to avoid re-uploading.
_file_ids: dict[str, str] = {}


def stickers_enabled() -> bool:
    return os.environ.get("TELEGRAM_KELVIN_STICKERS", "0").strip().lower() in ("1", "true", "yes", "on")


def sticker_path(mood: str):
    return STICKER_DIR / f"sticker-{mood}.webp"


async def send_kelvin_sticker(mood: str) -> bool:
    """Send one Kelvin sticker to the owner's Telegram chat. Never raises."""
    if mood not in MOODS or not stickers_enabled():
        return False
    if not (_st.telegram_app and _st.telegram_chat_id):
        return False
    try:
        sticker = _file_ids.get(mood)
        if sticker is None:
            path = sticker_path(mood)
            if not path.exists():
                logger.warning("Kelvin sticker missing: %s", path)
                return False
            sticker = path.read_bytes()
        msg = await _st.telegram_app.bot.send_sticker(chat_id=_st.telegram_chat_id, sticker=sticker)
        file_id = getattr(getattr(msg, "sticker", None), "file_id", None)
        if file_id:
            _file_ids[mood] = file_id
        return True
    except Exception as exc:
        logger.warning("Kelvin sticker (%s) failed: %s", mood, exc)
        return False


def kelvin_sticker_soon(mood: str) -> Optional[asyncio.Task]:
    """Fire-and-forget version for call sites that must not wait on Telegram."""
    if not stickers_enabled():
        return None
    try:
        return asyncio.get_running_loop().create_task(send_kelvin_sticker(mood))
    except RuntimeError:
        return None


def done_sticker_for_task(elapsed: float, output: str = "", source: str = "") -> Optional[asyncio.Task]:
    """Celebrate only long, user-started tasks that actually produced something."""
    text = (output or "").strip()
    if source in QUIET_SOURCES or elapsed < LONG_TASK_SECONDS or not text or text == "(stopped)":
        return None
    return kelvin_sticker_soon("done")


def error_sticker_for_task(source: str = "") -> Optional[asyncio.Task]:
    if source in QUIET_SOURCES:
        return None
    return kelvin_sticker_soon("error")
