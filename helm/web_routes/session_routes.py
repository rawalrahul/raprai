"""
helm/web_routes/session_routes.py — Session creation/deletion, integration status, model discovery endpoints.
"""

import asyncio
import os
import pathlib
import re
import string as _string
import sys
from fastapi import APIRouter
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.session_mgr import session_cwd
from .app import _find_cli, update_env, windows_folder_picker


router = APIRouter()


_CUSTOM_ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


def _command_binary_found(cmd: list[str]) -> bool:
    """Return whether the executable from a generated integration command exists."""
    if not cmd:
        return False
    exe = (cmd[0] or "").strip()
    if not exe:
        return False
    if exe == sys.executable:
        return pathlib.Path(exe).exists()
    if os.path.isabs(exe):
        return pathlib.Path(exe).exists()
    return _find_cli(exe)


def _integration_ready(key: str, info: dict) -> bool:
    """Readiness check for both CLI and Python/API-backed integrations."""
    if key == "nemoclaw":
        try:
            from helm.ai_runner.nemoclaw_bridge import is_available
            return bool(is_available())
        except Exception:
            return False

    if key in {"openrouter", "groq", "local_ai"}:
        try:
            from helm.ai_runner.core import is_backend_available
            return bool(is_backend_available(key))
        except Exception:
            logger.debug("Couldn't check whether %s is available", key, exc_info=True)

    env_vars_ok = all(os.environ.get(v, "").strip() for v in info.get("env_vars", []))
    try:
        command_ok = _command_binary_found(info["build_command"]("test", model=None))
    except Exception:
        command_ok = False
    return command_ok and env_vars_ok


# ---------------------------------------------------------------------------
# File serving and browsing
# ---------------------------------------------------------------------------

@router.get("/files/{filename:path}")
async def serve_file(filename: str):
    """Dynamically serve any file from the focused session's CWD."""
    from fastapi.responses import FileResponse as _FR, HTMLResponse
    cwd  = session_cwd()
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


def _is_hidden(entry: os.DirEntry) -> bool:
    """Dot-folders everywhere, plus folders Windows marks hidden or system (AppData...)."""
    if entry.name.startswith("."):
        return True
    attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attrs & 0x6)   # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM


def _browse_places() -> list:
    """Home and the usual user folders that exist (OneDrive-redirected ones too)."""
    home = pathlib.Path.home()
    places = [{"name": "Home", "path": str(home), "kind": "home"}]
    for name, kind in (("Desktop", "desktop"), ("Documents", "documents"), ("Downloads", "downloads")):
        for cand in (home / name, home / "OneDrive" / name):
            if cand.is_dir():
                places.append({"name": name, "path": str(cand), "kind": kind})
                break
    return places


def _recent_projects(limit: int = 8) -> list:
    """Folders sessions recently worked in, newest first, that still exist."""
    try:
        from helm.db import get_db
        rows = get_db().execute(
            "SELECT path, MAX(id) AS last FROM messages WHERE type = 'cwd' AND path IS NOT NULL "
            "GROUP BY path ORDER BY last DESC LIMIT ?",
            (limit * 3,),
        ).fetchall()
    except Exception:
        return []
    out, seen = [], set()
    for row in rows:
        path = row["path"]
        key = os.path.normcase(os.path.normpath(path))
        if key in seen or not os.path.isdir(path):
            continue
        seen.add(key)
        out.append({"name": pathlib.Path(path).name or path, "path": path})
        if len(out) >= limit:
            break
    return out


