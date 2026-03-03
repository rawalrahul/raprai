"""
helm/telegram_bot/browse.py — Directory browsing interface logic.

Covers: tg_browse, show_browse, browse state management.
"""

import pathlib

from helm.config import ALLOWED_USER_IDS

from .auth import authorized_only
from .keyboards import session_controls_keyboard, sessions_keyboard

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
except ImportError:
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None


# Browse state (user_id -> {"path": str, "dirs": list, "page": int})
_tg_browse_state: dict = {}
_BROWSE_PAGE_SIZE = 8


async def show_browse(target, user_id: int, path: str, edit: bool = False, page: int = 0):
    """Render a paginated directory listing as a Telegram inline keyboard."""
    from helm.session_mgr import session_cwd
    try:
        p = pathlib.Path(path).resolve()
        all_dirs = sorted(
            [d.name for d in p.iterdir() if d.is_dir()],
            key=lambda x: x.lower(),
        )
    except (PermissionError, OSError):
        all_dirs = []

    _tg_browse_state[user_id] = {"path": str(p), "dirs": all_dirs, "page": page}

    total = len(all_dirs)
    start = page * _BROWSE_PAGE_SIZE
    end = min(start + _BROWSE_PAGE_SIZE, total)
    page_dirs = all_dirs[start:end]
    total_pages = max(1, (total + _BROWSE_PAGE_SIZE - 1) // _BROWSE_PAGE_SIZE)

    keyboard: list[list] = []
    if str(p) != str(p.parent):
        keyboard.append([InlineKeyboardButton("⬆ Parent directory", callback_data="browse_up")])
    for i, d in enumerate(page_dirs):
        keyboard.append([InlineKeyboardButton(f"📂 {d}", callback_data=f"browse_d:{start + i}")])
    nav_row: list = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀ Prev", callback_data=f"browse_p:{page - 1}"))
    if end < total:
        nav_row.append(InlineKeyboardButton("▶ Next", callback_data=f"browse_p:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([
        InlineKeyboardButton("✅ Set as working dir", callback_data="browse_select"),
        InlineKeyboardButton("❌ Cancel", callback_data="browse_cancel"),
    ])

    text = f"📁 `{str(p)}`\n_{total} subfolder(s)_"
    if total_pages > 1:
        text += f" — page {page + 1}/{total_pages}"
    markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await target.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await target.reply_text(text, reply_markup=markup, parse_mode="Markdown")


_show_browse = show_browse  # legacy alias


@authorized_only
async def tg_browse(update, context):
    """/browse [path] — interactively navigate folders and set working directory."""
    from helm.session_mgr import session_cwd
    arg = (update.message.text or "").partition(" ")[2].strip()
    start = arg if arg else session_cwd()
    user_id = update.effective_user.id
    await show_browse(update.message, user_id, start, edit=False, page=0)


async def browse_callback(update, context):
    """Handle all inline keyboard button presses from /browse."""
    from helm.session_mgr import focused_session, session_cwd
    from helm.ai_runner import change_cwd

    query = update.callback_query
    user_id = query.from_user.id
    if not ALLOWED_USER_IDS or user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()

    data = query.data
    state = _tg_browse_state.get(user_id, {"path": session_cwd(), "dirs": [], "page": 0})
    current_path = state["path"]
    dirs = state["dirs"]

    if data == "browse_cancel":
        _tg_browse_state.pop(user_id, None)
        fs = focused_session()
        await query.edit_message_text(
            "Browse cancelled.",
            reply_markup=session_controls_keyboard() if fs else sessions_keyboard(),
        )

    elif data == "browse_select":
        _tg_browse_state.pop(user_id, None)
        ok = await change_cwd(current_path, source="telegram")
        fs = focused_session()
        if ok:
            await query.edit_message_text(
                f"✅ Working directory set to:\n`{current_path}`\n\nWhat would you like to do next?",
                parse_mode="Markdown",
                reply_markup=session_controls_keyboard() if fs else sessions_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ Could not set directory:\n{current_path}",
                reply_markup=session_controls_keyboard() if fs else sessions_keyboard(),
            )

    elif data == "browse_up":
        p = pathlib.Path(current_path)
        parent = str(p.parent) if str(p) != str(p.parent) else current_path
        await show_browse(query, user_id, parent, edit=True, page=0)

    elif data.startswith("browse_d:"):
        try:
            idx = int(data.split(":")[1])
        except (ValueError, IndexError):
            return
        if 0 <= idx < len(dirs):
            new_path = str(pathlib.Path(current_path) / dirs[idx])
            await show_browse(query, user_id, new_path, edit=True, page=0)

    elif data.startswith("browse_p:"):
        try:
            pg = int(data.split(":")[1])
        except (ValueError, IndexError):
            return
        await show_browse(query, user_id, current_path, edit=True, page=pg)
