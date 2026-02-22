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
from datetime import datetime
from functools import wraps
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
CLAUDE_TIMEOUT = float(os.environ.get("CLAUDE_TIMEOUT", "120"))
_DEFAULT_CWD = os.environ.get("SESSION_CWD", os.getcwd())
WEB_PORT = int(os.environ.get("WEB_PORT", "8000"))
WEB_HOST = os.environ.get("WEB_HOST", "127.0.0.1")

_CMD_EXT = ".cmd" if sys.platform == "win32" else ""

# ---------------------------------------------------------------------------
# ANSI cleaning
# ---------------------------------------------------------------------------

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][AB012]|\x1b.")


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
    path = pathlib.Path(_session_cwd) / filename
    if not path.exists() or not path.is_file():
        return HTMLResponse(
            f"<h2>File not found</h2><p><code>{filename}</code> not in <code>{_session_cwd}</code></p>",
            status_code=404,
        )
    return _FR(str(path))


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
        await update.message.reply_text(f"Session alive. PID: {_session.pid()}\nActive AI: {_active_ai or 'shell'}")
    else:
        await update.message.reply_text(f"No active session.\nActive AI: {_active_ai or 'shell'}")


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
async def tg_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward plain text from Telegram through the shared processor."""
    text = update.message.text or ""
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

</div>
<script>
const AI_LABEL = {claude:'Claude Code',gemini:'Gemini',codex:'Codex',shell:'Shell'};
const AI_CLASS = {claude:'active-claude',gemini:'active-gemini',codex:'active-codex',shell:'active-shell'};
let ws = null, activeAi = null;

function connect(){
  ws = new WebSocket(`ws://${location.host}/ws`);
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
    if(d.type==='message') renderMsg(d);
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
  ws.send(JSON.stringify({type:'message', content:txt}));
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