@router.get("/browse")
async def browse_directory(path: str = "", places: int = 0):
    """Subfolders and navigation info for the folder browser.

    `places=1` also returns Home/Desktop/Documents/Downloads, recent project
    folders and (on Windows) the drives, for the picker's side column.
    """
    cwd    = session_cwd()
    target = path.strip() if path.strip() else cwd
    p = pathlib.Path(target).expanduser().resolve()
    error = None
    if not p.exists() or not p.is_dir():
        if path.strip():
            error = "That folder doesn't exist."
        p = pathlib.Path(cwd).resolve()
    dirs, hidden = [], []
    try:
        with os.scandir(p) as it:
            for e in it:
                try:
                    if not e.is_dir():
                        continue
                    dirs.append(e.name)
                    if _is_hidden(e):
                        hidden.append(e.name)
                except OSError:
                    continue
        dirs.sort(key=str.lower)
    except (PermissionError, OSError):
        error = error or "RAPR can't open this folder (no permission)."
    parent = str(p.parent) if str(p) != str(p.parent) else None
    drives = []
    if sys.platform == "win32":
        drives = [f"{d}:\\" for d in _string.ascii_uppercase if pathlib.Path(f"{d}:\\").exists()]
    data = {"path": str(p), "dirs": dirs, "hidden": hidden, "parent": parent,
            "drives": drives, "sep": os.sep, "error": error}
    if places:
        data["places"] = await asyncio.to_thread(_browse_places)
        data["recent"] = await asyncio.to_thread(_recent_projects)
    return JSONResponse(data)


_BAD_FOLDER_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@router.post("/browse/mkdir")
async def browse_mkdir(payload: dict):
    """Create a folder inside `path` (the picker's "New folder")."""
    parent = pathlib.Path(str(payload.get("path") or "")).expanduser()
    name = str(payload.get("name") or "").strip()
    if not name or name in (".", "..") or _BAD_FOLDER_NAME.search(name) or name.endswith((".", " ")):
        return JSONResponse({"error": "Use a folder name without \\ / : * ? \" < > |"}, status_code=400)
    if not parent.is_dir():
        return JSONResponse({"error": "That folder doesn't exist."}, status_code=400)
    new = parent / name
    try:
        new.mkdir()
    except FileExistsError:
        return JSONResponse({"error": "A folder with that name already exists."}, status_code=400)
    except OSError as e:
        return JSONResponse({"error": f"Couldn't create the folder: {e.strerror or e}"}, status_code=400)
    return JSONResponse({"path": str(new.resolve())})


@router.get("/browse/native")
async def browse_native():
    """Open the Windows native folder-picker dialog on the server machine."""
    if sys.platform != "win32":
        return JSONResponse({"path": None})
    path = await asyncio.to_thread(windows_folder_picker)
    return JSONResponse({"path": path})


# ---------------------------------------------------------------------------
# Integration status and discovery
# ---------------------------------------------------------------------------

@router.get("/integrations")
async def list_integrations_endpoint():
    """Return all loaded AI integration plugins with readiness status.

    _find_cli() may run subprocesses, so we offload the whole check to a
    thread to avoid blocking the event loop.
    """

    def _build():
        result = []
        for key, info in _st.integrations.items():
            ready = _integration_ready(key, info)
            result.append({
                "key":        key,
                "name":       info["name"],
                "emoji":      info["emoji"],
                "color":      info["color"],
                "ready":      ready,
                "setup_hint": info.get("setup_hint", "") if not ready else "",
            })
        return result

    result = await asyncio.to_thread(_build)
    return JSONResponse(result)


@router.get("/integrations/gemini/status")
async def gemini_status():
    """Check whether the Gemini CLI is installed. API key is optional."""
    cli_ok = await asyncio.to_thread(_find_cli, "gemini")
    key_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    hint   = "" if cli_ok else "Install Gemini CLI: npm install -g @google/gemini-cli"
    return JSONResponse({
        "ready":         cli_ok,
        "cli_installed": cli_ok,
        "api_key_set":   key_ok,
        "setup_hint":    hint,
    })


