"""
web_app.py — TaskForge: Web UI + Telegram Bot in one process.

Replaces the bare command-prompt window with a local chat UI at http://localhost:8000.
The Telegram bot continues to work in parallel; both channels share the same state.
"""

import asyncio
import difflib
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

try:
    from croniter import croniter as _Croniter
    _CRONITER_OK = True
except ImportError:
    _CRONITER_OK = False

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
CLAUDE_TIMEOUT = float(os.environ.get("CLAUDE_TIMEOUT", "0"))  # 0 = unlimited (AI tool controls its own timeout)
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

# ---------------------------------------------------------------------------
# Multi-session state  (replaces the old single _active_ai / _session globals)
# ---------------------------------------------------------------------------
# _sessions: dict[sid, session_dict]
# Each session dict:
#   id          str       "s1", "s2", ...
#   ai          str|None  "claude" | plugin-key | None (shell)
#   cwd         str       absolute working directory for this session
#   status      str       "running" | "stopped"
#   terminal    TerminalSession  its own cmd.exe process
#   claude_msgs list      messages for --continue flag (claude only)
#   name        str       "Claude #1", "Gemini #2", ...
#   emoji       str       "🤖"
#   color       str       hex colour "#f59e0b"
#   created     float     time.time()
#   last_used   float     updated on every message
# ---------------------------------------------------------------------------
_sessions: dict[str, dict] = {}
_focused_id: Optional[str] = None        # which session Telegram/Web are talking to
_session_counter: int = 0               # incremented for each new session

_pending_tg_context: Optional[str] = None   # injected into next Telegram message after /resume
_tg_browse_state: dict = {}             # user_id → {"path": str, "dirs": list, "page": int}
_BROWSE_PAGE_SIZE = 8
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
# Session helpers
# ---------------------------------------------------------------------------

def _make_session(ai: Optional[str]) -> dict:
    """Create, launch, and register a new session. Returns the session dict."""
    global _session_counter, _focused_id
    _session_counter += 1
    sid = f"s{_session_counter}"
    if ai == "claude":
        name  = f"Claude #{_session_counter}";  emoji = "🤖"; color = "#f59e0b"
    elif ai and ai in _integrations:
        info  = _integrations[ai]
        name  = f"{info['name']} #{_session_counter}"; emoji = info["emoji"]; color = info["color"]
    else:
        name  = f"Shell #{_session_counter}";   emoji = "🐚"; color = "#6b7280"; ai = None
    t = TerminalSession()
    if ai is None:
        # Shell sessions need cmd.exe immediately.
        # AI sessions (claude / integrations) use _run_ai_popen instead — no cmd.exe needed.
        # Launching Popen on the event-loop thread for AI sessions blocked new-session creation
        # while another AI task was in flight; skipping it here makes creation instant.
        t.launch()
    sess: dict = {
        "id": sid, "ai": ai, "cwd": _DEFAULT_CWD, "status": "running",
        "terminal": t, "claude_msgs": [], "name": name, "emoji": emoji,
        "color": color, "created": time.time(), "last_used": time.time(),
        "busy": False, "task_start": None,  # progress tracking
        "proc": None,  # running Popen object (AI subprocess), killable
    }
    _sessions[sid] = sess
    return sess


def _focused_session() -> Optional[dict]:
    return _sessions.get(_focused_id) if _focused_id else None


def _session_cwd() -> str:
    """CWD of the focused session (or default if none focused)."""
    s = _focused_session()
    return s["cwd"] if s else _DEFAULT_CWD


def _session_status_icon(sess: dict) -> str:
    if sess["status"] == "stopped":
        return "🔴"
    if sess.get("busy"):
        return "🟡"   # actively processing a task
    return "🟢"       # idle (running but waiting for input)


def _sessions_state_payload() -> list[dict]:
    """Serialisable list of all sessions (no terminal objects)."""
    return [
        {"id": s["id"], "name": s["name"], "ai": s["ai"], "cwd": s["cwd"],
         "status": s["status"], "emoji": s["emoji"], "color": s["color"],
         "busy": s.get("busy", False)}
        for s in _sessions.values()
    ]


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
    """Persist all session state to last_state.json for resume fallback."""
    try:
        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        state_file = CHAT_LOG_DIR / "last_state.json"
        sessions_data = {}
        for sid, sess in _sessions.items():
            sessions_data[sid] = {k: v for k, v in sess.items() if k != "terminal"}
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(
                {"sessions": sessions_data, "focused_id": _focused_id,
                 "counter": _session_counter, "timestamp": _ts()},
                f, ensure_ascii=False,
            )
    except Exception as e:
        logger.warning("Could not save last state: %s", e)


async def _push_message(role: str, content: str, ai: Optional[str] = None,
                        source: str = "web", session_id: Optional[str] = None):
    """Record a chat message and broadcast it to all WS clients."""
    sess = _sessions.get(session_id) if session_id else None
    msg = {
        "type": "message", "role": role, "content": content, "ai": ai,
        "source": source, "timestamp": _ts(),
        "session_id": session_id,
        "session_name": sess["name"] if sess else None,
        "session_emoji": sess["emoji"] if sess else None,
    }
    _chat_history.append(msg)
    if len(_chat_history) > 200:
        del _chat_history[:-200]
    _save_message_to_log(msg)
    await _broadcast(msg)


async def _push_state():
    _save_last_state()
    fs = _focused_session()
    await _broadcast({
        "type": "state",
        "sessions": _sessions_state_payload(),
        "focused_id": _focused_id,
        "focused_ai": fs["ai"] if fs else None,
        "focused_cwd": fs["cwd"] if fs else _DEFAULT_CWD,
        "focused_status": fs["status"] if fs else None,
    })


async def _push_thinking(active: bool, ai: Optional[str] = None,
                         session_id: Optional[str] = None):
    """Broadcast thinking state.  session_id lets the client track per-session state."""
    effective_ai = ai
    if not effective_ai and session_id:
        s = _sessions.get(session_id)
        if s:
            effective_ai = s["ai"]
    if not effective_ai:
        fs = _focused_session()
        effective_ai = fs["ai"] if fs else None
    await _broadcast({
        "type": "thinking",
        "active": active,
        "ai": effective_ai,
        "session_id": session_id,
    })


# ---------------------------------------------------------------------------
# AI runner
# ---------------------------------------------------------------------------

