"""
helm/chat_bridge.py — Connects any chat app to RAPR's shared commands.

A chat app gives us (sender id, chat id, text). The bridge checks the sender is
allowed, runs the shared router, and sends the replies back to that chat. It
also receives group-chat messages so a group the chat is in is relayed there.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Iterable

from helm.config import logger

SendFn = Callable[[str, str], Awaitable[None]]   # (chat_id, text)
MAX_CHUNK = 1900   # Discord caps messages at 2000 characters; Slack is larger


def chunks(text: str, size: int = MAX_CHUNK) -> list[str]:
    text = text or ""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


class ChatBridge:
    def __init__(self, channel: str, send: SendFn, allowed_ids: Iterable[str]):
        self.channel = channel
        self.send = send
        self.allowed = {str(i).strip() for i in allowed_ids if str(i).strip()}
        self.last_chat: str | None = None

    def is_allowed(self, sender_id: str) -> bool:
        return bool(self.allowed) and str(sender_id) in self.allowed

    async def on_message(self, sender_id: str, chat_id: str, text: str) -> None:
        if not self.is_allowed(sender_id):
            logger.warning("%s: ignored a message from an unauthorised user", self.channel)
            return
        from helm.chat_router import handle
        self.last_chat = str(chat_id)
        try:
            replies = await handle(self.channel, text)
        except Exception as exc:
            logger.warning("%s: command failed: %s", self.channel, exc, exc_info=True)
            replies = [f"⚠️ Something went wrong: {exc}"]
        for reply in replies:
            for part in chunks(reply):
                await self.send(str(chat_id), part)

    async def relay_group(self, _group: dict, text: str) -> None:
        """Group messages go to the chat this app last talked in."""
        if self.last_chat:
            for part in chunks(text):
                await self.send(self.last_chat, part)

    def register(self) -> None:
        import helm.groupchat as gc
        gc.register_channel(self.channel, self.relay_group)