@router.get("/integrations/antigravity/status")
async def antigravity_status():
    """Check whether Antigravity CLI (agy) is installed. Auth is optional."""
    import shutil

    def _check():
        # Check PATH first, then %LOCALAPPDATA%\Antigravity\agy.exe on Windows
        if shutil.which("agy"):
            return True
        if sys.platform == "win32":
            local_app = os.environ.get("LOCALAPPDATA", "")
            if local_app:
                import pathlib
                exe = pathlib.Path(local_app) / "Antigravity" / "agy.exe"
                if exe.exists():
                    return True
        return False

    cli_ok = await asyncio.to_thread(_check)
    key_ok = bool(
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )
    hint = "" if cli_ok else "Install Antigravity CLI: see antigravity.google/docs/cli-using"
    return JSONResponse({
        "ready":         cli_ok,
        "cli_installed": cli_ok,
        "api_key_set":   key_ok,
        "setup_hint":    hint,
    })


@router.get("/integrations/claude/status")
async def claude_status():
    """Check whether the Claude CLI is installed. Auth is handled by the CLI itself."""
    cli_ok = await asyncio.to_thread(_find_cli, "claude")
    hint   = "" if cli_ok else "Install Claude CLI — run: claude  (or: npm install -g @anthropic-ai/claude-code)"

    return JSONResponse({
        "ready":         cli_ok,
        "cli_installed": cli_ok,
        "authenticated": cli_ok,
        "setup_hint":    hint,
    })


@router.get("/integrations/debug/{name}")
async def debug_integration(name: str):
    """
    Run every detection step for a CLI tool and return the raw results.
    Used by the Settings panel 'Debug' button to diagnose detection failures.
    Runs entirely in a background thread to avoid blocking the event loop.
    """

    def _run_debug():
        import shutil, subprocess
        home = pathlib.Path.home()
        steps = {}

        steps["which_plain"]   = shutil.which(name)
        steps["which_cmd"]     = shutil.which(name + ".cmd")
        steps["which_exe"]     = shutil.which(name + ".exe")

        candidates = {
            "npm_roaming_cmd":  str(home / "AppData" / "Roaming" / "npm" / f"{name}.cmd"),
            "npm_local_cmd":    str(home / "AppData" / "Local"   / "npm" / f"{name}.cmd"),
            "claude_local_exe": str(home / ".claude" / "local" / f"{name}.exe"),
            "claude_local_cmd": str(home / ".claude" / "local" / f"{name}.cmd"),
            "claude_bin_exe":   str(home / ".claude" / "bin"   / f"{name}.exe"),
            "claude_bin_cmd":   str(home / ".claude" / "bin"   / f"{name}.cmd"),
        }
        steps["candidates"] = {k: {"path": v, "exists": pathlib.Path(v).exists()}
                               for k, v in candidates.items()}

        probe = {}
        try:
            from helm.subprocess_utils import hidden_kwargs
            r = subprocess.run(
                [name, "--version"],
                shell=False, capture_output=True, timeout=5, text=True,
                **hidden_kwargs(),
            )
            probe["returncode"] = r.returncode
            probe["stdout"]     = r.stdout[:500]
            probe["stderr"]     = r.stderr[:500]
            probe["timed_out"]  = False
        except subprocess.TimeoutExpired:
            probe["returncode"] = None
            probe["stdout"]     = ""
            probe["stderr"]     = ""
            probe["timed_out"]  = True
        except Exception as exc:
            probe["error"] = str(exc)
        steps["subprocess_probe"] = probe
        steps["_find_cli_result"] = _find_cli(name)
        return steps

    result = await asyncio.to_thread(_run_debug)
    return JSONResponse(result)


