"""
web_app.py — Claude Remote: Web UI + Telegram Bot in one process.

Replaces the bare command-prompt window with a local chat UI at http://localhost:8000.
The Telegram bot continues to work in parallel; both channels share the same state.
"""

import asyncio
import json
import logging
import os
import pathlib
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS = set(
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
)
IDLE_TIMEOUT = float(os.environ.get("OUTPUT_IDLE_TIMEOUT", "1.5"))
MAX_WAIT = float(os.environ.get("OUTPUT_MAX_WAIT", "60"))
NO_OUTPUT_TIMEOUT = float(os.environ.get("OUTPUT_NO_RESPONSE", "5"))
CLAUDE_TIMEOUT = float(os.environ.get("CLAUDE_TIMEOUT", "600"))
_DEFAULT_CWD = os.environ.get("SESSION_CWD", os.getcwd())
WEB_PORT = int(os.environ.get("WEB_PORT", "8000"))
WEB_HOST = os.environ.get("WEB_HOST", "127.0.0.1")
CHAT_LOG_DIR = pathlib.Path(os.environ.get("CHAT_LOG_DIR", "chat_logs"))

_CMD_EXT = ".cmd" if sys.platform == "win32" else ""

# ---------------------------------------------------------------------------
# ANSI cleaning
# ---------------------------------------------------------------------------

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][AB012]|\x1b.")
HISTORY_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _clean_output(raw: str) -> str:
    text = ANSI_ESCAPE.sub("", raw)
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        parts = line.split("\r")
        result = ""
        for part in parts:
            if part:
                result = part
        cleaned.append(result)
    return "\n".join(cleaned)


# ---------------------------------------------------------------------------
# TerminalSession
# ---------------------------------------------------------------------------

class TerminalSession:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._q: queue.Queue = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def _read_loop(self):
        try:
            for line in self._proc.stdout:
                self._q.put(line)
        except Exception:
            pass
        self._q.put(None)

    def launch(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                raise RuntimeError("Session already running (PID %d)" % self._proc.pid)
            self._q = queue.Queue()
            self._proc = subprocess.Popen(
                ["cmd.exe"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    def write(self, text: str):
        if not self.is_alive():
            raise RuntimeError("No active session. Use /launch first.")
        self._proc.stdin.write(text + "\n")
        self._proc.stdin.flush()

    def drain(
        self,
        idle_timeout: float = IDLE_TIMEOUT,
        max_wait: float = MAX_WAIT,
        no_output_timeout: float = NO_OUTPUT_TIMEOUT,
    ) -> str:
        chunks: list[str] = []
        start = time.monotonic()
        got_first = False

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= max_wait:
                break
            if got_first:
                timeout = idle_timeout
            else:
                remaining = no_output_timeout - elapsed
                if remaining <= 0:
                    break
                timeout = min(remaining, no_output_timeout)
            try:
                item = self._q.get(timeout=timeout)
            except queue.Empty:
                break
            if item is None:
                break
            chunks.append(item)
            got_first = True

        raw = "".join(chunks)
        return _clean_output(raw)

    def send_interrupt(self):
        if not self.is_alive():
            raise RuntimeError("No active session.")
        os.kill(self._proc.pid, signal.CTRL_C_EVENT)

    def stop(self):
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None


# ---------------------------------------------------------------------------
# Shared global state
# ---------------------------------------------------------------------------

_active_ai: Optional[str] = None        # "claude" | "codex" | "gemini" | None
_pending_tg_context: Optional[str] = None   # injected into next Telegram message after /resume
_session_cwd: str = _DEFAULT_CWD        # live working directory — changeable at runtime
_tg_browse_state: dict = {}             # user_id → {"path": str, "dirs": list, "page": int}
_BROWSE_PAGE_SIZE = 8
_session = TerminalSession()
_claude_messages: list[str] = []
# For private bot DMs, chat_id == user_id, so pre-init from ALLOWED_USER_IDS.
# This ensures web-initiated responses are forwarded to Telegram even before
# the user sends their first Telegram message.
_telegram_chat_id: Optional[int] = next(iter(ALLOWED_USER_IDS), None)
_chat_history: list[dict] = []           # in-memory log for new WS clients joining mid-session
_ws_clients: set[WebSocket] = set()
_telegram_app: Optional[Application] = None  # set in main(), used to send Telegram messages from web

# ---------------------------------------------------------------------------
# AI integration plugin loader
# ---------------------------------------------------------------------------

# Populated at startup by _load_integrations().
# Each entry: key -> {"name": str, "emoji": str, "color": str,
#                     "build_command": callable, "env_vars": list, "setup_hint": str}
_integrations: dict = {}


def _load_integrations() -> None:
    """Scan the integrations/ folder and register every non-underscore .py file."""
    import importlib.util
    folder = pathlib.Path(__file__).parent / "integrations"
    if not folder.exists():
        logger.info("No integrations/ folder found — skipping plugin load.")
        return
    for path in sorted(folder.glob("*.py")):
        if path.stem.startswith("_"):
            continue                          # skip _template.py and __init__.py
        try:
            spec = importlib.util.spec_from_file_location(f"integrations.{path.stem}", path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            key = getattr(mod, "KEY", path.stem)
            _integrations[key] = {
                "name":          getattr(mod, "NAME",       key.title()),
                "emoji":         getattr(mod, "EMOJI",      "🤖"),
                "color":         getattr(mod, "COLOR",      "#6b7280"),
                "build_command": mod.build_command,
                "env_vars":      getattr(mod, "ENV_VARS",   []),
                "setup_hint":    getattr(mod, "SETUP_HINT", ""),
            }
            logger.info("Loaded AI integration: %s (%s)", key, _integrations[key]["name"])
        except Exception as exc:
            logger.warning("Failed to load integration %s: %s", path.name, exc)


# ---------------------------------------------------------------------------
# WebSocket broadcast helpers
# ---------------------------------------------------------------------------

async def _broadcast(data: dict):
    """Push a JSON message to every connected WebSocket client."""
    if not _ws_clients:
        return
    payload = json.dumps(data)
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


def _ts() -> str:
    return datetime.now().isoformat()


def _is_valid_history_date(date: str) -> bool:
    """Accept only YYYY-MM-DD date keys for history endpoints."""
    return bool(HISTORY_DATE_RE.fullmatch(date))


def _save_message_to_log(msg: dict):
    """Append a message to today's JSONL log file in CHAT_LOG_DIR."""
    try:
        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = CHAT_LOG_DIR / f"{date_str}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Could not save message to log: %s", e)


def _save_cwd_to_log(path: str):
    """Persist the current working directory as a record in today's JSONL log."""
    try:
        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = CHAT_LOG_DIR / f"{date_str}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "cwd", "path": path, "timestamp": _ts()}, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Could not save CWD to log: %s", e)


def _save_ai_to_log(model: Optional[str]):
    """Persist the active AI model as a record in today's JSONL log."""
    try:
        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = CHAT_LOG_DIR / f"{date_str}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "ai", "model": model, "timestamp": _ts()}, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Could not save AI model to log: %s", e)


def _save_last_state():
    """Write a persistent last_state.json with current CWD and AI.

    This is the resume fallback for old logs that pre-date per-session CWD records.
    Whenever the state changes (CWD or AI), this file is updated so _perform_resume
    can fall back to it when a session log has no embedded CWD record.
    """
    try:
        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        state_file = CHAT_LOG_DIR / "last_state.json"
        date_str = datetime.now().strftime("%Y-%m-%d")
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(
                {"cwd": _session_cwd, "ai": _active_ai, "date": date_str, "timestamp": _ts()},
                f,
                ensure_ascii=False,
            )
    except Exception as e:
        logger.warning("Could not save last state: %s", e)


async def _push_message(role: str, content: str, ai: Optional[str] = None, source: str = "web"):
    """Record a chat message and broadcast it to all WS clients."""
    msg = {
        "type": "message",
        "role": role,
        "content": content,
        "ai": ai,
        "source": source,
        "timestamp": _ts(),
    }
    _chat_history.append(msg)
    if len(_chat_history) > 200:
        del _chat_history[:-200]
    _save_message_to_log(msg)
    await _broadcast(msg)


async def _push_state():
    _save_ai_to_log(_active_ai)   # persist current AI model to today's log
    _save_last_state()            # update persistent fallback used by resume
    await _broadcast({
        "type": "state",
        "active_ai": _active_ai,
        "session_alive": _session.is_alive(),
        "cwd": _session_cwd,
    })


async def _push_thinking(active: bool, ai: Optional[str] = None):
    await _broadcast({"type": "thinking", "active": active, "ai": ai or _active_ai})


# ---------------------------------------------------------------------------
# AI runner
# ---------------------------------------------------------------------------

def _run_ai_print(cmd: list[str], cwd: str, name: str) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            timeout=CLAUDE_TIMEOUT,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            # Combine stdout + stderr so nothing is hidden
            parts = [p for p in [stdout, stderr] if p]
            output = "\n".join(parts) if parts else f"({name} exited {result.returncode})"
        else:
            output = stdout or "(no output)"

        return output
    except FileNotFoundError:
        return f"Error: '{cmd[0]}' not found in PATH."
    except subprocess.TimeoutExpired:
        return f"(timed out after {CLAUDE_TIMEOUT}s)"
    except Exception as e:
        return f"(error: {e})"


def _build_claude_cmd(prompt: str, has_history: bool) -> list[str]:
    cmd = ["claude"]
    if has_history:
        cmd.append("--continue")
    cmd.extend(["-p", prompt])
    return cmd


# ---------------------------------------------------------------------------
# Core message processor (shared by web + Telegram)
# ---------------------------------------------------------------------------

async def _process_message(text: str, source: str = "web") -> str:
    """
    Route `text` to the active AI or shell session.
    Returns the response string.
    Broadcasts user message + thinking + response to all WS clients.
    """
    global _active_ai, _claude_messages

    # Log the user message to web UI
    await _push_message("user", text, ai=None, source=source)

    if _active_ai == "claude":
        await _push_thinking(True, "claude")
        has_history = len(_claude_messages) > 0
        cmd = _build_claude_cmd(text, has_history)
        _claude_messages.append(text)
        before = await asyncio.to_thread(_snapshot_dir, _session_cwd)
        output = await asyncio.to_thread(_run_ai_print, cmd, _session_cwd, "claude")
        after  = await asyncio.to_thread(_snapshot_dir, _session_cwd)
        await _push_thinking(False)
        await _push_message("assistant", output, ai="claude", source=source)
        await _handle_new_files(before, after, source)
        return output

    if _active_ai in _integrations:
        await _push_thinking(True, _active_ai)
        cmd    = _integrations[_active_ai]["build_command"](text)
        before = await asyncio.to_thread(_snapshot_dir, _session_cwd)
        output = await asyncio.to_thread(_run_ai_print, cmd, _session_cwd, _active_ai)
        after  = await asyncio.to_thread(_snapshot_dir, _session_cwd)
        await _push_thinking(False)
        await _push_message("assistant", output, ai=_active_ai, source=source)
        await _handle_new_files(before, after, source)
        return output

    # Fallback: shell session
    if not _session.is_alive():
        msg = "No session running. Use Launch button or /launch to start cmd.exe."
        await _push_message("system", msg, source=source)
        return msg

    before = await asyncio.to_thread(_snapshot_dir, _session_cwd)
    _session.write(text)
    output = await asyncio.to_thread(_session.drain)
    after  = await asyncio.to_thread(_snapshot_dir, _session_cwd)
    output = output or "(no output)"
    await _push_message("assistant", output, ai="shell", source=source)
    await _handle_new_files(before, after, source)
    return output


async def _forward_to_telegram(text: str):
    """Send a message to the user's Telegram chat (fire-and-forget)."""
    if _telegram_app and _telegram_chat_id:
        try:
            await _telegram_app.bot.send_message(chat_id=_telegram_chat_id, text=text)
        except Exception as e:
            logger.warning("Telegram forward failed: %s", e)


async def _change_cwd(new_path: str, source: str = "web") -> bool:
    """Validate and switch the working directory. Broadcasts the change to all clients."""
    global _session_cwd
    if not new_path.strip():
        await _push_message("system", "❌ Path cannot be empty.", source=source)
        return False
    path = pathlib.Path(new_path.strip()).expanduser().resolve()
    if not path.exists():
        await _push_message("system", f"❌ Directory not found: {path}", source=source)
        return False
    if not path.is_dir():
        await _push_message("system", f"❌ Not a directory: {path}", source=source)
        return False
    _session_cwd = str(path)
    _save_cwd_to_log(_session_cwd)
    _save_last_state()            # keep persistent fallback up-to-date
    logger.info("Working directory changed to: %s", _session_cwd)
    # Broadcast new CWD to all web clients
    await _broadcast({"type": "cwd", "path": _session_cwd})
    await _push_message("system", f"📁 Working directory → {_session_cwd}", source=source)
    return True


# ---------------------------------------------------------------------------
# File detection & Telegram file sender
# ---------------------------------------------------------------------------

# Extensions we auto-send to Telegram after an AI command creates them
_PHOTO_EXT   = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_VIDEO_EXT   = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
_GIF_EXT     = {".gif"}
_DOC_EXT     = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc",
    ".xlsx", ".xls", ".csv",
    ".html", ".htm",
    ".zip", ".tar", ".gz",
    ".txt", ".md",
}
_ALL_SENDABLE = _PHOTO_EXT | _VIDEO_EXT | _GIF_EXT | _DOC_EXT

