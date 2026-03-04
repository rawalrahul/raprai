"""
helm/telegram_bot/auth.py — Authorization and message sending utilities.

Covers: authorized_only decorator, tg_send_chunks helper.
"""

import asyncio
from functools import wraps

import helm.state as _st
from helm.config import ALLOWED_USER_IDS, logger


def authorized_only(func):
    """Decorator to check if user is authorized."""
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if not ALLOWED_USER_IDS:
            await update.message.reply_text(
                "⛔ Bot is locked — no authorised users are configured.\n\n"
                "Add your Telegram user ID to ALLOWED_USER_IDS in your .env file, "
                "then restart RAPR AI."
            )
            logger.error(
                "SECURITY: Blocked user %d — ALLOWED_USER_IDS is empty. "
                "Set ALLOWED_USER_IDS in .env and restart.",
                user_id,
            )
            return
        if user_id not in ALLOWED_USER_IDS:
            await update.message.reply_text("⛔ Unauthorized.")
            logger.warning("Rejected unauthorised user %d", user_id)
            return
        # Store chat_id so web-initiated responses can be forwarded
        _st.telegram_chat_id = update.effective_chat.id
        return await func(update, context)
    return wrapper


async def tg_send_chunks(update, text: str, max_len: int = 3800, reply_markup=None):
    """Send text in Telegram-safe chunks. Attaches reply_markup to the last chunk."""
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)] if text.strip() else []
    if not chunks:
        await update.message.reply_text("(no output)", reply_markup=reply_markup)
        return
    for idx, chunk in enumerate(chunks):
        is_last = idx == len(chunks) - 1
        await update.message.reply_text(chunk, reply_markup=reply_markup if is_last else None)


# Legacy alias
_tg_send_chunks = tg_send_chunks
