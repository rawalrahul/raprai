"""
helm/web_routes/app.py — FastAPI app initialization, CORS, middleware, and health endpoint.
"""

import os
import pathlib
import secrets
import sys
from typing import Optional

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import helm.state as _st
from helm.config import logger
from helm.frontend import _HTML
from helm.paths import user_data_dir
import helm.auth as _auth


# ---------------------------------------------------------------------------
# FastAPI app initialization
# ---------------------------------------------------------------------------

app = FastAPI(title="RAPR AI")

# Serve logo.png (and any other static assets placed alongside web_app.py)
from helm.paths import PROJECT_ROOT
_static_dir = PROJECT_ROOT
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ---------------------------------------------------------------------------
# Auth middleware — redirects unauthenticated requests to /login
# ---------------------------------------------------------------------------

# Paths that are always public (no PIN required)
_PUBLIC_PREFIXES = ("/login", "/setup", "/activate", "/device/status", "/device/activate", "/prefs", "/static", "/health", "/manifest.json", "/sw.js", "/update/check")

# Plugin connect/OAuth routes are opened in popup windows which may not share
# the session cookie. These are localhost-only and protected by OAuth state tokens.
_PLUGIN_PUBLIC_PREFIXES = (
    "/plugins/oauth/callback",    # OAuth callback from proxy
)

# MCP endpoints are NOT fully public — they require localhost origin
# and a bearer token that's auto-generated at startup.
_MCP_PREFIXES = ("/mcp/call", "/mcp/servers")

# Bearer token for subprocess MCP calls + Chrome plugin auth.
# Persisted to .env so it survives restarts (Chrome plugin stores it once).
MCP_BEARER_TOKEN: str = os.environ.get("MCP_BEARER_TOKEN", "")
_MCP_TOKEN_IS_NEW = False
if not MCP_BEARER_TOKEN:
    MCP_BEARER_TOKEN = secrets.token_urlsafe(32)
    _MCP_TOKEN_IS_NEW = True
os.environ["MCP_BEARER_TOKEN"] = MCP_BEARER_TOKEN
logger.info("MCP bearer token: %s…%s", MCP_BEARER_TOKEN[:4], MCP_BEARER_TOKEN[-4:])


def _is_localhost(request: Request) -> bool:
    """True if the request originates from loopback (127.0.0.1 / ::1)."""
    client = request.client
    if not client:
        return False
    host = client.host or ""
    return host in ("127.0.0.1", "::1", "localhost")


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow fully-public routes through unconditionally
        if any(path == p or path.startswith(p + "/") or path.startswith(p + "?")
               for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # Plugin connect/OAuth routes — opened in popup windows that may
        # not share the session cookie. These are safe to expose because
        # they're localhost-only and the OAuth flow uses state tokens.
        if any(path == p or path.startswith(p) for p in _PLUGIN_PUBLIC_PREFIXES):
            return await call_next(request)
        # /plugins/<id>/connect and /plugins/<id>/oauth/* — popup OAuth flow
        if path.startswith("/plugins/") and (
            "/connect" in path or "/oauth/" in path
        ):
            return await call_next(request)

        # MCP endpoints: allow if (a) normal session cookie is valid, OR
        # (b) localhost + valid bearer token (for AI subprocesses)
        if any(path == p or path.startswith(p + "/") for p in _MCP_PREFIXES):
            # Option A: authenticated browser session
            if _auth.check_auth(request):
                return await call_next(request)
            # Option B: localhost + bearer token (for Codex/Gemini subprocesses)
            if _is_localhost(request):
                auth_header = request.headers.get("authorization", "")
                expected = f"Bearer {MCP_BEARER_TOKEN}"
                if secrets.compare_digest(auth_header, expected):
                    return await call_next(request)
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "unauthorized"}, status_code=401)

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
    from helm.subprocess_utils import hidden_kwargs
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

    # 3 — subprocess probe: run `<name> --version` directly (no shell).
    #     Timeout reduced to 3s to avoid blocking the caller too long.
    try:
        r = subprocess.run(
            [name, "--version"],
            shell=False,
            capture_output=True,
            timeout=3,
            text=True,
            **hidden_kwargs(),
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
    env_path = user_data_dir() / ".env"
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
    env_path = user_data_dir() / ".env"
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

# Persist the MCP bearer token to .env if it was just generated
# Only write if .env already exists — otherwise we'd create it prematurely
# and the setup wizard redirect (which checks .env existence) would be skipped.
if _MCP_TOKEN_IS_NEW and (user_data_dir() / ".env").exists():
    try:
        update_env("MCP_BEARER_TOKEN", MCP_BEARER_TOKEN)
    except Exception:
        pass


def reload_env():
    """Reload .env into os.environ AND re-apply vault tokens on top.

    Use this instead of raw ``load_dotenv(override=True)`` anywhere in the
    codebase, so that encrypted vault tokens aren't clobbered by the
    "vault-managed" placeholders stored in .env.
    """
    from helm.security import VAULT_ELIGIBLE_KEYS

    # Snapshot live decrypted values for vault-managed keys BEFORE
    # load_dotenv clobbers them with the "vault-managed" placeholder.
    _vault_backup: dict[str, str] = {}
    for key in VAULT_ELIGIBLE_KEYS:
        val = os.environ.get(key, "")
        if val and val != "vault-managed":
            _vault_backup[key] = val

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(user_data_dir() / ".env"), override=True)

    # Re-apply decrypted tokens so vault-managed placeholders don't stick
    try:
        from helm.token_vault import load_all_tokens
        load_all_tokens()
    except Exception:
        pass

    # Safety net: if any key is STILL "vault-managed" after load_all_tokens
    # (e.g. vault DB error), restore the pre-reload decrypted value so the
    # running process keeps working (Telegram bot stays connected, etc.)
    for key, original in _vault_backup.items():
        if os.environ.get(key) == "vault-managed":
            logger.warning("reload_env: restoring %s from backup (vault reload failed)", key)
            os.environ[key] = original


