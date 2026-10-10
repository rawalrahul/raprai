"""Start the chat apps that have tokens set (Settings or .env)."""

import asyncio
import os

from helm.config import logger


def _ids(name: str) -> list[str]:
    return [x.strip() for x in os.environ.get(name, "").split(",") if x.strip()]


def start_configured() -> list[asyncio.Task]:
    tasks = []
    if os.environ.get("DISCORD_BOT_TOKEN"):
        from helm.chat_adapters import discord_app
        tasks.append(asyncio.create_task(_supervised("Discord", discord_app.run(
            os.environ["DISCORD_BOT_TOKEN"], _ids("DISCORD_ALLOWED_USER_IDS")))))
    if os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_APP_TOKEN"):
        from helm.chat_adapters import slack_app
        tasks.append(asyncio.create_task(_supervised("Slack", slack_app.run(
            os.environ["SLACK_BOT_TOKEN"], os.environ["SLACK_APP_TOKEN"], _ids("SLACK_ALLOWED_USER_IDS")))))
    return tasks


async def _supervised(name: str, coro) -> None:
    """Keep the app running; if it stops or fails, say so in the log and don't crash RAPR."""
    try:
        await coro
    except ImportError as exc:
        logger.warning("%s is not installed (%s). Install it to use %s.", name, exc, name)
    except Exception as exc:
        logger.warning("%s stopped: %s", name, exc)
