"""
web_app.py — Helm HQ entry point.

This file is intentionally thin: all logic lives in the helm/ package.
Run with:  python web_app.py
"""

import asyncio
import webbrowser

import uvicorn

# Load environment variables first (helm/config.py does this via dotenv)
from helm.config import BOT_TOKEN, WEB_HOST, WEB_PORT, logger
from helm.integrations import load_integrations
from helm.skills import scan_skills
from helm.scheduler import load_scheduled_tasks, cron_runner
from helm.heartbeat import heartbeat_runner, heartbeat_callback
from helm.history import rebuild_hist_cache_sync
from helm.web_routes import app

import helm.state as _st


async def _main():
    # Load AI integration plugins from integrations/ folder
    load_integrations()

    # Scan for Claude skills and build the shared skill registry.
    # All non-Claude AIs (Ollama, Gemini, Codex, custom CLIs) will
    # automatically receive relevant skill instructions injected into
    # their prompts at dispatch time.
    scan_skills()

    # Warm history cache in background so first /history request is instant
    import concurrent.futures
    _thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    _thread_pool.submit(rebuild_hist_cache_sync)

    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled.")

    # --- Build Telegram application ---
    if BOT_TOKEN:
        from helm.config import ALLOWED_USER_IDS
        if not ALLOWED_USER_IDS:
            logger.error(
                "\n"
                "╔══════════════════════════════════════════════════════════╗\n"
                "║  ⛔  SECURITY WARNING — Telegram bot will NOT start      ║\n"
                "║                                                          ║\n"
                "║  ALLOWED_USER_IDS is missing or empty in your .env.     ║\n"
                "║  Without it, anyone who finds your bot can control it.  ║\n"
                "║                                                          ║\n"
                "║  Fix:                                                    ║\n"
                "║  1. Open http://localhost:%d/setup in your browser      ║\n"
                "║  2. Enter your Telegram user ID in the setup wizard     ║\n"
                "║     (find it via @userinfobot on Telegram)              ║\n"
                "║  3. Restart Helm HQ                                     ║\n"
                "╚══════════════════════════════════════════════════════════╝",
                WEB_PORT,
            )
    if BOT_TOKEN and ALLOWED_USER_IDS:
        from telegram import Update
        from telegram.ext import (
            Application, CallbackQueryHandler, CommandHandler,
            MessageHandler, filters,
        )
        from helm.telegram_bot import (
            action_callback, browse_callback, pipeline_callback,
            tg_browse, tg_clear, tg_clear_context, tg_claude, tg_cmd,
            tg_codex, tg_cwd, tg_gemini, tg_history, tg_interrupt,
            tg_launch, tg_menu, tg_pipeline, tg_resume, tg_schedule,
            tg_start, tg_status, tg_stop, tg_stop_ai, tg_text, tg_timeout,
            tg_voice, tg_file,
        )

        _st.telegram_app = (
            Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
        )
        tg = _st.telegram_app

        # Primary commands
        tg.add_handler(CommandHandler("start",   tg_start))
        tg.add_handler(CommandHandler("menu",    tg_menu))
        # AI selection
        tg.add_handler(CommandHandler("claude",  tg_claude))
        tg.add_handler(CommandHandler("gemini",  tg_gemini))
        tg.add_handler(CommandHandler("codex",   tg_codex))
        # Session controls
        tg.add_handler(CommandHandler("launch",    tg_launch))
        tg.add_handler(CommandHandler("stop",      tg_stop))
        tg.add_handler(CommandHandler("interrupt", tg_interrupt))
        tg.add_handler(CommandHandler("stop_ai",   tg_stop_ai))
        tg.add_handler(CommandHandler("status",    tg_status))
        # Utility
        tg.add_handler(CommandHandler("cwd",          tg_cwd))
        tg.add_handler(CommandHandler("browse",        tg_browse))
        tg.add_handler(CommandHandler("cmd",           tg_cmd))
        tg.add_handler(CommandHandler("timeout",       tg_timeout))
        tg.add_handler(CommandHandler("clear",         tg_clear))
        tg.add_handler(CommandHandler("history",       tg_history))
        tg.add_handler(CommandHandler("resume",        tg_resume))
        tg.add_handler(CommandHandler("clear_context", tg_clear_context))
        tg.add_handler(CommandHandler("schedule",      tg_schedule))
        tg.add_handler(CommandHandler("pipeline",      tg_pipeline))
        # Inline keyboard callbacks — action/ms: buttons BEFORE browse_callback
        tg.add_handler(CallbackQueryHandler(action_callback, pattern=r"^(action:|ms:)"))
        tg.add_handler(CallbackQueryHandler(pipeline_callback, pattern=r"^pl:"))
        tg.add_handler(CallbackQueryHandler(heartbeat_callback, pattern=r"^heartbeat:"))
        tg.add_handler(CallbackQueryHandler(browse_callback))
        # Voice / audio messages
        tg.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, tg_voice))
        # Photos and document attachments
        tg.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, tg_file))
        # Plain text + natural language
        tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_text))


    # --- Build uvicorn server ---
    config = uvicorn.Config(
        app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    url = f"http://{'localhost' if WEB_HOST in ('0.0.0.0', '127.0.0.1') else WEB_HOST}:{WEB_PORT}"
    logger.info("Starting web UI at %s", url)

    async def _open_browser():
        await asyncio.sleep(1.2)
        webbrowser.open(url)

    # Load persisted scheduled tasks and start the cron runner
    load_scheduled_tasks()
    asyncio.create_task(cron_runner())
    asyncio.create_task(heartbeat_runner())
    asyncio.create_task(_open_browser())

    if _st.telegram_app:
        from telegram import Update
        async with _st.telegram_app:
            await _st.telegram_app.start()
            await _st.telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram bot started. Polling for updates...")
            await server.serve()           # blocks until Ctrl+C
            await _st.telegram_app.updater.stop()
            await _st.telegram_app.stop()
    else:
        await server.serve()


def main():
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")


if __name__ == "__main__":
    main()
