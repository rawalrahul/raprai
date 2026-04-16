"""
helm/telegram_bot/ — Telegram bot handlers, keyboards, and callback routing.

This package re-exports all public interfaces from sub-modules so that existing
imports from web_app.py and other code continue to work transparently.
"""

# Auth utilities
from .auth import authorized_only, tg_send_chunks, _tg_send_chunks

# Keyboards
from .keyboards import (
    sessions_keyboard, session_controls_keyboard, new_session_keyboard,
    _sessions_keyboard, _session_controls_keyboard, _new_session_keyboard,
    _ai_select_keyboard, _running_keyboard,
    pipeline_approval_keyboard, pipeline_controls_keyboard, pipeline_list_keyboard,
    agent_list_keyboard,
)

# Browse
from .browse import (
    tg_browse, browse_callback, show_browse, _show_browse,
    _tg_browse_state,  # exposed for state access if needed
)

# Commands (all /command handlers)
from .commands import (
    tg_start, tg_menu, tg_launch, tg_claude, tg_codex, tg_gemini,
    tg_stop_ai, tg_clear, tg_cmd, tg_status, tg_interrupt, tg_stop,
    tg_cwd, tg_timeout, tg_schedule, tg_history, tg_resume,
    tg_clear_context, tg_text, tg_voice, tg_file, tg_pipeline, tg_agent,
    perform_resume, _perform_resume,
    _update_env,
)

# Callbacks (inline keyboard callbacks)
from .callbacks import action_callback, pipeline_callback, approval_callback, agent_callback

# Also export browse_callback from browse module for backward compat
# (already imported above from .browse)

__all__ = [
    # Auth
    "authorized_only",
    "tg_send_chunks",
    "_tg_send_chunks",

    # Keyboards
    "sessions_keyboard",
    "session_controls_keyboard",
    "new_session_keyboard",
    "_sessions_keyboard",
    "_session_controls_keyboard",
    "_new_session_keyboard",
    "_ai_select_keyboard",
    "_running_keyboard",

    # Browse
    "tg_browse",
    "browse_callback",
    "show_browse",
    "_show_browse",
    "_tg_browse_state",

    # Commands
    "tg_start",
    "tg_menu",
    "tg_launch",
    "tg_claude",
    "tg_codex",
    "tg_gemini",
    "tg_stop_ai",
    "tg_clear",
    "tg_cmd",
    "tg_status",
    "tg_interrupt",
    "tg_stop",
    "tg_cwd",
    "tg_timeout",
    "tg_schedule",
    "tg_history",
    "tg_resume",
    "tg_clear_context",
    "tg_text",
    "tg_voice",
    "tg_file",
    "perform_resume",
    "_perform_resume",
    "_update_env",

    # Pipeline
    "tg_pipeline",
    "pipeline_callback",
    "pipeline_approval_keyboard",
    "pipeline_controls_keyboard",
    "pipeline_list_keyboard",

    # Agents
    "tg_agent",
    "agent_callback",
    "agent_list_keyboard",

    # Callbacks
    "action_callback",
    "pipeline_callback",
    "approval_callback",
    "agent_callback",
]