def _run_ai_popen(cmd: list[str], cwd: str, name: str, sess: dict) -> str:
    """Run an AI CLI subprocess, storing the Popen handle in sess['proc'] so it
    can be killed externally by stop_session / interrupt handlers.
    CLAUDE_TIMEOUT == 0 means unlimited.
    """
    _timeout = CLAUDE_TIMEOUT if CLAUDE_TIMEOUT > 0 else None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
        )
        sess["proc"] = proc  # store so stop/interrupt can kill it
        try:
            stdout, stderr = proc.communicate(timeout=_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            sess["proc"] = None
            return f"(timed out after {int(_timeout)}s — use /timeout 0 for unlimited)"
        finally:
            sess["proc"] = None  # clear after natural completion

        stdout = stdout.strip()
        stderr = stderr.strip()

        if proc.returncode != 0:
            parts = [p for p in [stdout, stderr] if p]
            return "\n".join(parts) if parts else f"({name} exited {proc.returncode})"
        return stdout or "(no output)"

    except FileNotFoundError:
        return f"Error: '{cmd[0]}' not found in PATH."
    except Exception as e:
        return f"(error: {e})"


def _kill_session_proc(sess: dict) -> None:
    """Kill the running AI subprocess for a session (if any). Safe to call always."""
    proc = sess.get("proc")
    if proc is not None:
        try:
            proc.kill()
        except Exception:
            pass
        sess["proc"] = None


def _build_claude_cmd(prompt: str, has_history: bool) -> list[str]:
    cmd = ["claude"]
    if has_history:
        cmd.append("--continue")
    cmd.extend(["-p", prompt])
    return cmd


# ---------------------------------------------------------------------------
# Core message processor (shared by web + Telegram)
# ---------------------------------------------------------------------------

async def _process_message(text: str, source: str = "web",
                           session_id: Optional[str] = None) -> str:
    """
    Route `text` to the given session (or focused session if session_id is None).
    Returns the response string. Broadcasts to all WS clients.
    """
    sid  = session_id or _focused_id
    sess = _sessions.get(sid) if sid else None

    if not sess or sess["status"] == "stopped":
        msg = "No active session. Create or resume a session first."
        await _push_message("system", msg, source=source)
        return msg

    sess["last_used"] = time.time()
    sess["busy"]       = True
    sess["task_start"] = time.time()
    await _push_state()  # immediately reflect 🟡 busy status on web UI and Telegram

    ai       = sess["ai"]
    cwd      = sess["cwd"]
    terminal = sess["terminal"]

    await _push_message("user", text, ai=None, source=source, session_id=sid)

    output = ""  # safe default — overwritten in every branch below
    try:
        if ai == "claude":
            await _push_thinking(True, "claude", session_id=sid)
            has_history = len(sess["claude_msgs"]) > 0
            cmd = _build_claude_cmd(text, has_history)
            sess["claude_msgs"].append(text)
            before = await asyncio.to_thread(_snapshot_dir, cwd)
            output = await asyncio.to_thread(_run_ai_popen, cmd, cwd, "claude", sess)
            after  = await asyncio.to_thread(_snapshot_dir, cwd)
            await _push_thinking(False, session_id=sid)
            await _push_message("assistant", output, ai="claude", source=source, session_id=sid)
            await _handle_diff(before, after, source, cwd)

        elif ai in _integrations:
            await _push_thinking(True, ai, session_id=sid)
            cmd    = _integrations[ai]["build_command"](text)
            before = await asyncio.to_thread(_snapshot_dir, cwd)
            output = await asyncio.to_thread(_run_ai_popen, cmd, cwd, ai, sess)
            after  = await asyncio.to_thread(_snapshot_dir, cwd)
            await _push_thinking(False, session_id=sid)
            await _push_message("assistant", output, ai=ai, source=source, session_id=sid)
            await _handle_diff(before, after, source, cwd)

        else:
            # Shell mode
            if not terminal.is_alive():
                output = "Terminal stopped. Stop and restart this session."
                await _push_message("system", output, source=source, session_id=sid)
            else:
                before = await asyncio.to_thread(_snapshot_dir, cwd)
                terminal.write(text)
                output = await asyncio.to_thread(terminal.drain)
                after  = await asyncio.to_thread(_snapshot_dir, cwd)
                output = output or "(no output)"
                await _push_message("assistant", output, ai="shell", source=source, session_id=sid)
                await _handle_diff(before, after, source, cwd)

    finally:
        elapsed            = time.time() - sess["task_start"]
        sess["busy"]       = False
        sess["task_start"] = None
        await _push_state()  # flip session back to 🟢 idle
        await _tg_progress_notify(sess, output, elapsed, source)

    return output


async def _forward_to_telegram(text: str):
    """Send a message to the user's Telegram chat (fire-and-forget)."""
    if _telegram_app and _telegram_chat_id:
        try:
            await _telegram_app.bot.send_message(chat_id=_telegram_chat_id, text=text)
        except Exception as e:
            logger.warning("Telegram forward failed: %s", e)


async def _tg_progress_notify(sess: dict, output: str, elapsed: float, source: str) -> None:
    """Send a compact Telegram ping when a session finishes a task.

    Fires when:
    - Multiple sessions are currently running (parallel work) — every completion
      gets a timestamped ping so you can track which session finished when.
    - The task was triggered from the web UI (source=="web") — so you get a phone
      notification even when away from the browser.

    Skipped for single-session Telegram use — the normal reply is sufficient.
    """
    if not (_telegram_app and _telegram_chat_id):
        return

    running = [s for s in _sessions.values() if s["status"] == "running"]
    multi   = len(running) >= 2
    web_src = source == "web"

    if not multi and not web_src:
        return  # single session via Telegram — reply already serves as notification

    # Format elapsed time
    if elapsed < 60:
        elapsed_str = f"{elapsed:.0f}s"
    elif elapsed < 3600:
        elapsed_str = f"{elapsed/60:.1f}m"
    else:
        elapsed_str = f"{elapsed/3600:.1f}h"

    # Truncate output preview to one readable line
    preview = " ".join(output.strip().splitlines()[:3])
    if len(preview) > 300:
        preview = preview[:297] + "…"

    lines = [f"✅ {sess['emoji']} *{sess['name']}* — {elapsed_str}"]
    if preview:
        lines.append(preview)

    # Check if all running sessions are now idle (busy == False)
    still_busy = [s for s in running if s.get("busy")]
    if not still_busy and multi:
        lines.append(f"\n🏁 All {len(running)} sessions idle")

    try:
        await _telegram_app.bot.send_message(
            chat_id=_telegram_chat_id,
            text="\n".join(lines),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning("Progress notify failed: %s", e)


async def _change_cwd(new_path: str, source: str = "web",
                      session_id: Optional[str] = None) -> bool:
    """Validate and switch the CWD of the focused (or given) session."""
    sid  = session_id or _focused_id
    sess = _sessions.get(sid) if sid else None
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
    new_cwd = str(path)
    if sess:
        sess["cwd"] = new_cwd
    _save_cwd_to_log(new_cwd)
    _save_last_state()
    logger.info("Working directory changed to: %s", new_cwd)
    await _push_state()
    await _push_message("system", f"📁 Working directory → {new_cwd}", source=source,
                        session_id=sid)
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


def _snapshot_dir(cwd: str) -> dict[str, tuple[int, float]]:
    """Return {abs_path: (size_bytes, mtime)} for files in cwd (2 levels deep).

    Goes one level into subdirectories so files created inside a new folder
    (e.g. an HTML output dir) are still detected.
    Skips common large/build directories to stay fast.
    """
    result: dict[str, tuple[int, float]] = {}
    try:
        base = pathlib.Path(cwd)
        for entry in base.iterdir():
            if entry.is_file():
                try:
                    st = entry.stat()
                    result[str(entry)] = (st.st_size, st.st_mtime)
                except Exception:
                    pass
            elif entry.is_dir() and entry.name not in _SKIP_DIRS:
                try:
                    for child in entry.iterdir():
                        if child.is_file():
                            try:
                                st = child.stat()
                                result[str(child)] = (st.st_size, st.st_mtime)
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass
    return result


def _diff_snapshots(before: dict, after: dict) -> dict:
    """Compare two snapshots; return {new, modified, deleted} path lists."""
    b = set(before)
    a = set(after)
    return {
        "new":      sorted(a - b),
        "modified": sorted(p for p in b & a if before[p] != after[p]),
        "deleted":  sorted(b - a),
    }


def _git_diff_stat(cwd: str) -> Optional[str]:
    """Run `git diff --stat` in cwd. Returns None if not a git repo or no diff."""
    try:
        r = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        out = r.stdout.strip()
        return out if out else None
    except Exception:
        return None


def _git_is_repo(cwd: str) -> bool:
    """Return True if cwd is inside a git repository."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


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
        rel_posix = path.resolve().relative_to(pathlib.Path(_session_cwd()).resolve()).as_posix()
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


async def _handle_diff(before: dict, after: dict, source: str, cwd: str):
    """Diff snapshots → notify web chat + Telegram about new, modified, deleted files."""
    diff = _diff_snapshots(before, after)

    # ── New files ─────────────────────────────────────────────────────────────
    for filepath in diff["new"]:
        path = pathlib.Path(filepath)
        ext  = path.suffix.lower()
        if ext not in _ALL_SENDABLE:
            continue
        local_url = f"http://localhost:{WEB_PORT}/files/{path.name}"
        try:
            size_kb = path.stat().st_size // 1024
        except Exception:
            size_kb = 0
        await _push_message(
            "system",
            f"📎 New file: {path.name} ({size_kb} KB)  →  {local_url}",
            source=source,
        )
        await _send_file_to_telegram(filepath, source)

    # ── Modified files ────────────────────────────────────────────────────────
    if diff["modified"]:
        # Prefer git diff --stat (shows insertions/deletions per file)
        git_stat = await asyncio.to_thread(_git_diff_stat, cwd) if _git_is_repo(cwd) else None
        if git_stat:
            summary = f"📝 Changes:\n```\n{git_stat[:1400]}\n```"
        else:
            lines = [f"📝 Modified {len(diff['modified'])} file(s):"]
            for fp in diff["modified"][:12]:
                p = pathlib.Path(fp)
                old_sz, _ = before[fp]
                new_sz, _ = after[fp]
                delta     = new_sz - old_sz
                lines.append(f"  ✏️ {p.name}  ({delta:+,} B)")
            if len(diff["modified"]) > 12:
                lines.append(f"  … and {len(diff['modified']) - 12} more")
            summary = "\n".join(lines)

        await _push_message("system", summary, source=source)

        if _telegram_app and _telegram_chat_id:
            tg_text = git_stat or "\n".join(
                f"✏️ {pathlib.Path(fp).name}" for fp in diff["modified"][:10]
            )
            try:
                await _telegram_app.bot.send_message(
                    chat_id=_telegram_chat_id,
                    text=f"📝 *Changes:*\n```\n{tg_text[:1400]}\n```",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning("Diff Telegram notify failed: %s", e)

    # ── Deleted files ─────────────────────────────────────────────────────────
    if diff["deleted"]:
        names = ", ".join(pathlib.Path(fp).name for fp in diff["deleted"][:6])
        if len(diff["deleted"]) > 6:
            names += f" +{len(diff['deleted']) - 6} more"
        await _push_message("system", f"🗑️ Deleted: {names}", source=source)


# Keep old name as alias so any external callers don't break
async def _handle_new_files(before, after, source: str):
    cwd = _session_cwd()
    # Support both old set[str] and new dict[str, tuple] snapshots
    if isinstance(before, set):
        before = {p: (0, 0.0) for p in before}
        after  = {p: (0, 0.0) for p in after}
    await _handle_diff(before, after, source, cwd)


# ---------------------------------------------------------------------------
# Scheduled / cron AI tasks
# ---------------------------------------------------------------------------

_scheduled_tasks: dict[str, dict] = {}
_sched_counter: int = 0
_SCHED_FILE = CHAT_LOG_DIR / "scheduled_tasks.json"


def _next_cron_run(cron_expr: str) -> Optional[float]:
    """Return the next fire time (Unix timestamp) for cron_expr, or None on error."""
    if not _CRONITER_OK:
        return None
    try:
        return _Croniter(cron_expr, datetime.now()).get_next(float)
    except Exception:
        return None


def _make_sched_task(cron: str, ai: Optional[str], prompt: str,
                     cwd: Optional[str] = None, name: Optional[str] = None) -> dict:
    global _sched_counter
    _sched_counter += 1
    tid = f"t{_sched_counter}"
    return {
        "id":        tid,
        "name":      name or f"Task #{_sched_counter}",
        "ai":        ai,
        "cwd":       cwd or _DEFAULT_CWD,
        "prompt":    prompt,
        "cron":      cron,
        "enabled":   True,
        "next_run":  _next_cron_run(cron),
        "last_run":  None,
        "run_count": 0,
        "created":   time.time(),
    }


def _load_scheduled_tasks() -> None:
    global _scheduled_tasks, _sched_counter
    try:
        if _SCHED_FILE.exists():
            data = json.loads(_SCHED_FILE.read_text(encoding="utf-8"))
            _scheduled_tasks = data.get("tasks", {})
            _sched_counter   = data.get("counter", 0)
            # Recompute next_run so they're correct after a restart
            for task in _scheduled_tasks.values():
                if task.get("enabled") and task.get("cron"):
                    task["next_run"] = _next_cron_run(task["cron"])
    except Exception as e:
        logger.warning("Could not load scheduled tasks: %s", e)


def _save_scheduled_tasks() -> None:
    try:
        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _SCHED_FILE.open("w", encoding="utf-8") as f:
            json.dump({"tasks": _scheduled_tasks, "counter": _sched_counter},
                      f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Could not save scheduled tasks: %s", e)


async def _run_scheduled_task(task: dict) -> None:
    """Execute one scheduled task in a temporary session and report via Telegram."""
    logger.info("Running scheduled task %s: %s", task["id"], task["name"])

    sess = _make_session(task["ai"])
    if task.get("cwd"):
        sess["cwd"] = task["cwd"]

    # Announce start
    announce = f"⏰ *{task['name']}* starting…"
    await _push_message("system", announce, source="schedule", session_id=sess["id"])
    if _telegram_app and _telegram_chat_id:
        try:
            await _telegram_app.bot.send_message(
                chat_id=_telegram_chat_id, text=announce, parse_mode="Markdown"
            )
        except Exception:
            pass

    # Run the prompt (reuses all session machinery incl. progress notify)
    await _process_message(task["prompt"], source="schedule", session_id=sess["id"])

    task["run_count"] = task.get("run_count", 0) + 1
    task["last_run"]  = time.time()
    _save_scheduled_tasks()

    # Clean up ephemeral session
    sess["terminal"].stop()
    if sess["id"] in _sessions:
        del _sessions[sess["id"]]
    # Re-focus whatever was focused before (if anything)
    await _push_state()


async def _cron_runner() -> None:
    """Background loop: fires scheduled tasks when they're due (checks every 30 s)."""
    while True:
        await asyncio.sleep(30)
        now = time.time()
        for task in list(_scheduled_tasks.values()):
            if not task.get("enabled"):
                continue
            nxt = task.get("next_run")
            if nxt and now >= nxt:
                # Advance to next occurrence BEFORE launching so a slow task
                # can't double-fire on the next 30-second tick.
                task["next_run"] = _next_cron_run(task["cron"])
                task["last_run"] = now
                _save_scheduled_tasks()
                asyncio.create_task(_run_scheduled_task(task))


def _sched_tasks_payload() -> list[dict]:
    """JSON-safe list of scheduled tasks for the web UI."""
    out = []
    for t in _scheduled_tasks.values():
        nr = datetime.fromtimestamp(t["next_run"]).strftime("%Y-%m-%d %H:%M") if t.get("next_run") else "—"
        lr = datetime.fromtimestamp(t["last_run"]).strftime("%Y-%m-%d %H:%M") if t.get("last_run") else "never"
        out.append({**{k: v for k, v in t.items() if k not in ("next_run","last_run")},
                    "next_run_fmt": nr, "last_run_fmt": lr,
                    "next_run": t.get("next_run"), "last_run": t.get("last_run")})
    return out


# ---------------------------------------------------------------------------
# FastAPI app + WebSocket
# ---------------------------------------------------------------------------

app = FastAPI(title="TaskForge")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=_HTML)


@app.get("/files/{filename:path}")
async def serve_file(filename: str):
    """Dynamically serve any file from the focused session's CWD."""
    from fastapi.responses import FileResponse as _FR
    cwd  = _session_cwd()
    base = pathlib.Path(cwd).resolve()
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
            f"<h2>File not found</h2><p><code>{filename}</code> not in <code>{cwd}</code></p>",
            status_code=404,
        )
    return _FR(str(path))


@app.get("/browse")
async def browse_directory(path: str = ""):
    """Return subdirectories and navigation info for the folder browser."""
    from fastapi.responses import JSONResponse
    import string as _string
    cwd    = _session_cwd()
    target = path.strip() if path.strip() else cwd
    p = pathlib.Path(target).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        p = pathlib.Path(cwd).resolve()
    try:
        dirs = sorted(
            [d.name for d in p.iterdir() if d.is_dir()],
            key=lambda x: x.lower(),
        )
    except (PermissionError, OSError):
        dirs = []
    parent = str(p.parent) if str(p) != str(p.parent) else None
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


# ── History cache — serves instantly, refreshes in background ─────────────────
_hist_cache: list = []       # cached session metadata list
_hist_cache_ts: float = 0.0  # last refresh timestamp


