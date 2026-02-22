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
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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
_session = TerminalSession()
_claude_messages: list[str] = []
# For private bot DMs, chat_id == user_id, so pre-init from ALLOWED_USER_IDS.
# This ensures web-initiated responses are forwarded to Telegram even before
# the user sends their first Telegram message.
_telegram_chat_id: Optional[int] = next(iter(ALLOWED_USER_IDS), None)
_chat_history: list[dict] = []           # in-memory log for new WS clients joining mid-session
_ws_clients: set[WebSocket] = set()
_telegram_app: Optional[Application] = None  # set in main(), used to send Telegram messages from web

_AI_CMD = {
    "codex":  lambda p: [f"codex{_CMD_EXT}", "exec", "--full-auto", p],
    "gemini": lambda p: [f"gemini{_CMD_EXT}", "-p", p, "--yolo"],
}

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

    if _active_ai in _AI_CMD:
        await _push_thinking(True, _active_ai)
        cmd    = _AI_CMD[_active_ai](text)
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


def _snapshot_dir(cwd: str) -> set[str]:
    """Return a flat set of absolute file paths currently in cwd."""
    try:
        return {str(p) for p in pathlib.Path(cwd).iterdir() if p.is_file()}
    except Exception:
        return set()


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

    local_url = f"http://localhost:{WEB_PORT}/files/{path.name}"
    caption   = f"📎 {path.name}\n🔗 {local_url}"

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
                    if line.strip()
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
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except Exception:
                pass
    return JSONResponse(messages)


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

    elif command == "gemini":
        _active_ai = "gemini"
        await _push_state()
        await _push_message("system", "Gemini active. Send a message to start.", source="web")

    elif command == "codex":
        _active_ai = "codex"
        await _push_state()
        await _push_message("system", "Codex active. Send a message to start.", source="web")

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


async def _tg_send_chunks(update: Update, text: str, max_len: int = 3800):
    if not text.strip():
        await update.message.reply_text("(no output)")
        return
    for i in range(0, len(text), max_len):
        await update.message.reply_text(text[i:i + max_len])


@authorized_only
async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Claude Remote — Web + Telegram\n\n"
        "Open http://localhost:{port} for the web UI.\n\n"
        "AI modes:\n"
        "  /claude   — Activate Claude Code\n"
        "  /gemini   — Activate Gemini\n"
        "  /codex    — Activate Codex\n"
        "  /stop_ai  — Return to shell mode\n"
        "  /clear    — Clear Claude history\n\n"
        "Shell:\n"
        "  /launch      — Start cmd.exe session\n"
        "  /cmd <x>     — Run a shell command\n"
        "  /interrupt   — Send Ctrl+C\n"
        "  /stop        — Kill session\n"
        "  /status      — Session info\n\n"
        "Directory:\n"
        "  /cwd         — Show working directory\n"
        "  /cwd <path>  — Change working directory\n\n"
        "Settings:\n"
        "  /timeout          — Show current AI timeout\n"
        "  /timeout <secs>   — Change timeout (e.g. /timeout 1800)\n\n"
        "History:\n"
        "  /history              — Last 5 messages\n"
        "  /history <n>          — Last n messages (max 20)\n"
        "  /resume               — Load most recent session context\n"
        "  /resume <date>        — Load context from date (e.g. /resume 2026-02-22)\n"
        "  /clear_context        — Discard loaded context\n\n"
        "Plain text → active AI or shell."
    ).format(port=WEB_PORT)
    await update.message.reply_text(help_text)


@authorized_only
async def tg_launch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Starting cmd.exe...")
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
    await _tg_send_chunks(update, output or "cmd.exe started.")


