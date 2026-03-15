"""
helm/ai_runner/helpers.py — Helper utilities and notification functions.

Covers: forward_to_telegram, tg_update_focus, tg_progress_notify, change_cwd.
"""

import asyncio
import pathlib
import time
from typing import Optional

import helm.state as _st
from helm.broadcast import push_message, push_state
from helm.config import logger
from helm.history import save_cwd_to_log, save_last_state
from helm.session_mgr import focused_session


# ─────────────────────────────────────────────────────────────────────────────
# Telegram notification helpers
# ─────────────────────────────────────────────────────────────────────────────

async def forward_to_telegram(text: str):
    """Send a message to the user's Telegram chat (fire-and-forget)."""
    if _st.telegram_app and _st.telegram_chat_id:
        try:
            await _st.telegram_app.bot.send_message(chat_id=_st.telegram_chat_id, text=text)
        except Exception as e:
            logger.warning("Telegram forward failed: %s", e)


_forward_to_telegram = forward_to_telegram  # legacy alias


async def tg_update_focus():
    """Notify Telegram that the focused session has changed."""
    if not (_st.telegram_app and _st.telegram_chat_id):
        return
    from helm.telegram_bot import session_controls_keyboard, sessions_keyboard
    sess = focused_session()
    if sess:
        msg = f"✨ *{sess['name']}*\n📂 `{sess['cwd']}`"
        markup = session_controls_keyboard()
    else:
        msg = "No session focused."
        markup = sessions_keyboard()

    try:
        await _st.telegram_app.bot.send_message(
            chat_id=_st.telegram_chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        logger.warning("Telegram focus update failed: %s", e)


_tg_update_focus = tg_update_focus  # legacy alias


async def tg_progress_notify(sess: dict, output: str, elapsed: float, source: str,
                             prompt_text: str = "") -> None:
    """Send a compact Telegram ping when a session finishes a task."""
    if not (_st.telegram_app and _st.telegram_chat_id):
        return

    running = [s for s in _st.sessions.values() if s["status"] == "running"]
    multi   = len(running) >= 2
    web_src = source == "web"

    if not multi and not web_src:
        return  # single session via Telegram — reply already serves as notification

    # For web-sourced messages: forward the user's input first
    if web_src and prompt_text:
        try:
            await _st.telegram_app.bot.send_message(
                chat_id=_st.telegram_chat_id,
                text=f"🖥️ You (web): {prompt_text}",
            )
        except Exception:
            pass

    # Format elapsed time
    if elapsed < 60:
        elapsed_str = f"{elapsed:.0f}s"
    elif elapsed < 3600:
        elapsed_str = f"{elapsed/60:.1f}m"
    else:
        elapsed_str = f"{elapsed/3600:.1f}h"

    # Truncate output preview to one readable line
    preview = " ".join(output.strip().splitlines()[:3])
    if len(preview) > 300:
        preview = preview[:297] + "..."

    lines = [f"✨ *{sess['name']}* — {elapsed_str}"]
    if preview:
        lines.append(preview)

    # Check if all running sessions are now idle (busy == False)
    still_busy = [s for s in running if s.get("busy")]
    if not still_busy and multi:
        lines.append(f"\n🏁 All {len(running)} sessions idle")

    try:
        await _st.telegram_app.bot.send_message(
            chat_id=_st.telegram_chat_id,
            text="\n".join(lines),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning("Progress notify failed: %s", e)


_tg_progress_notify = tg_progress_notify  # legacy alias


# ─────────────────────────────────────────────────────────────────────────────
# CWD change
# ─────────────────────────────────────────────────────────────────────────────

async def change_cwd(new_path: str, source: str = "web",
                     session_id: Optional[str] = None) -> bool:
    """Validate and switch the CWD of the focused (or given) session."""
    sid  = session_id or _st.focused_id
    sess = _st.sessions.get(sid) if sid else None
    if not new_path.strip():
        await push_message("system", "❌ Path cannot be empty.", source=source)
        return False
    path = pathlib.Path(new_path.strip()).expanduser().resolve()
    if not path.exists():
        await push_message("system", f"❌ Directory not found: {path}", source=source)
        return False
    if not path.is_dir():
        await push_message("system", f"❌ Not a directory: {path}", source=source)
        return False
    new_cwd = str(path)
    _st.last_cwd = new_cwd  # remember the last selected CWD even with no active session
    if sess:
        sess["cwd"] = new_cwd
    save_cwd_to_log(new_cwd, session_id=sid)
    save_last_state()
    logger.info("Working directory changed to: %s", new_cwd)
    await push_state()
    # If no session focused, don't pollute default log with the announcement
    await push_message("system", f"📂 Working directory -> {new_cwd}", source=source,
                       session_id=sid, log=(sid is not None))
    return True


_change_cwd = change_cwd  # legacy alias
