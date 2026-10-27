"""Telegram keeps trying to connect at startup instead of giving up on a timeout
(computer just woke up, Wi-Fi not ready): the bot used to stay off until a restart."""
import asyncio

from telegram.error import InvalidToken, TimedOut

import helm.state as _st
import web_app


class FakeUpdater:
    running = False

    async def start_polling(self, **kw):
        self.running = True


class FakeTelegram:
    def __init__(self, failures):
        self.failures = list(failures)
        self.running = False
        self.updater = FakeUpdater()

    async def initialize(self):
        if self.failures:
            raise self.failures.pop(0)

    async def start(self):
        self.running = True


def _run(tg, monkeypatch):
    waits = []

    async def no_wait(s):
        waits.append(s)

    monkeypatch.setattr(web_app.asyncio, "sleep", no_wait)
    monkeypatch.setattr(_st, "telegram_app", tg)
    asyncio.run(web_app._keep_telegram_polling(tg, "Startup"))
    return waits


def test_timeouts_are_retried_until_telegram_answers(monkeypatch):
    tg = FakeTelegram([TimedOut(), TimedOut(), TimedOut()])
    waits = _run(tg, monkeypatch)
    assert tg.updater.running and _st.telegram_app is tg
    assert waits == [5, 10, 20]


def test_a_rejected_token_stops_trying(monkeypatch):
    tg = FakeTelegram([InvalidToken("Unauthorized")])
    waits = _run(tg, monkeypatch)
    assert waits == [] and not tg.updater.running and _st.telegram_app is None