@router.get("/integrations/rescan")
async def rescan_integrations():
    """
    Re-run CLI detection for all loaded AI integrations and return a fresh
    status map. Includes all file-based and custom integrations dynamically —
    not just the hardcoded built-ins.
    """
    from .app import _find_cli_cache

    # Static metadata for built-in CLIs (name, emoji, install hint)
    _BUILTIN_META = {
        "claude":       {"name": "Claude Code",    "emoji": "🤖", "hint": "Install: npm install -g @anthropic-ai/claude-code",
                         "about": "Anthropic's coding agent. Sign in with your Claude plan or an API key.",
                         "install": "npm install -g @anthropic-ai/claude-code",
                         "docs": "https://docs.anthropic.com/en/docs/claude-code/overview"},
        "antigravity":  {"name": "Antigravity",    "emoji": "🪐", "hint": "Install Antigravity CLI: see antigravity.google/docs/cli-using",
                         "about": "Google's coding agent (Gemini models, plus Claude). Replaces the Gemini CLI.",
                         "install": "", "docs": "https://antigravity.google/docs/cli-using"},
        "gemini":       {"name": "Gemini CLI",     "emoji": "✨", "hint": "Install: npm install -g @google/gemini-cli",
                         "about": "Google's older CLI. Personal accounts no longer work; use an API key or Antigravity.",
                         "install": "npm install -g @google/gemini-cli",
                         "docs": "https://github.com/google-gemini/gemini-cli"},
        "codex":        {"name": "Codex CLI",      "emoji": "🧠", "hint": "Install: npm install -g @openai/codex",
                         "about": "OpenAI's coding agent. Sign in with your ChatGPT plan or an API key.",
                         "install": "npm install -g @openai/codex",
                         "docs": "https://github.com/openai/codex"},
        "ollama":       {"name": "Ollama",         "emoji": "🦙", "hint": "Download from https://ollama.com/download",
                         "about": "Run open models on your own computer. Free and private.",
                         "install": "", "docs": "https://ollama.com/download"},
    }

    def _run_rescan():
        _find_cli_cache.clear()
        items = []

        # Built-in CLIs first
        for key, meta in _BUILTIN_META.items():
            if key == "antigravity":
                # Binary is "agy", not "antigravity"
                found = _find_cli("agy")
                if not found and sys.platform == "win32":
                    local_app = os.environ.get("LOCALAPPDATA", "")
                    if local_app:
                        import pathlib as _pl
                        found = (_pl.Path(local_app) / "Antigravity" / "agy.exe").exists()
            else:
                found = _find_cli(key)
            if key == "gemini" and not found:
                continue   # Gemini CLI no longer serves personal accounts; offer Antigravity instead
            item = {
                "key": key, "name": meta["name"], "emoji": meta["emoji"],
                "found": found, "hint": meta["hint"] if not found else "",
                "models": [],
                "about": meta["about"], "install": meta["install"], "docs": meta["docs"],
                # Startable from the catalog only if RAPR loaded it (Gemini is hidden when absent).
                "startable": found and (key == "claude" or key in _st.integrations),
            }
            if key == "ollama" and found:
                from helm.ai_runner.ollama import installed_models
                item["models"] = installed_models()
            items.append(item)

        # All other integrations loaded in state (file-based + custom)
        handled = set(_BUILTIN_META.keys())
        for key, info in _st.integrations.items():
            if key in handled:
                continue
            # NemoClaw uses WSL — use the bridge's own detection logic
            if key == "nemoclaw":
                found = False
                try:
                    from helm.ai_runner.nemoclaw_bridge import detect_nemoclaw
                    nc = detect_nemoclaw(auto_launch_docker=False)
                    found = nc.get("available", False)
                except Exception:
                    logger.debug("Couldn't detect NemoClaw", exc_info=True)
            else:
                # Detect by probing the first element of the integration's command
                found = False
                try:
                    info["build_command"]("test", model=None)
                    found = _integration_ready(key, info)
                except Exception:
                    logger.debug("Couldn't check whether %s is installed", key, exc_info=True)
            items.append({
                "key":    key,
                "name":   info.get("name", key.title()),
                "emoji":  info.get("emoji", "🤖"),
                "found":  found,
                "hint":   info.get("setup_hint", "") if not found else "",
                "models": [],
                "about":  info.get("about", ""),
                "install": info.get("install", ""),
                "docs":   info.get("docs", ""),
                "startable": found,
            })

        # Keep flat legacy keys for backward compat + add rich _items list
        result = {item["key"]: item["found"] for item in items}
        result["ollama_models"] = next(
            (i["models"] for i in items if i["key"] == "ollama"), []
        )
        result["_items"] = items
        return result

    result = await asyncio.to_thread(_run_rescan)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Skills endpoints