# Max file size to auto-send (50 MB — Telegram bot limit for most types)
_MAX_SEND_BYTES = 50 * 1024 * 1024


# Directories we never recurse into when snapshotting (avoid walking huge trees)
_SKIP_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".env", "dist", "build", ".next", ".nuxt", ".cache",
    ".tox", ".mypy_cache", ".pytest_cache", "target",
})


def _snapshot_dir(cwd: str) -> set[str]:
    """Return a set of absolute file paths in cwd, scanning up to 2 levels deep.

    Goes one level into newly-created subdirectories so files created inside
    a new folder (e.g. an HTML output directory) are still detected.
    Skips common large/build directories to stay fast.
    """
    result: set[str] = set()
    try:
        base = pathlib.Path(cwd)
        for entry in base.iterdir():
            if entry.is_file():
                result.add(str(entry))
            elif entry.is_dir() and entry.name not in _SKIP_DIRS:
                try:
                    for child in entry.iterdir():
                        if child.is_file():
                            result.add(str(child))
                except Exception:
                    pass
    except Exception:
        pass
    return result


async def _send_file_to_telegram(filepath: str, source: str = "web"):
    """Send a newly-created file to Telegram as the appropriate media type."""
    if not (_telegram_app and _telegram_chat_id):
        return

    path = pathlib.Path(filepath)
    ext  = path.suffix.lower()

    # Skip files that are too large or not in our sendable list
    try:
        size = path.stat().st_size
    except Exception:
        return
    if size == 0 or size > _MAX_SEND_BYTES:
        logger.info("Skipping large/empty file: %s (%d bytes)", path.name, size)
        return

    # Build a relative URL path so files inside subdirs work correctly
    try:
        rel_posix = path.resolve().relative_to(pathlib.Path(_session_cwd).resolve()).as_posix()
    except ValueError:
        rel_posix = path.name
    local_url = f"http://localhost:{WEB_PORT}/files/{rel_posix}"
    # Show a compact display name (include one parent dir if in a subdir)
    display   = str(pathlib.Path(rel_posix))
    caption   = f"📎 {display}\n🔗 {local_url}"

    try:
        with open(filepath, "rb") as fh:
            bot = _telegram_app.bot
            if ext in _PHOTO_EXT:
                await bot.send_photo(chat_id=_telegram_chat_id, photo=fh, caption=caption)
            elif ext in _VIDEO_EXT:
                await bot.send_video(chat_id=_telegram_chat_id, video=fh, caption=caption)
            elif ext in _GIF_EXT:
                await bot.send_animation(chat_id=_telegram_chat_id, animation=fh, caption=caption)
            else:
                await bot.send_document(chat_id=_telegram_chat_id, document=fh, caption=caption)
        logger.info("Sent file to Telegram: %s", path.name)
    except Exception as e:
        logger.warning("Could not send %s to Telegram: %s", path.name, e)


async def _handle_new_files(before: set[str], after: set[str], source: str):
    """Diff snapshots, notify in web chat, and forward each new file to Telegram."""
    new_files = sorted(after - before)
    for filepath in new_files:
        path = pathlib.Path(filepath)
        ext  = path.suffix.lower()
        if ext not in _ALL_SENDABLE:
            continue

        local_url = f"http://localhost:{WEB_PORT}/files/{path.name}"
        size_kb   = path.stat().st_size // 1024

        # Notify in web chat
        await _push_message(
            "system",
            f"📎 New file: {path.name} ({size_kb} KB)  →  {local_url}",
            source=source,
        )
        # Send to Telegram
        await _send_file_to_telegram(filepath, source)


# ---------------------------------------------------------------------------
# FastAPI app + WebSocket
# ---------------------------------------------------------------------------

app = FastAPI(title="Claude Remote")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=_HTML)


@app.get("/files/{filename:path}")
async def serve_file(filename: str):
    """Dynamically serve any file from the current _session_cwd."""
    from fastapi.responses import FileResponse as _FR
    base = pathlib.Path(_session_cwd).resolve()
    path = (base / filename).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return HTMLResponse(
            "<h2>Invalid file path</h2><p>Requested file must be inside current working directory.</p>",
            status_code=400,
        )
    if not path.exists() or not path.is_file():
        return HTMLResponse(
            f"<h2>File not found</h2><p><code>{filename}</code> not in <code>{_session_cwd}</code></p>",
            status_code=404,
        )
    return _FR(str(path))


@app.get("/browse")
async def browse_directory(path: str = ""):
    """Return subdirectories and navigation info for the folder browser."""
    from fastapi.responses import JSONResponse
    import string as _string
    target = path.strip() if path.strip() else _session_cwd
    p = pathlib.Path(target).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        # Fall back to session CWD if given path is bad
        p = pathlib.Path(_session_cwd).resolve()
    try:
        dirs = sorted(
            [d.name for d in p.iterdir() if d.is_dir()],
            key=lambda x: x.lower(),
        )
    except (PermissionError, OSError):
        dirs = []
    parent = str(p.parent) if str(p) != str(p.parent) else None
    # Enumerate available Windows drive letters
    drives = []
    if sys.platform == "win32":
        drives = [f"{d}:\\" for d in _string.ascii_uppercase if pathlib.Path(f"{d}:\\").exists()]
    return JSONResponse({"path": str(p), "dirs": dirs, "parent": parent, "drives": drives})


@app.get("/browse/native")
async def browse_native():
    """Open the Windows native folder-picker dialog on the server machine.
    Returns {"path": "<selected>"} or {"path": null} if cancelled / not supported."""
    from fastapi.responses import JSONResponse
    if sys.platform != "win32":
        return JSONResponse({"path": None})
    path = await asyncio.to_thread(_windows_folder_picker)
    return JSONResponse({"path": path})


@app.get("/integrations")
async def list_integrations_endpoint():
    """Return all loaded AI integration plugins so the web UI can build its menu dynamically."""
    from fastapi.responses import JSONResponse
    return JSONResponse([
        {
            "key":   key,
            "name":  info["name"],
            "emoji": info["emoji"],
            "color": info["color"],
        }
        for key, info in _integrations.items()
    ])


@app.get("/history")
async def history_list():
    """Return list of saved chat log sessions (date + message count), newest first."""
    from fastapi.responses import JSONResponse
    names = _load_chat_names()
    sessions = []
    if CHAT_LOG_DIR.exists():
        for log_file in sorted(CHAT_LOG_DIR.glob("*.jsonl"), reverse=True):
            date_str = log_file.stem
            try:
                count = sum(
                    1 for line in log_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and '"type": "message"' in line
                )
            except Exception:
                count = 0
            sessions.append({"date": date_str, "count": count, "name": names.get(date_str, "")})
    return JSONResponse(sessions)


@app.get("/history/{date}")
async def history_get(date: str):
    """Return all messages for a given date (YYYY-MM-DD)."""
    from fastapi.responses import JSONResponse
    if not _is_valid_history_date(date):
        return JSONResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status_code=400)
    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    messages = []
    last_cwd = None
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("type") == "cwd":
                last_cwd = rec["path"]
            elif rec.get("type") == "message":
                messages.append(rec)
        except Exception:
            pass
    return JSONResponse({"messages": messages, "cwd": last_cwd})


