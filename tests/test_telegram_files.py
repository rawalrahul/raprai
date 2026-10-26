"""Photos and files sent to the Telegram bot are saved to the session's folder.

The handler named saved photos with time.time() but never imported time, so
every photo (and every document without a file name) failed with a NameError.
"""
import asyncio
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.state as _st
from helm.telegram_bot import commands


class _File:
    async def download_to_drive(self, path):
        with open(path, "wb") as f:
            f.write(b"data")


class _Attachment:
    def __init__(self, file_name=None):
        self.file_name = file_name

    async def get_file(self):
        return _File()


def _update(replies, photo=None, document=None):
    async def reply_text(text, **kw):
        replies.append(text)
    msg = SimpleNamespace(photo=photo, document=document, caption=None, reply_text=reply_text)
    return SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))


@pytest.fixture
def session(tmp_path, monkeypatch):
    sess = {"id": "s1", "name": "Test", "emoji": "🧪", "status": "idle", "cwd": str(tmp_path)}
    monkeypatch.setattr(_st, "sessions", {"s1": sess})
    monkeypatch.setattr(_st, "focused_id", "s1")
    return tmp_path


@pytest.mark.parametrize("kind", ["photo", "unnamed document"])
def test_attachment_is_saved(session, kind):
    replies = []
    if kind == "photo":
        update = _update(replies, photo=[_Attachment()])
    else:
        update = _update(replies, document=_Attachment(file_name=None))
    asyncio.run(commands.tg_file.__wrapped__(update, None))
    saved = os.listdir(session)
    assert len(saved) == 1 and saved[0].startswith("telegram_")
    assert replies and replies[0].startswith("📎 Saved")
