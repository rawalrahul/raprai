"""Kelvin stickers on Telegram are opt-in and only sent at moments that matter."""
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.kelvin_stickers as ks
import helm.state as _st


class FakeBot:
    def __init__(self):
        self.calls = []

    async def send_sticker(self, chat_id, sticker):
        self.calls.append(("sticker", chat_id, sticker))
        return SimpleNamespace(sticker=SimpleNamespace(file_id=f"fid-{len(self.calls)}"))

    async def send_message(self, chat_id, text, **kw):
        self.calls.append(("message", chat_id, text))


def _telegram(monkeypatch, enabled=True):
    bot = FakeBot()
    monkeypatch.setattr(_st, "telegram_app", SimpleNamespace(bot=bot), raising=False)
    monkeypatch.setattr(_st, "telegram_chat_id", 42, raising=False)
    monkeypatch.setenv("TELEGRAM_KELVIN_STICKERS", "1" if enabled else "0")
    monkeypatch.setattr(ks, "_file_ids", {})
    return bot


def test_every_mood_has_a_sticker_file():
    for mood in ks.MOODS:
        assert ks.sticker_path(mood).exists(), mood


def test_off_by_default(monkeypatch):
    bot = _telegram(monkeypatch)
    monkeypatch.delenv("TELEGRAM_KELVIN_STICKERS")
    assert asyncio.run(ks.send_kelvin_sticker("done")) is False
    assert bot.calls == []


def test_uploads_once_then_reuses_the_file_id(monkeypatch):
    bot = _telegram(monkeypatch)
    assert asyncio.run(ks.send_kelvin_sticker("done")) is True
    assert asyncio.run(ks.send_kelvin_sticker("done")) is True
    first, second = bot.calls
    assert isinstance(first[2], bytes) and first[1] == 42
    assert second[2] == "fid-1"


def test_no_telegram_connected(monkeypatch):
    _telegram(monkeypatch)
    monkeypatch.setattr(_st, "telegram_app", None, raising=False)
    assert asyncio.run(ks.send_kelvin_sticker("error")) is False


def test_unknown_mood_is_ignored(monkeypatch):
    bot = _telegram(monkeypatch)
    assert asyncio.run(ks.send_kelvin_sticker("dancing")) is False
    assert bot.calls == []


def test_done_sticker_only_for_long_user_tasks(monkeypatch):
    bot = _telegram(monkeypatch)

    async def scenario():
        cases = [
            ks.done_sticker_for_task(5, "quick answer", "web"),          # too short
            ks.done_sticker_for_task(300, "", "web"),                    # nothing produced
            ks.done_sticker_for_task(300, "(stopped)", "web"),           # user stopped it
            ks.done_sticker_for_task(300, "step output", "pipeline"),    # sub-run
            ks.done_sticker_for_task(300, "node output", "agent"),       # sub-run
        ]
        assert cases == [None] * 5
        task = ks.done_sticker_for_task(300, "Here is the report", "telegram")
        assert task is not None
        await task

    asyncio.run(scenario())
    assert len(bot.calls) == 1


def test_error_sticker_quiet_for_sub_runs(monkeypatch):
    _telegram(monkeypatch)

    async def scenario():
        assert ks.error_sticker_for_task("pipeline") is None
        task = ks.error_sticker_for_task("web")
        assert task is not None
        await task

    asyncio.run(scenario())


def test_approval_request_sends_sticker_first(monkeypatch):
    bot = _telegram(monkeypatch)
    from helm.approval import _send_approval_to_telegram
    asyncio.run(_send_approval_to_telegram({"id": "a1", "action": "destructive_command",
                                            "description": "git push origin main"}))
    kinds = [c[0] for c in bot.calls]
    assert kinds == ["sticker", "message"]


def test_approval_request_without_stickers(monkeypatch):
    bot = _telegram(monkeypatch, enabled=False)
    from helm.approval import _send_approval_to_telegram
    asyncio.run(_send_approval_to_telegram({"id": "a1", "action": "destructive_command",
                                            "description": "git push origin main"}))
    assert [c[0] for c in bot.calls] == ["message"]
