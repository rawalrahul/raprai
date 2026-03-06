"""
helm/resilience.py — Error recovery and graceful degradation for RAPR AI.

Provides:
  - Port conflict auto-resolution (find next free port)
  - SQLite integrity check + auto-recovery on startup
  - Crash log file handler (rotating, structured)
  - FastAPI global exception handler
  - AI subprocess watchdog (detect dead processes, notify user)
  - Graceful shutdown helpers

All resilience features are wired up via functions called from web_app.py.
"""

import logging
import os
import pathlib
import shutil
import socket
import sqlite3
import sys
import time
import traceback
import asyncio
from logging.handlers import RotatingFileHandler
from typing import Optional

from helm.config import logger
from helm.paths import user_data_dir

# ---------------------------------------------------------------------------
# 1. Port conflict auto-resolution
# ---------------------------------------------------------------------------

MAX_PORT_TRIES = 10  # Try up to 10 ports before giving up


def _port_in_use(host: str, port: int) -> bool:
    """Check if a TCP port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_free_port(host: str, preferred_port: int) -> int:
    """
    Return *preferred_port* if it's free, otherwise try up to MAX_PORT_TRIES
    subsequent ports.  Raises RuntimeError if none are available.
    """
    for offset in range(MAX_PORT_TRIES):
        candidate = preferred_port + offset
        if candidate > 65535:
            break
        if not _port_in_use(host, candidate):
            if offset > 0:
                logger.warning(
                    "Port %d already in use — using port %d instead.",
                    preferred_port, candidate,
                )
            return candidate
    raise RuntimeError(
        f"Could not find a free port in range {preferred_port}–{preferred_port + MAX_PORT_TRIES - 1}. "
        f"Please close the application using that port or set WEB_PORT in .env."
    )


# ---------------------------------------------------------------------------
# 2. SQLite integrity check + auto-recovery
# ---------------------------------------------------------------------------

def check_db_integrity() -> bool:
    """
    Run PRAGMA integrity_check on the database.

    Returns True if the database is healthy.
    If corruption is detected:
      - Backs up the corrupt DB
      - Removes it so init_db() creates a fresh one
      - Returns False
    """
    from helm.db import db_path, get_db

    path = db_path()
    if not path.exists():
        return True  # No DB yet — will be created fresh

    try:
        conn = get_db()
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result and result[0] == "ok":
            logger.info("Database integrity check: OK")
            # Also run a WAL checkpoint to keep the WAL file small
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            return True
        else:
            status = result[0] if result else "unknown error"
            logger.error("Database integrity check FAILED: %s", status)
    except sqlite3.DatabaseError as e:
        logger.error("Database integrity check error: %s", e)
    except Exception as e:
        logger.error("Unexpected error during integrity check: %s", e)

    # --- Corruption detected: backup and recreate ---
    _backup_corrupt_db(path)
    return False


def _backup_corrupt_db(path: pathlib.Path):
    """Back up a corrupt database file before deletion."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_name = path.with_suffix(f".corrupt_{ts}.db")
    try:
        shutil.copy2(str(path), str(backup_name))
        logger.warning("Corrupt database backed up to: %s", backup_name)
    except Exception as e:
        logger.error("Failed to backup corrupt database: %s", e)

    # Remove corrupt DB so init_db() creates a fresh one
    try:
        path.unlink()
        # Also remove WAL and SHM files
        for suffix in (".db-wal", ".db-shm"):
            wal_path = path.with_suffix(suffix)
            if wal_path.exists():
                wal_path.unlink()
        logger.info("Removed corrupt database. A fresh one will be created.")
    except Exception as e:
        logger.error("Failed to remove corrupt database: %s", e)


# ---------------------------------------------------------------------------
# 3. Crash log — rotating file handler
# ---------------------------------------------------------------------------

_crash_log_handler: Optional[RotatingFileHandler] = None


def setup_crash_logging():
    """
    Set up a rotating crash log file that captures ERROR+ messages.

    Log file: {user_data_dir}/logs/helm.log
    Max 5 MB per file, keeps 3 backups.
    """
    global _crash_log_handler

    log_dir = user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "helm.log"

    handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    # Log everything INFO+ to file (more verbose than console for debugging)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Add to helm logger
    logger.addHandler(handler)

    # Also capture warnings and errors from uvicorn/asyncio
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    _crash_log_handler = handler

    # Log startup info
    logger.info("=" * 60)
    logger.info("RAPR AI starting — crash log: %s", log_file)
    logger.info("Python %s on %s", sys.version.split()[0], sys.platform)
    try:
        import platform
        logger.info("OS: %s | Machine: %s", platform.platform(), platform.machine())
    except Exception:
        pass
    logger.info("=" * 60)


def get_crash_log_path() -> Optional[pathlib.Path]:
    """Return the path to the crash log file, or None if not configured."""
    log_file = user_data_dir() / "logs" / "helm.log"
    return log_file if log_file.exists() else None


