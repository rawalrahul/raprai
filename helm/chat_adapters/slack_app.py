"""Slack: RAPR AI in a Slack workspace via Socket Mode (no public address needed).

Needs slack-bolt, a bot token (xoxb-…) and an app-level token (xapp-…) with the
connections:write scope. Voice messages (audio clips) need the files:read bot
scope so RAPR can download them; they are transcribed and handled like text.
"""

from __future__ import annotations

from helm.chat_bridge import ChatBridge
from helm.config import logger

MAX_AUDIO_BYTES = 25 * 1024 * 1024


def audio_file(event: dict) -> dict | None:
    """The first audio file shared in a Slack message event, or None."""
    if event.get("subtype") != "file_share":
        return None
    for f in event.get("files") or []:
        if ((f.get("mimetype") or "").startswith("audio/") or f.get("subtype") == "slack_audio") \
                and (f.get("size") or 0) <= MAX_AUDIO_BYTES and f.get("url_private_download"):
            return f
    return None


async def _download(url: str, bot_token: str) -> bytes:
    import aiohttp
    async with aiohttp.ClientSession() as http:
        async with http.get(url, headers={"Authorization": f"Bearer {bot_token}"}) as resp:
            resp.raise_for_status()
            return await resp.read()


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
        if event.get("bot_id"):
            return
        audio = audio_file(event)
        if audio is not None:
            from helm.voice import audio_ext
            try:
                data = await _download(audio["url_private_download"], bot_token)
            except Exception as exc:
                logger.warning("Slack: could not download a voice message: %s", exc)
                await send(event.get("channel", ""), "⚠️ Couldn't download the voice message. "
                           "Give the Slack app the files:read scope, then reinstall it.")
                return
            await bridge.on_voice(event.get("user", ""), event.get("channel", ""), data,
                                  audio_ext(audio.get("mimetype", ""), audio.get("name", "")))
            return
        if event.get("subtype"):
            return
        await bridge.on_message(event.get("user", ""), event.get("channel", ""), event.get("text", ""))

    logger.info("Slack app starting (Socket Mode)")
    await AsyncSocketModeHandler(app, app_token).start_async()