# ---------------------------------------------------------------------------
# Settings keys (for settings_routes.py)
# ---------------------------------------------------------------------------

_SETTINGS_KEYS = [
    "OUTPUT_IDLE_TIMEOUT",
    "OUTPUT_MAX_WAIT",
    "OUTPUT_NO_RESPONSE",
    "CLAUDE_TIMEOUT",
    "SESSION_DAYS",
    "WEB_PORT",
    "WEB_HOST",
    "USAGE_RESET_HOURS",
    "HEARTBEAT_ENABLED",
    "HEARTBEAT_INTERVAL",
    "HEARTBEAT_AI",
    "AI_MAX_RETRIES",
    "AI_AUTO_SWITCH",
    "PIPELINE_PLANNER_AI",
    "PIPELINE_MAX_PARALLEL",
    "PIPELINE_AUTO_SUGGEST",
    "PIPELINE_CONTEXT_THRESHOLD",
    "LOCAL_AI_URL",
    "LOCAL_AI_MODEL",
    "BUDGET_ENABLED",
    "BUDGET_DAILY_GEMINI_USD",
    "BUDGET_DAILY_OPENAI_USD",
    "BUDGET_DAILY_CODEX_USD",
    "BUDGET_WARN_GEMINI_USD",
    "BUDGET_WARN_OPENAI_USD",
    "BUDGET_WARN_CODEX_USD",
    # Context windows (tokens) — override per-AI defaults in context_manager.py
    "CONTEXT_WINDOW_CLAUDE",
    "CONTEXT_WINDOW_OPENAI",
    "CONTEXT_WINDOW_CODEX",
    "CONTEXT_WINDOW_GEMINI",
    "CONTEXT_WINDOW_OLLAMA",
]


# ---------------------------------------------------------------------------
# Separated frontend support
# ---------------------------------------------------------------------------
# The backend can serve a separated frontend from a standalone directory.
# Priority: FRONTEND_DIR env var > frontend2/ > frontend/ > embedded HTML.
# Set FRONTEND_DIR env var to override auto-detection.

if os.environ.get("FRONTEND_DIR"):
    _FRONTEND_DIR = pathlib.Path(os.environ["FRONTEND_DIR"])
elif (PROJECT_ROOT / "frontend2" / "index.html").exists():
    _FRONTEND_DIR = PROJECT_ROOT / "frontend2"
elif (PROJECT_ROOT / "frontend" / "index.html").exists():
    _FRONTEND_DIR = PROJECT_ROOT / "frontend"
else:
    _FRONTEND_DIR = PROJECT_ROOT / "frontend"

_USE_SEPARATED_FRONTEND = _FRONTEND_DIR.exists() and (_FRONTEND_DIR / "index.html").exists()