# ---------------------------------------------------------------------------

@router.get("/skills")
async def list_skills_endpoint():
    """Return all registered skills for the Settings panel, with pending proposal counts."""
    from helm.skills import list_skills_with_proposals, get_skills_dir, get_pending_proposal_count
    return JSONResponse({
        "skills_dir": get_skills_dir(),
        "skills": list_skills_with_proposals(),
        "pending_proposals_total": get_pending_proposal_count(),
    })


@router.post("/skills/toggle")
async def toggle_skill(payload: dict):
    """Enable or disable skill injection for a specific skill+AI pair."""
    from helm.skills import set_skill_enabled
    skill = payload.get("skill", "")
    ai    = payload.get("ai", "")
    val   = bool(payload.get("enabled", True))
    if not skill or not ai:
        return JSONResponse({"error": "skill and ai are required"}, status_code=400)
    set_skill_enabled(skill, ai, val)
    return JSONResponse({"ok": True, "skill": skill, "ai": ai, "enabled": val})


@router.get("/skills/rescan")
async def rescan_skills():
    """Re-scan the skills directory and return the refreshed registry."""
    from helm.skills import scan_skills, list_skills_with_proposals, get_skills_dir, get_pending_proposal_count
    scan_skills()
    return JSONResponse({
        "skills_dir": get_skills_dir(),
        "skills": list_skills_with_proposals(),
        "pending_proposals_total": get_pending_proposal_count(),
    })


@router.get("/skills/proposals/count")
async def skills_proposal_count():
    """Return count of pending skill proposals — used for nav badge."""
    from helm.skills import get_pending_proposal_count
    return JSONResponse({"count": get_pending_proposal_count()})


@router.get("/integrations/ollama/status")
async def ollama_status():
    """Check whether Ollama is installed, running, and has at least one model pulled."""
    import shutil

    cli_ok = shutil.which("ollama") is not None

    models: list[str] = []
    current_model = (_st.default_models.get("ollama", "") or os.environ.get("OLLAMA_MODEL", "qwen3:4b")).strip()
    model_ok = False

    if cli_ok:
        from helm.ai_runner.ollama import installed_models
        models = await asyncio.to_thread(installed_models)
        model_ok = current_model in models

    if not cli_ok:
        hint = "Install Ollama from https://ollama.com/download"
    elif not models:
        hint = "Pull a model first: ollama pull qwen3:4b"
    elif not model_ok:
        hint = f"Model '{current_model}' not found — set default model in Settings to one of: {', '.join(models)}"
    else:
        hint = ""

    return JSONResponse({
        "ready":         cli_ok and model_ok,
        "cli_installed": cli_ok,
        "models":        models,
        "current_model": current_model,
        "model_ready":   model_ok,
        "setup_hint":    hint,
    })


# ---------------------------------------------------------------------------
# Custom AI integrations — CRUD via Settings UI
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from typing import Optional


class CustomAIRequest(BaseModel):
    key: str
    name: str
    emoji: str = "🤖"
    color: str = "#6b7280"
    command: str                  # e.g. "mygpt --model {model} --prompt {prompt}"
    env_vars: list[str] = []
    env_values: dict[str, str] = {}
    setup_hint: str = ""
    stdin_prompt: bool = False


class CustomAIUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    color: Optional[str] = None
    command: Optional[str] = None
    env_vars: Optional[list[str]] = None
    setup_hint: Optional[str] = None
    stdin_prompt: Optional[bool] = None


@router.get("/integrations/custom")
async def list_custom_integrations():
    """List all custom (user-defined) integrations."""
    from helm.integrations import list_custom
    entries = list_custom()
    return {"ok": True, "integrations": entries}