@authorized_only
async def tg_claude(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai, _claude_messages
    _active_ai = "claude"
    _claude_messages = []
    await _push_state()
    await _push_message("system", "Claude Code active (via Telegram).", source="telegram")
    await update.message.reply_text(
        "Claude Code active.\nSend messages to talk to Claude.\n/stop_ai to exit."
    )


@authorized_only
async def tg_codex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai
    _active_ai = "codex"
    await _push_state()
    await _push_message("system", "Codex active (via Telegram).", source="telegram")
    await update.message.reply_text("Codex active. /stop_ai to exit.")


@authorized_only
async def tg_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai
    _active_ai = "gemini"
    await _push_state()
    await _push_message("system", "Gemini active (via Telegram).", source="telegram")
    await update.message.reply_text("Gemini active. /stop_ai to exit.")


@authorized_only
async def tg_stop_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_ai
    _active_ai = None
    await _push_state()
    await _push_message("system", "AI mode off (via Telegram).", source="telegram")
    await update.message.reply_text("AI mode off. Text now goes to shell.")


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
        await update.message.reply_text("Ctrl+C sent.")
    except RuntimeError as e:
        await update.message.reply_text(str(e))


@authorized_only
async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _session.stop()
    await _push_state()
    await _push_message("system", "Session stopped (via Telegram).", source="telegram")
    await update.message.reply_text("Session stopped.")


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


@authorized_only
async def tg_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resume [date] — load a past session's context so the next message continues from it."""
    global _pending_tg_context
    arg = (update.message.text or "").partition(" ")[2].strip()

    # Determine which date to load
    if arg:
        date_str = arg
        log_file = CHAT_LOG_DIR / f"{date_str}.jsonl"
        if not log_file.exists():
            await update.message.reply_text(f"❌ No history found for {date_str}.")
            return
    else:
        # Default: most recent available log file
        if not CHAT_LOG_DIR.exists():
            await update.message.reply_text("No history saved yet.")
            return
        logs = sorted(CHAT_LOG_DIR.glob("*.jsonl"), reverse=True)
        if not logs:
            await update.message.reply_text("No history saved yet.")
            return
        log_file = logs[0]
        date_str = log_file.stem

    # Load and build context string from last 10 user+assistant turns
    messages = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
            if m.get("role") in ("user", "assistant"):
                messages.append(m)
        except Exception:
            pass

    if not messages:
        await update.message.reply_text(f"No user/assistant messages found in {date_str}.")
        return

    turns = messages[-10:]
    lines_ctx = []
    for m in turns:
        role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
        body = (m.get("content") or "")[:300]
        if len(m.get("content", "")) > 300:
            body += "…"
        lines_ctx.append(f"{role}: {body}")

    label = _load_chat_names().get(date_str) or date_str
    _pending_tg_context = f"[Previous conversation — {label}]\n" + "\n".join(lines_ctx) + "\n[End context]\n\n"

    await update.message.reply_text(
        f"✅ Context from \"{label}\" loaded ({len(turns)} exchanges).\n"
        f"Send your next message to continue — the context will be injected automatically.\n"
        f"Send /clear_context to cancel."
    )


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
    """Forward plain text from Telegram through the shared processor."""
    global _pending_tg_context
    text = update.message.text or ""
    if _pending_tg_context:
        text = _pending_tg_context + text
        _pending_tg_context = None
        await update.message.reply_text("📎 Context injected. Thinking…")
    else:
        await update.message.reply_text("Thinking…")
    response = await _process_message(text, source="telegram")
    await _tg_send_chunks(update, response)


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
.ai-badge{
  display:flex;align-items:center;gap:7px;font-size:12px;color:var(--dim);
  padding:5px 11px;border-radius:20px;border:1px solid var(--border);
  background:var(--surface2);user-select:none}
.dot{width:7px;height:7px;border-radius:50%;background:var(--muted);transition:background .2s}
.dot.claude{background:var(--claude)}.dot.gemini{background:var(--gemini)}
.dot.codex{background:var(--codex)}.dot.shell{background:var(--shell)}

/* ── Mode bar ── */
.mode-bar{
  padding:9px 20px;border-bottom:1px solid var(--border);
  display:flex;gap:6px;align-items:center;background:var(--bg);flex-shrink:0;flex-wrap:wrap}
.mode-btn{
  padding:4px 12px;border-radius:6px;border:1px solid var(--border);
  background:transparent;color:var(--dim);font-size:12px;cursor:pointer;
  transition:all .15s;font-family:inherit;line-height:1.6}
.mode-btn:hover{border-color:#3a3a3a;color:var(--text)}
.active-claude{border-color:var(--claude)!important;color:var(--claude)!important;background:rgba(245,158,11,.07)!important}
.active-gemini{border-color:var(--gemini)!important;color:var(--gemini)!important;background:rgba(59,130,246,.07)!important}
.active-codex{border-color:var(--codex)!important;color:var(--codex)!important;background:rgba(34,197,94,.07)!important}
.active-shell{border-color:var(--shell)!important;color:var(--shell)!important;background:rgba(107,114,128,.07)!important}
.spacer{flex:1}
.act-btn{
  padding:4px 11px;border-radius:6px;border:1px solid var(--border);
  background:transparent;color:var(--dim);font-size:11px;cursor:pointer;
  font-family:inherit;line-height:1.6;transition:all .15s}
.act-btn:hover{color:var(--text);border-color:#3a3a3a}

/* ── Messages ── */
#messages{
  flex:1;overflow-y:auto;padding:20px 20px 8px;
  display:flex;flex-direction:column;gap:14px;scroll-behavior:smooth}
#messages::-webkit-scrollbar{width:4px}
#messages::-webkit-scrollbar-track{background:transparent}
#messages::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

.grp{display:flex;flex-direction:column;gap:3px;max-width:78%}
.grp.user{align-self:flex-end;align-items:flex-end}
.grp.assistant{align-self:flex-start;align-items:flex-start}
.grp.system{align-self:center;align-items:center;max-width:92%}

.meta{font-size:11px;color:var(--muted);padding:0 3px}
.meta .who{font-weight:500}
.who.claude{color:var(--claude)}.who.gemini{color:var(--gemini)}
.who.codex{color:var(--codex)}.who.shell{color:var(--shell)}
.via{color:#333}

.bubble{padding:9px 13px;border-radius:11px;line-height:1.65;white-space:pre-wrap;word-break:break-word}
.user .bubble{background:var(--user-bg);color:var(--user-text);border-bottom-right-radius:3px}
.assistant .bubble{
  background:var(--surface2);color:var(--text);border-bottom-left-radius:3px;
  font-family:'SF Mono','Fira Code','Consolas',monospace;font-size:12.5px}
.system .bubble{
  background:transparent;color:var(--muted);font-size:11.5px;text-align:center;
  border:1px solid var(--border);border-radius:20px;padding:3px 13px}

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
  padding:11px 20px;border-top:1px solid var(--border);
  display:flex;gap:9px;background:var(--surface);align-items:flex-end;flex-shrink:0}
#inp{
  flex:1;background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;padding:9px 13px;color:var(--text);font-family:inherit;
  font-size:14px;resize:none;outline:none;min-height:40px;max-height:120px;
  line-height:1.5;transition:border-color .15s}
#inp:focus{border-color:#3a3a3a}
#inp::placeholder{color:var(--muted)}
#send{
  padding:9px 17px;border-radius:8px;border:none;background:var(--claude);
  color:#000;font-weight:600;font-size:13px;cursor:pointer;
  font-family:inherit;transition:opacity .15s;flex-shrink:0}