if _USE_SEPARATED_FRONTEND:
    logger.info("Serving separated frontend from: %s", _FRONTEND_DIR)
    # Mount frontend static assets (js/, css/, assets/)
    for sub in ("js", "css", "assets"):
        sub_dir = _FRONTEND_DIR / sub
        if sub_dir.exists():
            app.mount(f"/{sub}", StaticFiles(directory=str(sub_dir)), name=f"frontend-{sub}")

    # Serve PWA manifest.json and service worker from frontend root
    from fastapi.responses import FileResponse

    @app.get("/manifest.json")
    async def pwa_manifest():
        mf = _FRONTEND_DIR / "manifest.json"
        if mf.exists():
            return FileResponse(str(mf), media_type="application/manifest+json")
        return JSONResponse({"error": "not found"}, status_code=404)

    @app.get("/sw.js")
    async def pwa_service_worker():
        sw = _FRONTEND_DIR / "sw.js"
        if sw.exists():
            return FileResponse(str(sw), media_type="application/javascript",
                                headers={"Service-Worker-Allowed": "/"})
        return JSONResponse({"error": "not found"}, status_code=404)


# ---------------------------------------------------------------------------
# Main page and health endpoint
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    # First run: no .env file yet → full setup wizard
    if not (user_data_dir() / ".env").exists():
        return RedirectResponse(url="/setup")

    # .env exists but no device token → activation gate
    # This catches users who completed onboarding but closed the app
    # before entering their activation code. They must activate first.
    try:
        from helm.device_link import get_device_token
        if not get_device_token():
            return RedirectResponse(url="/activate")
    except Exception:
        pass  # If device_link import fails, don't block the app

    # Serve from separated frontend if available, otherwise use embedded HTML
    if _USE_SEPARATED_FRONTEND:
        return HTMLResponse(content=(_FRONTEND_DIR / "index.html").read_text(encoding="utf-8"))
    return HTMLResponse(content=_HTML)