@router.post("/integrations/custom")
async def add_custom_integration(req: CustomAIRequest):
    """Add a new custom AI integration."""
    from helm.integrations import add_custom
    try:
        payload = req.model_dump()
        env_values = payload.pop("env_values", {}) or {}
        pending_env = []
        for env_key, env_value in env_values.items():
            env_key = (env_key or "").strip().upper()
            env_value = (env_value or "").strip()
            if not env_key or not env_value:
                continue
            if not _CUSTOM_ENV_RE.match(env_key):
                return {"ok": False, "error": f"Invalid env var name: {env_key}"}
            pending_env.append((env_key, env_value))
        key = add_custom(payload)
        for env_key, env_value in pending_env:
            update_env(env_key, env_value)
            os.environ[env_key] = env_value
        return {"ok": True, "key": key}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@router.put("/integrations/custom/{key}")
async def update_custom_integration(key: str, req: CustomAIUpdate):
    """Update an existing custom integration."""
    from helm.integrations import update_custom
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    ok = update_custom(key, updates)
    return {"ok": ok, "error": "" if ok else f"Integration '{key}' not found"}


@router.delete("/integrations/custom/{key}")
async def delete_custom_integration(key: str):
    """Remove a custom integration."""
    from helm.integrations import remove_custom
    ok = remove_custom(key)
    return {"ok": ok}


# ---------------------------------------------------------------------------
# Model discovery & selection endpoints
# ---------------------------------------------------------------------------

_model_cache: dict[str, tuple[float, list[str]]] = {}
_MODEL_CACHE_TTL = 300  # 5 minutes


async def _fetch_models_cached(ai: str) -> list[str]:
    import time
    from helm.web_routes.helpers import (
        _fetch_antigravity_models,
        _fetch_claude_models,
        _fetch_gemini_models,
        _fetch_ollama_models,
        _fetch_openai_models,
    )
    _fetch_fns = {
        "claude":       _fetch_claude_models,
        "codex":        _fetch_openai_models,
        "gemini":       _fetch_gemini_models,
        "antigravity":  _fetch_antigravity_models,
        "ollama":       _fetch_ollama_models,
    }
    fn = _fetch_fns.get(ai)
    if fn is None:
        return []
    now = time.time()
    cached_at, cached_models = _model_cache.get(ai, (0.0, []))
    if now - cached_at < _MODEL_CACHE_TTL and cached_models:
        return cached_models
    models = await asyncio.to_thread(fn)
    _model_cache[ai] = (now, models)
    return models


@router.get("/api/models/selected")
async def get_selected_models():
    """Return all persisted model selections."""
    from helm.model_prefs import get_all_prefs
    selected = get_all_prefs()
    return {"ok": True, "selected": selected}


@router.get("/api/models/{ai}")
async def get_models(ai: str):
    """Return available models for AI (cached 5 min)."""
    models = await _fetch_models_cached(ai)
    from helm.model_prefs import get_model_pref
    selected = get_model_pref(ai)
    return {"ok": True, "ai": ai, "models": models, "selected": selected}


from pydantic import BaseModel as _BaseModel


class _SetModelRequest(_BaseModel):
    model: str | None = None


@router.put("/api/models/{ai}")
async def set_model(ai: str, req: _SetModelRequest):
    """Persist model selection for AI and apply to all active sessions."""
    model = req.model or None
    from helm.model_prefs import set_model_pref
    set_model_pref(ai, model)
    # Apply to all live sessions for this AI
    for sess in _st.sessions.values():
        if sess.get("ai") == ai:
            sess["model"] = model
    return {"ok": True, "ai": ai, "model": model}


@router.post("/api/models/{ai}/refresh")
async def refresh_models(ai: str):
    """Bust cache and re-fetch model list for AI."""
    import time
    _model_cache.pop(ai, None)
    models = await _fetch_models_cached(ai)
    _model_cache[ai] = (time.time(), models)
    return {"ok": True, "ai": ai, "models": models, "count": len(models)}
