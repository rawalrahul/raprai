"""Slack: RAPR AI in a Slack workspace via Socket Mode (no public address needed).

Needs slack-bolt, a bot token (xoxb-…) and an app-level token (xapp-…) with the
connections:write scope.
"""

from __future__ import annotations

from helm.chat_bridge import ChatBridge
from helm.config import logger


async def run(bot_token: str, app_token: str, allowed_user_ids: list[str]) -> None:
    from slack_bolt.async_app import AsyncApp              # optional: pip install slack-bolt
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

    app = AsyncApp(token=bot_token)

    async def send(chat_id: str, text: str) -> None:
        await app.client.chat_postMessage(channel=chat_id, text=text)

    bridge = ChatBridge("slack", send, allowed_user_ids)
    bridge.register()

    @app.event("message")
    async def on_message(event, say):
        # Ignore bot posts (including our own replies) and message edits.
        if event.get("subtype") or event.get("bot_id"):
            return
        await bridge.on_message(event.get("user", ""), event.get("channel", ""), event.get("text", ""))

    logger.info("Slack app starting (Socket Mode)")
    await AsyncSocketModeHandler(app, app_token).start_async()