# ---------------------------------------------------------------------------
# 4. FastAPI global exception handler
# ---------------------------------------------------------------------------

def install_exception_handlers(app):
    """
    Register global exception handlers on the FastAPI app.

    Catches unhandled errors and logs them to the crash log
    instead of just printing to console.
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception):
        # Log the full traceback
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        logger.error(
            "Unhandled exception on %s %s:\n%s",
            request.method, request.url.path,
            "".join(tb),
        )
        # Return a safe error to the client (don't leak internals)
        return JSONResponse(
            {"error": "Internal server error. Check logs for details."},
            status_code=500,
        )

    @app.exception_handler(404)
    async def _not_found(request: Request, exc):
        return JSONResponse(
            {"error": f"Not found: {request.url.path}"},
            status_code=404,
        )

    logger.info("Global exception handlers installed")


# ---------------------------------------------------------------------------
# 5. AI subprocess watchdog
# ---------------------------------------------------------------------------

_watchdog_running = False


async def ai_watchdog(check_interval: float = 15.0):
    """
    Background task that periodically checks AI subprocess health.

    If a session's AI process has died silently, it:
      - Marks the session as not busy
      - Notifies connected WebSocket clients
      - Logs the failure

    Runs every `check_interval` seconds.
    """
    global _watchdog_running
    if _watchdog_running:
        return
    _watchdog_running = True

    import helm.state as _st

    logger.info("AI watchdog started (interval: %.0fs)", check_interval)

    while True:
        try:
            await asyncio.sleep(check_interval)

            for sid, sess in list(_st.sessions.items()):
                if not sess.get("busy"):
                    continue

                proc = sess.get("proc")
                if proc is None:
                    continue

                # Check if the subprocess is still alive
                poll_result = None
                try:
                    if hasattr(proc, "poll"):
                        poll_result = proc.poll()
                    elif hasattr(proc, "returncode"):
                        poll_result = proc.returncode
                except Exception:
                    continue

                if poll_result is not None:
                    # Process has died — clean up the session
                    exit_code = poll_result
                    session_name = sess.get("name", sid)
                    logger.warning(
                        "Watchdog: AI process for session '%s' (PID: %s) exited with code %s",
                        session_name,
                        sess.get("pid", "?"),
                        exit_code,
                    )

                    # Mark session as not busy
                    sess["busy"] = False
                    sess["status"] = f"crashed (exit {exit_code})"
                    sess.pop("proc", None)

                    # Notify WebSocket clients about the crash
                    try:
                        from helm.broadcast import broadcast
                        await broadcast({
                            "type": "session_update",
                            "session_id": sid,
                            "status": "crashed",
                            "message": (
                                f"AI process crashed (exit code {exit_code}). "
                                f"Send a new message to auto-restart."
                            ),
                        })
                    except Exception as e:
                        logger.debug("Watchdog broadcast error: %s", e)

        except asyncio.CancelledError:
            logger.info("AI watchdog stopped")
            break
        except Exception as e:
            logger.error("AI watchdog error: %s", e)
            await asyncio.sleep(check_interval)


# ---------------------------------------------------------------------------
# 6. Graceful shutdown
# ---------------------------------------------------------------------------

async def graceful_shutdown():
    """
    Clean up resources before exit.

    Called from web_app.py's finally block or signal handler.
    """
    logger.info("Graceful shutdown initiated...")

    import helm.state as _st

    # Stop all active AI subprocesses
    stopped = 0
    for sid, sess in list(_st.sessions.items()):
        proc = sess.get("proc")
        if proc is not None:
            try:
                if hasattr(proc, "kill"):
                    proc.kill()
                elif hasattr(proc, "terminate"):
                    proc.terminate()
                stopped += 1
            except Exception:
                pass
            sess["busy"] = False
            sess.pop("proc", None)

    if stopped:
        logger.info("Stopped %d active AI process(es)", stopped)

    # Close database connections
    try:
        from helm.db import close_all
        close_all()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database: %s", e)

    # Flush log handlers
    for handler in logger.handlers:
        try:
            handler.flush()
        except Exception:
            pass

    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# 7. Startup health summary
# ---------------------------------------------------------------------------

def log_startup_health():
    """Log a health summary on startup for diagnostics."""
    try:
        import shutil
        import platform

        # Disk space
        total, used, free = shutil.disk_usage(str(user_data_dir()))
        free_gb = free / (1024 ** 3)
        if free_gb < 1.0:
            logger.warning("Low disk space: %.1f GB free", free_gb)
        else:
            logger.info("Disk space: %.1f GB free", free_gb)

        # Memory (best-effort)
        try:
            import psutil
            mem = psutil.virtual_memory()
            logger.info("RAM: %.1f GB total, %.1f%% used", mem.total / (1024**3), mem.percent)
        except ImportError:
            pass

    except Exception as e:
        logger.debug("Startup health check error: %s", e)