def _scan_log_fast(log_file: pathlib.Path) -> dict:
    """Read only the last 4 KB of a log file to extract metadata quickly."""
    date_str = log_file.stem
    try:
        size = log_file.stat().st_size
        mtime = log_file.stat().st_mtime
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            if size > 4096:
                f.seek(size - 4096)
                f.readline()  # discard partial line
            tail_lines = f.readlines()
        preview = ""
        last_ai = ""
        last_ts: Optional[float] = None
        count_tail = 0
        for line in tail_lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") == "message":
                count_tail += 1
                if rec.get("role") == "assistant":
                    txt = rec.get("content", "")
                    if txt:
                        preview = txt[:100].replace("\n", " ")
                if rec.get("ai"):
                    last_ai = rec["ai"]
                if rec.get("ts"):
                    last_ts = rec["ts"]
        return {
            "date": date_str, "count": count_tail if size <= 4096 else max(1, size // 200),
            "name": "", "preview": preview, "ai": last_ai,
            "ts": last_ts, "mtime": mtime,
        }
    except Exception:
        return {"date": date_str, "count": 0, "name": "", "preview": "", "ai": "", "ts": None, "mtime": 0}


def _rebuild_hist_cache_sync() -> list:
    """Synchronous cache rebuild — run in thread pool."""
    global _hist_cache, _hist_cache_ts
    if not CHAT_LOG_DIR.exists():
        _hist_cache = []
        _hist_cache_ts = time.time()
        return _hist_cache
    log_files = list(CHAT_LOG_DIR.glob("*.jsonl"))
    sessions = [_scan_log_fast(f) for f in log_files]
    sessions.sort(key=lambda s: s.get("mtime", 0), reverse=True)
    names = _load_chat_names()
    for s in sessions:
        s["name"] = names.get(s["date"], "")
        s.pop("mtime", None)
    _hist_cache = sessions
    _hist_cache_ts = time.time()
    return sessions


@app.get("/history")
async def history_list():
    """Return cached session list instantly. Refreshes in background if stale."""
    from fastapi.responses import JSONResponse
    global _hist_cache, _hist_cache_ts
    age = time.time() - _hist_cache_ts
    if _hist_cache and age < 30:
        # Serve from cache instantly
        return JSONResponse(_hist_cache)
    if _hist_cache:
        # Serve stale cache NOW, refresh in background
        asyncio.get_event_loop().run_in_executor(None, _rebuild_hist_cache_sync)
        return JSONResponse(_hist_cache)
    # First load ever — must wait, but do it in thread pool to not block event loop
    sessions = await asyncio.get_event_loop().run_in_executor(None, _rebuild_hist_cache_sync)
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
        _hist_cache_ts = 0  # invalidate cache
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


@app.post("/history/{date}/rename")
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
    fs = _focused_session()
    await websocket.send_text(json.dumps({
        "type": "state",
        "sessions": _sessions_state_payload(),
        "focused_id": _focused_id,
        "focused_ai": fs["ai"] if fs else None,
        "focused_cwd": fs["cwd"] if fs else _DEFAULT_CWD,
        "focused_status": fs["status"] if fs else None,
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
                # Capture focused session NOW (before the task runs) so we route
                # to the session the user intended, even if focus changes later.
                _dispatch_sid = _focused_id

                async def _fire_and_forward(
                    _text: str = content,
                    _sid: str = _dispatch_sid,
                ) -> None:
                    response = await _process_message(_text, source="web",
                                                      session_id=_sid)
                    # Forward to Telegram after completion
                    await _forward_to_telegram(f"🖥️ You (web): {_text}")
                    for chunk in [response[i:i+3800]
                                  for i in range(0, len(response), 3800)]:
                        await _forward_to_telegram(chunk)

                # create_task so the receive loop is never blocked by the AI run
                asyncio.create_task(_fire_and_forward())

            elif data.get("type") == "command":
                cmd = data.get("command", "")
                if cmd == "cwd":
                    # CWD change carries its path in the same message
                    await _change_cwd(data.get("path", ""), source="web")
                else:
                    try:
                        await _handle_web_command(cmd, websocket)
                    except Exception as _cmd_err:
                        logger.warning("Command error (%s): %s", cmd, _cmd_err)
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "message", "role": "system",
                                "content": f"⚠️ Command failed: {_cmd_err}",
                                "source": "web", "timestamp": _ts(),
                            }))
                        except Exception:
                            pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WS error: %s", e)
    finally:
        _ws_clients.discard(websocket)
        logger.info("WS client disconnected (total: %d)", len(_ws_clients))


async def _handle_web_command(command: str, ws: WebSocket):
    """Handle control commands sent from the web UI (multi-session aware)."""
    global _focused_id

    # ── new_session:{ai} — create and focus a new session ────────────────────
    if command.startswith("new_session:"):
        ai_key = command.split(":", 1)[1].strip() or None
        if ai_key == "shell":
            ai_key = None
        sess = _make_session(ai_key)
        _focused_id = sess["id"]
        await _push_state()
        label = sess["emoji"] + " " + sess["name"]
        await _push_message("system", f"Session created: {label}", source="web",
                            session_id=sess["id"])
        return

    # ── focus:{sid} — switch focused session ─────────────────────────────────
    if command.startswith("focus:"):
        sid = command.split(":", 1)[1]
        if sid in _sessions:
            _focused_id = sid
            await _push_state()
        return

    # ── stop_session — stop the focused session ───────────────────────────────
    if command == "stop_session":
        sess = _focused_session()
        if sess:
            _kill_session_proc(sess)          # kill AI subprocess immediately
            sess["terminal"].stop()
            sess["status"] = "stopped"
            sess["busy"]      = False
            sess["task_start"] = None
            await _push_thinking(False, session_id=sess["id"])  # clear spinner NOW
            await _push_state()
            await _push_message("system", f"Session stopped: {sess['name']}", source="web",
                                session_id=sess["id"])
        return

    # ── delete_session — remove focused session entirely ─────────────────────
    if command == "delete_session":
        sess = _focused_session()
        if sess:
            sess["terminal"].stop()
            sid = sess["id"]
            del _sessions[sid]
            # focus the most-recently-used remaining session, or None
            _focused_id = max(_sessions, key=lambda k: _sessions[k]["last_used"],
                              default=None) if _sessions else None
            await _push_state()
        return

    # ── switch_ai:{ai} — change AI of focused session ────────────────────────
    if command.startswith("switch_ai:"):
        sess = _focused_session()
        if sess:
            ai_key = command.split(":", 1)[1].strip()
            if ai_key == "shell":
                ai_key = None
                # AI sessions skip cmd.exe at creation; launch it now on first shell switch
                if not sess["terminal"].is_alive():
                    await asyncio.to_thread(sess["terminal"].launch)
            sess["ai"] = ai_key
            sess["claude_msgs"] = []
            if ai_key == "claude":
                sess["emoji"] = "🤖"; sess["color"] = "#f59e0b"
            elif ai_key and ai_key in _integrations:
                info = _integrations[ai_key]
                sess["emoji"] = info["emoji"]; sess["color"] = info["color"]
            else:
                sess["emoji"] = "🐚"; sess["color"] = "#6b7280"
            await _push_state()
            await _push_message("system",
                f"Switched to {sess['emoji']} {ai_key or 'Shell'}", source="web",
                session_id=sess["id"])
        return

    # ── interrupt — send Ctrl+C to focused session ────────────────────────────
    if command == "interrupt":
        sess = _focused_session()
        if sess:
            try:
                if sess["ai"]:
                    # AI session — kill the subprocess directly (more reliable than Ctrl+C)
                    _kill_session_proc(sess)
                    sess["busy"]       = False
                    sess["task_start"] = None
                    await _push_thinking(False, session_id=sess["id"])  # clear spinner NOW
                    await _push_state()
                    await _push_message("system", "⏸ Task cancelled.", source="web",
                                        session_id=sess["id"])
                else:
                    # Shell session — send Ctrl+C to the terminal
                    sess["terminal"].send_interrupt()
                    await _push_message("system", "Ctrl+C sent.", source="web",
                                        session_id=sess["id"])
            except RuntimeError as e:
                await _push_message("system", str(e), source="web")
        return

    # ── clear — clear Claude context for focused session ─────────────────────
    if command == "clear":
        sess = _focused_session()
        if sess:
            sess["claude_msgs"] = []
            await _push_message("system", "Claude conversation history cleared.", source="web",
                                session_id=sess["id"])
        return

    # ── schedule_list — return scheduled tasks to web UI ─────────────────────
    if command == "schedule_list":
        await ws.send_text(json.dumps({
            "type":  "schedule_list",
            "tasks": _sched_tasks_payload(),
        }))
        return

    # ── schedule_add:<cron>|<ai>|<prompt> ────────────────────────────────────
    if command.startswith("schedule_add:"):
        parts = command[len("schedule_add:"):].split("|", 2)
        if len(parts) < 3:
            await _push_message("system", "❌ Invalid schedule_add format.", source="web")
            return
        cron_expr, ai_key, prompt = parts[0].strip(), parts[1].strip() or None, parts[2].strip()
        if not prompt:
            await _push_message("system", "❌ Prompt cannot be empty.", source="web")
            return
        if _next_cron_run(cron_expr) is None:
            await _push_message("system",
                f"❌ Invalid cron expression: {cron_expr}  (needs 5 fields, e.g. 0 9 * * *)",
                source="web")
            return
        if ai_key not in ("claude", None, "", *_integrations):
            ai_key = None
        task = _make_sched_task(cron_expr, ai_key or None, prompt,
                                cwd=_session_cwd())
        _scheduled_tasks[task["id"]] = task
        _save_scheduled_tasks()
        nr = datetime.fromtimestamp(task["next_run"]).strftime("%Y-%m-%d %H:%M") \
             if task.get("next_run") else "?"
        await _push_message("system",
            f"⏰ Scheduled *{task['name']}* (`{task['id']}`)\n"
            f"`{cron_expr}` · {ai_key or 'shell'} · next: {nr}",
            source="web")
        await ws.send_text(json.dumps({"type": "schedule_list", "tasks": _sched_tasks_payload()}))
        return

    # ── schedule_delete:<id> ──────────────────────────────────────────────────
    if command.startswith("schedule_delete:"):
        tid = command[len("schedule_delete:"):].strip()
        if tid in _scheduled_tasks:
            name = _scheduled_tasks[tid]["name"]
            del _scheduled_tasks[tid]
            _save_scheduled_tasks()
            await _push_message("system", f"🗑️ Deleted scheduled task: {name}", source="web")
        await ws.send_text(json.dumps({"type": "schedule_list", "tasks": _sched_tasks_payload()}))
        return

    # ── schedule_toggle:<id> ──────────────────────────────────────────────────
    if command.startswith("schedule_toggle:"):
        tid = command[len("schedule_toggle:"):].strip()
        if tid in _scheduled_tasks:
            task = _scheduled_tasks[tid]
            task["enabled"] = not task["enabled"]
            if task["enabled"]:
                task["next_run"] = _next_cron_run(task["cron"])
            _save_scheduled_tasks()
        await ws.send_text(json.dumps({"type": "schedule_list", "tasks": _sched_tasks_payload()}))
        return

    # ── schedule_run:<id> — manual trigger ────────────────────────────────────
    if command.startswith("schedule_run:"):
        tid = command[len("schedule_run:"):].strip()
        if tid in _scheduled_tasks:
            asyncio.create_task(_run_scheduled_task(_scheduled_tasks[tid]))
        return


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
            initialdir=_session_cwd(),
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

def _sessions_keyboard() -> InlineKeyboardMarkup:
    """Session list — one button per session + New Session + History/Resume."""
    rows: list = []
    for sess in sorted(_sessions.values(), key=lambda s: s["last_used"], reverse=True):
        icon = _session_status_icon(sess)
        cwd_short = pathlib.Path(sess["cwd"]).name or sess["cwd"]
        label = f"{icon} {sess['name']}  ·  {cwd_short}"
        rows.append([InlineKeyboardButton(label, callback_data=f"ms:focus:{sess['id']}")])
    rows.append([InlineKeyboardButton("➕ New Session", callback_data="ms:new")])
    rows.append([
        InlineKeyboardButton("💬 Past chats",    callback_data="action:history"),
        InlineKeyboardButton("🔁 Resume old",    callback_data="action:resume"),
    ])
    return InlineKeyboardMarkup(rows)


def _session_controls_keyboard() -> InlineKeyboardMarkup:
    """Controls for the currently-focused session."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 All Sessions",  callback_data="ms:list"),
            InlineKeyboardButton("📁 Change Dir",    callback_data="ms:browse"),
        ],
        [
            InlineKeyboardButton("🔀 Switch AI",     callback_data="ms:switch"),
            InlineKeyboardButton("⏸ Cancel Task",    callback_data="ms:interrupt"),
        ],
        [
            InlineKeyboardButton("🗑 Delete Session", callback_data="ms:delete"),
        ],
    ])


def _new_session_keyboard(resume_sid: str = "") -> InlineKeyboardMarkup:
    """AI picker for creating a new session (or resuming a stopped one)."""
    rows: list = []
    ai_buttons = [InlineKeyboardButton("🤖 Claude Code",
                                       callback_data=f"ms:new_ai:claude:{resume_sid}")]
    for key, info in _integrations.items():
        ai_buttons.append(InlineKeyboardButton(
            f"{info['emoji']} {info['name']}",
            callback_data=f"ms:new_ai:{key}:{resume_sid}",
        ))
    ai_buttons.append(InlineKeyboardButton("🐚 Shell",
                                            callback_data=f"ms:new_ai:shell:{resume_sid}"))
    for i in range(0, len(ai_buttons), 2):
        rows.append(ai_buttons[i : i + 2])
    rows.append([InlineKeyboardButton("← Back", callback_data="ms:list")])
    return InlineKeyboardMarkup(rows)


# Keep thin aliases for any remaining code that calls the old names
def _ai_select_keyboard() -> InlineKeyboardMarkup:
    return _sessions_keyboard()


def _running_keyboard() -> InlineKeyboardMarkup:
    return _session_controls_keyboard()


@authorized_only
async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message — show session list or prompt to create first session."""
    if _sessions:
        await update.message.reply_text(
            "👋 *TaskForge* — Multi-Session Mode\n\n"
            "Tap a session to focus it, or create a new one.\n"
            f"Web UI: http://localhost:{WEB_PORT}",
            parse_mode="Markdown",
            reply_markup=_sessions_keyboard(),
        )
    else:
        await update.message.reply_text(
            "👋 *TaskForge* — Multi-Session Mode\n\n"
            "No sessions yet. Create your first session:\n"
            f"Web UI: http://localhost:{WEB_PORT}",
            parse_mode="Markdown",
            reply_markup=_new_session_keyboard(),
        )


@authorized_only
async def tg_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/menu — show sessions or controls for focused session."""
    fs = _focused_session()
    if fs:
        ai_label = fs["emoji"] + " " + (fs["ai"] or "Shell")
        await update.message.reply_text(
            f"*TaskForge — {fs['name']}*\n"
            f"AI: {ai_label}  ·  Status: {fs['status']}\n"
            f"📁 `{fs['cwd']}`",
            parse_mode="Markdown",
            reply_markup=_session_controls_keyboard(),
        )
    else:
        await update.message.reply_text(
            "*TaskForge — Sessions*\nNo session focused. Pick one:",
            parse_mode="Markdown",
            reply_markup=_sessions_keyboard(),
        )


@authorized_only
async def tg_launch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new shell session (quick shortcut)."""
    global _focused_id
    sess = _make_session(None)  # None = shell
    _focused_id = sess["id"]
    output = await asyncio.to_thread(sess["terminal"].drain, IDLE_TIMEOUT, 10.0, 5.0)
    await _push_state()
    await _push_message("system", f"Session created: {sess['name']} (via Telegram).",
                        source="telegram", session_id=sess["id"])
    if output:
        await _push_message("assistant", output, ai="shell", source="telegram",
                            session_id=sess["id"])
    await update.message.reply_text(
        f"✅ {sess['name']} started. Type to send shell commands:",
        reply_markup=_session_controls_keyboard(),
    )


@authorized_only
async def tg_claude(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create or focus a Claude Code session."""
    global _focused_id
    sess = _make_session("claude")
    _focused_id = sess["id"]
    await _push_state()
    await _push_message("system", f"{sess['name']} created (via Telegram).", source="telegram",
                        session_id=sess["id"])
    await update.message.reply_text(
        f"🤖 *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=_session_controls_keyboard(),
    )


@authorized_only
async def tg_codex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new Codex session (if plugin is loaded)."""
    global _focused_id
    if "codex" not in _integrations:
        await update.message.reply_text("Codex integration not loaded.")
        return
    sess = _make_session("codex")
    _focused_id = sess["id"]
    await _push_state()
    await update.message.reply_text(
        f"💻 *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=_session_controls_keyboard(),
    )


@authorized_only
async def tg_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new Gemini session (if plugin is loaded)."""
    global _focused_id
    if "gemini" not in _integrations:
        await update.message.reply_text("Gemini integration not loaded.")
        return
    sess = _make_session("gemini")
    _focused_id = sess["id"]
    await _push_state()
    await update.message.reply_text(
        f"✨ *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=_session_controls_keyboard(),
    )


@authorized_only
async def tg_stop_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the focused session's AI (switch to shell)."""
    sess = _focused_session()
    if not sess:
        await update.message.reply_text("No session focused.", reply_markup=_sessions_keyboard())
        return
    sess["ai"] = None
    sess["emoji"] = "🐚"
    sess["color"] = "#6b7280"
    await _push_state()
    await update.message.reply_text(
        f"🐚 {sess['name']} switched to Shell mode.",
        reply_markup=_session_controls_keyboard(),
    )


@authorized_only
async def tg_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sess = _focused_session()
    if sess:
        sess["claude_msgs"] = []
    await _push_message("system", "Claude history cleared (via Telegram).", source="telegram")
    await update.message.reply_text("Conversation history cleared.")


@authorized_only
async def tg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("Usage: /cmd <command>")
        return
    sess = _focused_session()
    if not sess or not sess["terminal"].is_alive():
        await update.message.reply_text("No active session terminal. Create a session first.")
        return
    await _push_message("user", f"/cmd {text}", source="telegram", session_id=sess["id"])
    sess["terminal"].write(text)
    output = await asyncio.to_thread(sess["terminal"].drain)
    output = output or "(no output)"
    await _push_message("assistant", output, ai="shell", source="telegram", session_id=sess["id"])
    await _tg_send_chunks(update, output)


@authorized_only
async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _sessions:
        await update.message.reply_text("No sessions. Use /start to create one.")
        return
    lines = ["*Active Sessions:*"]
    for sess in sorted(_sessions.values(), key=lambda s: s["last_used"], reverse=True):
        icon = _session_status_icon(sess)
        focused = " ← focused" if sess["id"] == _focused_id else ""
        lines.append(f"{icon} *{sess['name']}* [{sess['ai'] or 'shell'}]{focused}\n"
                     f"  📁 {sess['cwd']}")
    timeout_label = "unlimited" if CLAUDE_TIMEOUT == 0 else f"{int(CLAUDE_TIMEOUT)}s"
    lines.append(f"\n⏱ Timeout: {timeout_label}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                    reply_markup=_sessions_keyboard())


@authorized_only
async def tg_interrupt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sess = _focused_session()
    if not sess:
        await update.message.reply_text("No session focused.")
        return
    try:
        if sess["ai"]:
            # AI session — kill the subprocess
            _kill_session_proc(sess)
            sess["busy"]       = False
            sess["task_start"] = None
            await _push_thinking(False, session_id=sess["id"])
            await _push_state()
            await _push_message("system", "⏹ AI task interrupted (via Telegram).",
                                source="telegram", session_id=sess["id"])
            await update.message.reply_text("⏹ AI task interrupted.",
                                            reply_markup=_session_controls_keyboard())
        else:
            sess["terminal"].send_interrupt()
            await _push_message("system", "Ctrl+C sent (via Telegram).", source="telegram",
                                session_id=sess["id"])
            await update.message.reply_text("⏸ Ctrl+C sent.",
                                            reply_markup=_session_controls_keyboard())
    except RuntimeError as e:
        await update.message.reply_text(str(e))


@authorized_only
async def tg_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sess = _focused_session()
    if not sess:
        await update.message.reply_text("No session focused.", reply_markup=_sessions_keyboard())
        return
    _kill_session_proc(sess)          # kill AI subprocess immediately
    sess["terminal"].stop()
    sess["status"]    = "stopped"
    sess["busy"]      = False
    sess["task_start"] = None
    await _push_thinking(False, session_id=sess["id"])  # clear spinner on web NOW
    await _push_state()
    await _push_message("system", f"{sess['name']} stopped (via Telegram).", source="telegram",
                        session_id=sess["id"])
    await update.message.reply_text(
        f"🛑 {sess['name']} stopped.\nSessions:",
        reply_markup=_sessions_keyboard(),
    )


@authorized_only
async def tg_cwd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show or change the working directory of the focused session."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    sess = _focused_session()
    if not arg:
        cwd = sess["cwd"] if sess else _DEFAULT_CWD
        await update.message.reply_text(f"📁 Current directory:\n{cwd}")
        return
    ok = await _change_cwd(arg, source="telegram")
    if ok:
        sess = _focused_session()
        cwd = sess["cwd"] if sess else _DEFAULT_CWD
        await update.message.reply_text(f"📁 Working directory changed to:\n{cwd}")


@authorized_only
async def tg_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get or set the AI timeout: /timeout  or  /timeout <seconds>  or  /timeout 0 for unlimited"""
    global CLAUDE_TIMEOUT
    arg = (update.message.text or "").partition(" ")[2].strip()
    if not arg:
        limit_str = "unlimited (AI tool controls its own timeout)" if CLAUDE_TIMEOUT == 0 else f"{int(CLAUDE_TIMEOUT)}s"
        await update.message.reply_text(
            f"⏱ Current AI timeout: {limit_str}\n"
            f"Use /timeout <seconds> to set a hard cap, or /timeout 0 for unlimited."
        )
        return
    try:
        value = float(arg)
        if value < 0:
            await update.message.reply_text("❌ Use 0 for unlimited, or a positive number of seconds.")
            return
        if 0 < value < 10:
            await update.message.reply_text("❌ Minimum timeout is 10 seconds (or 0 for unlimited).")
            return
        CLAUDE_TIMEOUT = value
        _update_env("CLAUDE_TIMEOUT", str(int(value)))
        label = "unlimited" if value == 0 else f"{int(value)}s"
        await _push_message("system", f"⏱ AI timeout set to {label}", source="telegram")
        await update.message.reply_text(f"⏱ Timeout updated to {label} (saved to .env)")
    except ValueError:
        await update.message.reply_text("❌ Invalid value. Use seconds (e.g. /timeout 1800) or 0 for unlimited.")


@authorized_only
async def tg_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/schedule [list | add <cron5> <ai> <prompt> | delete <id> | on <id> | off <id>]"""
    text  = (update.message.text or "").strip()
    parts = text.split(None, 2)
    sub   = parts[1].strip().lower() if len(parts) > 1 else "list"
    rest  = parts[2].strip() if len(parts) > 2 else ""

    # ── list ─────────────────────────────────────────────────────────────────
    if sub in ("list", "ls", "") or not sub:
        if not _scheduled_tasks:
            await update.message.reply_text(
                "No scheduled tasks.\n"
                "Add one: /schedule add 0 9 * * * claude Review git diff"
            )
            return
        lines = ["*Scheduled Tasks:*"]
        for task in _scheduled_tasks.values():
            ico = "✅" if task["enabled"] else "⏸"
            nr  = datetime.fromtimestamp(task["next_run"]).strftime("%m/%d %H:%M") \
                  if task.get("next_run") else "—"
            lines.append(
                f"{ico} `{task['id']}` *{task['name']}*\n"
                f"  `{task['cron']}`  ·  {task['ai'] or 'shell'}  ·  next: {nr}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── add <cron5> <ai> <prompt> ─────────────────────────────────────────────
    if sub == "add":
        tokens = rest.split()
        if len(tokens) < 7:
            await update.message.reply_text(
                "Usage: /schedule add <cron 5 fields> <ai> <prompt>\n"
                "Example: /schedule add 0 9 * * * claude Review git diff today\n"
                "AI options: claude  shell  (or any integration key)"
            )
            return
        cron_expr = " ".join(tokens[:5])
        ai_raw    = tokens[5]
        prompt    = " ".join(tokens[6:])
        ai_key    = ai_raw if ai_raw in ("claude", *_integrations) else None

        if _next_cron_run(cron_expr) is None:
            if not _CRONITER_OK:
                await update.message.reply_text("❌ croniter not installed — run: pip install croniter")
            else:
                await update.message.reply_text(f"❌ Invalid cron: `{cron_expr}`", parse_mode="Markdown")
            return

        task = _make_sched_task(cron_expr, ai_key, prompt)
        _scheduled_tasks[task["id"]] = task
        _save_scheduled_tasks()
        nr = datetime.fromtimestamp(task["next_run"]).strftime("%Y-%m-%d %H:%M")
        await update.message.reply_text(
            f"✅ Scheduled *{task['name']}* (`{task['id']}`)\n"
            f"`{cron_expr}` · {ai_key or 'shell'}\n"
            f"Next run: {nr}",
            parse_mode="Markdown",
        )
        return

    # ── delete <id> ───────────────────────────────────────────────────────────
    if sub in ("delete", "del", "rm", "remove"):
        tid = rest.strip()
        if tid in _scheduled_tasks:
            name = _scheduled_tasks[tid]["name"]
            del _scheduled_tasks[tid]
            _save_scheduled_tasks()
            await update.message.reply_text(f"🗑️ Deleted: {name}")
        else:
            await update.message.reply_text(f"❌ Task not found: `{tid}`", parse_mode="Markdown")
        return

    # ── on / off <id> ─────────────────────────────────────────────────────────
    if sub in ("on", "off", "enable", "disable"):
        tid     = rest.strip()
        enable  = sub in ("on", "enable")
        if tid in _scheduled_tasks:
            _scheduled_tasks[tid]["enabled"] = enable
            if enable:
                _scheduled_tasks[tid]["next_run"] = _next_cron_run(_scheduled_tasks[tid]["cron"])
            _save_scheduled_tasks()
            icon = "✅" if enable else "⏸"
            state = "enabled" if enable else "paused"
            await update.message.reply_text(f"{icon} Task `{tid}` {state}.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Task not found: `{tid}`", parse_mode="Markdown")
        return

    # ── run <id> (manual trigger) ─────────────────────────────────────────────
    if sub in ("run", "trigger", "now"):
        tid = rest.strip()
        if tid in _scheduled_tasks:
            task = _scheduled_tasks[tid]
            await update.message.reply_text(f"▶️ Running *{task['name']}* now…", parse_mode="Markdown")
            asyncio.create_task(_run_scheduled_task(task))
        else:
            await update.message.reply_text(f"❌ Task not found: `{tid}`", parse_mode="Markdown")
        return

    await update.message.reply_text(
        "Subcommands:\n"
        "  /schedule list\n"
        "  /schedule add <cron5> <ai> <prompt>\n"
        "  /schedule delete <id>\n"
        "  /schedule on <id>  /  off <id>\n"
        "  /schedule run <id>   ← manual trigger"
    )


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
    start = arg if arg else _session_cwd()
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
    state = _tg_browse_state.get(user_id, {"path": _session_cwd(), "dirs": [], "page": 0})
    current_path = state["path"]
    dirs = state["dirs"]

    if data == "browse_cancel":
        _tg_browse_state.pop(user_id, None)
        fs = _focused_session()
        await query.edit_message_text(
            "Browse cancelled.",
            reply_markup=_session_controls_keyboard() if fs else _sessions_keyboard(),
        )

    elif data == "browse_select":
        _tg_browse_state.pop(user_id, None)
        ok = await _change_cwd(current_path, source="telegram")
        fs = _focused_session()
        if ok:
            await query.edit_message_text(
                f"✅ Working directory set to:\n`{current_path}`\n\nWhat would you like to do next?",
                parse_mode="Markdown",
                reply_markup=_session_controls_keyboard() if fs else _sessions_keyboard(),
            )
        else:
            await query.edit_message_text(
                f"❌ Could not set directory:\n{current_path}",
                reply_markup=_session_controls_keyboard() if fs else _sessions_keyboard(),
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
    creates a new session (restoring AI + CWD), injects the conversation
    context as a prefix, and replies with a summary + controls keyboard.
    """
    global _focused_id, _pending_tg_context

    # ── Resolve which log file to load ────────────────────────────────────────
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

    # ── Read the log — collect messages, last CWD, last AI ───────────────────
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
                last_ai = m.get("model")
            elif m.get("role") in ("user", "assistant"):
                messages.append(m)
        except Exception:
            pass

    if not messages:
        await message.reply_text(f"No conversation messages found in session {date_str}.")
        return

    # ── Fallback: load CWD/AI from last_state.json if log pre-dates records ──
    if not last_cwd or not last_ai:
        try:
            state_file = CHAT_LOG_DIR / "last_state.json"
            if state_file.exists():
                st = json.loads(state_file.read_text(encoding="utf-8"))
                # last_state.json now stores sessions dict; try to pick the
                # first session's data as a best-effort fallback
                sessions_saved = st.get("sessions", {})
                if sessions_saved:
                    first = next(iter(sessions_saved.values()))
                    if not last_cwd:
                        last_cwd = first.get("cwd") or None
                    if not last_ai:
                        last_ai = first.get("ai") or None
                # Legacy format fallback (pre-multi-session last_state.json)
                if not last_cwd:
                    last_cwd = st.get("cwd") or None
                if not last_ai:
                    last_ai = st.get("ai") or None
        except Exception:
            pass

    # ── Build context string from last 10 exchanges ───────────────────────────
    turns = messages[-10:]
    lines_ctx = []
    for m in turns:
        role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
        body = (m.get("content") or "")[:300]
        if len(m.get("content", "")) > 300:
            body += "…"
        lines_ctx.append(f"{role}: {body}")

    label = _load_chat_names().get(date_str) or date_str
    context_prefix = (
        f"[Previous conversation — {label}]\n"
        + "\n".join(lines_ctx)
        + "\n[End context]\n\n"
    )

    # ── Create a new session for the resumed work ─────────────────────────────
    valid_ai = last_ai and (last_ai == "claude" or last_ai in _integrations)
    ai_to_use = last_ai if valid_ai else None
    sess = _make_session(ai_to_use)
    _focused_id = sess["id"]

    # Restore CWD inside the new session
    cwd_note = ""
    if last_cwd:
        cwd_ok = await _change_cwd(last_cwd, source="telegram", session_id=sess["id"])
        cwd_note = (
            f"\n📁 Directory restored: `{last_cwd}`"
            if cwd_ok
            else f"\n⚠️ Could not restore directory: `{last_cwd}`"
        )

    # Inject the context prefix into the next message sent to this session
    _pending_tg_context = context_prefix

    await _push_state()

    if valid_ai:
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
        reply_markup=_session_controls_keyboard() if valid_ai else _sessions_keyboard(),
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
    global _pending_tg_context, _focused_id
    text = (update.message.text or "").strip()
    low = text.lower()

    # ── Natural language shortcuts ──────────────────────────────────────────
    if low in ("menu", "help", "options", "?"):
        await tg_menu.__wrapped__(update, context)
        return
    if low in ("sessions", "list sessions", "show sessions"):
        await tg_status.__wrapped__(update, context)
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
    if low in ("new session", "create session", "new claude", "start claude", "use claude",
               "claude code"):
        await tg_claude.__wrapped__(update, context)
        return
    # Dynamic NL shortcuts for all loaded integrations
    for _ikey, _iinfo in _integrations.items():
        _n = _ikey.lower()
        if any(low.startswith(p) for p in (f"new {_n}", f"start {_n}", f"use {_n}",
                                            f"switch to {_n}")):
            if _ikey in _integrations:
                sess = _make_session(_ikey)
                _focused_id = sess["id"]
                await _push_state()
                await update.message.reply_text(
                    f"{_iinfo['emoji']} *{sess['name']}* created.\nJust type your task.",
                    parse_mode="Markdown",
                    reply_markup=_session_controls_keyboard(),
                )
                return
    if low in ("shell", "shell mode", "new shell"):
        await tg_launch.__wrapped__(update, context)
        return

    # ── No focused session → show session list / new session picker ──────────
    if not _focused_id or _focused_id not in _sessions:
        if _sessions:
            await update.message.reply_text(
                "👋 Tap a session to focus it, or create a new one:",
                reply_markup=_sessions_keyboard(),
            )
        else:
            await update.message.reply_text(
                "👋 No sessions yet. Create your first one:",
                reply_markup=_new_session_keyboard(),
            )
        return

    sess = _sessions.get(_focused_id)
    if sess and sess["status"] == "stopped":
        await update.message.reply_text(
            f"⏹ *{sess['name']}* is stopped. Resume it or switch session:",
            parse_mode="Markdown",
            reply_markup=_sessions_keyboard(),
        )
        return

    # ── Focused session is active → forward message ──────────────────────────
    if _pending_tg_context:
        text = _pending_tg_context + text
        _pending_tg_context = None
        await update.message.reply_text("📎 Context injected. Thinking…")
    else:
        fs = _focused_session()
        label = f"{fs['emoji']} {fs['name']}" if fs else "session"
        await update.message.reply_text(f"Thinking… [{label}]")

    # Fire-and-forget: run the AI task in the background so the Telegram
    # handler returns immediately and new updates (button clicks, commands,
    # new-session requests) can be processed in parallel.
    async def _tg_fire(
        _text: str = text,
        _update: Update = update,
    ) -> None:
        try:
            response = await _process_message(_text, source="telegram")
            await _tg_send_chunks(_update, response,
                                  reply_markup=_session_controls_keyboard())
        except Exception as exc:
            logger.warning("tg_fire error: %s", exc)
            try:
                await _update.message.reply_text(f"⚠️ Error: {exc}")
            except Exception:
                pass

    asyncio.create_task(_tg_fire())


# ---------------------------------------------------------------------------
# Inline action button callback handler
# ---------------------------------------------------------------------------

async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all ms:* and action:* inline keyboard button presses."""
    global _focused_id
    query = update.callback_query
    user_id = query.from_user.id
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.")
        return
    await query.answer()

    data = query.data  # e.g. "ms:focus:s1", "ms:new_ai:claude:", "action:history"

    # ── ms: multi-session actions ─────────────────────────────────────────────
    if data.startswith("ms:"):
        parts = data.split(":")  # ["ms", verb, arg1?, arg2?]
        verb  = parts[1] if len(parts) > 1 else ""

        if verb == "list":
            txt  = "📋 *Sessions* — tap to focus:" if _sessions else "No sessions yet."
            await query.edit_message_text(txt, parse_mode="Markdown",
                                          reply_markup=_sessions_keyboard())

        elif verb == "new":
            await query.edit_message_text("Choose AI for new session:",
                                          reply_markup=_new_session_keyboard())

        elif verb == "new_ai":
            # ms:new_ai:{ai}:{resume_sid}
            ai_key     = parts[2] if len(parts) > 2 else "shell"
            resume_sid = parts[3] if len(parts) > 3 else ""
            if ai_key == "shell":
                ai_key = None
            if resume_sid and resume_sid in _sessions:
                # Resume a stopped session with a (possibly different) AI
                sess = _sessions[resume_sid]
                sess["ai"]     = ai_key
                sess["status"] = "running"
                sess["claude_msgs"] = []
                if ai_key == "claude":
                    sess["emoji"] = "🤖"; sess["color"] = "#f59e0b"
                elif ai_key and ai_key in _integrations:
                    info = _integrations[ai_key]
                    sess["emoji"] = info["emoji"]; sess["color"] = info["color"]
                else:
                    sess["emoji"] = "🐚"; sess["color"] = "#6b7280"
                # Restart terminal
                sess["terminal"].stop()
                t = TerminalSession()
                if ai_key is None:
                    # Only shell sessions need cmd.exe immediately
                    t.launch()
                sess["terminal"] = t
                _focused_id = resume_sid
            else:
                # Create brand-new session
                sess = _make_session(ai_key)
                _focused_id = sess["id"]
            await _push_state()
            label = f"{sess['emoji']} *{sess['name']}*"
            await _push_message("system", f"Session ready: {sess['name']} (via Telegram).",
                                source="telegram", session_id=sess["id"])
            await query.edit_message_text(
                f"{label} is ready.\nJust type your task.",
                parse_mode="Markdown",
                reply_markup=_session_controls_keyboard(),
            )

        elif verb == "focus":
            sid = parts[2] if len(parts) > 2 else ""
            if sid in _sessions:
                sess = _sessions[sid]
                if sess["status"] == "stopped":
                    await query.edit_message_text(
                        f"⏹ *{sess['name']}* is stopped. Resume as:",
                        parse_mode="Markdown",
                        reply_markup=_new_session_keyboard(resume_sid=sid),
                    )
                else:
                    _focused_id = sid
                    fs = _sessions[sid]
                    ai_lbl = fs["emoji"] + " " + (fs["ai"] or "Shell")
                    await query.edit_message_text(
                        f"✅ *{fs['name']}* focused\n"
                        f"AI: {ai_lbl}  ·  📁 {pathlib.Path(fs['cwd']).name or fs['cwd']}\n\n"
                        f"Type your message to send to this session:",
                        parse_mode="Markdown",
                        reply_markup=_session_controls_keyboard(),
                    )
            else:
                await query.edit_message_text("Session not found.", reply_markup=_sessions_keyboard())

        elif verb == "stop":
            sess = _focused_session()
            if sess:
                sess["terminal"].stop()
                sess["status"] = "stopped"
                await _push_state()
                await _push_message("system", f"{sess['name']} stopped (via Telegram).",
                                    source="telegram", session_id=sess["id"])
                await query.edit_message_text(
                    f"⏹ *{sess['name']}* stopped. Sessions:",
                    parse_mode="Markdown",
                    reply_markup=_sessions_keyboard(),
                )
            else:
                await query.edit_message_text("No focused session.", reply_markup=_sessions_keyboard())

        elif verb == "delete":
            sess = _focused_session()
            if sess:
                sess["terminal"].stop()
                sid = sess["id"]
                name = sess["name"]
                del _sessions[sid]
                _focused_id = (max(_sessions, key=lambda k: _sessions[k]["last_used"],
                                   default=None) if _sessions else None)
                await _push_state()
                await query.edit_message_text(
                    f"🗑 *{name}* deleted. Sessions:",
                    parse_mode="Markdown",
                    reply_markup=_sessions_keyboard(),
                )
            else:
                await query.edit_message_text("No focused session.", reply_markup=_sessions_keyboard())

        elif verb == "switch":
            await query.edit_message_text("Switch AI for this session — pick one:",
                                          reply_markup=_new_session_keyboard(
                                              resume_sid=_focused_id or ""))

        elif verb == "interrupt":
            sess = _focused_session()
            if sess:
                try:
                    sess["terminal"].send_interrupt()
                    await _push_message("system", "Ctrl+C sent (via Telegram).",
                                        source="telegram", session_id=sess["id"])
                    await query.edit_message_text("⏸ Interrupted.",
                                                  reply_markup=_session_controls_keyboard())
                except RuntimeError as e:
                    await query.edit_message_text(str(e))
            else:
                await query.edit_message_text("No focused session.", reply_markup=_sessions_keyboard())

        elif verb == "browse":
            if query.message:
                cwd = _focused_session()["cwd"] if _focused_session() else _DEFAULT_CWD
                await _show_browse(query.message, query.from_user.id, cwd, edit=False, page=0)

        return  # end of ms: handling

    # ── action: legacy / shared actions ──────────────────────────────────────
    action = data.split(":", 1)[1] if ":" in data else data

    if action == "history":
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
        if query.message:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=history_text[:3800],
                reply_markup=_sessions_keyboard(),
            )

    elif action == "browse":
        if query.message:
            cwd = _focused_session()["cwd"] if _focused_session() else _DEFAULT_CWD
            await _show_browse(query.message, query.from_user.id, cwd, edit=False, page=0)

    elif action == "resume":
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
<title>TaskForge</title>
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
#app{height:100vh;display:flex;flex-direction:row;overflow:hidden}

/* ── Left Sidebar ── */
#left-sidebar{
  width:260px;flex-shrink:0;display:flex;flex-direction:column;
  background:var(--bg);border-right:1px solid var(--border);overflow:hidden}
.sb-search{padding:10px 12px;flex-shrink:0;border-bottom:1px solid var(--border)}
.sb-search input{
  width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:6px;
  padding:7px 10px 7px 30px;font-size:12px;color:var(--text);outline:none;box-sizing:border-box;
  font-family:inherit;transition:border-color .15s}
.sb-search input:focus{border-color:#3a3a3a}
.sb-search{position:relative}
.sb-search svg{position:absolute;left:22px;top:50%;transform:translateY(-50%);pointer-events:none;color:var(--muted)}
.sb-tabs{display:flex;flex-shrink:0;border-bottom:1px solid var(--border)}
.sb-tab{
  flex:1;padding:8px 0;font-size:11px;font-weight:600;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);background:none;border:none;border-bottom:2px solid transparent;
  cursor:pointer;transition:all .15s;text-align:center;font-family:inherit}
.sb-tab:hover{color:var(--dim)}
.sb-tab.active{color:var(--text);border-bottom-color:var(--claude)}
.sb-panel{flex:1;overflow-y:auto;min-height:0;display:none}
.sb-panel.active{display:block}
.sb-panel::-webkit-scrollbar{width:4px}
.sb-panel::-webkit-scrollbar-track{background:transparent}
.sb-panel::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.sb-empty{padding:32px 16px;text-align:center;color:var(--muted);font-size:12px}
.sb-hcard{
  padding:9px 14px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .12s}
.sb-hcard:hover{background:var(--surface2)}
.sb-hcard-name{
  font-size:12px;font-weight:600;color:var(--text);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}
.sb-hcard-meta{font-size:10px;color:var(--muted);display:flex;gap:6px;align-items:center}
.sb-hcard-ai{
  font-size:9px;padding:1px 5px;border-radius:3px;font-weight:500;
  background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);color:var(--muted)}
.sb-sched-item{padding:9px 14px;border-bottom:1px solid var(--border);font-size:12px}
.sb-sched-top{display:flex;align-items:center;gap:6px;margin-bottom:3px}
.sb-sched-name{font-weight:600;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb-sched-prompt{color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:3px}
.sb-sched-meta{font-size:10px;color:var(--muted);margin-bottom:5px}
.sb-sched-btns{display:flex;gap:4px}
.sb-sched-btns button{
  flex:1;padding:2px;font-size:10px;background:var(--surface);border:1px solid var(--border);
  cursor:pointer;border-radius:3px;color:var(--dim);font-family:inherit;transition:all .12s}
.sb-sched-btns button:hover{background:var(--surface2);color:var(--text)}
.sb-add-form{padding:10px 14px;border-top:1px solid var(--border);flex-shrink:0}
.sb-add-form summary{cursor:pointer;font-size:11px;color:var(--muted);user-select:none}
.sb-add-form input,.sb-add-form textarea,.sb-add-form select{
  width:100%;background:var(--surface2);color:var(--text);border:1px solid var(--border);
  border-radius:5px;padding:5px 8px;font-size:12px;outline:none;font-family:inherit;box-sizing:border-box;
  margin-top:6px}
.sb-add-form textarea{resize:vertical}
.sb-add-form input:focus,.sb-add-form textarea:focus{border-color:var(--claude)}
.sb-add-form button.sb-add-btn{
  margin-top:8px;padding:5px 14px;background:var(--claude);color:#000;border:none;
  border-radius:5px;cursor:pointer;font-weight:600;font-size:12px;font-family:inherit;float:right}

/* ── Center Panel ── */
#center-panel{flex:1;display:flex;flex-direction:column;min-width:0;
  border-right:1px solid var(--border)}

/* ── Right Sidebar ── */
#right-sidebar{
  width:280px;flex-shrink:0;display:flex;flex-direction:column;
  background:var(--bg);overflow:hidden}
.rs-header{
  padding:12px 14px;font-size:11px;font-weight:600;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.rs-list{flex:1;overflow-y:auto;min-height:0}
.rs-list::-webkit-scrollbar{width:4px}
.rs-list::-webkit-scrollbar-track{background:transparent}
.rs-list::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.rs-item{
  padding:10px 14px;border-bottom:1px solid var(--border);display:flex;
  align-items:flex-start;gap:10px;cursor:pointer;transition:background .12s}
.rs-item:hover{background:var(--surface2)}
.rs-item.focused{background:var(--surface2)}
.rs-dot{
  width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px;transition:background .3s}
.rs-dot.idle{background:var(--codex)}
.rs-dot.busy{background:var(--claude);animation:sess-pulse 1.2s ease-in-out infinite}
.rs-dot.stopped{background:#ef4444}
.rs-info{flex:1;min-width:0}
.rs-name{
  font-size:12px;font-weight:600;color:var(--text);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;margin-bottom:2px}
.rs-meta{font-size:10px;color:var(--muted);display:flex;align-items:center;gap:6px}
.rs-ai-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
.rs-timer{font-family:'SF Mono','Fira Code','Consolas',monospace;font-size:10px}
.rs-actions{display:none;gap:4px;flex-shrink:0;margin-top:2px}
.rs-item:hover .rs-actions{display:flex}
.rs-act{
  background:var(--surface);border:1px solid var(--border);color:var(--muted);
  border-radius:4px;padding:2px 7px;font-size:10px;cursor:pointer;transition:all .12s;
  font-family:inherit}
.rs-act:hover{background:var(--surface2);color:var(--text);border-color:#3a3a3a}
.rs-empty{padding:32px 14px;text-align:center;color:var(--muted);font-size:12px}
.rs-new-btn{
  flex-shrink:0;margin:10px 14px;padding:8px;border-radius:7px;border:1px dashed var(--border);
  background:none;color:var(--dim);font-size:12px;cursor:pointer;font-family:inherit;
  transition:all .15s;text-align:center}
.rs-new-btn:hover{border-color:#3a3a3a;color:var(--text);background:var(--surface)}

/* ── Mobile sidebar toggles ── */
.sb-toggle{
  background:none;border:none;color:var(--dim);cursor:pointer;padding:5px;
  border-radius:6px;display:none;align-items:center;transition:color .15s;line-height:1}
.sb-toggle:hover{color:var(--text)}
@media(max-width:900px){
  #left-sidebar,#right-sidebar{display:none;position:fixed;top:0;height:100vh;z-index:95;
    box-shadow:0 0 40px rgba(0,0,0,.6)}
  #left-sidebar{left:0}
  #right-sidebar{right:0}
  #left-sidebar.open,#right-sidebar.open{display:flex}
  #center-panel{border-right:none}
  .sb-toggle{display:flex}
  .sb-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:94}
  .sb-overlay.open{display:block}
}

/* ── Header ── */
header{
  padding:13px 20px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  background:var(--surface);flex-shrink:0}
.logo{font-size:15px;font-weight:700;letter-spacing:-.3px;color:var(--text)}
.logo em{color:#818cf8;font-style:normal}
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
  min-width:195px;z-index:50;overflow-y:auto;
  max-height:calc(100vh - 120px);
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
.ai-menu-item.session-focused{color:var(--text)!important;background:var(--surface2)}
.ai-menu-item.session-busy{opacity:.9}
@keyframes sess-pulse{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes spin{to{transform:rotate(360deg)}}
.sess-busy-dot{
  display:inline-block;width:6px;height:6px;border-radius:50%;
  background:var(--accent,#f59e0b);margin-left:6px;vertical-align:middle;
  animation:sess-pulse 1.2s ease-in-out infinite}
.session-badge{
  font-size:10px;color:var(--muted);padding:1px 6px 1px 0;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0}

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

/* ── History viewing/resume banner ── */
/* History viewing / resume banner — sits between dir-bar and messages */
#hist-banner{
  display:none;align-items:center;gap:10px;flex-shrink:0;
  padding:0 18px;height:36px;font-size:12px;
  border-bottom:1px solid var(--border);transition:background .2s}
#hist-banner.on{display:flex}
#hist-banner.view{background:rgba(99,102,241,.08);border-color:rgba(99,102,241,.25);color:#a5b4fc}
#hist-banner.resume{background:rgba(34,197,94,.07);border-color:rgba(34,197,94,.25);color:var(--codex)}
#hist-banner-icon{font-size:14px;flex-shrink:0}
#hist-banner-date{flex:1;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hist-live-btn{
  padding:3px 11px;border-radius:5px;font-size:11px;cursor:pointer;
  font-family:inherit;transition:all .15s;font-weight:500;flex-shrink:0;
  background:transparent;border:1px solid currentColor;color:inherit}
.hist-live-btn:hover{opacity:.75}

/* ── Schedule modal rows ── */
.sched-row{
  padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px}
.sched-row:last-child{border-bottom:none}
.sched-meta{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px}
.sched-prompt{color:var(--muted);font-size:12px;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sched-times{color:var(--muted);font-size:11px;margin-bottom:5px}
.sched-actions{display:flex;gap:6px}
.sched-actions button{
  background:var(--surface2);border:1px solid var(--border);color:var(--text);
  border-radius:5px;padding:2px 8px;cursor:pointer;font-size:12px}
.sched-actions button:hover{background:var(--border)}
.sched-ai-badge{
  font-size:10px;padding:1px 6px;border-radius:9px;background:var(--surface2);
  border:1px solid var(--border);color:var(--muted);text-transform:uppercase}
.sched-ai-badge.claude{background:#f59e0b22;border-color:#f59e0b55;color:#f59e0b}
#sched-modal .modal-box{padding:0 0 16px}
#sched-modal .modal-header{padding:14px 18px}
#sched-modal details>summary{padding:0 16px}
#sched-modal details>div{padding:0 16px}
#sched-modal input,#sched-modal textarea,#sched-modal select{
  background:var(--surface2);color:var(--text);border:1px solid var(--border);
  border-radius:6px;padding:6px 9px;font-size:13px;outline:none}
#sched-modal input:focus,#sched-modal textarea:focus{border-color:var(--accent,#f59e0b)}
/* ── Shared modal chrome ── */
.modal-overlay{
  display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);
  z-index:100;align-items:center;justify-content:center;backdrop-filter:blur(2px)}
.modal-overlay.open{display:flex}
.modal-box{
  background:var(--surface);border:1px solid var(--border);border-radius:14px;
  width:min(420px,92vw);max-height:74vh;display:flex;flex-direction:column;overflow:hidden;
  box-shadow:0 24px 64px rgba(0,0,0,.5)}
.modal-header{
  padding:15px 18px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0;
  background:var(--surface2)}
.modal-title{font-size:14px;font-weight:700;letter-spacing:.01em}
.modal-close{
  background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;
  padding:0 4px;line-height:1;transition:color .15s;border-radius:4px}
.modal-close:hover{color:var(--text);background:var(--surface)}
.modal-body{overflow-y:auto;padding:8px 0;flex:1}
.modal-empty{
  padding:48px 24px;text-align:center;color:var(--muted);font-size:13px;
  line-height:1.7;display:flex;flex-direction:column;align-items:center;gap:8px}
.modal-empty svg{opacity:.3;margin-bottom:4px}

/* ── History search bar ── */
.hist-search{
  padding:10px 14px;border-bottom:1px solid var(--border);flex-shrink:0;
  background:var(--surface)}
.hist-search input{
  width:100%;background:var(--bg);border:1px solid var(--border);border-radius:7px;
  padding:6px 10px;font-size:12px;color:var(--text);font-family:inherit;
  outline:none;box-sizing:border-box;transition:border-color .15s}
.hist-search input:focus{border-color:#3a3a3a}

/* ── History session cards ── */
.hcard{
  display:flex;align-items:stretch;cursor:pointer;
  border-bottom:1px solid var(--border);transition:background .12s;
  position:relative}
.hcard:last-child{border-bottom:none}
.hcard:hover{background:var(--surface2)}
.hcard:hover .hcard-del{opacity:1}
.hcard-accent{
  width:3px;flex-shrink:0;border-radius:0}
.hcard-body{
  flex:1;padding:11px 14px 10px;min-width:0;overflow:hidden}
.hcard-top{
  display:flex;align-items:center;gap:8px;margin-bottom:3px}
.hcard-name{
  font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
.hcard-ai-badge{
  font-size:10px;padding:1px 6px;border-radius:4px;flex-shrink:0;
  font-weight:500;opacity:.85;background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.1);color:var(--muted)}
.hcard-meta{
  font-size:11px;color:var(--muted);margin-bottom:5px;display:flex;
  align-items:center;gap:6px}
.hcard-preview{
  font-size:12px;color:var(--dim);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;line-height:1.4;font-style:italic}
.hcard-actions{
  display:none;align-items:center;gap:6px;padding:8px 14px 10px;
  background:var(--bg);border-bottom:1px solid var(--border)}
.hcard-actions.open{display:flex}
.hcard-del{
  position:absolute;right:12px;top:12px;background:none;border:none;
  color:var(--muted);cursor:pointer;font-size:13px;padding:3px 5px;
  border-radius:4px;transition:all .12s;opacity:0}
.hcard-del:hover{color:#ef4444;background:rgba(239,68,68,.1)}
.hact{
  padding:4px 12px;border-radius:6px;border:1px solid var(--border);
  background:transparent;color:var(--dim);font-size:12px;cursor:pointer;
  font-family:inherit;transition:all .15s;display:flex;align-items:center;gap:4px}
.hact:hover{color:var(--text);border-color:#4a4a4a;background:var(--surface)}
.hact.primary{
  border-color:rgba(99,102,241,.5);color:#818cf8}
.hact.primary:hover{background:rgba(99,102,241,.1);border-color:#818cf8}
.hact.resume{
  border-color:rgba(34,197,94,.4);color:var(--codex)}
.hact.resume:hover{background:rgba(34,197,94,.08);border-color:var(--codex)}

/* ── Rename inline input ── */
.sess-rename-input{
  font-size:13px;font-weight:600;background:var(--bg);border:1px solid var(--codex);
  border-radius:5px;padding:2px 7px;color:var(--text);font-family:inherit;
  width:100%;box-sizing:border-box;outline:none}

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

<!-- ── Left Sidebar ── -->
<div id="left-sidebar">
  <div class="sb-search">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input id="sb-search-inp" placeholder="Search sessions…" oninput="filterSidebarHistory(this.value)" autocomplete="off">
  </div>
  <div class="sb-tabs">
    <button class="sb-tab active" onclick="switchSbTab('history',this)">History</button>
    <button class="sb-tab" onclick="switchSbTab('scheduled',this)">Scheduled</button>
  </div>
  <div class="sb-panel active" id="sb-panel-history">
    <div class="sb-empty">Loading…</div>
  </div>
  <div class="sb-panel" id="sb-panel-scheduled">
    <div id="sb-sched-list"><div class="sb-empty">Loading…</div></div>
    <details class="sb-add-form">
      <summary>+ Add scheduled task</summary>
      <input id="sb-sched-cron" placeholder="Cron  e.g. 0 9 * * *">
      <select id="sb-sched-ai">
        <option value="claude">Claude Code</option>
        <option value="">Shell</option>
      </select>
      <textarea id="sb-sched-prompt" rows="2" placeholder="Prompt to run…"></textarea>
      <button class="sb-add-btn" onclick="sbSchedAdd()">Schedule</button>
    </details>
  </div>
</div>

<!-- ── Sidebar overlay (mobile) ── -->
<div class="sb-overlay" id="sb-overlay" onclick="closeSidebars()"></div>

<!-- ── Center Panel ── -->
<div id="center-panel">

<header>
  <div class="logo">⚡ Task<em>Forge</em></div>
  <div class="header-right">
    <button class="sb-toggle" id="toggle-left" onclick="toggleLeft()" title="History & Scheduled">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
    </button>
    <button class="sb-toggle" id="toggle-right" onclick="toggleRight()" title="Sessions">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/></svg>
    </button>
    <!-- Schedule & History buttons removed — now in left sidebar -->
    <div id="conn" title="WebSocket status"></div>
  </div>
</header>

<!-- ── Schedules modal ────────────────────────────────────────────────────── -->
<div id="sched-modal" class="modal-overlay" onclick="if(event.target===this)closeSchedules()" style="display:none">
  <div class="modal-box" style="max-width:600px">
    <div class="modal-header">
      <span>⏰ Scheduled Tasks</span>
      <button class="modal-close" onclick="closeSchedules()">✕</button>
    </div>
    <div id="sched-list" style="max-height:320px;overflow-y:auto;margin-bottom:12px"></div>
    <details id="sched-add-details" style="margin-top:8px">
      <summary style="cursor:pointer;font-size:13px;color:var(--muted);padding:4px 0">
        + Add scheduled task
      </summary>
      <div style="display:flex;flex-direction:column;gap:8px;margin-top:10px">
        <input id="sched-cron"   placeholder="Cron expression  e.g.  0 9 * * *" style="width:100%">
        <select id="sched-ai" style="width:100%;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 8px">
          <option value="claude">Claude Code</option>
          <option value="">Shell</option>
        </select>
        <textarea id="sched-prompt" rows="3" placeholder="Prompt to run (e.g. Review git diff and summarise changes)" style="width:100%;resize:vertical"></textarea>
        <button onclick="schedAdd()" style="align-self:flex-end;padding:6px 18px;background:var(--accent,#f59e0b);color:#000;border:none;border-radius:6px;cursor:pointer;font-weight:600">Schedule</button>
      </div>
    </details>
  </div>
</div>

<div class="dir-bar">
  <span class="dir-icon">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
    </svg>
  </span>
  <span id="session-badge" class="session-badge" title="Focused session"></span>
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
  <span id="hist-banner-icon">📖</span>
  <span id="hist-banner-date"></span>
  <button class="hist-live-btn" onclick="returnToLive()">↩ Back to live</button>
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

  <!-- Sessions + AI dropdown menu — sessions injected dynamically by applyState(); integrations by loadIntegrations() -->
  <div class="ai-menu" id="ai-menu">
    <div class="ai-menu-section">Active Sessions</div>
    <div id="ai-menu-sessions"><!-- filled by applyState() --></div>
    <div class="ai-menu-divider"></div>
    <div class="ai-menu-section">New Session</div>
    <button class="ai-menu-item" onclick="cmd('new_session:claude');closeAiMenu()">
      <span class="menu-dot claude"></span>New: Claude Code</button>
    <!-- integration "New: …" buttons inserted here by loadIntegrations() -->
    <button class="ai-menu-item" id="shell-mode-btn" onclick="cmd('new_session:');closeAiMenu()">
      <span class="menu-dot shell"></span>New: Shell</button>
    <div class="ai-menu-divider"></div>
    <div class="ai-menu-section">Focused Session</div>
    <button class="ai-menu-item" onclick="cmd('interrupt');closeAiMenu()">⏸ Cancel Task</button>
    <button class="ai-menu-item" onclick="if(confirm('Delete this session?'))cmd('delete_session');closeAiMenu()">🗑 Delete Session</button>
    <button class="ai-menu-item" onclick="cmd('clear');closeAiMenu()">↺ Clear Chat</button>
  </div>

  <textarea id="inp" placeholder="Type a message…  (Enter to send, Shift+Enter for newline)" rows="1"></textarea>
  <button id="send" onclick="send()">Send</button>
</div>

<!-- History modal -->
<div class="modal-overlay" id="hist-modal" onclick="if(event.target===this)closeHistory()">
  <div class="modal-box" style="width:min(540px,94vw)">
    <div class="modal-header">
      <span class="modal-title">Session History</span>
      <button class="modal-close" onclick="closeHistory()">✕</button>
    </div>
    <div class="hist-search">
      <input id="hist-search-inp" placeholder="Search sessions…" oninput="filterHistory(this.value)" autocomplete="off">
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

</div><!-- /center-panel -->

<!-- ── Right Sidebar: Session Dashboard ── -->
<div id="right-sidebar">
  <div class="rs-header">
    <span>Active Sessions</span>
    <span id="rs-count" style="font-size:10px;color:var(--dim);font-weight:400;text-transform:none;letter-spacing:0"></span>
  </div>
  <div class="rs-list" id="rs-list">
    <div class="rs-empty">No sessions yet</div>
  </div>
  <button class="rs-new-btn" onclick="toggleAiMenu(event)">+ New Session</button>
</div>

</div><!-- /app -->
<script>
const AI_LABEL = {claude:'Claude Code',shell:'Shell'};
let ws = null, activeAi = null, _viewingHistory = false, _liveHistory = [], _pendingContext = '';
let _sessNames = {};
// Multi-session state
let _sessions = [], _focusedId = null, _focusedAi = null;
// Sidebar state
let _sbHistSessions = [], _sbSchedTasks = [], _sessionTimers = {}, _integrationKeys = {};
const AI_COLOR = {claude:'var(--claude)',gemini:'var(--gemini)',codex:'var(--codex)',shell:'var(--shell)'};

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
      // Update label map + integration registry
      AI_LABEL[key] = name;
      _integrationKeys[key] = name;
      AI_COLOR[key] = 'var(--' + key + ')';
      // Inject "New Session: …" button before Shell mode
      const btn = document.createElement('button');
      btn.className = 'ai-menu-item';
      btn.dataset.newAi = key;
      btn.innerHTML = `<span class="menu-dot ${key}"></span>New: ${escHtml(name)}`;
      btn.onclick = () => { cmd('new_session:'+key); closeAiMenu(); };
      shellBtn.parentNode.insertBefore(btn, shellBtn);
    }
    const styleEl = document.createElement('style');
    styleEl.textContent = css;
    document.head.appendChild(styleEl);
    _sbSchedPopulateAi();
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
    else if(d.type==='thinking') setThinking(d.active, d.ai, d.session_id);
    else if(d.type==='cwd') applyCwd(d.path);
    else if(d.type==='schedule_list') renderSchedules(d.tasks);
  };
}

function applyState(s){
  // Multi-session state format: { sessions, focused_id, focused_ai, focused_cwd, focused_status }
  // Also support legacy format: { active_ai, cwd }
  if(s.sessions !== undefined){
    _sessions = s.sessions || [];
    _focusedId = s.focused_id || null;
    _focusedAi = s.focused_ai || null;
    activeAi = _focusedAi;
    // Update sessions list in the dropdown
    const sessContainer = document.getElementById('ai-menu-sessions');
    if(sessContainer){
      if(!_sessions.length){
        sessContainer.innerHTML = '<div style="padding:7px 13px;font-size:12px;color:var(--muted)">No active sessions</div>';
      } else {
        sessContainer.innerHTML = _sessions.map(sess => {
          const isFocused = sess.id === _focusedId;
          const icon = sess.status === 'stopped' ? '🔴' : sess.busy ? '🟡' : '🟢';
          const busyTag = sess.busy
            ? `<span class="sess-busy-dot" title="Working…"></span>`
            : '';
          const folder = sess.cwd ? sess.cwd.split(/[/\\]/).pop() || sess.cwd : '';
          return `<button class="ai-menu-item${isFocused ? ' session-focused' : ''}${sess.busy ? ' session-busy' : ''}"
            onclick="cmd('focus:${sess.id}');closeAiMenu()"
            style="${isFocused ? 'color:var(--text);background:var(--surface2);' : ''}">
            ${icon} ${escHtml(sess.name)}${isFocused ? ' ✓' : ''}${busyTag}
            <span style="margin-left:auto;font-size:10px;color:var(--muted)">${escHtml(folder)}</span>
          </button>`;
        }).join('');
      }
    }
    // Update the focused session display
    const focusedSess = _sessions.find(s => s.id === _focusedId);
    const picker = document.getElementById('ai-picker');
    const badge = document.getElementById('session-badge');
    if(focusedSess){
      const aiKey = focusedSess.ai || 'shell';
      document.getElementById('dot').className = 'dot ' + aiKey;
      document.getElementById('ai-label').textContent = focusedSess.emoji + ' ' + focusedSess.name;
      picker.className = 'ai-picker' + (focusedSess.ai ? ' active-' + aiKey : '');
      if(badge){
        const busyCount = _sessions.filter(s => s.busy).length;
        if(_sessions.length > 1 && busyCount > 0)
          badge.textContent = `${busyCount}/${_sessions.length} running · `;
        else if(_sessions.length > 1)
          badge.textContent = `${_sessions.length} sessions · `;
        else
          badge.textContent = '';
      }
    } else {
      document.getElementById('dot').className = 'dot';
      document.getElementById('ai-label').textContent = 'No session';
      picker.className = 'ai-picker';
      if(badge) badge.textContent = '';
    }
    if(s.focused_cwd) applyCwd(s.focused_cwd);
    // After focus may have changed, update the thinking indicator so it always
    // reflects the currently focused session (not whatever was thinking before).
    _refreshThinkingUI();
    // Update right sidebar session dashboard
    updateRightSidebar(_sessions, _focusedId);
  } else {
    // Legacy format
    activeAi = s.active_ai;
    const key = activeAi || 'shell';
    const picker = document.getElementById('ai-picker');
    document.getElementById('dot').className = 'dot ' + key;
    document.getElementById('ai-label').textContent = AI_LABEL[key] || key;
    picker.className = 'ai-picker' + (activeAi ? ' active-' + activeAi : '');
    if(s.cwd) applyCwd(s.cwd);
  }
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

// ── Thinking (per-session) ────────────────────────────────────────────────────
// Track which sessions are currently "thinking" so we can show/hide the
// indicator correctly when sessions run in parallel or the user switches focus.
const _thinkingState = {};   // { session_id: { active: bool, ai: string } }

function setThinking(active, ai, session_id){
  // Update per-session tracking
  if(session_id){
    if(active) _thinkingState[session_id] = { active: true, ai: ai };
    else        delete _thinkingState[session_id];
  }
  // Show the indicator only for the focused session
  _refreshThinkingUI();
}

function _refreshThinkingUI(){
  const el      = document.getElementById('thinking');
  const focused = _thinkingState[_focusedId];
  if(focused && focused.active){
    el.className = 'on';
    const k     = focused.ai || _focusedAi || activeAi || '';
    const sess  = _sessions.find(s => s.id === _focusedId);
    const label = sess ? (sess.emoji + ' ' + sess.name) : (AI_LABEL[k] || 'AI');
    document.getElementById('thlabel').textContent = label + '…';
    scroll();
  } else {
    el.className = '';
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
      // Show session label on user messages when multiple sessions exist
      const sessTag = (m.session_name && _sessions.length > 1)
        ? `<span class="via">[${escHtml(m.session_emoji||'')} ${escHtml(m.session_name)}] </span>`
        : '';
      meta.innerHTML = sessTag + via + 'You';
    } else {
      const k = m.ai || '';
      const aiName = AI_LABEL[k] || k || 'AI';
      // Show session name badge if multiple sessions or session is identified
      const sessLabel = (m.session_name && _sessions.length > 1)
        ? ` <span style="font-size:10px;color:var(--muted);font-weight:normal">${escHtml(m.session_emoji||'')} ${escHtml(m.session_name)}</span>`
        : '';
      meta.innerHTML = `<span class="who ${k}">${escHtml(aiName)}</span>${sessLabel}`;
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
    returnToLive();   // clear the resume banner
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
// ── Schedules modal ──────────────────────────────────────────────────────────
let _schedTasks = [];

function openSchedules(){
  document.getElementById('sched-modal').style.display = 'flex';
  cmd('schedule_list');  // request fresh list from server
}
function closeSchedules(){
  document.getElementById('sched-modal').style.display = 'none';
}

function renderSchedules(tasks){
  _schedTasks = tasks || [];
  // Update sidebar scheduled tasks
  updateSbScheduled(_schedTasks);
  const el = document.getElementById('sched-list');
  if(!_schedTasks.length){
    el.innerHTML = '<div class="modal-empty">No scheduled tasks yet.<br>Use the form below to add one.</div>';
    return;
  }
  el.innerHTML = _schedTasks.map(t => {
    const ico = t.enabled ? '✅' : '⏸';
    const ai  = t.ai || 'shell';
    return `<div class="sched-row">
      <div class="sched-meta">
        ${ico} <strong>${escHtml(t.name)}</strong>
        <code style="margin-left:6px;font-size:11px">${escHtml(t.cron)}</code>
        <span class="sched-ai-badge ${ai}">${ai}</span>
      </div>
      <div class="sched-prompt">${escHtml(t.prompt.length>80 ? t.prompt.slice(0,80)+'…' : t.prompt)}</div>
      <div class="sched-times">Next: ${escHtml(t.next_run_fmt)} &nbsp;·&nbsp; Last: ${escHtml(t.last_run_fmt)} &nbsp;·&nbsp; Runs: ${t.run_count||0}</div>
      <div class="sched-actions">
        <button onclick="cmd('schedule_run:${t.id}')" title="Run now">▶</button>
        <button onclick="cmd('schedule_toggle:${t.id}')" title="${t.enabled?'Pause':'Enable'}">${t.enabled?'⏸':'▶️'}</button>
        <button onclick="if(confirm('Delete ${escHtml(t.name)}?'))cmd('schedule_delete:${t.id}')" title="Delete" style="color:#f87171">🗑</button>
      </div>
    </div>`;
  }).join('');
}

function schedAdd(){
  const cron   = document.getElementById('sched-cron').value.trim();
  const ai     = document.getElementById('sched-ai').value;
  const prompt = document.getElementById('sched-prompt').value.trim();
  if(!cron || !prompt){ alert('Cron expression and prompt are required.'); return; }
  cmd(`schedule_add:${cron}|${ai}|${prompt}`);
  document.getElementById('sched-cron').value   = '';
  document.getElementById('sched-prompt').value = '';
  document.getElementById('sched-add-details').open = false;
}

// Populate the AI dropdown in schedules modal with loaded integrations
function _schedPopulateAiSelect(){
  const sel = document.getElementById('sched-ai');
  if(!sel) return;
  // Remove existing integration options (keep claude + shell)
  [...sel.options].filter(o => o.dataset.integration).forEach(o => o.remove());
  Object.entries(_integrationKeys||{}).forEach(([key, name]) => {
    const opt = document.createElement('option');
    opt.value = key; opt.textContent = name; opt.dataset.integration = '1';
    sel.insertBefore(opt, sel.options[sel.options.length-1]);
  });
}

// ── History modal ─────────────────────────────────────────────────────────────
let _histSessions = [];   // full session list loaded from /history
const AI_COLOR = {        // accent colours for session cards
  claude:'#f59e0b', gemini:'#3b82f6', codex:'#22c55e', shell:'#6b7280'
};
const AI_DISPLAY = {claude:'Claude Code', gemini:'Gemini', codex:'Codex', shell:'Shell'};

function _fmtDate(dateStr, ts){
  // dateStr = YYYY-MM-DD; ts = unix timestamp of last message (optional)
  try {
    const d = ts ? new Date(ts * 1000) : new Date(dateStr + 'T12:00:00');
    const now = new Date();
    const diffDays = Math.floor((now - d) / 86400000);
    if(diffDays === 0) return 'Today';
    if(diffDays === 1) return 'Yesterday';
    if(diffDays < 7)  return d.toLocaleDateString(undefined,{weekday:'long'});
    return d.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
  } catch(e){ return dateStr; }
}

function _renderHistoryList(sessions){
  const list = document.getElementById('hist-list');
  if(!sessions.length){
    list.innerHTML = `<div class="modal-empty">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      No saved sessions yet.<br>Sessions are saved automatically as you chat.
    </div>`;
    return;
  }
  list.innerHTML = sessions.map(s => {
    const displayName = s.name || _fmtDate(s.date, s.ts);
    const subline     = (s.name ? _fmtDate(s.date, s.ts) + ' · ' : '') +
                        s.count + ' message' + (s.count !== 1 ? 's' : '');
    const accentColor = AI_COLOR[s.ai] || '#4b5563';
    const aiBadge     = s.ai ? `<span class="hcard-ai-badge">${escHtml(AI_DISPLAY[s.ai] || s.ai)}</span>` : '';
    const preview     = s.preview
      ? `<div class="hcard-preview">${escHtml(s.preview)}</div>` : '';
    return `
    <div class="hcard" id="hcard-${s.date}">
      <div class="hcard-accent" style="background:${accentColor}"></div>
      <div class="hcard-body" onclick="toggleHistCard('${s.date}')">
        <div class="hcard-top">
          <div class="hcard-name" id="hcard-name-${s.date}">${escHtml(displayName)}</div>
          ${aiBadge}
        </div>
        <div class="hcard-meta">${escHtml(subline)}</div>
        ${preview}
      </div>
      <button class="hcard-del" title="Delete session" onclick="delSession(event,'${s.date}')">✕</button>
    </div>
    <div class="hcard-actions" id="hcard-act-${s.date}">
      <button class="hact primary" onclick="loadSession('${s.date}')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>View
      </button>
      <button class="hact resume" onclick="resumeSession('${s.date}')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>Resume
      </button>
      <button class="hact" onclick="startRename(event,'${s.date}')">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>Rename
      </button>
    </div>`;
  }).join('');
}

async function openHistory(){
  // Reset search
  const sinp = document.getElementById('hist-search-inp');
  if(sinp) sinp.value = '';

  const list = document.getElementById('hist-list');
  list.innerHTML = '<div class="modal-empty" style="padding:32px 0"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:.3;animation:spin 1s linear infinite"><path d="M21 12a9 9 0 11-18 0"/></svg></div>';
  document.getElementById('hist-modal').classList.add('open');

  try {
    const res = await fetch('/history');
    _histSessions = await res.json();
    _sessNames = {};
    _histSessions.forEach(s => { if(s.name) _sessNames[s.date] = s.name; });
    _renderHistoryList(_histSessions);
  } catch(e){
    list.innerHTML = '<div class="modal-empty">Failed to load sessions.</div>';
  }
}

function filterHistory(q){
  const lq = q.toLowerCase().trim();
  if(!lq){ _renderHistoryList(_histSessions); return; }
  const filtered = _histSessions.filter(s =>
    (s.name || s.date).toLowerCase().includes(lq) ||
    (s.preview || '').toLowerCase().includes(lq) ||
    (s.ai || '').toLowerCase().includes(lq)
  );
  _renderHistoryList(filtered);
}

function closeHistory(){
  document.getElementById('hist-modal').classList.remove('open');
}

function toggleHistCard(date){
  const act = document.getElementById('hcard-act-' + date);
  const isOpen = act.classList.contains('open');
  document.querySelectorAll('.hcard-actions.open').forEach(el => el.classList.remove('open'));
  if(!isOpen) act.classList.add('open');
}

async function loadSession(date){
  closeHistory();
  const res = await fetch('/history/' + date);
  const data = await res.json();
  const msgs = data.messages || data;
  _viewingHistory = true;
  const name = _sessNames[date] || _fmtDate(date);
  const banner = document.getElementById('hist-banner');
  banner.className = 'on view';
  document.getElementById('hist-banner-icon').textContent = '📖';
  document.getElementById('hist-banner-date').textContent = 'Viewing: ' + name;
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  msgs.forEach(renderMsg);
  scroll();
}

function returnToLive(){
  _viewingHistory = false;
  const banner = document.getElementById('hist-banner');
  banner.className = '';
  const wrap = document.getElementById('messages');
  wrap.innerHTML = '';
  _liveHistory.forEach(renderMsg);
  scroll();
}

async function resumeSession(date){
  closeHistory();
  const res = await fetch('/history/' + date + '/resume');
  const data = await res.json();
  _pendingContext = data.context || '';
  const name = _sessNames[date] || _fmtDate(date);
  const banner = document.getElementById('hist-banner');
  banner.className = 'on resume';
  document.getElementById('hist-banner-icon').textContent = '▶';
  document.getElementById('hist-banner-date').textContent = 'Context from: ' + name + ' — type your message to continue';
  document.getElementById('inp').focus();
}

async function delSession(e, date){
  e.stopPropagation();
  if(!confirm('Delete session "' + (_sessNames[date] || date) + '"?')) return;
  await fetch('/history/' + date, {method: 'DELETE'});
  // Remove from local list and re-render
  _histSessions = _histSessions.filter(s => s.date !== date);
  _renderHistoryList(_histSessions);
}

function startRename(e, date){
  e.stopPropagation();
  const nameEl = document.getElementById('hcard-name-' + date);
  const cur = nameEl.textContent;
  nameEl.innerHTML = `<input class="sess-rename-input" value="${escHtml(cur)}"
    onkeydown="finishRename(event,'${date}')" onblur="finishRename(event,'${date}',true)">`;
  const inp = nameEl.querySelector('input');
  inp.focus(); inp.select();
}

async function finishRename(e, date, blur){
  if(!blur && e.key !== 'Enter' && e.key !== 'Escape') return;
  const nameEl = document.getElementById('hcard-name-' + date);
  if(!nameEl) return;
  const inp = nameEl.querySelector('input');
  if(!inp) return;
  const newName = (e.key === 'Escape') ? '' : inp.value.trim();
  if(newName && newName !== date){
    await fetch('/history/' + date + '/rename', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: newName})
    });
    _sessNames[date] = newName;
    // Update local cache
    const s = _histSessions.find(s => s.date === date);
    if(s) s.name = newName;
  }
  // Re-render just this card's name
  const s = _histSessions.find(s => s.date === date);
  if(nameEl && s){
    nameEl.textContent = s.name || _fmtDate(s.date, s.ts);
  }
}

// ── Right Sidebar: Session Dashboard ──────────────────────────────────────────
function _fmtElapsed(ts){
  if(!ts) return '';
  const sec = Math.floor((Date.now() - ts) / 1000);
  if(sec < 60) return sec + 's';
  const m = Math.floor(sec / 60);
  if(m < 60) return m + 'm ' + (sec % 60) + 's';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'm';
}
function updateRightSidebar(sessions, focusedId){
  const el = document.getElementById('rs-list');
  const countEl = document.getElementById('rs-count');
  if(!el) return;
  if(!sessions.length){
    el.innerHTML = '<div class="rs-empty">No sessions yet.<br>Create one below.</div>';
    if(countEl) countEl.textContent = '';
    return;
  }
  const busy = sessions.filter(s => s.busy).length;
  if(countEl) countEl.textContent = busy > 0 ? busy + ' running' : sessions.length + ' total';
  el.innerHTML = sessions.map(sess => {
    const f = sess.id === focusedId;
    let dot = 'idle';
    if(sess.status === 'stopped') dot = 'stopped';
    else if(sess.busy) dot = 'busy';
    const aiKey = sess.ai || 'shell';
    const color = AI_COLOR[aiKey] || 'var(--shell)';
    const folder = sess.cwd ? sess.cwd.split(/[/\\]/).pop() || '' : '';
    const timer = sess.busy && sess.task_start ? _fmtElapsed(sess.task_start) : '';
    return `<div class="rs-item${f ? ' focused' : ''}" data-sid="${sess.id}" onclick="cmd('focus:${sess.id}')">
      <div class="rs-dot ${dot}"></div>
      <div class="rs-info">
        <div class="rs-name">${escHtml(sess.name)}</div>
        <div class="rs-meta">
          <div class="rs-ai-dot" style="background:${color}"></div>
          <span>${aiKey}</span>
          ${timer ? `<span class="rs-timer">${timer}</span>` : ''}
          ${folder ? `<span style="opacity:.5">${escHtml(folder)}</span>` : ''}
        </div>
      </div>
      <div class="rs-actions">
        <button class="rs-act" onclick="event.stopPropagation();cmd('interrupt')" title="Cancel running task">⏸</button>
        <button class="rs-act" onclick="event.stopPropagation();if(confirm('Delete this session?'))cmd('delete_session')" title="Delete session">🗑</button>
      </div>
    </div>`;
  }).join('');
  // Manage elapsed timers
  Object.keys(_sessionTimers).forEach(id => {
    if(!sessions.find(s => s.id === id && s.busy && s.task_start)){
      clearInterval(_sessionTimers[id]);
      delete _sessionTimers[id];
    }
  });
  sessions.forEach(sess => {
    if(sess.busy && sess.task_start && !_sessionTimers[sess.id]){
      _sessionTimers[sess.id] = setInterval(() => {
        const te = document.querySelector(`.rs-item[data-sid="${sess.id}"] .rs-timer`);
        if(te) te.textContent = _fmtElapsed(sess.task_start);
      }, 1000);
    }
  });
}

// ── Left Sidebar: Tab Switching ──────────────────────────────────────────────
function switchSbTab(tab, btn){
  document.querySelectorAll('.sb-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.sb-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('sb-panel-' + tab).classList.add('active');
  if(tab === 'scheduled') cmd('schedule_list');
}

// ── Left Sidebar: History ────────────────────────────────────────────────────
function loadSbHistory(){
  const el = document.getElementById('sb-panel-history');
  // Show stale cached data instantly while refreshing in background
  if(!_sbHistSessions.length){
    el.innerHTML = '<div class="sb-empty" style="opacity:.5">Loading…</div>';
  }
  fetch('/history').then(r => r.json()).then(sessions => {
    _sbHistSessions = sessions;
    renderSbHistory(sessions);
  }).catch(() => {
    if(!_sbHistSessions.length) el.innerHTML = '<div class="sb-empty">Could not load history</div>';
  });
}
function renderSbHistory(sessions){
  const el = document.getElementById('sb-panel-history');
  if(!sessions.length){
    el.innerHTML = '<div class="sb-empty">No saved sessions yet</div>';
    return;
  }
  el.innerHTML = sessions.map(s => {
    const name = s.name || _fmtDate(s.date, s.ts);
    const ai = s.ai || '';
    const color = AI_COLOR[ai] || '';
    return `<div class="sb-hcard" onclick="loadSession('${s.date}')">
      <div style="display:flex;align-items:center;gap:6px">
        <div class="sb-hcard-name" style="flex:1">${escHtml(name)}</div>
        ${ai ? `<span class="sb-hcard-ai" style="${color ? 'border-color:' + color + ';color:' + color : ''}">${ai}</span>` : ''}
      </div>
      <div class="sb-hcard-meta">
        <span>${_fmtDate(s.date, s.ts)}</span>
        <span>${s.count || 0} msg${(s.count||0) !== 1 ? 's' : ''}</span>
      </div>
    </div>`;
  }).join('');
}
function filterSidebarHistory(q){
  const lq = q.toLowerCase().trim();
  if(!lq){ renderSbHistory(_sbHistSessions); return; }
  renderSbHistory(_sbHistSessions.filter(s =>
    (s.name || s.date).toLowerCase().includes(lq) ||
    (s.preview || '').toLowerCase().includes(lq) ||
    (s.ai || '').toLowerCase().includes(lq)
  ));
}

// ── Left Sidebar: Scheduled Tasks ────────────────────────────────────────────
function updateSbScheduled(tasks){
  const el = document.getElementById('sb-sched-list');
  if(!el) return;
  if(!tasks.length){
    el.innerHTML = '<div class="sb-empty">No scheduled tasks</div>';
    return;
  }
  el.innerHTML = tasks.map(t => {
    const ico = t.enabled ? '✅' : '⏸';
    const ai = t.ai || 'shell';
    return `<div class="sb-sched-item">
      <div class="sb-sched-top">
        <span>${ico}</span>
        <span class="sb-sched-name">${escHtml(t.name)}</span>
        <span class="sb-hcard-ai">${ai}</span>
      </div>
      <div class="sb-sched-prompt">${escHtml(t.prompt.length > 60 ? t.prompt.slice(0,60) + '…' : t.prompt)}</div>
      <div class="sb-sched-meta"><code style="font-size:10px">${escHtml(t.cron)}</code> · Next: ${escHtml(t.next_run_fmt)}</div>
      <div class="sb-sched-btns">
        <button onclick="cmd('schedule_run:${t.id}')" title="Run now">▶ Run</button>
        <button onclick="cmd('schedule_toggle:${t.id}')">${t.enabled ? '⏸' : '▶'}</button>
        <button onclick="if(confirm('Delete?'))cmd('schedule_delete:${t.id}')" style="color:#f87171">✕</button>
      </div>
    </div>`;
  }).join('');
}
function sbSchedAdd(){
  const cron   = document.getElementById('sb-sched-cron').value.trim();
  const ai     = document.getElementById('sb-sched-ai').value;
  const prompt = document.getElementById('sb-sched-prompt').value.trim();
  if(!cron || !prompt){ alert('Cron expression and prompt are required.'); return; }
  cmd(`schedule_add:${cron}|${ai}|${prompt}`);
  document.getElementById('sb-sched-cron').value = '';
  document.getElementById('sb-sched-prompt').value = '';
}

// Also populate sidebar AI dropdown with integrations
function _sbSchedPopulateAi(){
  const sel = document.getElementById('sb-sched-ai');
  if(!sel) return;
  [...sel.options].filter(o => o.dataset.integration).forEach(o => o.remove());
  Object.entries(_integrationKeys||{}).forEach(([key, name]) => {
    const opt = document.createElement('option');
    opt.value = key; opt.textContent = name; opt.dataset.integration = '1';
    sel.insertBefore(opt, sel.options[sel.options.length - 1]);
  });
}

// ── Mobile sidebar toggles ───────────────────────────────────────────────────
function toggleLeft(){
  const el = document.getElementById('left-sidebar');
  const ov = document.getElementById('sb-overlay');
  const isOpen = el.classList.contains('open');
  closeSidebars();
  if(!isOpen){ el.classList.add('open'); ov.classList.add('open'); }
}
function toggleRight(){
  const el = document.getElementById('right-sidebar');
  const ov = document.getElementById('sb-overlay');
  const isOpen = el.classList.contains('open');
  closeSidebars();
  if(!isOpen){ el.classList.add('open'); ov.classList.add('open'); }
}
function closeSidebars(){
  document.getElementById('left-sidebar').classList.remove('open');
  document.getElementById('right-sidebar').classList.remove('open');
  document.getElementById('sb-overlay').classList.remove('open');
}

// ── Redirect old modal openers to sidebars (on desktop) / toggle (mobile) ────
const _origOpenHistory = openHistory;
openHistory = function(){
  if(window.innerWidth > 900){
    switchSbTab('history', document.querySelector('.sb-tab'));
    loadSbHistory();
  } else {
    toggleLeft();
    switchSbTab('history', document.querySelector('.sb-tab'));
    loadSbHistory();
  }
};
const _origOpenSchedules = openSchedules;
openSchedules = function(){
  if(window.innerWidth > 900){
    switchSbTab('scheduled', document.querySelectorAll('.sb-tab')[1]);
    cmd('schedule_list');
  } else {
    toggleLeft();
    switchSbTab('scheduled', document.querySelectorAll('.sb-tab')[1]);
    cmd('schedule_list');
  }
};

// ── Init sidebars on load ────────────────────────────────────────────────────
setTimeout(() => { loadSbHistory(); cmd('schedule_list'); _sbSchedPopulateAi(); }, 500);

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

    if not BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled.")

    # --- Build Telegram application ---
    if BOT_TOKEN:
        _telegram_app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
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
        _telegram_app.add_handler(CommandHandler("schedule",      tg_schedule))
        # Inline keyboard callbacks — action/ms: buttons come BEFORE browse_callback
        _telegram_app.add_handler(CallbackQueryHandler(action_callback, pattern=r"^(action:|ms:)"))
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

    # Load persisted scheduled tasks and start the cron runner
    _load_scheduled_tasks()
    asyncio.create_task(_cron_runner())
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