@app.delete("/history/{date}")
async def history_delete(date: str):
    """Delete the log file for a given date."""
    from fastapi.responses import JSONResponse
    if not _is_valid_history_date(date):
        return JSONResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status_code=400)
    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    try:
        log_file.unlink()
        _save_chat_name(date, "")  # remove custom name entry if any
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def _load_chat_names() -> dict:
    """Load the chat_names.json sidecar file, returning a date→name mapping."""
    names_file = CHAT_LOG_DIR / "chat_names.json"
    if names_file.exists():
        try:
            return json.loads(names_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_chat_name(date: str, name: str) -> None:
    """Persist (or clear) a custom display name for a chat session date."""
    CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    names_file = CHAT_LOG_DIR / "chat_names.json"
    names = _load_chat_names()
    name = name.strip()
    if name:
        names[date] = name
    else:
        names.pop(date, None)
    names_file.write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")


@app.patch("/history/{date}/name")
async def history_rename(date: str, request: Request):
    """Set or clear a custom display name for a chat session date."""
    from fastapi.responses import JSONResponse
    if not _is_valid_history_date(date):
        return JSONResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status_code=400)
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    _save_chat_name(date, name)
    return JSONResponse({"ok": True, "name": name})


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info("WS client connected (total: %d)", len(_ws_clients))

    # Send current state + recent history to the new client
    await websocket.send_text(json.dumps({
        "type": "state",
        "active_ai": _active_ai,
        "session_alive": _session.is_alive(),
        "cwd": _session_cwd,
    }))
    for msg in _chat_history[-50:]:
        await websocket.send_text(json.dumps(msg))

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue
                response = await _process_message(content, source="web")
                # Forward to Telegram: prompt first (for context), then the response
                await _forward_to_telegram(f"🖥️ You (web): {content}")
                for chunk in [response[i:i+3800] for i in range(0, len(response), 3800)]:
                    await _forward_to_telegram(chunk)

            elif data.get("type") == "command":
                cmd = data.get("command", "")
                if cmd == "cwd":
                    # CWD change carries its path in the same message
                    await _change_cwd(data.get("path", ""), source="web")
                else:
                    await _handle_web_command(cmd, websocket)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WS error: %s", e)
    finally:
        _ws_clients.discard(websocket)
        logger.info("WS client disconnected (total: %d)", len(_ws_clients))


async def _handle_web_command(command: str, ws: WebSocket):
    """Handle control commands sent from the web UI."""
    global _active_ai, _claude_messages

    if command == "claude":
        _active_ai = "claude"
        _claude_messages = []
        await _push_state()
        await _push_message("system", "Claude Code active. Send a message to start.", source="web")

    elif command in _integrations:
        # Any registered integration — activated generically
        _active_ai = command
        await _push_state()
        info = _integrations[command]
        await _push_message(
            "system",
            f"{info['emoji']} {info['name']} active. Send a message to start.",
            source="web",
        )

    elif command == "stop_ai":
        _active_ai = None
        await _push_state()
        await _push_message("system", "AI mode off. Messages go to shell session.", source="web")

    elif command == "launch":
        try:
            _session.launch()
            output = await asyncio.to_thread(_session.drain, IDLE_TIMEOUT, 10.0, 5.0)
            await _push_state()
            await _push_message("system", "Shell session started.", source="web")
            if output:
                await _push_message("assistant", output, ai="shell", source="web")
        except RuntimeError as e:
            await _push_message("system", str(e), source="web")

    elif command == "stop":
        _session.stop()
        await _push_state()
        await _push_message("system", "Session stopped.", source="web")

    elif command == "interrupt":
        try:
            _session.send_interrupt()
            await _push_message("system", "Ctrl+C sent.", source="web")
        except RuntimeError as e:
            await _push_message("system", str(e), source="web")

    elif command == "clear":
        _claude_messages = []
        await _push_message("system", "Claude conversation history cleared.", source="web")


# ---------------------------------------------------------------------------
# Telegram handlers  (mirror all activity to web UI)
# ---------------------------------------------------------------------------

def _windows_folder_picker() -> Optional[str]:
    """Open a native Windows folder-picker dialog on the server desktop.
    Returns the selected absolute path, or None if the user cancelled."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(
            title="Select Working Directory",
            initialdir=_session_cwd,
        )
        root.destroy()
        return str(pathlib.Path(path)) if path else None
    except Exception:
        return None


def _update_env(key: str, value: str):
    """Update or add a key=value line in the .env file."""
    env_path = pathlib.Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def authorized_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global _telegram_chat_id
        user_id = update.effective_user.id
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            await update.message.reply_text("Unauthorized.")
            logger.warning("Rejected user %d", user_id)
            return
        # Store chat_id so web-initiated responses can be forwarded
        _telegram_chat_id = update.effective_chat.id
        return await func(update, context)
    return wrapper


async def _tg_send_chunks(
    update: Update,
    text: str,
    max_len: int = 3800,
    reply_markup=None,
):
    """Send text in Telegram-safe chunks. Attaches reply_markup to the last chunk."""
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)] if text.strip() else []
    if not chunks:
        await update.message.reply_text("(no output)", reply_markup=reply_markup)
        return
    for idx, chunk in enumerate(chunks):
        is_last = idx == len(chunks) - 1
        await update.message.reply_text(chunk, reply_markup=reply_markup if is_last else None)


# ---------------------------------------------------------------------------
# Inline keyboard helpers
# ---------------------------------------------------------------------------

def _ai_select_keyboard() -> InlineKeyboardMarkup:
    """Buttons shown when no AI is active — pick an AI to start.
    Claude is always first; all loaded integrations follow; Shell mode caps the list.
    """
    rows: list = []
    ai_buttons = [InlineKeyboardButton("🤖 Claude Code", callback_data="action:claude")]
    for key, info in _integrations.items():
        ai_buttons.append(
            InlineKeyboardButton(f"{info['emoji']} {info['name']}", callback_data=f"action:{key}")
        )
    ai_buttons.append(InlineKeyboardButton("🐚 Shell mode", callback_data="action:stop_ai"))
    # Pack 2 per row
    for i in range(0, len(ai_buttons), 2):
        rows.append(ai_buttons[i : i + 2])
    rows.append([InlineKeyboardButton("🔁 Resume last session", callback_data="action:resume")])
    rows.append([
        InlineKeyboardButton("💬 Past chats",    callback_data="action:history"),
        InlineKeyboardButton("📁 Change folder", callback_data="action:browse"),
    ])
    return InlineKeyboardMarkup(rows)


def _running_keyboard() -> InlineKeyboardMarkup:
    """Buttons shown while an AI session is active."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Interrupt",     callback_data="action:interrupt"),
            InlineKeyboardButton("🛑 Stop AI",       callback_data="action:stop"),
        ],
        [
            InlineKeyboardButton("🔀 Switch AI",     callback_data="action:switch"),
            InlineKeyboardButton("📁 Change folder", callback_data="action:browse"),
        ],
        [
            InlineKeyboardButton("💬 Past chats",    callback_data="action:history"),
            InlineKeyboardButton("🔁 Resume a session", callback_data="action:resume"),
        ],
    ])


@authorized_only
async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with AI picker buttons — no commands to memorise."""
    await update.message.reply_text(
        "👋 *Claude Remote*\n\n"
        "Pick an AI to get started, or just type your task.\n"
        f"Web UI: http://localhost:{WEB_PORT}",
        parse_mode="Markdown",
        reply_markup=_ai_select_keyboard(),
    )


@authorized_only
async def tg_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/menu — show the main action keyboard."""
    status = "🟢 Running" if _session.is_alive() else "⚪ No session"
    ai_name = {"claude": "Claude Code", "gemini": "Gemini", "codex": "Codex"}.get(_active_ai or "", "Shell mode")
    await update.message.reply_text(
        f"*Claude Remote — Menu*\n"
        f"Session: {status}   ·   AI: {ai_name}\n"
        f"📁 `{_session_cwd}`",
        parse_mode="Markdown",
        reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
    )


@authorized_only
async def tg_launch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Starting session…")
    try:
        _session.launch()
    except RuntimeError as e:
        await update.message.reply_text(str(e))
        await _push_message("system", str(e), source="telegram")
        return
    output = await asyncio.to_thread(_session.drain, IDLE_TIMEOUT, 10.0, 5.0)
    await _push_state()
    await _push_message("system", "Shell session started (via Telegram).", source="telegram")
    if output:
        await _push_message("assistant", output, ai="shell", source="telegram")
    await update.message.reply_text(
        output or "✅ Session started. Choose an AI:",
        reply_markup=_ai_select_keyboard(),
    )


