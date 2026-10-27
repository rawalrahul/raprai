"""The heartbeat's Continue button resumes the session it names.

It called perform_resume(payload, update, context), but perform_resume takes
(message, date_str): pressing it showed "Resuming…" and then failed with a
TypeError, so nothing resumed.
"""
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.heartbeat as heartbeat
import helm.telegram_bot as telegram_bot


def test_continue_resumes_the_named_session(monkeypatch):
    resumed = []

    async def fake_resume(message, date_str=""):
        resumed.append((message, date_str))
    monkeypatch.setattr(telegram_bot, "perform_resume", fake_resume)

    answers = []

    async def answer(text=""):
        answers.append(text)
    message = object()
    query = SimpleNamespace(data="heartbeat:resume:2026-10-27_0900", answer=answer, message=message)
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1))

    asyncio.run(heartbeat.heartbeat_callback.__wrapped__(update, None))
    assert resumed == [(message, "2026-10-27_0900")]
    assert answers == ["Resuming…"]


def test_only_allowed_users_can_press_it(monkeypatch):
    import helm.telegram_bot.auth as tg_auth
    monkeypatch.setattr(tg_auth._cfg, "ALLOWED_USER_IDS", {1})
    pressed, replies = [], []

    async def answer(text=""):
        pressed.append(text)

    async def reply_text(text):
        replies.append(text)
    query = SimpleNamespace(data="heartbeat:snooze", answer=answer, edit_message_text=answer)
    # A button press: no update.message, only the message the button is on.
    update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=999),
                             message=None, effective_message=SimpleNamespace(reply_text=reply_text))
    asyncio.run(heartbeat.heartbeat_callback(update, None))
    assert pressed == [] and replies == ["⛔ Unauthorized."]