#send:hover{opacity:.85}
#send:disabled{opacity:.35;cursor:not-allowed}

/* ── WS status dot ── */
#conn{
  width:6px;height:6px;border-radius:50%;background:#ef4444;
  flex-shrink:0;transition:background .3s;margin-bottom:2px}
#conn.ok{background:var(--codex)}

/* ── Directory bar ── */
.dir-bar{
  padding:6px 20px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:8px;background:var(--bg);
  flex-shrink:0;min-height:32px}
.dir-icon{font-size:12px;color:var(--muted);flex-shrink:0}
#cwd-display{
  flex:1;font-size:11.5px;color:var(--dim);
  font-family:'SF Mono','Fira Code','Consolas',monospace;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  cursor:pointer;padding:2px 4px;border-radius:4px;transition:color .15s}
#cwd-display:hover{color:var(--text)}
#cwd-input{
  flex:1;font-size:11.5px;color:var(--text);background:var(--surface2);
  border:1px solid var(--claude);border-radius:4px;padding:2px 7px;outline:none;
  font-family:'SF Mono','Fira Code','Consolas',monospace;display:none}
.dir-edit-btn{
  padding:2px 8px;border-radius:4px;border:1px solid var(--border);
  background:transparent;color:var(--muted);font-size:11px;cursor:pointer;
  font-family:inherit;flex-shrink:0;transition:all .15s;line-height:1.5}