@authorized_only
async def tg_claude(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai, _claude_messages
    _active_ai = "claude"
    _claude_messages = []
    await _push_state()
    await _push_message("system", "Claude Code active (via Telegram).", source="telegram")
    await update.message.reply_text(
        "🤖 *Claude Code* is active.\nJust type your task — I'll send it straight to Claude.",
        parse_mode="Markdown",
        reply_markup=_running_keyboard(),
    )


@authorized_only
async def tg_codex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai
    _active_ai = "codex"
    await _push_state()
    await _push_message("system", "Codex active (via Telegram).", source="telegram")
    await update.message.reply_text(
        "💻 *Codex* is active.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=_running_keyboard(),
    )


@authorized_only
async def tg_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai
    _active_ai = "gemini"
    await _push_state()
    await _push_message("system", "Gemini active (via Telegram).", source="telegram")
    await update.message.reply_text(
        "✨ *Gemini* is active.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=_running_keyboard(),
    )


@authorized_only
async def tg_stop_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai
    _active_ai = None
    await _push_state()
    await _push_message("system", "AI mode off (via Telegram).", source="telegram")
    await update.message.reply_text(
        "🐚 Back to shell mode.\nPick an AI to start again:",
        reply_markup=_ai_select_keyboard(),
    )


@authorized_only
async def tg_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _claude_messages
    _claude_messages = []
    await _push_message("system", "Claude history cleared (via Telegram).", source="telegram")
    await update.message.reply_text("Conversation history cleared.")


@authorized_only
async def tg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("Usage: /cmd <command>")
        return
    if not _session.is_alive():
        await update.message.reply_text("No session. /launch first.")
        return
    await _push_message("user", f"/cmd {text}", source="telegram")
    _session.write(text)
    output = await asyncio.to_thread(_session.drain)
    output = output or "(no output)"
    await _push_message("assistant", output, ai="shell", source="telegram")
    await _tg_send_chunks(update, output)


@authorized_only
async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _session.is_alive():
        await update.message.reply_text(
            f"Session alive. PID: {_session.pid()}\n"
            f"Active AI: {_active_ai or 'shell'}\n"
            f"⏱ Timeout: {int(CLAUDE_TIMEOUT)}s"
        )
    else:
        await update.message.reply_text(
            f"No active session.\n"
            f"Active AI: {_active_ai or 'shell'}\n"
            f"⏱ Timeout: {int(CLAUDE_TIMEOUT)}s"
        )


@authorized_only
async def tg_interrupt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        _session.send_interrupt()
        await _push_message("system", "Ctrl+C sent (via Telegram).", source="telegram")
        await update.message.reply_text(
            "⏸ Interrupted.",
            reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
        )
    except RuntimeError as e:
        await update.message.reply_text(str(e))


@authorized_only
async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _session.stop()
    await _push_state()
    await _push_message("system", "Session stopped (via Telegram).", source="telegram")
    await update.message.reply_text(
        "🛑 Session stopped.\nReady when you are:",
        reply_markup=_ai_select_keyboard(),
    )


@authorized_only
async def tg_cwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show or change the working directory: /cwd  or  /cwd <path>"""
    arg = (update.message.text or "").partition(" ")[2].strip()
    if not arg:
        # Just show current directory
        await update.message.reply_text(f"📁 Current directory:\n{_session_cwd}")
        return
    ok = await _change_cwd(arg, source="telegram")
    if ok:
        await update.message.reply_text(f"📁 Working directory changed to:\n{_session_cwd}")


@authorized_only
async def tg_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get or set the AI timeout: /timeout  or  /timeout <seconds>"""
    global CLAUDE_TIMEOUT
    arg = (update.message.text or "").partition(" ")[2].strip()
    if not arg:
        await update.message.reply_text(
            f"⏱ Current AI timeout: {int(CLAUDE_TIMEOUT)}s\n"
            f"Use /timeout <seconds> to change (e.g. /timeout 1800 for 30 min)"
        )
        return
    try:
        value = float(arg)
        if value < 10:
            await update.message.reply_text("❌ Minimum timeout is 10 seconds.")
            return
        CLAUDE_TIMEOUT = value
        _update_env("CLAUDE_TIMEOUT", str(int(value)))
        await _push_message("system", f"⏱ AI timeout set to {int(value)}s", source="telegram")
        await update.message.reply_text(f"⏱ Timeout updated to {int(value)}s (saved to .env)")
    except ValueError:
        await update.message.reply_text("❌ Invalid value. Use seconds, e.g. /timeout 1800")


@authorized_only
async def tg_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/history [n] — show last n user+assistant messages from the log (default 5, max 20)."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    try:
        n = max(1, min(20, int(arg))) if arg else 5
    except ValueError:
        n = 5

    # Walk back through daily log files (today first, then yesterday, etc.) until we have n msgs
    messages: list[dict] = []
    for delta in range(7):
        d = (datetime.now() - timedelta(days=delta)).strftime("%Y-%m-%d")
        log_file = CHAT_LOG_DIR / f"{d}.jsonl"
        if not log_file.exists():
            continue
        day_msgs = []
        for line in log_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
                if m.get("role") in ("user", "assistant"):
                    day_msgs.append(m)
            except Exception:
                pass
        messages = day_msgs + messages          # prepend so oldest first
        if len(messages) >= n:
            break

    messages = messages[-n:]
    if not messages:
        await update.message.reply_text("No history found.")
        return

    lines_out = []
    for m in messages:
        role = "You" if m["role"] == "user" else (m.get("ai") or "AI").title()
        ts = m.get("timestamp", "")[:16].replace("T", " ")
        preview = m.get("content", "")[:200]
        if len(m.get("content", "")) > 200:
            preview += "…"
        lines_out.append(f"[{ts}] {role}:\n{preview}")

    await _tg_send_chunks(update, "\n\n".join(lines_out))


# ---------------------------------------------------------------------------
# Telegram folder browser (inline keyboard)
# ---------------------------------------------------------------------------

async def _show_browse(target, user_id: int, path: str, edit: bool = False, page: int = 0):
    """Render a paginated directory listing as a Telegram inline keyboard.
    target = Message (for new message) or CallbackQuery (for edit)."""
    try:
        p = pathlib.Path(path).resolve()
        all_dirs = sorted(
            [d.name for d in p.iterdir() if d.is_dir()],
            key=lambda x: x.lower(),
        )
    except (PermissionError, OSError):
        all_dirs = []

    _tg_browse_state[user_id] = {"path": str(p), "dirs": all_dirs, "page": page}

    total = len(all_dirs)
    start = page * _BROWSE_PAGE_SIZE
    end = min(start + _BROWSE_PAGE_SIZE, total)
    page_dirs = all_dirs[start:end]
    total_pages = max(1, (total + _BROWSE_PAGE_SIZE - 1) // _BROWSE_PAGE_SIZE)

    keyboard: list[list[InlineKeyboardButton]] = []
    if str(p) != str(p.parent):
        keyboard.append([InlineKeyboardButton("⬆ Parent directory", callback_data="browse_up")])
    for i, d in enumerate(page_dirs):
        keyboard.append([InlineKeyboardButton(f"📁 {d}", callback_data=f"browse_d:{start + i}")])
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀ Prev", callback_data=f"browse_p:{page - 1}"))
    if end < total:
        nav_row.append(InlineKeyboardButton("▶ Next", callback_data=f"browse_p:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([
        InlineKeyboardButton("✅ Set as working dir", callback_data="browse_select"),
        InlineKeyboardButton("❌ Cancel", callback_data="browse_cancel"),
    ])

    text = f"📂 `{str(p)}`\n_{total} subfolder(s)_"
    if total_pages > 1:
        text += f" — page {page + 1}/{total_pages}"
    markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await target.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await target.reply_text(text, reply_markup=markup, parse_mode="Markdown")


@authorized_only
async def tg_browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/browse [path] — interactively navigate folders and set working directory."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    start = arg if arg else _session_cwd
    user_id = update.effective_user.id
    await _show_browse(update.message, user_id, start, edit=False, page=0)


async def browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline keyboard button presses from /browse."""
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.")
        return
    await query.answer()

    data = query.data
    state = _tg_browse_state.get(user_id, {"path": _session_cwd, "dirs": [], "page": 0})
    current_path = state["path"]
    dirs = state["dirs"]

    if data == "browse_cancel":
        _tg_browse_state.pop(user_id, None)
        await query.edit_message_text(
            "Browse cancelled.",
            reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
        )

    elif data == "browse_select":
        _tg_browse_state.pop(user_id, None)
        ok = await _change_cwd(current_path, source="telegram")
        if ok:
            await query.edit_message_text(
                f"✅ Working directory set to:\n`{current_path}`\n\nWhat would you like to do next?",
                parse_mode="Markdown",
                reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ Could not set directory:\n{current_path}",
                reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
            )

    elif data == "browse_up":
        p = pathlib.Path(current_path)
        parent = str(p.parent) if str(p) != str(p.parent) else current_path
        await _show_browse(query, user_id, parent, edit=True, page=0)

    elif data.startswith("browse_d:"):
        try:
            idx = int(data.split(":")[1])
        except (ValueError, IndexError):
            return
        if 0 <= idx < len(dirs):
            new_path = str(pathlib.Path(current_path) / dirs[idx])
            await _show_browse(query, user_id, new_path, edit=True, page=0)

    elif data.startswith("browse_p:"):
        try:
            pg = int(data.split(":")[1])
        except (ValueError, IndexError):
            return
        await _show_browse(query, user_id, current_path, edit=True, page=pg)


async def _perform_resume(message, date_str: str = "") -> None:
    """Core resume logic — usable from both /resume command and inline button.

    Loads the session log for `date_str` (or the most recent log if blank),
    restores the working directory and AI model automatically, injects the
    conversation context, and replies to `message` with a summary + buttons.
    """
    global _pending_tg_context, _active_ai, _claude_messages

    # Resolve which log file to load
    if date_str:
        log_file = CHAT_LOG_DIR / f"{date_str}.jsonl"
        if not log_file.exists():
            await message.reply_text(f"❌ No history found for {date_str}.")
            return
    else:
        if not CHAT_LOG_DIR.exists():
            await message.reply_text("No chat history saved yet.")
            return
        logs = sorted(CHAT_LOG_DIR.glob("*.jsonl"), reverse=True)
        if not logs:
            await message.reply_text("No chat history saved yet.")
            return
        log_file = logs[0]
        date_str = log_file.stem

    # Read the log — collect messages, last CWD, last AI
    messages: list[dict] = []
    last_cwd: Optional[str] = None
    last_ai:  Optional[str] = None
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
            if m.get("type") == "cwd":
                last_cwd = m["path"]
            elif m.get("type") == "ai":
                last_ai = m.get("model")      # keep the last one seen
            elif m.get("role") in ("user", "assistant"):
                messages.append(m)
        except Exception:
            pass

    if not messages:
        await message.reply_text(f"No conversation messages found in session {date_str}.")
        return

    # Build context string from last 10 exchanges
    turns = messages[-10:]
    lines_ctx = []
    for m in turns:
        role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
        body = (m.get("content") or "")[:300]
        if len(m.get("content", "")) > 300:
            body += "…"
        lines_ctx.append(f"{role}: {body}")

    label = _load_chat_names().get(date_str) or date_str
    _pending_tg_context = (
        f"[Previous conversation — {label}]\n"
        + "\n".join(lines_ctx)
        + "\n[End context]\n\n"
    )

    # ── Auto-restore working directory ────────────────────────────────────────
    # Fallback: if this session log pre-dates per-session CWD records, read
    # from last_state.json (written on every state change going forward).
    if not last_cwd:
        try:
            state_file = CHAT_LOG_DIR / "last_state.json"
            if state_file.exists():
                st = json.loads(state_file.read_text(encoding="utf-8"))
                last_cwd = st.get("cwd") or None
                if not last_ai:
                    last_ai = st.get("ai") or None
        except Exception:
            pass

    cwd_note = ""
    if last_cwd:
        cwd_ok = await _change_cwd(last_cwd, source="telegram")
        cwd_note = (
            f"\n📁 Directory restored: `{last_cwd}`"
            if cwd_ok
            else f"\n⚠️ Could not restore directory: `{last_cwd}`"
        )

    # ── Auto-restore AI model ─────────────────────────────────────────────────
    ai_note = ""
    valid_ai = last_ai and (last_ai == "claude" or last_ai in _integrations)
    if valid_ai:
        _active_ai = last_ai
        if last_ai == "claude":
            _claude_messages = []
        await _push_state()
        if last_ai == "claude":
            ai_label = "🤖 Claude Code"
        elif last_ai in _integrations:
            info = _integrations[last_ai]
            ai_label = f"{info['emoji']} {info['name']}"
        else:
            ai_label = last_ai.title()
        ai_note = f"\n{ai_label} re-activated — just type to continue."
    else:
        ai_note = "\nPick an AI below to continue:"

    await message.reply_text(
        f"✅ *Resumed: {label}* ({len(turns)} exchanges loaded){cwd_note}{ai_note}",
        parse_mode="Markdown",
        reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
    )


@authorized_only
async def tg_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resume [date] — restore a past session's directory, AI model, and context."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    await _perform_resume(update.message, date_str=arg)


@authorized_only
async def tg_clear_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Discard any pending resume context without sending it."""
    global _pending_tg_context
    if _pending_tg_context:
        _pending_tg_context = None
        await update.message.reply_text("✅ Pending context cleared.")
    else:
        await update.message.reply_text("No pending context to clear.")


@authorized_only
async def tg_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward plain text — with natural language shortcut detection."""
    global _pending_tg_context, _active_ai, _claude_messages
    text = (update.message.text or "").strip()
    low = text.lower()

    # ── Natural language shortcuts (always checked, regardless of AI state) ──
    # These let users say things like "stop", "history", "start claude"
    # without memorising any slash commands.

    if low in ("menu", "help", "options", "?"):
        await tg_menu.__wrapped__(update, context)
        return

    if low in ("stop", "quit", "kill", "exit session"):
        await tg_stop.__wrapped__(update, context)
        return

    if low in ("interrupt", "cancel", "ctrl+c", "ctrl c"):
        await tg_interrupt.__wrapped__(update, context)
        return

    if low in ("history", "show history", "past sessions"):
        await tg_history.__wrapped__(update, context)
        return

    if low in ("resume", "continue", "load context"):
        await _perform_resume(update.message, date_str="")
        return

    if low in ("status", "session status"):
        await tg_status.__wrapped__(update, context)
        return

    if low in ("folder", "cwd", "directory", "show folder"):
        await tg_cwd.__wrapped__(update, context)
        return

    if any(low.startswith(p) for p in ("start claude", "use claude", "switch to claude", "claude code")):
        await tg_claude.__wrapped__(update, context)
        return

    # Dynamic NL shortcuts for all loaded integrations
    for _ikey, _iinfo in _integrations.items():
        _n = _ikey.lower()
        if any(low.startswith(p) for p in (f"start {_n}", f"use {_n}", f"switch to {_n}")):
            _active_ai = _ikey
            await _push_state()
            await _push_message("system", f"{_iinfo['name']} active (via Telegram).", source="telegram")
            await update.message.reply_text(
                f"{_iinfo['emoji']} *{_iinfo['name']}* is active.\nJust type your task.",
                parse_mode="Markdown",
                reply_markup=_running_keyboard(),
            )
            return

    if low in ("shell", "shell mode", "stop ai", "no ai"):
        await tg_stop_ai.__wrapped__(update, context)
        return

    # ── No AI selected → show action buttons for ANY message ─────────────────
    # Once the user has picked an AI (or shell mode), every message goes straight
    # to that AI. Before any selection, always guide them with buttons.
    if not _active_ai:
        status = "🟢 Running" if _session.is_alive() else "⚪ No session"
        await update.message.reply_text(
            f"👋 *Claude Remote* — Ready!\n"
            f"Session: {status}   ·   AI: none selected\n"
            f"📁 `{_session_cwd}`\n\n"
            f"Pick an AI or action to get started:",
            parse_mode="Markdown",
            reply_markup=_ai_select_keyboard(),
        )
        return

    # ── AI is active → forward every message straight to it ──────────────────
    if _pending_tg_context:
        text = _pending_tg_context + text
        _pending_tg_context = None
        await update.message.reply_text("📎 Context injected. Thinking…")
    else:
        await update.message.reply_text("Thinking…")
    response = await _process_message(text, source="telegram")
    await _tg_send_chunks(update, response, reply_markup=_running_keyboard())


# ---------------------------------------------------------------------------
# Inline action button callback handler
# ---------------------------------------------------------------------------

async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all action:* inline keyboard button presses."""
    global _active_ai, _claude_messages
    query = update.callback_query
    user_id = query.from_user.id
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.")
        return
    await query.answer()

    action = query.data.split(":", 1)[1] if ":" in query.data else query.data

    if action == "claude":
        _active_ai = "claude"
        _claude_messages = []
        await _push_state()
        await _push_message("system", "Claude Code active (via Telegram).", source="telegram")
        await query.edit_message_text(
            "🤖 *Claude Code* is active.\nJust type your task.",
            parse_mode="Markdown",
            reply_markup=_running_keyboard(),
        )

    elif action in _integrations:
        # Generic handler for any loaded integration plugin
        info = _integrations[action]
        _active_ai = action
        await _push_state()
        await _push_message("system", f"{info['name']} active (via Telegram).", source="telegram")
        await query.edit_message_text(
            f"{info['emoji']} *{info['name']}* is active.\nJust type your task.",
            parse_mode="Markdown",
            reply_markup=_running_keyboard(),
        )

    elif action == "stop_ai":
        _active_ai = None
        await _push_state()
        await _push_message("system", "AI mode off (via Telegram).", source="telegram")
        await query.edit_message_text(
            "🐚 Shell mode — plain text goes straight to the terminal.\nPick an AI to start again:",
            reply_markup=_ai_select_keyboard(),
        )

    elif action == "stop":
        _session.stop()
        await _push_state()
        await _push_message("system", "Session stopped (via Telegram).", source="telegram")
        await query.edit_message_text(
            "🛑 Session stopped.\nReady when you are:",
            reply_markup=_ai_select_keyboard(),
        )

    elif action == "interrupt":
        try:
            _session.send_interrupt()
            await _push_message("system", "Ctrl+C sent (via Telegram).", source="telegram")
            await query.edit_message_text(
                "⏸ Interrupted.",
                reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
            )
        except RuntimeError as e:
            await query.edit_message_text(str(e))

    elif action == "switch":
        await query.edit_message_text(
            "Switch AI — pick one:",
            reply_markup=_ai_select_keyboard(),
        )

    elif action == "history":
        # Show last 5 messages inline
        messages: list[dict] = []
        for delta in range(7):
            d = (datetime.now() - timedelta(days=delta)).strftime("%Y-%m-%d")
            log_file = CHAT_LOG_DIR / f"{d}.jsonl"
            if not log_file.exists():
                continue
            day_msgs = []
            for line in log_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                    if m.get("role") in ("user", "assistant"):
                        day_msgs.append(m)
                except Exception:
                    pass
            messages = day_msgs + messages
            if len(messages) >= 5:
                break
        messages = messages[-5:]
        if not messages:
            await query.answer("No history found.", show_alert=True)
            return
        lines_out = []
        for m in messages:
            role = "You" if m["role"] == "user" else (m.get("ai") or "AI").title()
            ts = m.get("timestamp", "")[:16].replace("T", " ")
            preview = m.get("content", "")[:120]
            if len(m.get("content", "")) > 120:
                preview += "…"
            lines_out.append(f"[{ts}] {role}:\n{preview}")
        history_text = "\n\n".join(lines_out)
        # Can't edit with too-long text — send new message
        if query.message:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=history_text[:3800],
                reply_markup=_running_keyboard() if _active_ai else _ai_select_keyboard(),
            )

    elif action == "browse":
        # Telegram always uses the inline folder browser (paginated inline keyboard).
        # The Windows native picker is only used from the web UI.
        if query.message:
            user_id = query.from_user.id
            await _show_browse(query.message, user_id, _session_cwd, edit=False, page=0)

    elif action == "resume":
        # Resume the most recent session directly from the inline button
        if query.message:
            await query.edit_message_text("⏳ Loading last session…")
            await _perform_resume(query.message, date_str="")


# ---------------------------------------------------------------------------
# Embedded HTML frontend
# ---------------------------------------------------------------------------

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Remote</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0d0d;--surface:#141414;--surface2:#1c1c1c;--border:#242424;
  --text:#e2e2e2;--muted:#555;--dim:#888;
  --claude:#f59e0b;--gemini:#3b82f6;--codex:#22c55e;--shell:#6b7280;
  --user-bg:#1a2e4a;--user-text:#b8d0ee;
}
html,body{height:100%;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.5}
#app{height:100vh;display:flex;flex-direction:column;max-width:820px;margin:0 auto;
  border-left:1px solid var(--border);border-right:1px solid var(--border)}