@app.get("/agent-run/{run_id}", response_class=HTMLResponse)
async def agent_run_window(run_id: str):
    """Standalone monitor page for one agent run."""
    import json as _json
    safe_run_id = _json.dumps(run_id)
    return HTMLResponse(content=f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agent Run</title>
  <style>
    :root {{ color-scheme: dark; --bg:#101010; --panel:#171717; --border:#2a2a2a; --fg:#e6e6e6; --dim:#909090; --acc:#4a9eff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--fg); font-family:Inter,Segoe UI,Arial,sans-serif; }}
    header {{ display:flex; align-items:center; gap:10px; padding:10px 14px; border-bottom:1px solid var(--border); background:#151515; position:sticky; top:0; z-index:5; }}
    h1 {{ font-size:14px; margin:0; font-weight:650; }}
    .badge {{ font-size:11px; padding:2px 8px; border-radius:8px; background:#222; color:var(--dim); }}
    .spacer {{ flex:1; }}
    button {{ border-radius:6px; border:1px solid var(--border); background:#202020; color:var(--fg); padding:6px 10px; cursor:pointer; }}
    button.danger {{ color:#ff8f98; border-color:#7d3038; background:#281418; }}
    main {{ display:grid; grid-template-columns:minmax(360px,1fr) minmax(320px,420px); gap:12px; padding:12px; }}
    .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:8px; min-height:120px; }}
    .panel h2 {{ font-size:12px; margin:0; padding:10px 12px; border-bottom:1px solid var(--border); color:#cfcfcf; }}
    #nodes {{ padding:10px; display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:10px; }}
    .node {{ border:1px solid var(--border); border-radius:8px; background:#1d1d1d; padding:10px; min-height:110px; }}
    .node-title {{ font-size:12px; font-weight:650; margin-bottom:6px; display:flex; gap:6px; align-items:center; }}
    .chip {{ font-size:9px; text-transform:uppercase; padding:2px 5px; border-radius:5px; background:#232f42; color:#8fb2ff; }}
    .status {{ margin-left:auto; font-size:10px; color:var(--dim); }}
    .task,.output {{ font-size:11px; line-height:1.4; color:#aaa; white-space:pre-wrap; overflow-wrap:anywhere; }}
    .output {{ margin-top:8px; color:#d2d2d2; max-height:220px; overflow:auto; }}
    #feedback {{ padding:12px; display:none; }}
    textarea {{ width:100%; min-height:150px; resize:vertical; background:#101010; color:var(--fg); border:1px solid var(--border); border-radius:6px; padding:9px; font-family:inherit; }}
    .hint {{ color:var(--dim); font-size:12px; line-height:1.45; margin-bottom:8px; white-space:pre-wrap; }}
    @media (max-width: 860px) {{ main {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1 id="title">Agent Run</h1>
    <span class="badge" id="status">loading</span>
    <span class="badge" id="progress"></span>
    <div class="spacer"></div>
    <button onclick="location.reload()">Refresh</button>
    <button class="danger" id="stopBtn" onclick="cancelRun()" style="display:none">Stop</button>
    <button onclick="window.opener&&window.opener.focus()">Main app</button>
  </header>
  <main>
    <section class="panel">
      <h2>Workflow</h2>
      <div id="nodes"></div>
    </section>
    <aside class="panel">
      <h2>Manager / Input</h2>
      <div id="feedback">
        <div class="hint" id="question"></div>
        <textarea id="reply" placeholder="Reply YES if you are happy, or describe what should change."></textarea>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:10px">
          <button onclick="sendReply()">Send feedback</button>
        </div>
      </div>
      <div id="idle" class="hint" style="padding:12px">This window keeps monitoring the agent run. You can continue using the main app.</div>
    </aside>
  </main>
  <script>
    const RUN_ID = {safe_run_id};
    let currentRun = null;
    function esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}
    function terminal(s) {{ return ['completed','failed','cancelled'].includes(s); }}
    async function poll() {{
      try {{
        const data = await fetch('/api/agents/runs/' + encodeURIComponent(RUN_ID)).then(r => r.json());
        if (data.run) render(data.run);
      }} catch (e) {{
        document.getElementById('status').textContent = 'offline';
      }}
    }}
    function render(run) {{
      currentRun = run;
      document.title = run.agent_name || 'Agent Run';
      document.getElementById('title').textContent = run.agent_name || 'Agent Run';
      document.getElementById('status').textContent = run.status || 'unknown';
      const p = run.progress || {{}};
      const done = (p.completed || 0) + (p.failed || 0) + (p.skipped || 0);
      document.getElementById('progress').textContent = done + '/' + (p.total || (run.nodes || []).length || 0);
      document.getElementById('stopBtn').style.display = terminal(run.status) ? 'none' : 'inline-block';
      document.getElementById('nodes').innerHTML = (run.nodes || []).map(n => `
        <div class="node">
          <div class="node-title"><span class="chip">${{esc(n.type || 'ai')}}</span>${{esc(n.title || 'Step')}}<span class="status">${{esc(n.status || '')}}</span></div>
          <div class="task">${{esc(n.task || '')}}</div>
          ${{n.output || n.error || n.stream_buffer ? `<div class="output">${{esc(n.output || n.error || n.stream_buffer)}}</div>` : ''}}
        </div>`).join('');
      const waiting = run.status === 'waiting_input';
      const node = (run.nodes || []).find(n => ['input','manager'].includes(n.type || 'ai') && n.status === 'running');
      document.getElementById('feedback').style.display = waiting ? 'block' : 'none';
      document.getElementById('idle').style.display = waiting ? 'none' : 'block';
      if (waiting) {{
        const manager = node && (node.type || 'ai') === 'manager';
        document.getElementById('question').textContent = manager
          ? 'Manager is waiting for feedback. Reply YES if you are happy, or describe what should change. You can also switch to the manager session in the main app later.'
          : ((node && node.task) || 'This workflow is waiting for input.');
      }}
      if (terminal(run.status)) clearInterval(timer);
    }}
    async function sendReply() {{
      const el = document.getElementById('reply');
      const input = el.value.trim();
      if (!input) {{ el.focus(); return; }}
      const data = await fetch('/api/agents/runs/' + encodeURIComponent(RUN_ID) + '/resume', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{input}})
      }}).then(r => r.json());
      if (data.error) alert(data.error);
      else {{ el.value = ''; poll(); }}
    }}
    async function cancelRun() {{
      if (!currentRun || !confirm('Stop this agent run?')) return;
      await fetch('/api/agents/' + encodeURIComponent(currentRun.agent_id) + '/runs/' + encodeURIComponent(RUN_ID) + '/cancel', {{method:'POST'}});
      poll();
    }}
    const timer = setInterval(poll, 2000);
    poll();
  </script>
</body>
</html>""")


@app.get("/activate", response_class=HTMLResponse)
async def activate_gate():
    """Standalone activation page — shown when .env exists but no device token.

    If the user is already activated, redirect straight to the main app.
    """
    try:
        from helm.device_link import get_device_token
        if get_device_token():
            return RedirectResponse(url="/")
    except Exception:
        pass

    from helm.setup_wizard import _ACTIVATE_HTML
    return HTMLResponse(content=_ACTIVATE_HTML)


@app.get("/health")
async def health():
    """Quick health check."""
    from fastapi.responses import JSONResponse
    return JSONResponse({"ok": True, "sessions": len(_st.sessions), "ws_clients": len(_st.ws_clients)})
