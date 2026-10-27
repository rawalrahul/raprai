"""A getUpdates conflict (e.g. the old RAPR's last poll right after an update)
must not stop Telegram polling: PTB retries and recovers on its own."""
import asyncio
import logging

from telegram.error import Conflict

import web_app


def test_conflict_keeps_polling_and_warns_once(caplog):
    async def run():
        on_error = web_app._telegram_polling_error_handler("Startup")
        with caplog.at_level(logging.WARNING, logger="helm"):
            for _ in range(3):
                on_error(Conflict("terminated by other getUpdates request"))
        await asyncio.sleep(0)               # let any task it scheduled run
        return [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    assert asyncio.run(run()) == []          # nothing scheduled to stop the updater
    warnings = [r for r in caplog.records if "getUpdates" in r.getMessage()]
    assert len(warnings) == 1