/* ── Header ── */
header{
  padding:13px 20px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  background:var(--surface);flex-shrink:0}
.logo{font-size:15px;font-weight:600;letter-spacing:-.3px;color:var(--text)}
.logo em{color:var(--claude);font-style:normal}
.header-right{display:flex;align-items:center;gap:14px}
.icon-btn{
  background:none;border:none;color:var(--dim);cursor:pointer;
  padding:5px;border-radius:6px;display:flex;align-items:center;
  transition:color .15s;line-height:1}
.icon-btn:hover{color:var(--text)}
#conn{
  width:6px;height:6px;border-radius:50%;background:#ef4444;
  flex-shrink:0;transition:background .3s}
#conn.ok{background:var(--codex)}

/* ── Dir bar ── */
.dir-bar{
  padding:6px 20px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:8px;background:var(--bg);
  flex-shrink:0;min-height:32px}
.dir-icon{color:var(--muted);flex-shrink:0;display:flex;align-items:center}
#cwd-display{
  flex:1;font-size:11px;color:var(--dim);
  font-family:'SF Mono','Fira Code','Consolas',monospace;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  cursor:pointer;padding:2px 4px;border-radius:4px;transition:color .15s}
#cwd-display:hover{color:var(--text)}
#cwd-input{
  flex:1;font-size:11px;color:var(--text);background:var(--surface2);
  border:1px solid var(--claude);border-radius:4px;padding:2px 7px;outline:none;
  font-family:'SF Mono','Fira Code','Consolas',monospace;display:none}
