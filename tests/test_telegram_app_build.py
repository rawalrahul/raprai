"""Startup and the hot-start after setup build the bot from one function, so
both get every command and button."""
from telegram.ext import CallbackQueryHandler, CommandHandler

import web_app


def test_the_bot_gets_every_command_and_button():
    tg = web_app._build_telegram_app("123456:TESTTOKENabcdefghijklmnopqrstuvwxyz")
    handlers = tg.handlers[0]
    commands = set().union(*(h.commands for h in handlers if isinstance(h, CommandHandler)))
    assert {"start", "menu", "claude", "codex", "gemini", "antigravity", "agy", "status", "stop",
            "history", "resume", "schedule", "pipeline", "agent", "group", "brief", "model"} <= commands
    buttons = [h for h in handlers if isinstance(h, CallbackQueryHandler)]
    assert buttons[-1].pattern is None          # the catch-all browse buttons go last
    assert len(handlers) == 37
