"""
web_app.py — RAPR AI entry point.

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
    # Set up crash logging FIRST — everything after this is logged to file
    from helm.resilience import setup_crash_logging
    setup_crash_logging()

    # Check database integrity before initializing
    from helm.resilience import check_db_integrity
    db_ok = check_db_integrity()
    if not db_ok:
        logger.warning("Database was corrupt — a fresh database will be created.")

    # Initialize SQLite database (create tables, run migrations, import legacy data)
    from helm.db import init_db
    init_db()

    # Install security middleware (rate limiting, CSRF, security headers)
    from helm.security import install_security
    install_security(app)

    # Install global exception handlers (catches unhandled errors, logs to crash file)
    from helm.resilience import install_exception_handlers
    install_exception_handlers(app)

    # Load persisted brute-force lockout state
    from helm.auth import load_lockout_from_db
    load_lockout_from_db()

    # Log startup health summary (disk space, OS info)
    from helm.resilience import log_startup_health
    log_startup_health()

    # Load AI integration plugins from integrations/ folder
    load_integrations()

    # Load default models per AI from .env (DEFAULT_MODEL_OLLAMA, etc.)
    import os
    for key, val in os.environ.items():
        if key.startswith("DEFAULT_MODEL_") and val.strip():
            ai_key = key[len("DEFAULT_MODEL_"):].lower()
            _st.default_models[ai_key] = val.strip()
            logger.info("Default model for %s: %s", ai_key, val.strip())

    # Scan for Claude skills and build the shared skill registry.
    # All non-Claude AIs (Ollama, Gemini, Codex, custom CLIs) will
    # automatically receive relevant skill instructions injected into
    # their prompts at dispatch time.
    scan_skills()

    # Restore persisted usage stats from database
    from helm.session_mgr import load_usage_from_db
    load_usage_from_db()

    # Load encrypted tokens from vault into os.environ (must run before plugins/MCP)
    try:
        from helm.token_vault import load_all_tokens
        loaded = load_all_tokens()
        if loaded:
            logger.info("Token vault: loaded %d token(s) into environment", len(loaded))
    except Exception as exc:
        logger.warning("Token vault init: %s", exc)

    # Load Helm-level plugins (helm/plugins/ directory)
    from helm.plugins import load_plugins
    load_plugins()

    # Migrate any remaining plaintext plugin tokens into the encrypted vault
    # (must run after load_plugins so _registry is populated)
    try:
        from helm.token_vault import migrate_env_tokens
        from helm.plugins import _registry as _plugin_registry
        token_env_keys = []
        for info in _plugin_registry.values():
            auth = info.get("auth", {})
            if auth.get("token_env"):
                token_env_keys.append(auth["token_env"])
            for t in auth.get("tokens", []):
                if t.get("token_env"):
                    token_env_keys.append(t["token_env"])
            fb = auth.get("fallback_token", {})
            if fb.get("token_env"):
                token_env_keys.append(fb["token_env"])
            if auth.get("refresh_token_env"):
                token_env_keys.append(auth["refresh_token_env"])
        if token_env_keys:
            migrated = migrate_env_tokens(token_env_keys)
            if migrated:
                logger.info("Token vault: migrated %d plaintext token(s)", migrated)
    except Exception as exc:
        logger.warning("Token migration: %s", exc)

    # Auto-start MCP servers from mcp_servers.json
    # We block here (up to 30s) so servers are ready before first AI query.
    try:
        import asyncio as _aio
        from helm.mcp import get_manager as _get_mcp_mgr
        _mcp_mgr = _get_mcp_mgr()

        def _start_mcp():
            loop = _aio.new_event_loop()
            try:
                loop.run_until_complete(_mcp_mgr.load_and_start())
            finally:
                loop.close()

        import concurrent.futures as _cf
        fut = _cf.ThreadPoolExecutor(max_workers=1).submit(_start_mcp)
        try:
            fut.result(timeout=30)   # block up to 30s for servers to start
            logger.info("MCP servers ready")
        except _cf.TimeoutError:
            logger.warning("MCP auto-start: timed out after 30s (servers may still be starting)")
        except Exception as exc:
            logger.warning("MCP auto-start error: %s", exc)
    except Exception as exc:
        logger.warning("MCP auto-start skipped: %s", exc)

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
                "║  3. Restart RAPR AI                                     ║\n"
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
            approval_callback,
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
        tg.add_handler(CallbackQueryHandler(approval_callback, pattern=r"^appr:"))
        tg.add_handler(CallbackQueryHandler(heartbeat_callback, pattern=r"^heartbeat:"))
        tg.add_handler(CallbackQueryHandler(browse_callback))
        # Voice / audio messages
        tg.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, tg_voice))
        # Photos and document attachments
        tg.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, tg_file))
        # Plain text + natural language
        tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_text))


    # --- Resolve port conflicts ---
    from helm.resilience import find_free_port
    actual_port = find_free_port(WEB_HOST, WEB_PORT)

    # --- Build uvicorn server ---
    config = uvicorn.Config(
        app,
        host=WEB_HOST,
        port=actual_port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    url = f"http://{'localhost' if WEB_HOST in ('0.0.0.0', '127.0.0.1') else WEB_HOST}:{actual_port}"
    logger.info("Starting web UI at %s", url)

    async def _open_browser():
        await asyncio.sleep(1.2)
        webbrowser.open(url)

    # Load persisted scheduled tasks and start the cron runner
    load_scheduled_tasks()
    asyncio.create_task(cron_runner())
    asyncio.create_task(heartbeat_runner())
    asyncio.create_task(_open_browser())

    # Start cloud backup scheduler (checks every 5 min for due backups)
    try:
        from helm.cloud_backup.scheduler import start_scheduler
        asyncio.create_task(start_scheduler())
    except Exception as exc:
        logger.warning("Cloud backup scheduler start failed: %s", exc)

    # Start AI subprocess watchdog (detects dead processes, notifies users)
    from helm.resilience import ai_watchdog
    asyncio.create_task(ai_watchdog())

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
        logger.info("Shutting down (Ctrl+C).")
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
    finally:
        # Graceful shutdown — stop AI processes, close DB, flush logs
        try:
            import asyncio as _aio
            loop = _aio.new_event_loop()
            from helm.resilience import graceful_shutdown
            loop.run_until_complete(graceful_shutdown())
            loop.close()
        except Exception:
            # Fallback: at least close DB connections
            try:
                from helm.db import close_all
                close_all()
            except Exception:
                pass


if __name__ == "__main__":
    main()
