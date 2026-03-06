"""
helm/web_routes/session_routes.py — Session creation/deletion, integration status, model discovery endpoints.
"""

import asyncio
import os
import pathlib
import string as _string
import sys
from fastapi import APIRouter
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.session_mgr import session_cwd
from .app import _find_cli, windows_folder_picker


router = APIRouter()


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
            cli_ok = _find_cli(key)
            env_vars_ok = all(os.environ.get(v, "").strip() for v in info.get("env_vars", []))
            ready = cli_ok and env_vars_ok
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
            r = subprocess.run(
                f"{name} --version",
                shell=True, capture_output=True, timeout=5, text=True,
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
    Re-run CLI detection for all known AI tools and return a fresh status map.
    Called by the Settings panel's 'Re-scan' button.
    Runs in a background thread to avoid blocking the event loop.
    """
    from .app import _find_cli_cache

    def _run_rescan():
        import subprocess
        # Bust the cache so we actually re-probe
        _find_cli_cache.clear()

        ollama_cli = _find_cli("ollama")
        ollama_models: list[str] = []
        if ollama_cli:
            try:
                r = subprocess.run(
                    ["ollama", "list"], capture_output=True, text=True, timeout=5,
                )
                for line in r.stdout.splitlines()[1:]:
                    parts = line.split()
                    if parts:
                        ollama_models.append(parts[0])
            except Exception:
                pass

        return {
            "claude":  _find_cli("claude"),
            "gemini":  _find_cli("gemini"),
            "codex":   _find_cli("codex"),
            "ollama":  ollama_cli,
            "ollama_models": ollama_models,
        }

    result = await asyncio.to_thread(_run_rescan)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Skills endpoints
# ---------------------------------------------------------------------------

@router.get("/skills")
async def list_skills_endpoint():
    """Return all registered skills for the Settings panel."""
    from helm.skills import list_skills, get_skills_dir
    return JSONResponse({
        "skills_dir": get_skills_dir(),
        "skills": list_skills(),
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
    from helm.skills import scan_skills, list_skills, get_skills_dir
    scan_skills()
    return JSONResponse({
        "skills_dir": get_skills_dir(),
        "skills": list_skills(),
    })


@router.get("/integrations/ollama/status")
async def ollama_status():
    """Check whether Ollama is installed, running, and has at least one model pulled."""
    import shutil, subprocess

    cli_ok = shutil.which("ollama") is not None

    models: list[str] = []
    current_model = (_st.default_models.get("ollama", "") or os.environ.get("OLLAMA_MODEL", "qwen3:4b")).strip()
    model_ok = False

    if cli_ok:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5,
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
        key = add_custom(req.model_dump())
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
