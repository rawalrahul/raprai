"""Discord: RAPR AI as a bot in your server or DMs (needs discord.py and a bot token).

Voice messages (and audio files sent without text) are transcribed and handled
like typed text.
"""

from __future__ import annotations

from helm.chat_bridge import ChatBridge
from helm.config import logger

MAX_AUDIO_BYTES = 25 * 1024 * 1024


def _audio_attachment(message):
    """The first audio attachment of a message, or None."""
    for a in getattr(message, "attachments", None) or []:
        if (a.content_type or "").startswith("audio/") and (a.size or 0) <= MAX_AUDIO_BYTES:
            return a
    return None


async def run(token: str, allowed_user_ids: list[str]) -> None:
    import discord  # optional dependency: pip install discord.py

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    async def send(chat_id: str, text: str) -> None:
        channel = client.get_channel(int(chat_id)) or await client.fetch_channel(int(chat_id))
        await channel.send(text)

    bridge = ChatBridge("discord", send, allowed_user_ids)
    bridge.register()

    @client.event
    async def on_ready():
        logger.info("Discord bot connected as %s", client.user)

    @client.event
    async def on_message(message):
        if message.author.bot:
            return
        audio = None if (message.content or "").strip() else _audio_attachment(message)
        if audio is not None:
            from helm.voice import audio_ext
            await bridge.on_voice(str(message.author.id), str(message.channel.id),
                                  await audio.read(), audio_ext(audio.content_type, audio.filename))
            return
        await bridge.on_message(str(message.author.id), str(message.channel.id), message.content or "")

    await client.start(token)
