"""Telegram keeps trying to connect at startup instead of giving up on a timeout
(computer just woke up, Wi-Fi not ready): the bot used to stay off until a restart."""
import asyncio

from telegram.error import Conflict, InvalidToken, TimedOut

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


def test_settings_shows_why_telegram_is_not_connected(monkeypatch):
    from helm.web_routes.settings_routes import telegram_status
    import json

    def shown():
        return json.loads(asyncio.run(telegram_status()).body)

    tg = FakeTelegram([TimedOut("Timed out")])
    seen = []
    real = web_app._tg_status
    monkeypatch.setattr(web_app, "_tg_status", lambda *a: (real(*a), seen.append(dict(_st.telegram_status))))
    _run(tg, monkeypatch)
    assert seen[0]["status"] == "connecting" and "Timed out" in seen[0]["error"]
    assert shown() == {"status": "connected", "error": ""}

    _st.telegram_app = None
    web_app._tg_status("error", "rejected")
    assert shown()["status"] == "error"


def test_a_polling_error_clears_once_polling_has_been_quiet(monkeypatch):
    from helm.web_routes.settings_routes import telegram_status
    import json

    tg = FakeTelegram([])
    tg.updater.running = True
    monkeypatch.setattr(_st, "telegram_app", tg)
    web_app._telegram_polling_error_handler("Startup")(Conflict("other getUpdates"))
    assert json.loads(asyncio.run(telegram_status()).body)["status"] == "conflict"
    _st.telegram_status["at"] -= 120              # no new error for two minutes
    assert json.loads(asyncio.run(telegram_status()).body)["status"] == "connected"
