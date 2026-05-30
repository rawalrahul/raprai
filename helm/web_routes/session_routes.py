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
            pass

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


@router.get("/browse")
async def browse_directory(path: str = ""):
    """Return subdirectories and navigation info for the folder browser."""
    cwd    = session_cwd()
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
            # NemoClaw lives in WSL — _find_cli won't find it on Windows PATH,
            # so use the bridge's cached detection instead
            if key == "nemoclaw":
                try:
                    from helm.ai_runner.nemoclaw_bridge import is_available
                    cli_ok = is_available()
                except Exception:
                    cli_ok = False
            else:
                cli_ok = _find_cli(key)
            env_vars_ok = all(os.environ.get(v, "").strip() for v in info.get("env_vars", []))
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
        from .app import _find_cli_cache
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
        "claude":       {"name": "Claude Code",    "emoji": "🤖", "hint": "Install: npm install -g @anthropic-ai/claude-code"},
        "gemini":       {"name": "Gemini CLI",     "emoji": "✨", "hint": "Install: npm install -g @google/gemini-cli"},
        "antigravity":  {"name": "Antigravity",    "emoji": "🪐", "hint": "Install Antigravity CLI: see antigravity.google/docs/cli-using"},
        "codex":        {"name": "Codex CLI",      "emoji": "🧠", "hint": "Install: npm install -g @openai/codex"},
        "ollama":       {"name": "Ollama",         "emoji": "🦙", "hint": "Download from https://ollama.com/download"},
    }

    def _run_rescan():
        import subprocess
        from helm.subprocess_utils import hidden_kwargs
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
            item = {
                "key": key, "name": meta["name"], "emoji": meta["emoji"],
                "found": found, "hint": meta["hint"] if not found else "",
                "models": [],
            }
            if key == "ollama" and found:
                try:
                    r = subprocess.run(
                        ["ollama", "list"], capture_output=True, text=True, timeout=5, **hidden_kwargs(),
                    )
                    for line in r.stdout.splitlines()[1:]:
                        parts = line.split()
                        if parts:
                            item["models"].append(parts[0])
                except Exception:
                    pass
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
                    pass
            else:
                # Detect by probing the first element of the integration's command
                found = False
                try:
                    cmd = info["build_command"]("test", model=None)
                    found = _integration_ready(key, info)
                except Exception:
                    pass
            items.append({
                "key":    key,
                "name":   info.get("name", key.title()),
                "emoji":  info.get("emoji", "🤖"),
                "found":  found,
                "hint":   info.get("setup_hint", "") if not found else "",
                "models": [],
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
    import shutil, subprocess
    from helm.subprocess_utils import hidden_kwargs

    cli_ok = shutil.which("ollama") is not None

    models: list[str] = []
    current_model = (_st.default_models.get("ollama", "") or os.environ.get("OLLAMA_MODEL", "qwen3:4b")).strip()
    model_ok = False

    if cli_ok:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5, **hidden_kwargs(),
            )
            for line in result.stdout.splitlines()[1:]:   # skip header row
                parts = line.split()
                if parts:
                    models.append(parts[0])
            model_ok = current_model in models
        except Exception:
            pass

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
_OAUTH_CLI_MODEL_DISABLED = {"claude", "gemini", "codex"}


async def _fetch_models_cached(ai: str) -> list[str]:
    import time
    from helm.web_routes.helpers import (
        _fetch_antigravity_models,
        _fetch_ollama_models,
    )
    if ai in _OAUTH_CLI_MODEL_DISABLED:
        return []
    _fetch_fns = {
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
    for ai in _OAUTH_CLI_MODEL_DISABLED:
        selected[ai] = None
    return {"ok": True, "selected": selected}


@router.get("/api/models/{ai}")
async def get_models(ai: str):
    """Return available models for AI (cached 5 min)."""
    if ai in _OAUTH_CLI_MODEL_DISABLED:
        return {
            "ok": True,
            "ai": ai,
            "models": [],
            "selected": None,
            "model_switching": False,
            "reason": "Model discovery and switching are disabled for OAuth CLI integrations.",
        }
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
    if ai in _OAUTH_CLI_MODEL_DISABLED:
        return {
            "ok": False,
            "ai": ai,
            "model": None,
            "error": "Model switching is disabled for OAuth CLI integrations.",
        }
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
    if ai in _OAUTH_CLI_MODEL_DISABLED:
        _model_cache.pop(ai, None)
        return {
            "ok": True,
            "ai": ai,
            "models": [],
            "count": 0,
            "model_switching": False,
            "reason": "Model discovery is disabled for OAuth CLI integrations.",
        }
    import time
    _model_cache.pop(ai, None)
    models = await _fetch_models_cached(ai)
    _model_cache[ai] = (time.time(), models)
    return {"ok": True, "ai": ai, "models": models, "count": len(models)}
