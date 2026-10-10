"""
helm/telegram_bot/groups.py — Group chats on Telegram.

/group opens a list of your group chats as buttons. Tap one to enter it: your
messages then go to the whole group and every reply comes back here, signed by
the AI that wrote it. "➕ New group" lets you tick AI sessions and create a
group from them. Text forms (/group 2, /group new Launch: 1 3, /group leave …)
come from helm/groupchat_channels.py and work the same on WhatsApp.
"""

import helm.state as _st
import helm.groupchat as gc
import helm.groupchat_channels as gch
from helm.config import ALLOWED_USER_IDS, logger

from .auth import authorized_only

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
except ImportError:
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None

CHANNEL = "telegram"
_MAX_LEN = 3800


def groups_keyboard():
    rows = []
    current = gc.active_groups.get(CHANNEL)
    for g in gch.ordered_groups():
        mark = "✅ " if g["id"] == current else "👥 "
        rows.append([InlineKeyboardButton(mark + g["name"][:40], callback_data=f"gc:open:{g['id']}")])
    rows.append([InlineKeyboardButton("➕ New group", callback_data="gc:new")])
    if current:
        rows.append([InlineKeyboardButton("🚪 Leave group", callback_data="gc:leave")])
    rows.append([InlineKeyboardButton("← Sessions", callback_data="ms:list")])
    return InlineKeyboardMarkup(rows)


def in_group_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏹ Stop replies", callback_data="gc:stop"),
         InlineKeyboardButton("👥 Members", callback_data="gc:who")],
        [InlineKeyboardButton("📋 All groups", callback_data="gc:list"),
         InlineKeyboardButton("🚪 Leave group", callback_data="gc:leave")],
    ])


def _picker_keyboard(picked: set):
    rows = []
    for s in gch.ai_sessions():
        tick = "☑️" if s["id"] in picked else "⬜"
        rows.append([InlineKeyboardButton(f"{tick} {s.get('emoji', '🤖')} {s['name']}",
                                          callback_data=f"gc:t:{s['id']}")])
    rows.append([InlineKeyboardButton(f"✅ Create group ({len(picked)})", callback_data="gc:mk"),
                 InlineKeyboardButton("← Back", callback_data="gc:list")])
    return InlineKeyboardMarkup(rows)


def _keyboard_for_state():
    return in_group_keyboard() if gc.active_group(CHANNEL) else groups_keyboard()


async def send_group_text(_group: dict, text: str) -> None:
    """Relay a group message to the Telegram chat (registered with groupchat)."""
    if not (_st.telegram_app and _st.telegram_chat_id):
        return
    from helm.ai_runner import forward_to_telegram
    chunks = [text[i:i + _MAX_LEN] for i in range(0, len(text), _MAX_LEN)] or [text]
    for i, chunk in enumerate(chunks):
        await forward_to_telegram(chunk, reply_markup=in_group_keyboard() if i == len(chunks) - 1 else None)


def register() -> None:
    gc.register_channel(CHANNEL, send_group_text)


@authorized_only
async def tg_group(update, context):
    """/group [args] — list, enter, create, stop or leave group chats."""
    args = " ".join(context.args or []) if context and getattr(context, "args", None) else ""
    if not args:
        await update.message.reply_text(gch.list_text(CHANNEL), reply_markup=groups_keyboard())
        return
    if args.strip().lower() == "new":
        context.user_data["gc_pick"] = set()
        await update.message.reply_text("Tick the AI sessions to put in the group:",
                                        reply_markup=_picker_keyboard(set()))
        return
    reply = await gch.handle_command(CHANNEL, args)
    await update.message.reply_text(reply, reply_markup=_keyboard_for_state())


async def handle_group_text(update, text: str) -> bool:
    """Called from tg_text. Returns True when the text was handled as group chat."""
    group = gc.active_group(CHANNEL)
    if not group:
        return False
    low = text.strip().lower()
    if low in ("leave", "leave group", "exit group", "/leave"):
        reply = await gch.handle_command(CHANNEL, "leave")
        await update.message.reply_text(reply, reply_markup=groups_keyboard())
        return True
    if low in ("stop", "stop group"):
        reply = await gch.handle_command(CHANNEL, "stop")
        await update.message.reply_text(reply, reply_markup=in_group_keyboard())
        return True
    if low in ("menu", "group", "groups"):
        await update.message.reply_text(gch.list_text(CHANNEL), reply_markup=groups_keyboard())
        return True
    await gc.send_user_message(group, text, source=CHANNEL)
    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass
    return True


async def group_callback(update, context):
    """Inline buttons with gc:* data."""
    query = update.callback_query
    if not ALLOWED_USER_IDS or query.from_user.id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()
    _st.telegram_chat_id = query.message.chat.id
    parts = (query.data or "").split(":")
    verb = parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else ""

    try:
        if verb == "list":
            await query.edit_message_text(gch.list_text(CHANNEL), reply_markup=groups_keyboard())
        elif verb == "open":
            group = gc.groups.get(arg)
            if not group:
                await query.edit_message_text("That group no longer exists.", reply_markup=groups_keyboard())
                return
            gc.set_active_group(CHANNEL, group["id"])
            await query.edit_message_text(gch.enter_text(group), reply_markup=in_group_keyboard())
        elif verb == "leave":
            reply = await gch.handle_command(CHANNEL, "leave")
            await query.edit_message_text(reply, reply_markup=groups_keyboard())
        elif verb == "stop":
            reply = await gch.handle_command(CHANNEL, "stop")
            await query.edit_message_text(reply, reply_markup=in_group_keyboard())
        elif verb == "who":
            reply = await gch.handle_command(CHANNEL, "who")
            await query.edit_message_text(reply, reply_markup=_keyboard_for_state())
        elif verb == "new":
            if not gch.ai_sessions():
                await query.edit_message_text(gch.sessions_text(), reply_markup=groups_keyboard())
                return
            context.user_data["gc_pick"] = set()
            await query.edit_message_text("Tick the AI sessions to put in the group:",
                                          reply_markup=_picker_keyboard(set()))
        elif verb == "t":
            picked = context.user_data.setdefault("gc_pick", set())
            picked.symmetric_difference_update({arg})
            await query.edit_message_reply_markup(reply_markup=_picker_keyboard(picked))
        elif verb == "mk":
            picked = context.user_data.pop("gc_pick", set())
            if not picked:
                context.user_data["gc_pick"] = set()
                await query.edit_message_text("Tick at least one AI session first:",
                                              reply_markup=_picker_keyboard(set()))
                return
            group, text = await gch.create_group(CHANNEL, "", list(picked))
            await query.edit_message_text(
                text + ("\n\nRename it any time in the web UI." if group else ""),
                reply_markup=in_group_keyboard() if group else groups_keyboard())
    except Exception as exc:
        # "Message is not modified" and similar edit races are harmless.
        logger.debug("group_callback %s: %s", query.data, exc)
