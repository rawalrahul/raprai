"""
helm/web_routes/app.py — FastAPI app initialization, CORS, middleware, and health endpoint.
"""

import os
import pathlib
import sys
from typing import Optional

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import helm.state as _st
from helm.config import logger
from helm.frontend import _HTML
import helm.auth as _auth


# ---------------------------------------------------------------------------
# FastAPI app initialization
# ---------------------------------------------------------------------------

app = FastAPI(title="Helm HQ")

# Serve logo.png (and any other static assets placed alongside web_app.py)
_static_dir = pathlib.Path(__file__).parent.parent.parent
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ---------------------------------------------------------------------------
# Auth middleware — redirects unauthenticated requests to /login
# ---------------------------------------------------------------------------

# Paths that are always public (no PIN required)
_PUBLIC_PREFIXES = ("/login", "/setup", "/static")


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow public routes through unconditionally
        path = request.url.path
        if any(path == p or path.startswith(p + "/") or path.startswith(p + "?")
               for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        # Allow WebSocket upgrades — the WS handler checks auth itself
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        # If no PIN is configured, let everything through
        if not _auth.pin_is_set():
            return await call_next(request)
        # Check session cookie
        if not _auth.check_auth(request):
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)


app.add_middleware(_AuthMiddleware)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

_find_cli_cache: dict[str, bool] = {}   # name -> found (survives the process)


def _find_cli(name: str) -> bool:
    """
    Return True if a CLI tool can be found.  Results are cached so the
    expensive subprocess probe runs at most once per CLI name.

    Checks in order:
      1. In-memory cache (instant)
      2. Standard PATH lookup via shutil.which
      3. Common Windows npm / nvm global bin directories
      4. Subprocess probe — actually runs `<name> --version` with a 3-second
         timeout as a last resort
    """
    if name in _find_cli_cache:
        return _find_cli_cache[name]

    import shutil, subprocess
    # 1 — fast PATH lookup
    if shutil.which(name) or shutil.which(name + ".cmd") or shutil.which(name + ".exe"):
        _find_cli_cache[name] = True
        return True

    if sys.platform == "win32":
        home = pathlib.Path.home()
        candidates = [
            # npm global (Roaming)
            home / "AppData" / "Roaming" / "npm" / f"{name}.cmd",
            home / "AppData" / "Roaming" / "npm" / name,
            # npm global (Local)
            home / "AppData" / "Local" / "npm" / f"{name}.cmd",
            home / "AppData" / "Local" / "npm" / name,
            # nvm for Windows
            home / "AppData" / "Roaming" / "nvm" / "current" / f"{name}.cmd",
            # Claude native installer — places binary under ~/.claude/
            home / ".claude" / "local" / f"{name}.exe",
            home / ".claude" / "local" / f"{name}.cmd",
            home / ".claude" / "local" / name,
            home / ".claude" / "bin"   / f"{name}.exe",
            home / ".claude" / "bin"   / f"{name}.cmd",
            home / ".claude" / "bin"   / name,
            # winget / scoop / system Node
            home / "AppData" / "Local" / "Programs" / name / f"{name}.exe",
            pathlib.Path("C:/Program Files/nodejs") / f"{name}.cmd",
        ]
        for env_key in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_key, "")
            if base:
                candidates += [
                    pathlib.Path(base) / "npm" / f"{name}.cmd",
                    pathlib.Path(base) / "npm" / name,
                ]
        # 2 — file-system candidates
        if any(p.exists() for p in candidates):
            _find_cli_cache[name] = True
            return True

    # 3 — shell probe: ask cmd.exe / sh exactly like the user's terminal would.
    #     Timeout reduced to 3s to avoid blocking the caller too long.
    try:
        r = subprocess.run(
            f"{name} --version",
            shell=True,
            capture_output=True,
            timeout=3,
            text=True,
        )
        if r.returncode == 9009:
            _find_cli_cache[name] = False
            return False
        combined = (r.stdout + r.stderr).lower()
        not_found_phrases = (
            "is not recognized as an internal or external command",
            "command not found",
        )
        if any(p in combined for p in not_found_phrases):
            _find_cli_cache[name] = False
            return False
        _find_cli_cache[name] = True
        return True
    except subprocess.TimeoutExpired:
        _find_cli_cache[name] = True
        return True
    except (OSError, FileNotFoundError):
        pass

    _find_cli_cache[name] = False
    return False


def _claude_ready() -> bool:
    """Return True if the Claude CLI binary is installed."""
    return _find_cli("claude")


def _gemini_ready() -> bool:
    """Return True if the Gemini CLI binary is installed (API key is optional)."""
    return _find_cli("gemini")


def _telegram_configured() -> bool:
    """Return True if both TELEGRAM_BOT_TOKEN and ALLOWED_USER_IDS are set in .env."""
    from dotenv import dotenv_values
    env_path = pathlib.Path(".env")
    vals = dotenv_values(env_path) if env_path.exists() else {}
    return bool(vals.get("TELEGRAM_BOT_TOKEN", "").strip() and vals.get("ALLOWED_USER_IDS", "").strip())


def windows_folder_picker() -> Optional[str]:
    """Open a native Windows folder-picker dialog on the server desktop."""
    from helm.session_mgr import session_cwd
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        path = filedialog.askdirectory(
            title="Select Working Directory",
            initialdir=session_cwd(),
        )
        root.destroy()
        return str(pathlib.Path(path)) if path else None
    except Exception:
        return None


_windows_folder_picker = windows_folder_picker  # legacy alias


def update_env(key: str, value: str):
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


_update_env = update_env  # legacy alias


# ---------------------------------------------------------------------------
# Settings keys (for settings_routes.py)
# ---------------------------------------------------------------------------

_SETTINGS_KEYS = [
    "OUTPUT_IDLE_TIMEOUT",
    "OUTPUT_MAX_WAIT",
    "OUTPUT_NO_RESPONSE",
    "CLAUDE_TIMEOUT",
    "SESSION_DAYS",
    "OLLAMA_MODEL",
    "WEB_PORT",
    "WEB_HOST",
    "USAGE_RESET_HOURS",
    "WEBHOOK_TOKEN",
    "HEARTBEAT_ENABLED",
    "HEARTBEAT_INTERVAL",
    "HEARTBEAT_AI",
    "AI_MAX_RETRIES",
    "AI_AUTO_SWITCH",
]


# ---------------------------------------------------------------------------
# Main page and health endpoint
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    # Only redirect to setup on true first run (no .env file yet).
    # Everything else (Telegram, AI CLIs) is optional — the user can configure
    # them later via the Settings panel or by editing .env directly.
    if not pathlib.Path(".env").exists():
        return RedirectResponse(url="/setup")
    return HTMLResponse(content=_HTML)


@app.get("/health")
async def health():
    """Quick health check."""
    from fastapi.responses import JSONResponse
    return JSONResponse({"ok": True, "sessions": len(_st.sessions), "ws_clients": len(_st.ws_clients)})
