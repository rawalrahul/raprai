"""
web_app.py — RAPR AI entry point.

This file is intentionally thin: all logic lives in the helm/ package.
Run with:  python web_app.py
"""

import asyncio
import ctypes
import os
import shutil
import subprocess
import sys
import webbrowser

import uvicorn

from helm.subprocess_utils import hidden_kwargs


# ── Windows: Create a named mutex so Inno Setup can detect the running app ──
_win_mutex = None
if sys.platform == "win32":
    try:
        _win_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "RAPR_AI_SingleInstance")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            print("RAPR AI is already running. Close the existing instance before starting another.")
            sys.exit(0)
    except Exception:
        pass

# Load environment variables first (helm/config.py does this via dotenv)
from helm.config import BOT_TOKEN, WEB_HOST, WEB_PORT, logger
from helm.integrations import load_integrations
from helm.skills import scan_skills
from helm.scheduler import load_scheduled_tasks, cron_runner
from helm.heartbeat import heartbeat_runner, heartbeat_callback
from helm.history import rebuild_hist_cache_sync
from helm.web_routes import app

import helm.state as _st


def _telegram_polling_error_handler(label: str, tg):
    """Return a sync PTB polling error callback that suppresses conflict spam."""
    from telegram.error import Conflict

    stopping = False

    def _on_error(exc):
        nonlocal stopping
        if isinstance(exc, Conflict):
            if not stopping:
                stopping = True
                logger.warning(
                    "%s Telegram polling disabled: another process is already using getUpdates "
                    "for this bot token.",
                    label,
                )

                async def _stop_polling():
                    try:
                        if tg.updater and tg.updater.running:
                            await tg.updater.stop()
                    except Exception as stop_exc:
                        logger.warning("Telegram polling stop after conflict failed: %s", stop_exc)

                try:
                    asyncio.create_task(_stop_polling())
                except RuntimeError:
                    pass
            return
        logger.exception("Exception happened while polling for Telegram updates.", exc_info=exc)

    return _on_error


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

    # Check NemoClaw availability (WSL + Docker + OpenShell + NemoClaw)
    # Non-blocking: if anything is missing, NemoClaw just doesn't appear.
    if sys.platform == "win32":
        try:
            from helm.ai_runner.nemoclaw_bridge import startup_check as _nemoclaw_startup
            import concurrent.futures as _ncf
            _nc_pool = _ncf.ThreadPoolExecutor(max_workers=1)
            _nc_pool.submit(_nemoclaw_startup)
            logger.info("NemoClaw: startup check launched in background")
        except Exception as exc:
            logger.info("NemoClaw: startup check skipped (%s)", exc)

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

    # Refresh module-level config constants that were cached at import time
    # BEFORE load_all_tokens() ran.  After vault migration, .env contains
    # "vault-managed" placeholders — the real values are only in os.environ
    # now that the vault has been decrypted.
    import helm.config as _cfg
    _cfg.BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if _cfg.BOT_TOKEN == "vault-managed":
        _cfg.BOT_TOKEN = ""  # placeholder is not a real token
    _cfg.ALLOWED_USER_IDS = set(
        int(uid.strip())
        for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
        if uid.strip()
    )

    # Sync telegram_chat_id with the post-vault ALLOWED_USER_IDS so
    # web→Telegram forwarding works even if state.py was imported before
    # vault decryption populated the real user IDs.
    if _cfg.ALLOWED_USER_IDS:
        _st.telegram_chat_id = next(iter(_cfg.ALLOWED_USER_IDS), None)

    # Re-bind the local names used later in this function so they
    # reflect the post-vault-decryption values (the line-14 import
    # captured stale values before load_all_tokens ran).
    BOT_TOKEN = _cfg.BOT_TOKEN                # noqa: F841
    ALLOWED_USER_IDS = _cfg.ALLOWED_USER_IDS  # noqa: F841

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
            migrated = migrate_env_tokens(token_env_keys, scrub_env=True)
            if migrated:
                logger.info("Token vault: migrated %d plaintext plugin token(s)", migrated)
    except Exception as exc:
        logger.warning("Token migration (plugins): %s", exc)

    # Migrate core API keys & credentials from plaintext .env to encrypted vault.
    # This covers GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
    # PIN_HASH and PIN_SALT are excluded (they are hashed values, not raw secrets).
    try:
        from helm.security import VAULT_ELIGIBLE_KEYS
        core_migrated = migrate_env_tokens(list(VAULT_ELIGIBLE_KEYS), scrub_env=True)
        if core_migrated:
            logger.info("Token vault: migrated %d core credential(s) from .env", core_migrated)
    except Exception as exc:
        logger.warning("Token migration (core): %s", exc)

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

    # Index any pre-existing memories for semantic recall (idempotent, best-effort).
    # No-op if the vector layer is disabled/unavailable; cheap once the back-catalogue
    # is indexed. Runs in the background so it never delays startup.
    try:
        from helm.memory import backfill_vectors
        _thread_pool.submit(backfill_vectors)
    except Exception as exc:
        logger.debug("semantic memory backfill not scheduled: %s", exc)

    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled.")

    # --- Build Telegram application ---
    if BOT_TOKEN:
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
            approval_callback, agent_callback,
            tg_browse, tg_clear, tg_clear_context, tg_claude, tg_cmd,
            tg_codex, tg_cwd, tg_gemini, tg_history, tg_interrupt,
            tg_launch, tg_menu, tg_pipeline, tg_agent, tg_resume, tg_schedule,
            tg_start, tg_status, tg_kelvin, tg_stop, tg_stop_ai, tg_text, tg_timeout,
            tg_voice, tg_file,
        )
        from helm.telegram_bot.groups import tg_group, group_callback, register as _register_tg_groups
        _register_tg_groups()

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
        tg.add_handler(CommandHandler("kelvin",    tg_kelvin))
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
        tg.add_handler(CommandHandler("agent",         tg_agent))
        tg.add_handler(CommandHandler("group",         tg_group))
        # Inline keyboard callbacks — action/ms: buttons BEFORE browse_callback
        tg.add_handler(CallbackQueryHandler(action_callback, pattern=r"^(action:|ms:)"))
        tg.add_handler(CallbackQueryHandler(pipeline_callback, pattern=r"^pl:"))
        tg.add_handler(CallbackQueryHandler(approval_callback, pattern=r"^appr:"))
        tg.add_handler(CallbackQueryHandler(agent_callback, pattern=r"^ag:"))
        tg.add_handler(CallbackQueryHandler(group_callback, pattern=r"^gc:"))
        tg.add_handler(CallbackQueryHandler(heartbeat_callback, pattern=r"^heartbeat:"))
        tg.add_handler(CallbackQueryHandler(browse_callback))
        # Voice / audio messages
        tg.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, tg_voice))
        # Photos and document attachments
        tg.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, tg_file))
        # Plain text + natural language
        tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_text))


    # --- Hot-start Telegram function (called from setup_save if bot wasn't started at launch) ---
    async def _hot_start_telegram():
        """Build + start the Telegram bot after initial setup provides token/user IDs."""
        if _st.telegram_app:
            logger.info("Telegram bot already running — skipping hot-start")
            return
        import helm.config as _cfg
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if token == "vault-managed":
            try:
                from helm.token_vault import load_all_tokens
                load_all_tokens()
                token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            except Exception:
                pass
        if not token or token == "vault-managed":
            logger.warning("Telegram hot-start: no valid token found")
            return
        user_ids = set(
            int(uid.strip())
            for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
            if uid.strip()
        )
        if not user_ids:
            logger.warning("Telegram hot-start: ALLOWED_USER_IDS empty")
            return
        _cfg.BOT_TOKEN = token
        _cfg.ALLOWED_USER_IDS = user_ids
        # Pre-set chat_id so web→Telegram forwarding works immediately
        # without waiting for the user to send the first Telegram message.
        _st.telegram_chat_id = next(iter(user_ids), None)
        try:
            from telegram import Update as _Upd
            from telegram.ext import (
                Application, CallbackQueryHandler, CommandHandler,
                MessageHandler, filters,
            )
            from helm.telegram_bot import (
                action_callback, browse_callback, pipeline_callback,
                approval_callback, agent_callback,
                tg_browse, tg_clear, tg_clear_context, tg_claude, tg_cmd,
                tg_codex, tg_cwd, tg_gemini, tg_history, tg_interrupt,
                tg_launch, tg_menu, tg_pipeline, tg_agent, tg_resume, tg_schedule,
                tg_start, tg_status, tg_kelvin, tg_stop, tg_stop_ai, tg_text, tg_timeout,
                tg_voice, tg_file,
            )
            from helm.telegram_bot.groups import tg_group, group_callback, register as _register_tg_groups
            _register_tg_groups()
            _st.telegram_app = (
                Application.builder().token(token).concurrent_updates(True).build()
            )
            tg = _st.telegram_app
            tg.add_handler(CommandHandler("start",   tg_start))
            tg.add_handler(CommandHandler("menu",    tg_menu))
            tg.add_handler(CommandHandler("claude",  tg_claude))
            tg.add_handler(CommandHandler("gemini",  tg_gemini))
            tg.add_handler(CommandHandler("codex",   tg_codex))
            tg.add_handler(CommandHandler("launch",    tg_launch))
            tg.add_handler(CommandHandler("stop",      tg_stop))
            tg.add_handler(CommandHandler("interrupt", tg_interrupt))
            tg.add_handler(CommandHandler("stop_ai",   tg_stop_ai))
            tg.add_handler(CommandHandler("status",    tg_status))
            tg.add_handler(CommandHandler("kelvin",    tg_kelvin))
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
            tg.add_handler(CommandHandler("agent",         tg_agent))
            tg.add_handler(CommandHandler("group",         tg_group))
            tg.add_handler(CallbackQueryHandler(action_callback, pattern=r"^(action:|ms:)"))
            tg.add_handler(CallbackQueryHandler(pipeline_callback, pattern=r"^pl:"))
            tg.add_handler(CallbackQueryHandler(approval_callback, pattern=r"^appr:"))
            tg.add_handler(CallbackQueryHandler(agent_callback, pattern=r"^ag:"))
            tg.add_handler(CallbackQueryHandler(group_callback, pattern=r"^gc:"))
            tg.add_handler(CallbackQueryHandler(heartbeat_callback, pattern=r"^heartbeat:"))
            tg.add_handler(CallbackQueryHandler(browse_callback))
            tg.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, tg_voice))
            tg.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, tg_file))
            tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_text))
            await tg.initialize()
            await tg.start()
            await tg.updater.start_polling(
                allowed_updates=_Upd.ALL_TYPES,
                error_callback=_telegram_polling_error_handler("Hot-start", tg),
            )
            logger.info("Telegram bot hot-started successfully after setup!")
        except Exception as exc:
            logger.error("Telegram hot-start failed: %s", exc)
            _st.telegram_app = None

    # Store reference so setup_save can call it
    _st._hot_start_telegram = _hot_start_telegram

    # --- Resolve port conflicts ---
    from helm.resilience import find_free_port
    actual_port = find_free_port(WEB_HOST, WEB_PORT)
    # Store actual port so OAuth callbacks use the right port
    os.environ["WEB_PORT"] = str(actual_port)
    # And on disk, so launchers (the macOS app) can open the right address.
    try:
        from helm.paths import user_data_dir
        (user_data_dir() / "web_port").write_text(str(actual_port), encoding="utf-8")
    except Exception:
        pass

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

    # --- System tray icon + hide console (Windows) ---
    def _tray_shutdown():
        """Graceful shutdown when user clicks Quit in the system tray.

        Runs in the tray thread — performs critical synchronous cleanup
        (save state, kill AI processes, close DB) before exiting.
        """
        logger.info("Tray shutdown: saving state and cleaning up...")
        # 1. Save session state so sessions survive restart
        try:
            from helm.history import save_last_state
            save_last_state()
        except Exception:
            pass
        # 2. Extract memories from active sessions
        try:
            from helm.memory import save_extracted_memories
            for sess in list(_st.sessions.values()):
                try:
                    save_extracted_memories(sess)
                except Exception:
                    pass
        except Exception:
            pass
        # 3. Kill running AI subprocesses so they don't get orphaned
        try:
            for sess in list(_st.sessions.values()):
                proc = sess.get("proc")
                if proc:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        except Exception:
            pass
        # 4. Flush pending telemetry so install/usage events aren't lost
        try:
            from helm.device_link import flush_telemetry
            flush_telemetry()
        except Exception:
            pass
        # 5. Close database connections
        try:
            from helm.db import close_all
            close_all()
        except Exception:
            pass
        logger.info("Tray shutdown: cleanup complete, exiting.")
        os._exit(0)

    try:
        from helm.kelvin_status import startup_banner
        startup_banner(url)
    except Exception:
        pass

    from helm.headless import is_headless
    if is_headless():
        logger.info("Headless mode: no tray, desktop Kelvin or keep-awake (Telegram, WhatsApp and the web UI still work)")
    else:
        try:
            from helm.keep_awake import start_keep_awake
            start_keep_awake()
        except Exception as exc:
            logger.info("Keep-awake not available: %s", exc)

        try:
            from helm.tray import hide_console, start_tray, stop_tray
            hide_console()
            start_tray(actual_port, shutdown_callback=_tray_shutdown)
        except Exception as exc:
            logger.info("Tray icon not available: %s (console will remain visible)", exc)

    async def _open_browser():
        await asyncio.sleep(1.2)
        # Try to open in Chrome/Edge "app mode" (standalone window, no tabs/address bar)
        # This gives the PWA-like experience without requiring a manual install
        opened = False
        if sys.platform == "win32":
            for browser_path in [
                shutil.which("chrome"),
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                shutil.which("msedge"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ]:
                if browser_path and os.path.isfile(browser_path):
                    try:
                        subprocess.Popen([browser_path, f"--app={url}"], **hidden_kwargs())
                        opened = True
                        logger.info("Opened in app mode via %s", browser_path)
                        break
                    except Exception as exc:
                        logger.debug("Could not launch %s: %s", browser_path, exc)
        if not opened:
            webbrowser.open(url)

    # Load agents and start the agent schedule cron runner
    from helm.agent.runner import register_agent_schedules, agent_cron_runner, resume_interrupted_runs
    register_agent_schedules()
    asyncio.create_task(agent_cron_runner())
    # A4: clean up any runs that were in-flight when the server last stopped
    asyncio.create_task(resume_interrupted_runs())

    # Load persisted scheduled tasks and start the cron runner
    load_scheduled_tasks()
    asyncio.create_task(cron_runner())
    from helm.kelvin_report import daily_checkin_loop
    asyncio.create_task(daily_checkin_loop())
    asyncio.create_task(heartbeat_runner())
    asyncio.create_task(_open_browser())

    # WhatsApp: reconnect if it was linked before (QR scanned in Settings).
    try:
        from helm.whatsapp_bridge import autostart as _wa_autostart
        asyncio.create_task(_wa_autostart())
    except Exception as exc:
        logger.warning("WhatsApp autostart failed: %s", exc)

    # Discord and Slack bots, when their tokens are set (see .env.example).
    try:
        from helm.chat_adapters.startup import start_configured as _start_chat_apps
        _start_chat_apps()
    except Exception as exc:
        logger.warning("Chat apps not started: %s", exc)

    # Start cloud backup scheduler (checks every 5 min for due backups)
    try:
        from helm.cloud_backup.scheduler import start_scheduler
        asyncio.create_task(start_scheduler())
    except Exception as exc:
        logger.warning("Cloud backup scheduler start failed: %s", exc)

    # Start learning hygiene runner (weekly: stale playbooks, log compaction, index refresh)
    try:
        from helm.learning.hygiene import hygiene_runner as _hygiene_runner
        asyncio.create_task(_hygiene_runner())
    except Exception as exc:
        logger.warning("Learning hygiene runner start failed: %s", exc)

    # Start AI subprocess watchdog (detects dead processes, notifies users)
    from helm.resilience import ai_watchdog
    asyncio.create_task(ai_watchdog())

    # Start auto-update checker (checks every 4 hours, first check after 30s)
    from helm.updater import auto_check_loop
    asyncio.create_task(auto_check_loop())

    # Start device link sync loop (syncs connections + flushes telemetry every 30 min)
    from helm.device_link import device_sync_loop, track_usage
    asyncio.create_task(device_sync_loop())

    # Track app launch
    try:
        from helm.version import APP_VERSION
        track_usage("app", "launched", {"version": APP_VERSION})
    except Exception:
        pass

    if _st.telegram_app:
        from telegram import Update
        try:
            async with _st.telegram_app:
                await _st.telegram_app.start()
                await _st.telegram_app.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    error_callback=_telegram_polling_error_handler("Startup", _st.telegram_app),
                )
                logger.info("Telegram bot started. Polling for updates...")
                if _st.telegram_chat_id:
                    logger.info("Telegram chat_id pre-set to %s — web→Telegram forwarding ready", _st.telegram_chat_id)
                else:
                    logger.warning("No ALLOWED_USER_IDS configured — web→Telegram forwarding disabled until first Telegram message")
                await server.serve()           # blocks until Ctrl+C
                await _st.telegram_app.updater.stop()
                await _st.telegram_app.stop()
        except Exception as exc:
            # Telegram init/start must never take down the web UI. A network
            # timeout reaching api.telegram.org (firewall/VPN/ISP block) or a
            # stale token should degrade gracefully: log it, drop the bot, and
            # keep serving the web app.
            logger.error("Telegram bot disabled (%s) — serving web UI without Telegram", exc)
            _st.telegram_app = None
            if not server.started:
                await server.serve()
    else:
        await server.serve()
        # Clean up any hot-started Telegram bot
        if _st.telegram_app:
            try:
                await _st.telegram_app.updater.stop()
                await _st.telegram_app.stop()
                await _st.telegram_app.shutdown()
                logger.info("Hot-started Telegram bot stopped.")
            except Exception as exc:
                logger.warning("Telegram shutdown error: %s", exc)


def main():
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Shutting down (Ctrl+C).")
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
    finally:
        # Flush telemetry before anything else so events aren't lost
        try:
            from helm.device_link import flush_telemetry
            flush_telemetry()
        except Exception:
            pass
        # Graceful shutdown — stop AI processes, close DB, flush logs
        try:
            import asyncio as _aio
            loop = _aio.new_event_loop()
            from helm.resilience import graceful_shutdown
            loop.run_until_complete(graceful_shutdown())
            loop.close()
        except (Exception, asyncio.CancelledError):
            # Fallback: at least close DB connections. (A task left over from the
            # stopped server loop can surface as CancelledError here.)
            try:
                from helm.db import close_all
                close_all()
            except Exception:
                pass


if __name__ == "__main__":
    main()