.dir-edit-btn:hover{color:var(--text);border-color:#3a3a3a}

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
</style>
</head>
<body>
<div id="app">

<header>
  <div class="logo">◈ Claude <em>Remote</em></div>
  <div class="ai-badge">
    <div class="dot" id="dot"></div>
    <span id="ai-label">Shell</span>
    <div id="conn" title="WebSocket"></div>
  </div>
</header>

<div class="mode-bar">
  <button class="mode-btn" id="btn-claude"  onclick="cmd('claude')">Claude Code</button>
  <button class="mode-btn" id="btn-gemini"  onclick="cmd('gemini')">Gemini</button>
  <button class="mode-btn" id="btn-codex"   onclick="cmd('codex')">Codex</button>
  <button class="mode-btn" id="btn-shell"   onclick="cmd('stop_ai')">Shell</button>
  <div class="spacer"></div>
  <button class="act-btn" onclick="openHistory()">📂 History</button>
  <button class="act-btn" onclick="cmd('launch')">⚡ Launch</button>
  <button class="act-btn" onclick="cmd('interrupt')">✕ Interrupt</button>
  <button class="act-btn" onclick="cmd('clear')">↺ Clear</button>
</div>

<div class="dir-bar">
  <span class="dir-icon">📁</span>
  <span id="cwd-display" title="Click to change directory" onclick="startCwdEdit()">—</span>
  <input id="cwd-input" placeholder="Enter full path and press Enter…"
         onkeydown="cwdKey(event)" onblur="cancelCwdEdit()">
  <button class="dir-edit-btn" onclick="startCwdEdit()" title="Change working directory">✎</button>
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
  <textarea id="inp" placeholder="Type a message… (Enter to send, Shift+Enter for newline)" rows="1"></textarea>
  <button id="send" onclick="send()">Send</button>
</div>

<!-- History modal -->
<div class="modal-overlay" id="hist-modal" onclick="closeHistory(event)">
  <div class="modal-box">
    <div class="modal-header">
      <span class="modal-title">📂 Chat History</span>
      <button class="modal-close" onclick="closeHistory()">✕</button>
    </div>
    <div class="modal-body" id="hist-list"></div>
  </div>
</div>

</div>
<script>
const AI_LABEL = {claude:'Claude Code',gemini:'Gemini',codex:'Codex',shell:'Shell'};
const AI_CLASS = {claude:'active-claude',gemini:'active-gemini',codex:'active-codex',shell:'active-shell'};
let ws = null, activeAi = null, _viewingHistory = false, _liveHistory = [], _pendingContext = '';
let _sessNames = {};
function escHtml(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function connect(){
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${wsProto}://${location.host}/ws`);
  ws.onopen = () => {
    document.getElementById('conn').className = 'ok';
  };
  ws.onclose = () => {
    document.getElementById('conn').className = '';
    setTimeout(connect, 2500);
  };
  ws.onerror = () => {};
  ws.onmessage = e => {
    const d = JSON.parse(e.data);
    if(d.type==='message'){
      _liveHistory.push(d);
      if(!_viewingHistory) renderMsg(d);
    }
    else if(d.type==='state') applyState(d);
    else if(d.type==='thinking') setThinking(d.active, d.ai);
    else if(d.type==='cwd') applyCwd(d.path);
  };
}

function applyState(s){
  activeAi = s.active_ai;
  const dot = document.getElementById('dot');
  const lbl = document.getElementById('ai-label');
  const key = activeAi || 'shell';
  dot.className = 'dot ' + key;
  lbl.textContent = AI_LABEL[key] || key;
  ['claude','gemini','codex'].forEach(k => {
    document.getElementById('btn-'+k).className = 'mode-btn' + (activeAi===k?' '+AI_CLASS[k]:'');
  });
  document.getElementById('btn-shell').className = 'mode-btn' + (!activeAi?' active-shell':'');
  if(s.cwd) applyCwd(s.cwd);
}

function applyCwd(path){
  const el = document.getElementById('cwd-display');
  el.textContent = path;
  el.title = 'Working directory: ' + path + '\nClick to change';
}

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

function applyCwdEdit(){
  const input = document.getElementById('cwd-input');
  const path  = input.value.trim();
  cancelCwdEdit();
  if(!path || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({type:'command', command:'cwd', path:path}));
}

function cwdKey(e){
  if(e.key === 'Enter')  { e.preventDefault(); applyCwdEdit(); }
  if(e.key === 'Escape') { cancelCwdEdit(); }
}

function setThinking(on, ai){
  const el = document.getElementById('thinking');
  el.className = on ? 'on' : '';
  if(on){
    const k = ai || activeAi || '';
    document.getElementById('thlabel').textContent = (AI_LABEL[k]||'AI') + '…';
    scroll();
  }
}

function renderMsg(m){
  const wrap = document.getElementById('messages');
  // remove "Connecting…" placeholder if still there
  const placeholder = wrap.querySelector('.grp.system .bubble');
  if(placeholder && placeholder.textContent === 'Connecting to server…') {
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

function scroll(){
  const m = document.getElementById('messages');
  m.scrollTop = m.scrollHeight;
}

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

// ── History ──────────────────────────────────────────────────────────────────
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
  const msgs = await res.json();
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  msgs.forEach(renderMsg);
  _viewingHistory = true;
  const viewLabel = _sessNames[date] || date;
  document.getElementById('hist-banner-date').textContent = '\uD83D\uDCC5 Viewing: '+viewLabel;
  document.getElementById('hist-banner').classList.add('on');
  scroll();
}

function toggleSess(e, date){
  if(e.target.classList.contains('sess-del')) return;
  if(e.target.tagName === 'INPUT') return;
  const actions = document.getElementById('sess-act-'+date);
  const wasOpen = actions.classList.contains('open');
  document.querySelectorAll('.sess-actions').forEach(el => el.classList.remove('open'));
  if(!wasOpen) actions.classList.add('open');
}

function startRename(e, date){
  e.stopPropagation();
  const nameEl = document.getElementById('sess-name-'+date);
  if(!nameEl || nameEl.tagName === 'INPUT') return;
  const currentVal = nameEl.textContent === date ? '' : nameEl.textContent;
  const input = document.createElement('input');
  input.className = 'sess-rename-input';
  input.id = 'sess-name-'+date;
  input.value = currentVal;
  input.placeholder = date;
  nameEl.replaceWith(input);
  input.focus();
  input.select();
  let done = false;
  async function save(){
    if(done) return; done = true;
    const newName = input.value.trim();
    await fetch('/history/'+date+'/name', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({name: newName})
    });
    if(newName) _sessNames[date] = newName; else delete _sessNames[date];
    const span = document.createElement('span');
    span.className = 'sess-name'; span.id = 'sess-name-'+date;
    span.textContent = newName || date;
    input.replaceWith(span);
    const info = span.closest('.sess-info');
    if(info){
      const sub = info.querySelector('.sess-subdate');
      if(sub){ const m = sub.textContent.match(/(\d+ msg)/); const cnt = m?m[1]:''; sub.textContent = newName ? date+' \xB7 '+cnt : cnt; }
    }
  }
  function cancel(){
    if(done) return; done = true;
    const span = document.createElement('span');
    span.className = 'sess-name'; span.id = 'sess-name-'+date;
    span.textContent = currentVal || date;
    input.replaceWith(span);
  }
  input.addEventListener('keydown', ev => {
    if(ev.key==='Enter'){ ev.preventDefault(); save(); }
    if(ev.key==='Escape'){ cancel(); }
  });
  input.addEventListener('blur', save);
}

async function resumeSession(date){
  document.getElementById('hist-modal').classList.remove('open');
  const res = await fetch('/history/'+date);
  const msgs = await res.json();

  // Render the old messages so user can see context
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  msgs.forEach(renderMsg);

  // Build condensed context from last 10 user+assistant turns
  const turns = msgs.filter(m => m.role==='user' || m.role==='assistant').slice(-10);
  const lines = turns.map(m => {
    const role = m.role==='user' ? 'User' : (AI_LABEL[m.ai]||'AI');
    const body = (m.content||'').length > 300 ? m.content.slice(0,300)+'…' : (m.content||'');
    return role+': '+body;
  });
  const resumeLabel = _sessNames[date] || date;
  _pendingContext = '[Previous conversation — '+resumeLabel+']\n'+lines.join('\n')+'\n[End context]\n\n';

  // Go live (new messages will append below the old ones)
  _viewingHistory = false;
  document.getElementById('hist-banner-date').textContent = '\u25B6 Resumed from '+resumeLabel+' \u2014 context injected on first send';
  document.getElementById('hist-banner').classList.add('on');
  document.getElementById('inp').focus();
  scroll();
}

async function delSession(e, date){
  e.stopPropagation();
  if(!confirm('Delete all history for '+date+'?')) return;
  await fetch('/history/'+date, {method:'DELETE'});
  const item = e.target.closest('.sess-item');
  if(item) item.parentElement.remove();
  const list = document.getElementById('hist-list');
  if(!list.querySelector('.sess-item'))
    list.innerHTML = '<div class="modal-empty">No saved history yet.<br>Messages are saved automatically as you chat.</div>';
}

function returnToLive(){
  _viewingHistory = false;
  _pendingContext = '';
  document.getElementById('hist-banner').classList.remove('on');
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  _liveHistory.forEach(renderMsg);
  scroll();
}

connect();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point: run FastAPI + Telegram in the same asyncio event loop
# ---------------------------------------------------------------------------

async def _main():
    global _telegram_app

    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled.")

    # --- Build Telegram application ---
    if BOT_TOKEN:
        _telegram_app = Application.builder().token(BOT_TOKEN).build()
        _telegram_app.add_handler(CommandHandler("start",     tg_start))
        _telegram_app.add_handler(CommandHandler("launch",    tg_launch))
        _telegram_app.add_handler(CommandHandler("claude",    tg_claude))
        _telegram_app.add_handler(CommandHandler("codex",     tg_codex))
        _telegram_app.add_handler(CommandHandler("gemini",    tg_gemini))
        _telegram_app.add_handler(CommandHandler("stop_ai",   tg_stop_ai))
        _telegram_app.add_handler(CommandHandler("clear",     tg_clear))
        _telegram_app.add_handler(CommandHandler("cmd",       tg_cmd))
        _telegram_app.add_handler(CommandHandler("status",    tg_status))
        _telegram_app.add_handler(CommandHandler("interrupt", tg_interrupt))
        _telegram_app.add_handler(CommandHandler("stop",      tg_stop))
        _telegram_app.add_handler(CommandHandler("cwd",       tg_cwd))
        _telegram_app.add_handler(CommandHandler("timeout",   tg_timeout))
        _telegram_app.add_handler(CommandHandler("history",       tg_history))
        _telegram_app.add_handler(CommandHandler("resume",        tg_resume))
        _telegram_app.add_handler(CommandHandler("clear_context", tg_clear_context))
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
