"""Telegram reads the allowed users when a message arrives, not when it's imported.

At startup RAPR replaces helm.config.ALLOWED_USER_IDS once the vault is loaded
(web_app.py), and the setup wizard does again when it turns the bot on. The
Telegram modules copied the set at import, so if they were imported before
that (helm/heartbeat.py imports them early), every message was refused: the bot
answered nothing while WhatsApp kept working.
"""
import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.config as cfg
import helm.telegram_bot.auth as tg_auth


def _update(user_id, replies):
    async def reply_text(text):
        replies.append(text)
    msg = SimpleNamespace(reply_text=reply_text)
    return SimpleNamespace(effective_user=SimpleNamespace(id=user_id), effective_message=msg,
                           message=msg, effective_chat=SimpleNamespace(id=user_id))


def test_users_added_after_import_are_let_in(monkeypatch):
    monkeypatch.setattr(cfg, "ALLOWED_USER_IDS", set())        # what the import saw
    ran = []

    @tg_auth.authorized_only
    async def handler(update, context):
        ran.append(update.effective_user.id)

    monkeypatch.setattr(cfg, "ALLOWED_USER_IDS", {42})         # what startup sets after the vault
    replies = []
    asyncio.run(handler(_update(42, replies), None))
    assert ran == [42] and replies == []


def test_every_telegram_module_reads_the_live_list():
    import pathlib
    folder = pathlib.Path(tg_auth.__file__).parent
    for f in folder.glob("*.py"):
        assert "from helm.config import ALLOWED_USER_IDS" not in f.read_text(encoding="utf-8"), f.name
        assert "import ALLOWED_USER_IDS," not in f.read_text(encoding="utf-8"), f.name