.dir-browse-btn{
  background:none;border:none;color:var(--muted);cursor:pointer;
  padding:3px;border-radius:4px;display:flex;align-items:center;
  transition:color .15s}
.dir-browse-btn:hover{color:var(--text)}

/* ── Messages ── */
#messages{
  flex:1;overflow-y:auto;padding:22px 20px 8px;
  display:flex;flex-direction:column;gap:16px;scroll-behavior:smooth}
#messages::-webkit-scrollbar{width:4px}
#messages::-webkit-scrollbar-track{background:transparent}
#messages::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

.grp{display:flex;flex-direction:column;gap:4px;max-width:80%}
.grp.user{align-self:flex-end;align-items:flex-end}
.grp.assistant{align-self:flex-start;align-items:flex-start}
.grp.system{align-self:center;align-items:center;max-width:95%}

.meta{font-size:11px;color:var(--muted);padding:0 3px}
.meta .who{font-weight:500}
.who.claude{color:var(--claude)}.who.gemini{color:var(--gemini)}
.who.codex{color:var(--codex)}.who.shell{color:var(--shell)}
.via{color:#333}

.bubble{padding:10px 14px;border-radius:12px;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.user .bubble{background:var(--user-bg);color:var(--user-text);border-bottom-right-radius:3px}
.assistant .bubble{
  background:var(--surface2);color:var(--text);border-bottom-left-radius:3px;
  font-family:'SF Mono','Fira Code','Consolas',monospace;font-size:12.5px}
.system .bubble{
  background:transparent;color:var(--muted);font-size:11.5px;text-align:center;
  border:1px solid var(--border);border-radius:20px;padding:4px 14px}

/* ── Thinking ── */
#thinking{
  display:none;align-items:center;gap:8px;color:var(--muted);
  font-size:12px;padding:6px 4px;flex-shrink:0;margin:0 20px}
#thinking.on{display:flex}
.dots{display:flex;gap:4px}
.dots span{width:5px;height:5px;border-radius:50%;background:var(--muted);
  animation:blink 1.2s ease-in-out infinite}
.dots span:nth-child(2){animation-delay:.2s}
.dots span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,100%{opacity:.25;transform:scale(.8)}50%{opacity:1;transform:scale(1)}}

/* ── Input bar ── */
.input-bar{
  padding:12px 16px;border-top:1px solid var(--border);
  display:flex;gap:8px;background:var(--surface);align-items:flex-end;
  flex-shrink:0;position:relative}

/* AI picker chip */
.ai-picker{
  display:flex;align-items:center;gap:6px;height:40px;
  padding:0 11px;border-radius:8px;
  border:1px solid var(--border);background:var(--surface2);
  cursor:pointer;flex-shrink:0;user-select:none;
  transition:border-color .15s,background .15s}
.ai-picker:hover{border-color:#3a3a3a}
.dot{width:7px;height:7px;border-radius:50%;background:var(--muted);transition:background .2s;flex-shrink:0}
.dot.claude{background:var(--claude)}.dot.gemini{background:var(--gemini)}
.dot.codex{background:var(--codex)}.dot.shell{background:var(--shell)}
#ai-label{font-size:12px;color:var(--dim);white-space:nowrap;transition:color .2s}
.chevron{color:var(--muted);flex-shrink:0;transition:transform .15s}
.ai-picker.menu-open .chevron{transform:rotate(180deg)}

.ai-picker.active-claude{border-color:rgba(245,158,11,.35);background:rgba(245,158,11,.05)}
.ai-picker.active-claude #ai-label{color:var(--claude)}
.ai-picker.active-gemini{border-color:rgba(59,130,246,.35);background:rgba(59,130,246,.05)}
.ai-picker.active-gemini #ai-label{color:var(--gemini)}
.ai-picker.active-codex{border-color:rgba(34,197,94,.35);background:rgba(34,197,94,.05)}
.ai-picker.active-codex #ai-label{color:var(--codex)}

/* AI dropdown */
.ai-menu{
  display:none;position:absolute;bottom:calc(100% + 8px);left:16px;
  background:var(--surface);border:1px solid var(--border);border-radius:10px;
  min-width:195px;z-index:50;overflow:hidden;
  box-shadow:0 8px 32px rgba(0,0,0,.5)}
.ai-menu.open{display:block}
.ai-menu-section{
  padding:8px 13px 3px;font-size:10px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--muted);font-weight:600}
.ai-menu-item{
  display:flex;align-items:center;gap:9px;width:100%;
  padding:8px 13px;background:none;border:none;color:var(--dim);
  font-size:13px;font-family:inherit;cursor:pointer;text-align:left;
  transition:background .1s,color .1s}
.ai-menu-item:hover{background:var(--surface2);color:var(--text)}
.menu-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.menu-dot.claude{background:var(--claude)}
.menu-dot.gemini{background:var(--gemini)}
.menu-dot.codex{background:var(--codex)}
.menu-dot.shell{background:var(--shell)}
.ai-menu-divider{height:1px;background:var(--border);margin:4px 0}

/* Textarea */
#inp{
  flex:1;background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;padding:9px 13px;color:var(--text);font-family:inherit;
  font-size:14px;resize:none;outline:none;min-height:40px;max-height:120px;
  line-height:1.5;transition:border-color .15s}
#inp:focus{border-color:#3a3a3a}
#inp::placeholder{color:var(--muted)}
#send{
  padding:0 17px;border-radius:8px;border:none;background:var(--claude);
  color:#000;font-weight:600;font-size:13px;cursor:pointer;
  font-family:inherit;transition:opacity .15s;flex-shrink:0;height:40px}
#send:hover{opacity:.85}
#send:disabled{opacity:.35;cursor:not-allowed}

/* ── History banner ── */
#hist-banner{
  display:none;padding:7px 20px;background:#1a1a0d;border-bottom:1px solid #3a3a10;
  color:#cca840;font-size:12px;align-items:center;gap:10px;flex-shrink:0}
#hist-banner.on{display:flex}
#hist-banner-date{flex:1;font-weight:500}
.hist-live-btn{
  padding:3px 10px;border-radius:5px;border:1px solid #cca840;
  background:transparent;color:#cca840;font-size:11px;cursor:pointer;
  font-family:inherit;transition:all .15s}
.hist-live-btn:hover{background:#cca840;color:#000}

/* ── History modal ── */
.modal-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);
  z-index:100;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal-box{
  background:var(--surface);border:1px solid var(--border);border-radius:12px;
  width:min(420px,92vw);max-height:70vh;display:flex;flex-direction:column;overflow:hidden}
