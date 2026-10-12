"""
helm/ai_runner/helpers.py — Helper utilities and notification functions.

Covers: forward_to_telegram, tg_update_focus, tg_progress_notify, change_cwd.
"""

import asyncio
import pathlib
import re
import time
from typing import Optional

import helm.state as _st
from helm.broadcast import push_message, push_state
from helm.config import logger
from helm.history import save_cwd_to_log, save_last_state
from helm.session_mgr import focused_session


# Lines matching these patterns are stderr noise (Node.js warnings, SSH
# banners, etc.) and should be stripped from AI output before displaying
# on Telegram or building previews.
_NOISE_RE = re.compile(
    r"^\(node:\d+\)|"               # (node:5199) …
    r"^UNDICI-|"                     # UNDICI-EHPA Warning …
    r"^Warning:|"                    # generic Warning: lines
    r"^\(Use node --trace-warnings", # (Use node --trace-warnings …)
    re.IGNORECASE,
)


def _clean_output(text: str) -> str:
    """Remove stderr noise lines (Node.js warnings etc.) from AI output."""
    return "\n".join(
        line for line in text.splitlines()
        if not _NOISE_RE.match(line.strip())
    ).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Telegram notification helpers
# ─────────────────────────────────────────────────────────────────────────────

# Module-level lock prevents interleaved Telegram messages when multiple
# sessions finish at roughly the same time.
_tg_send_lock = asyncio.Lock()


async def forward_to_telegram(text: str, reply_markup=None):
    """Send a message to the user's Telegram chat (fire-and-forget).

    If *reply_markup* is not supplied, the session-controls keyboard is
    attached automatically so the user always has action buttons visible.
    Acquires ``_tg_send_lock`` to prevent interleaved messages.
    """
    if _st.telegram_app and _st.telegram_chat_id:
        if reply_markup is None:
            try:
                from helm.telegram_bot import session_controls_keyboard
                reply_markup = session_controls_keyboard()
            except Exception:
                pass
        async with _tg_send_lock:
            try:
                await _st.telegram_app.bot.send_message(
                    chat_id=_st.telegram_chat_id, text=text,
                    reply_markup=reply_markup,
                )
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

    async with _tg_send_lock:
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
    """Send a Telegram notification when a session finishes a task.

    For web-sourced messages: forwards the full AI response to Telegram
    (not just a preview) so the user sees the same content on both UI and
    Telegram.  Noise lines (Node.js warnings etc.) are stripped first.

    The **last** message in every notification always carries the session-
    controls inline keyboard so the user never has to scroll up for buttons.

    The entire notification sequence is wrapped in ``_tg_send_lock`` so
    messages from different sessions never interleave.
    """
    if not (_st.telegram_app and _st.telegram_chat_id):
        return
    if source == "agent" or (sess or {}).get("agent_silent_telegram"):
        return

    # Resolve the controls keyboard once — attached to the final message
    try:
        from helm.telegram_bot import session_controls_keyboard
        _kb = session_controls_keyboard()
    except Exception:
        _kb = None

    running = [s for s in _st.sessions.values() if s["status"] == "running"]
    multi   = len(running) >= 2
    # The web UI and the other chat apps are mirrored to Telegram.
    web_src = source in ("web",) + _CHAT_APPS

    if not multi and not web_src:
        return  # single session via Telegram — reply already serves as notification

    # Hold the lock for the entire notification sequence so multi-message
    # notifications from different sessions don't interleave.
    async with _tg_send_lock:
        # For web-sourced messages: forward the user's input first (no buttons)
        if web_src and prompt_text:
            try:
                await _st.telegram_app.bot.send_message(
                    chat_id=_st.telegram_chat_id,
                    text=(f"📱 You ({_APP_NAMES.get(source, source)}): {prompt_text}" if source != "web"
                          else f"🖥️ You (web): {prompt_text}"),
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

        # Clean noise lines (Node.js warnings, SSH banners, etc.)
        clean = _clean_output(output) if output else ""

        # ── Send the full response to Telegram (chunked if needed) ────────
        # Header line
        header = f"✨ {sess['name']} — {elapsed_str}"

        # Check if all running sessions are now idle
        still_busy = [s for s in running if s.get("busy")]
        if not still_busy and multi:
            header += f"\n🏁 All {len(running)} sessions idle"

        # If there's no body to send, attach keyboard to the header itself
        has_body = bool(clean) or (not clean and output)
        try:
            await _st.telegram_app.bot.send_message(
                chat_id=_st.telegram_chat_id,
                text=header,
                reply_markup=_kb if not has_body else None,
            )
        except Exception as e:
            logger.warning("Progress notify header failed: %s", e)

        # Send the full cleaned response in Telegram-safe chunks
        if clean:
            max_len = 3800
            chunks = [clean[i:i + max_len] for i in range(0, len(clean), max_len)]
            for idx, chunk in enumerate(chunks):
                is_last = idx == len(chunks) - 1
                try:
                    await _st.telegram_app.bot.send_message(
                        chat_id=_st.telegram_chat_id,
                        text=chunk,
                        reply_markup=_kb if is_last else None,
                    )
                except Exception as e:
                    logger.warning("Progress notify chunk failed: %s", e)
                    break
        elif not clean and output:
            # Output was entirely noise — send a note instead of nothing
            try:
                await _st.telegram_app.bot.send_message(
                    chat_id=_st.telegram_chat_id,
                    text="(response contained only system warnings — check the UI for details)",
                    reply_markup=_kb,
                )
            except Exception:
                pass


_tg_progress_notify = tg_progress_notify  # legacy alias


# ---------------------------------------------------------------------------
# Keep every linked chat app in sync with a session (Telegram is handled above)
# ---------------------------------------------------------------------------

_CHAT_APPS = ("whatsapp", "discord", "slack")
_APP_NAMES = {"web": "the app", "telegram": "Telegram", "whatsapp": "WhatsApp",
              "discord": "Discord", "slack": "Slack"}
_MIRROR_PROMPT_MAX = 500


async def mirror_to_chat_apps(sess: dict, output: str, source: str, prompt_text: str = "") -> None:
    """Send a finished session exchange (your message and the AI's reply) to every
    linked chat app except the one it came from, so they all stay in sync.
    Uses the senders the chat apps register for group chats; each one does nothing
    when its app isn't linked. Telegram has its own mirror (tg_progress_notify)."""
    if not sess or source == "agent" or sess.get("agent_silent_telegram"):
        return
    try:
        import helm.groupchat as gc
        senders = [(ch, fn) for ch, fn in list(gc._channel_senders.items())
                   if ch in _CHAT_APPS and ch != source]
    except Exception:
        return
    if not senders:
        return
    clean = (_clean_output(output) if output else "") or (output or "")
    prompt = (prompt_text or "").strip()
    if len(prompt) > _MIRROR_PROMPT_MAX:
        prompt = prompt[:_MIRROR_PROMPT_MAX] + "…"
    head = f"{sess.get('emoji') or '🤖'} {sess.get('name') or 'AI'}"
    text = head + (f"\n🧑 You (from {_APP_NAMES.get(source, source)}): {prompt}" if prompt else "")
    text += f"\n\n{clean.strip()}" if clean.strip() else ""
    for channel, send in senders:
        try:
            await send({}, text)
        except Exception as exc:
            logger.warning("mirror to %s failed: %s", channel, exc)


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
