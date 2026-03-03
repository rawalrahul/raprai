"""
helm/telegram_bot/keyboards.py — Inline keyboard builders for Telegram UI.

Covers: sessions_keyboard, session_controls_keyboard, new_session_keyboard.
"""

import pathlib

import helm.state as _st

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
except ImportError:
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None


def sessions_keyboard():
    """Session list — one button per session + New Session + History/Resume."""
    from helm.session_mgr import session_status_icon
    rows: list = []
    for sess in sorted(_st.sessions.values(), key=lambda s: s["last_used"], reverse=True):
        icon = session_status_icon(sess)
        cwd_short = pathlib.Path(sess["cwd"]).name or sess["cwd"]
        label = f"{icon} {sess['name']} · {cwd_short}"
        rows.append([InlineKeyboardButton(label, callback_data=f"ms:focus:{sess['id']}")])
    rows.append([InlineKeyboardButton("➕ New Session", callback_data="ms:new")])
    rows.append([InlineKeyboardButton("📊 Usage", callback_data="ms:usage")])
    rows.append([
        InlineKeyboardButton("💬 Past chats", callback_data="action:history"),
        InlineKeyboardButton("🔄 Resume old", callback_data="action:resume"),
    ])
    return InlineKeyboardMarkup(rows)


def session_controls_keyboard():
    """Controls for the currently-focused session."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 All Sessions", callback_data="ms:list"),
            InlineKeyboardButton("📁 Change Dir", callback_data="ms:browse"),
        ],
        [
            InlineKeyboardButton("🔄 Switch AI", callback_data="ms:switch"),
            InlineKeyboardButton("⏸ Cancel Task", callback_data="ms:interrupt"),
        ],
        [
            InlineKeyboardButton("🎯 Model", callback_data="ms:model"),
            InlineKeyboardButton("📊 Usage", callback_data="ms:usage"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete Session", callback_data="ms:delete"),
        ],
    ])


def new_session_keyboard(resume_sid: str = ""):
    """AI picker for creating a new session (or resuming a stopped one)."""
    rows: list = []
    ai_buttons = [InlineKeyboardButton("🤖 Claude Code",
                                       callback_data=f"ms:new_ai:claude:{resume_sid}")]
    for key, info in _st.integrations.items():
        ai_buttons.append(InlineKeyboardButton(
            f"{info['emoji']} {info['name']}",
            callback_data=f"ms:new_ai:{key}:{resume_sid}",
        ))
    ai_buttons.append(InlineKeyboardButton("🐚 Shell",
                                            callback_data=f"ms:new_ai:shell:{resume_sid}"))
    for i in range(0, len(ai_buttons), 2):
        rows.append(ai_buttons[i : i + 2])
    rows.append([InlineKeyboardButton("← Back", callback_data="ms:list")])
    return InlineKeyboardMarkup(rows)


# Keep thin aliases for any remaining code that calls the old names
def _sessions_keyboard():
    return sessions_keyboard()

def _session_controls_keyboard():
    return session_controls_keyboard()

def _new_session_keyboard(resume_sid: str = ""):
    return new_session_keyboard(resume_sid)

def _ai_select_keyboard():
    return sessions_keyboard()

def _running_keyboard():
    return session_controls_keyboard()
