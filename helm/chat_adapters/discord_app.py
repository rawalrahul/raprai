"""Discord: RAPR AI as a bot in your server or DMs (needs discord.py and a bot token)."""

from __future__ import annotations

from helm.chat_bridge import ChatBridge
from helm.config import logger


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
        await bridge.on_message(str(message.author.id), str(message.channel.id), message.content or "")

    await client.start(token)