.modal-header{
  padding:14px 18px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.modal-title{font-size:14px;font-weight:600}
.modal-close{
  background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;
  padding:0 4px;line-height:1;transition:color .15s}
.modal-close:hover{color:var(--text)}
.modal-body{overflow-y:auto;padding:10px 0;flex:1}
.sess-item{
  display:flex;align-items:center;padding:9px 18px;cursor:pointer;
  border-bottom:1px solid var(--border);gap:10px;transition:background .12s}
.sess-item:hover{background:var(--surface2)}
.sess-info{flex:1;min-width:0;overflow:hidden}
.sess-name{font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sess-subdate{font-size:11px;color:var(--muted)}
.sess-rename-input{
  font-size:13px;font-weight:500;background:var(--bg);border:1px solid var(--codex);
  border-radius:4px;padding:1px 6px;color:var(--text);font-family:inherit;
  width:100%;box-sizing:border-box;outline:none}
.sess-del{
  background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px;
  padding:2px 6px;border-radius:4px;transition:color .12s}
.sess-del:hover{color:#ef4444}
.modal-empty{padding:24px 18px;color:var(--muted);font-size:13px;text-align:center}
.sess-actions{
  display:none;padding:7px 18px 10px;background:var(--surface2);
  gap:8px;border-bottom:1px solid var(--border)}
.sess-actions.open{display:flex}
.sess-action-btn{
  padding:4px 12px;border-radius:5px;border:1px solid var(--border);
  background:transparent;color:var(--dim);font-size:12px;cursor:pointer;
  font-family:inherit;transition:all .15s}
.sess-action-btn:hover{color:var(--text);border-color:#3a3a3a}
.sess-action-btn.resume{border-color:var(--codex);color:var(--codex)}
.sess-action-btn.resume:hover{background:rgba(34,197,94,.08)}

/* ── Browse modal ── */
.browse-box{width:min(480px,94vw)}
.browse-crumb{
  padding:8px 18px;font-size:11px;color:var(--dim);
  font-family:'SF Mono','Fira Code','Consolas',monospace;
  border-bottom:1px solid var(--border);word-break:break-all;flex-shrink:0;
  background:var(--surface2)}
.browse-item{
  padding:8px 18px;cursor:pointer;font-size:13px;
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:8px;transition:background .12s}
.browse-item:hover{background:var(--surface2)}
.browse-item.up{color:var(--muted);font-style:italic}
.browse-footer{
  padding:10px 18px;border-top:1px solid var(--border);
  display:flex;justify-content:flex-end;gap:8px;flex-shrink:0;
  background:var(--surface)}
.browse-empty{padding:24px 18px;color:var(--muted);font-size:13px;text-align:center}
.browse-drives{
  padding:6px 18px 8px;border-bottom:1px solid var(--border);
  display:flex;flex-wrap:wrap;gap:6px;background:var(--surface2)}
.drive-chip{
  padding:3px 10px;border-radius:5px;border:1px solid var(--border);
  background:var(--bg);font-size:12px;cursor:pointer;
  font-family:'SF Mono','Fira Code','Consolas',monospace;
  color:var(--dim);transition:all .12s}
.drive-chip:hover{color:var(--text);border-color:#3a3a3a}
</style>
</head>
<body>
<div id="app">

<header>
  <div class="logo">◈ Claude <em>Remote</em></div>
  <div class="header-right">
    <button class="icon-btn" onclick="openHistory()" title="Chat history">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 3h18v18H3z" style="display:none"/>
        <rect x="3" y="3" width="18" height="3" rx="1"/>
        <rect x="3" y="8" width="18" height="2" rx="1" opacity=".6"/>
        <rect x="3" y="12" width="12" height="2" rx="1" opacity=".4"/>
      </svg>
    </button>
    <div id="conn" title="WebSocket status"></div>
  </div>
</header>

<div class="dir-bar">
  <span class="dir-icon">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
    </svg>
  </span>
  <span id="cwd-display" title="Click to change directory" onclick="startCwdEdit()">—</span>
  <input id="cwd-input" placeholder="Enter full path and press Enter…"
         onkeydown="cwdKey(event)" onblur="cancelCwdEdit()">
  <button class="dir-browse-btn" onclick="openBrowse()" title="Browse folders">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
  </button>
</div>

<div id="hist-banner">
  <span id="hist-banner-date"></span>
  <button class="hist-live-btn" onclick="returnToLive()">↩ Back to Live</button>
</div>

<div id="messages">
  <div class="grp system">
    <div class="bubble">Connecting to server…</div>
  </div>
</div>
<div id="thinking">
  <div class="dots"><span></span><span></span><span></span></div>
  <span id="thlabel">Thinking…</span>
</div>

<div class="input-bar">
  <!-- AI picker chip -->
  <div class="ai-picker" id="ai-picker" onclick="toggleAiMenu(event)">
    <div class="dot" id="dot"></div>
    <span id="ai-label">Shell</span>
    <svg class="chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M6 9l6 6 6-6"/>
    </svg>
  </div>

  <!-- AI dropdown menu — static items; integrations injected dynamically by loadIntegrations() -->
  <div class="ai-menu" id="ai-menu">
    <div class="ai-menu-section">AI Mode</div>
    <button class="ai-menu-item" onclick="cmd('claude');closeAiMenu()">
      <span class="menu-dot claude"></span>Claude Code</button>
    <!-- integration buttons inserted here by loadIntegrations() -->
    <button class="ai-menu-item" id="shell-mode-btn" onclick="cmd('stop_ai');closeAiMenu()">
      <span class="menu-dot shell"></span>Shell mode</button>
    <div class="ai-menu-divider"></div>
    <div class="ai-menu-section">Session</div>
    <button class="ai-menu-item" onclick="cmd('launch');closeAiMenu()">⚡ Launch session</button>
    <button class="ai-menu-item" onclick="cmd('interrupt');closeAiMenu()">⏸ Interrupt</button>
    <button class="ai-menu-item" onclick="cmd('clear');closeAiMenu()">↺ Clear Claude history</button>
  </div>

  <textarea id="inp" placeholder="Type a message…  (Enter to send, Shift+Enter for newline)" rows="1"></textarea>
  <button id="send" onclick="send()">Send</button>
</div>

<!-- History modal -->
<div class="modal-overlay" id="hist-modal" onclick="closeHistory(event)">
  <div class="modal-box">
    <div class="modal-header">
      <span class="modal-title">Chat History</span>
      <button class="modal-close" onclick="closeHistory()">✕</button>
    </div>
    <div class="modal-body" id="hist-list"></div>
  </div>
</div>

<!-- Browse directory modal -->
<div class="modal-overlay" id="browse-modal" onclick="closeBrowse(event)">
  <div class="modal-box browse-box">
    <div class="modal-header">
      <span class="modal-title">Browse Directory</span>
      <button class="modal-close" onclick="closeBrowseModal()">✕</button>
    </div>
    <div id="browse-crumb" class="browse-crumb"></div>
    <div class="modal-body" id="browse-list"></div>
    <div class="browse-footer">
      <button class="sess-action-btn" onclick="closeBrowseModal()">Cancel</button>
      <button class="sess-action-btn resume" onclick="selectBrowsePath()">✓ Select This Folder</button>
    </div>
  </div>
</div>

</div>
<script>
const AI_LABEL = {claude:'Claude Code',shell:'Shell'};
let ws = null, activeAi = null, _viewingHistory = false, _liveHistory = [], _pendingContext = '';
let _sessNames = {};

// Load integrations from server and inject menu items + CSS vars dynamically
async function loadIntegrations(){
  try {
    const res = await fetch('/integrations');
    if(!res.ok) return;
    const integrations = await res.json();
    if(!integrations.length) return;
    const root = document.documentElement;
    let css = '';
    const shellBtn = document.getElementById('shell-mode-btn');
    for(const {key, name, emoji, color} of integrations){
      // Register CSS variable
      root.style.setProperty('--'+key, color);
      // Parse hex → r,g,b for rgba()
      const r = parseInt(color.slice(1,3),16);
      const g = parseInt(color.slice(3,5),16);
      const b = parseInt(color.slice(5,7),16);
      css += `.dot.${key}{background:var(--${key})}`;
      css += `.who.${key}{color:var(--${key})}`;
      css += `.ai-picker.active-${key}{border-color:rgba(${r},${g},${b},.35);background:rgba(${r},${g},${b},.05)}`;
      css += `.ai-picker.active-${key} #ai-label{color:var(--${key})}`;
      // Update label map
      AI_LABEL[key] = name;
      // Inject menu button before Shell mode
      const btn = document.createElement('button');
      btn.className = 'ai-menu-item';
      btn.innerHTML = `<span class="menu-dot ${key}"></span>${escHtml(name)}`;
      btn.onclick = () => { cmd(key); closeAiMenu(); };
      shellBtn.parentNode.insertBefore(btn, shellBtn);
    }
    const styleEl = document.createElement('style');
    styleEl.textContent = css;
    document.head.appendChild(styleEl);
  } catch(e){ console.warn('loadIntegrations failed', e); }
}
function escHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function connect(){
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${wsProto}://${location.host}/ws`);
  ws.onopen = () => { document.getElementById('conn').className = 'ok'; };
  ws.onclose = () => { document.getElementById('conn').className = ''; setTimeout(connect, 2500); };
  ws.onerror = () => {};
  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    if(d.type==='message'){ _liveHistory.push(d); if(!_viewingHistory) renderMsg(d); }
    else if(d.type==='state') applyState(d);
    else if(d.type==='thinking') setThinking(d.active, d.ai);
    else if(d.type==='cwd') applyCwd(d.path);
  };
}

function applyState(s){
  activeAi = s.active_ai;
  const key = activeAi || 'shell';
  const picker = document.getElementById('ai-picker');
  document.getElementById('dot').className = 'dot ' + key;
  document.getElementById('ai-label').textContent = AI_LABEL[key] || key;
  picker.className = 'ai-picker' + (activeAi ? ' active-' + activeAi : '');
  if(s.cwd) applyCwd(s.cwd);
}

function applyCwd(path){
  const el = document.getElementById('cwd-display');
  el.textContent = path;
  el.title = 'Working directory: ' + path + '\nClick to change';
}

// ── AI Menu ──────────────────────────────────────────────────────────────────
function toggleAiMenu(e){
  e.stopPropagation();
  const menu = document.getElementById('ai-menu');
  const picker = document.getElementById('ai-picker');
  const isOpen = menu.classList.contains('open');
  if(isOpen){ closeAiMenu(); } else {
    menu.classList.add('open');
    picker.classList.add('menu-open');
  }
}
function closeAiMenu(){
  document.getElementById('ai-menu').classList.remove('open');
  document.getElementById('ai-picker').classList.remove('menu-open');
}
document.addEventListener('click', e => {
  if(!document.getElementById('ai-picker').contains(e.target) &&
     !document.getElementById('ai-menu').contains(e.target)){
    closeAiMenu();
  }
});

// ── Dir bar ──────────────────────────────────────────────────────────────────
function startCwdEdit(){
  const display = document.getElementById('cwd-display');
  const input   = document.getElementById('cwd-input');
  input.value = display.textContent === '—' ? '' : display.textContent;
  display.style.display = 'none';
  input.style.display   = 'block';
  input.focus();
  input.select();
}
function cancelCwdEdit(){
  document.getElementById('cwd-display').style.display = '';
  document.getElementById('cwd-input').style.display   = 'none';
}
function applyCwdEdit(forcedPath){
  const path = forcedPath !== undefined ? forcedPath : document.getElementById('cwd-input').value.trim();
  cancelCwdEdit();
  if(!path || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({type:'command', command:'cwd', path:path}));
}
function cwdKey(e){
  if(e.key === 'Enter')  { e.preventDefault(); applyCwdEdit(); }
  if(e.key === 'Escape') { cancelCwdEdit(); }
}

// ── Browse directory modal ────────────────────────────────────────────────────
let _browsePath = '';
async function openBrowse(){
  // Try the native Windows folder-picker first (only works on the server machine)
  try {
    const res = await fetch('/browse/native');
    if(res.ok){
      const data = await res.json();
      if(data.path){
        // User picked a folder — apply it directly, no modal needed
        applyCwdEdit(data.path);
        return;
      }
    }
  } catch(e){ /* ignore — fall through to modal */ }

  // Fall back to the in-browser folder browser modal
  _browsePath = document.getElementById('cwd-display').textContent;
  if(_browsePath === '—') _browsePath = '';
  await loadBrowse(_browsePath);
  document.getElementById('browse-modal').classList.add('open');
}
async function loadBrowse(path){
  const res = await fetch('/browse?path=' + encodeURIComponent(path || ''));
  if(!res.ok) return;
  const data = await res.json();
  _browsePath = data.path;
  document.getElementById('browse-crumb').textContent = data.path;
  let html = '';
  if(data.drives && data.drives.length){
    html += '<div class="browse-drives">' +
      data.drives.map(d => `<span class="drive-chip" onclick="loadBrowse('${esc(d)}')">${escHtml(d)}</span>`).join('') +
      '</div>';
  }
  if(data.parent)
    html += `<div class="browse-item up" onclick="loadBrowse('${esc(data.parent)}')">⬆ ..</div>`;
  if(!data.dirs.length)
    html += '<div class="browse-empty">No subfolders in this directory</div>';
  const sep = data.path.includes('\\') ? '\\' : '/';
  data.dirs.forEach(d => {
    const full = data.path.replace(/[/\\]+$/, '') + sep + d;
    html += `<div class="browse-item" onclick="loadBrowse('${esc(full)}')">📁 ${escHtml(d)}</div>`;
  });
  document.getElementById('browse-list').innerHTML = html;
}
function selectBrowsePath(){ if(_browsePath) applyCwdEdit(_browsePath); closeBrowseModal(); }
function closeBrowseModal(){ document.getElementById('browse-modal').classList.remove('open'); }
function closeBrowse(e){ if(e.target.id === 'browse-modal') closeBrowseModal(); }
function esc(s){ return s.replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }

// ── Thinking ─────────────────────────────────────────────────────────────────
function setThinking(on, ai){
  const el = document.getElementById('thinking');
  el.className = on ? 'on' : '';
  if(on){
    const k = ai || activeAi || '';
    document.getElementById('thlabel').textContent = (AI_LABEL[k]||'AI') + '…';
    scroll();
  }
}

// ── Messages ─────────────────────────────────────────────────────────────────
function renderMsg(m){
  const wrap = document.getElementById('messages');
  const placeholder = wrap.querySelector('.grp.system .bubble');
  if(placeholder && placeholder.textContent === 'Connecting to server…'){
    placeholder.closest('.grp').remove();
  }
  const grp = document.createElement('div');
  grp.className = 'grp ' + m.role;
  if(m.role !== 'system'){
    const meta = document.createElement('div');
    meta.className = 'meta';
    if(m.role==='user'){
      const via = m.source==='telegram' ? '<span class="via">via Telegram · </span>' : '';
      meta.innerHTML = via + 'You';
    } else {
      const k = m.ai || '';
      meta.innerHTML = `<span class="who ${k}">${AI_LABEL[k]||'AI'}</span>`;
    }
    grp.appendChild(meta);
  }
  const bub = document.createElement('div');
  bub.className = 'bubble';
  bub.textContent = m.content;
  grp.appendChild(bub);
  wrap.appendChild(grp);
  scroll();
}
function scroll(){ const m = document.getElementById('messages'); m.scrollTop = m.scrollHeight; }

// ── Send ─────────────────────────────────────────────────────────────────────
function send(){
  const inp = document.getElementById('inp');
  const txt = inp.value.trim();
  if(!txt || !ws || ws.readyState !== 1) return;
  let content = txt;
  if(_pendingContext){
    content = _pendingContext + txt;
    _pendingContext = '';
    document.getElementById('hist-banner').classList.remove('on');
  }
  ws.send(JSON.stringify({type:'message', content:content}));
  inp.value = '';
  inp.style.height = 'auto';
}
function cmd(c){
  if(!ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({type:'command', command:c}));
}
const inp = document.getElementById('inp');
inp.addEventListener('input', () => {
  inp.style.height = 'auto';
  inp.style.height = Math.min(inp.scrollHeight, 120) + 'px';
});
inp.addEventListener('keydown', e => {
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
});

// ── History modal ─────────────────────────────────────────────────────────────
async function openHistory(){
  const res = await fetch('/history');
  const sessions = await res.json();
  const list = document.getElementById('hist-list');
  if(!sessions.length){
    list.innerHTML = '<div class="modal-empty">No saved history yet.<br>Messages are saved automatically as you chat.</div>';
  } else {
    _sessNames = {};
    sessions.forEach(s => { if(s.name) _sessNames[s.date] = s.name; });
    list.innerHTML = sessions.map(s =>
      `<div>
        <div class="sess-item" onclick="toggleSess(event,'${s.date}')">
          <div class="sess-info">
            <div class="sess-name" id="sess-name-${s.date}">${s.name ? escHtml(s.name) : s.date}</div>
            <div class="sess-subdate">${s.name ? s.date+' &middot; ' : ''}${s.count} msg</div>
          </div>
          <button class="sess-del" title="Delete" onclick="delSession(event,'${s.date}')">🗑</button>
        </div>
        <div class="sess-actions" id="sess-act-${s.date}">
          <button class="sess-action-btn" onclick="loadSession('${s.date}')">&#128065; View</button>
          <button class="sess-action-btn resume" onclick="resumeSession('${s.date}')">&#9654; Resume with context</button>
          <button class="sess-action-btn" onclick="startRename(event,'${s.date}')">&#9998; Rename</button>
        </div>
      </div>`
    ).join('');
  }
  document.getElementById('hist-modal').classList.add('open');
}
function closeHistory(e){
  if(e && e.target !== document.getElementById('hist-modal')) return;
  document.getElementById('hist-modal').classList.remove('open');
}
async function loadSession(date){
  document.getElementById('hist-modal').classList.remove('open');
  const res = await fetch('/history/'+date);
  const data = await res.json();
  const msgs = data.messages || data;
  _viewingHistory = true;
  const name = _sessNames[date] || date;
  document.getElementById('hist-banner-date').textContent = '📖 Viewing: ' + name;
  document.getElementById('hist-banner').classList.add('on');
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  msgs.forEach(renderMsg);
  scroll();
}
function returnToLive(){
  _viewingHistory = false;
  document.getElementById('hist-banner').classList.remove('on');
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  _liveHistory.forEach(renderMsg);
  scroll();
}
async function resumeSession(date){
  document.getElementById('hist-modal').classList.remove('open');
  const res = await fetch('/history/'+date+'/resume');
  const data = await res.json();
  _pendingContext = data.context || '';
  const name = _sessNames[date] || date;
  document.getElementById('hist-banner-date').textContent = '▶ Context loaded from: ' + name + ' — send your message to continue';
  document.getElementById('hist-banner').classList.add('on');
  document.getElementById('inp').focus();
}
function toggleSess(e, date){
  if(e.target.classList.contains('sess-del') || e.target.classList.contains('sess-rename-input')) return;
  const act = document.getElementById('sess-act-'+date);
  const isOpen = act.classList.contains('open');
  document.querySelectorAll('.sess-actions.open').forEach(el => el.classList.remove('open'));
  if(!isOpen) act.classList.add('open');
}
async function delSession(e, date){
  e.stopPropagation();
  if(!confirm('Delete session ' + (date) + '?')) return;
  await fetch('/history/'+date, {method:'DELETE'});
  openHistory();
}
function startRename(e, date){
  e.stopPropagation();
  const nameEl = document.getElementById('sess-name-'+date);
  const cur = nameEl.textContent;
  nameEl.innerHTML = `<input class="sess-rename-input" value="${escHtml(cur)}"
    onkeydown="finishRename(event,'${date}')" onblur="finishRename(event,'${date}',true)">`;
  const inp = nameEl.querySelector('input');
  inp.focus(); inp.select();
}
async function finishRename(e, date, blur){
  if(!blur && e.key !== 'Enter' && e.key !== 'Escape') return;
  const inp = document.getElementById('sess-name-'+date).querySelector('input');
  if(!inp) return;
  const newName = (e.key === 'Escape') ? '' : inp.value.trim();
  if(newName && newName !== date){
    await fetch('/history/'+date+'/rename', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:newName})});
    _sessNames[date] = newName;
  }
  openHistory();
}

connect();
loadIntegrations();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point: run FastAPI + Telegram in the same asyncio event loop
# ---------------------------------------------------------------------------

async def _main():
    global _telegram_app

    # Load AI integration plugins from integrations/ folder
    _load_integrations()

    # Log the initial working directory so resume can restore it
    _save_cwd_to_log(_session_cwd)

    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled.")

    # --- Build Telegram application ---
    if BOT_TOKEN:
        _telegram_app = Application.builder().token(BOT_TOKEN).build()
        # Primary commands users need to know
        _telegram_app.add_handler(CommandHandler("start",   tg_start))
        _telegram_app.add_handler(CommandHandler("menu",    tg_menu))
        # AI selection (kept for power users / discoverability via BotFather menu)
        _telegram_app.add_handler(CommandHandler("claude",  tg_claude))
        _telegram_app.add_handler(CommandHandler("gemini",  tg_gemini))
        _telegram_app.add_handler(CommandHandler("codex",   tg_codex))
        # Session controls
        _telegram_app.add_handler(CommandHandler("launch",    tg_launch))
        _telegram_app.add_handler(CommandHandler("stop",      tg_stop))
        _telegram_app.add_handler(CommandHandler("interrupt", tg_interrupt))
        _telegram_app.add_handler(CommandHandler("stop_ai",   tg_stop_ai))
        _telegram_app.add_handler(CommandHandler("status",    tg_status))
        # Utility
        _telegram_app.add_handler(CommandHandler("cwd",          tg_cwd))
        _telegram_app.add_handler(CommandHandler("browse",        tg_browse))
        _telegram_app.add_handler(CommandHandler("cmd",           tg_cmd))
        _telegram_app.add_handler(CommandHandler("timeout",       tg_timeout))
        _telegram_app.add_handler(CommandHandler("clear",         tg_clear))
        _telegram_app.add_handler(CommandHandler("history",       tg_history))
        _telegram_app.add_handler(CommandHandler("resume",        tg_resume))
        _telegram_app.add_handler(CommandHandler("clear_context", tg_clear_context))
        # Inline keyboard callbacks — action buttons come BEFORE browse_callback
        _telegram_app.add_handler(CallbackQueryHandler(action_callback, pattern=r"^action:"))
        _telegram_app.add_handler(CallbackQueryHandler(browse_callback))
        # Plain text + natural language
        _telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tg_text))
        if not ALLOWED_USER_IDS:
            logger.warning("ALLOWED_USER_IDS is empty — Telegram bot is open to anyone!")

    # --- Build uvicorn server ---
    config = uvicorn.Config(
        app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="warning",  # keep console clean
    )
    server = uvicorn.Server(config)

    url = f"http://{'localhost' if WEB_HOST in ('0.0.0.0', '127.0.0.1') else WEB_HOST}:{WEB_PORT}"
    logger.info("Starting web UI at %s", url)

    # Open browser after a short delay so the server is ready
    async def _open_browser():
        await asyncio.sleep(1.2)
        webbrowser.open(url)

    asyncio.create_task(_open_browser())

    if _telegram_app:
        async with _telegram_app:
            await _telegram_app.start()
            await _telegram_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram bot started. Polling for updates…")
            await server.serve()           # blocks until Ctrl+C
            await _telegram_app.updater.stop()
            await _telegram_app.stop()
    else:
        # No Telegram — just run the web server
        await server.serve()


def main():
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")


if __name__ == "__main__":
    main()
