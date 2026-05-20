"""
helm/web_routes/packages_routes.py — RAPR Packages marketplace API endpoints.

Endpoints:
    GET  /packages/catalog          — Browse catalog (with optional search)
    GET  /packages/search           — Search catalog by query + type
    GET  /packages/installed        — List installed packages
    GET  /packages/info/{pkg_id}    — Get info for an installed package
    GET  /packages/history          — Install/uninstall transaction log
    POST /packages/install          — Install a package (from catalog or file)
    POST /packages/uninstall        — Remove an installed package
    POST /packages/catalog/refresh  — Force refresh catalog from remote
"""

import asyncio
import os
import pathlib
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from helm.config import logger

# ---------------------------------------------------------------------------
# Background install task tracking
# ---------------------------------------------------------------------------

_install_tasks: dict[str, dict] = {}  # task_id → {status, progress, steps, current_step, ...}

def _current_platform() -> str:
    """Return the normalized platform name used by marketplace command metadata."""
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return system or "unknown"


def _command_for_platform(cmd_info: dict) -> tuple[str, str]:
    """Pick the right command and shell for this OS."""
    current = _current_platform()
    platforms = cmd_info.get("platforms") or cmd_info.get("platform")
    if isinstance(platforms, str):
        platforms = [platforms]
    if platforms and current not in [str(p).lower() for p in platforms]:
        return "", ""

    shell_name = cmd_info.get("shell")
    if not shell_name:
        shell_name = "powershell" if current == "windows" else "default"
    shell_name = str(shell_name).lower()

    command = cmd_info.get("cmd", "")
    if current == "windows":
        command = cmd_info.get("powershell_cmd") or cmd_info.get("windows_cmd") or command
        if cmd_info.get("powershell_cmd"):
            shell_name = "powershell"
    elif current == "macos":
        command = cmd_info.get("macos_cmd") or command
    elif current == "linux":
        command = cmd_info.get("linux_cmd") or command
    return command, shell_name


def _check_command_for_platform(cmd_info: dict, fallback_shell: str) -> tuple[str, str]:
    """Pick the right check command and shell for this OS."""
    current = _current_platform()
    shell_name = cmd_info.get("check_shell") or fallback_shell
    shell_name = str(shell_name).lower()

    command = cmd_info.get("check_cmd", "")
    if current == "windows":
        command = (
            cmd_info.get("powershell_check_cmd")
            or cmd_info.get("windows_check_cmd")
            or command
        )
        if cmd_info.get("powershell_check_cmd"):
            shell_name = "powershell"
    elif current == "macos":
        command = cmd_info.get("macos_check_cmd") or command
    elif current == "linux":
        command = cmd_info.get("linux_check_cmd") or command

    return command, shell_name


def _run_catalog_command(command: str, shell_name: str, timeout: int, cwd: str | None = None):
    """Run a catalog command with Windows-aware shell handling."""
    cwd = os.path.expandvars(os.path.expanduser(cwd)) if cwd else None
    # Prevent console window flash on Windows
    no_window = {"creationflags": subprocess.CREATE_NO_WINDOW} if platform.system().lower().startswith("win") else {}
    if shell_name in ("powershell", "pwsh"):
        exe = "pwsh" if shell_name == "pwsh" else "powershell"
        return subprocess.run(
            [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            **no_window,
        )
    if shell_name in ("cmd", "cmd.exe"):
        return subprocess.run(
            ["cmd", "/c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            **no_window,
        )
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        **no_window,
    )


def _run_install_background(task_id: str, package_id: str, url: str | None, force: bool):
    """Run the full install in a background thread with progress tracking.

    url=None means command-only install (no .raprpkg file to download).
    """
    task = _install_tasks[task_id]

    try:
        if url:
            # Step 1: Download and install the package files
            task["current_step"] = "Downloading package..."
            task["progress"] = 10

            from helm.packages.installer import install_package as _install
            result = _install(url, force=force)

            task["progress"] = 40
            task["current_step"] = "Package files installed"
            task["install_result"] = result
        else:
            # No package file — jump straight to install_commands
            task["progress"] = 10
            task["current_step"] = "Running install commands..."

        # Step 2: Run install_commands from catalog (for CLI skills)
        from helm.packages.marketplace import get_catalog_entry
        entry = get_catalog_entry(package_id)
        install_cmds = []
        if entry:
            install_cmds = entry.get("install_commands") or []

        if install_cmds:
            total_cmds = len(install_cmds)
            for i, cmd_info in enumerate(install_cmds):
                cmd, shell_name = _command_for_platform(cmd_info)
                label = cmd_info.get("label", f"Running: {cmd[:40]}...")
                check_cmd, check_shell_name = _check_command_for_platform(cmd_info, shell_name)
                timeout_seconds = int(cmd_info.get("timeout_seconds", 300))
                check_timeout_seconds = int(cmd_info.get("check_timeout_seconds", 15))
                cwd = cmd_info.get("cwd") or cmd_info.get("working_dir")

                if cmd_info.get("manual") or cmd_info.get("run") is False or cmd_info.get("long_running"):
                    detail = cmd_info.get("instructions") or cmd_info.get("detail") or cmd or "Manual setup required."
                    task["steps"].append({"label": label, "status": "manual", "detail": detail})
                    task["current_step"] = f"Manual step: {label}"
                    task["progress"] = 40 + int(50 * (i + 1) / total_cmds)
                    continue

                if not cmd:
                    task["steps"].append({"label": label, "status": "skipped", "detail": "No command for this platform"})
                    task["progress"] = 40 + int(50 * (i + 1) / total_cmds)
                    continue

                # Check if already installed
                if check_cmd:
                    task["current_step"] = f"Checking: {label}..."
                    try:
                        check_result = _run_catalog_command(
                            check_cmd, check_shell_name, check_timeout_seconds, cwd
                        )
                        if check_result.returncode == 0:
                            task["current_step"] = f"Already installed: {label}"
                            task["progress"] = 40 + int(50 * (i + 1) / total_cmds)
                            task["steps"].append({"label": label, "status": "skipped", "detail": "Already installed"})
                            continue
                    except Exception:
                        pass  # Check failed — proceed with install

                # Run the install command
                task["current_step"] = label
                task["progress"] = 40 + int(50 * i / total_cmds)
                task["steps"].append({"label": label, "status": "running"})

                try:
                    proc = _run_catalog_command(cmd, shell_name, timeout_seconds, cwd)
                    if proc.returncode == 0:
                        task["steps"][-1]["status"] = "done"
                    else:
                        error_msg = (proc.stderr or proc.stdout or "").strip()[-200:]
                        task["steps"][-1]["status"] = "failed"
                        task["steps"][-1]["detail"] = error_msg
                        logger.warning("Install command failed for %s: %s → %s", package_id, cmd, error_msg)
                except subprocess.TimeoutExpired:
                    task["steps"][-1]["status"] = "failed"
                    task["steps"][-1]["detail"] = f"Timed out after {timeout_seconds} seconds"
                except Exception as e:
                    task["steps"][-1]["status"] = "failed"
                    task["steps"][-1]["detail"] = str(e)

                task["progress"] = 40 + int(50 * (i + 1) / total_cmds)

        # Done
        task["progress"] = 100
        task["status"] = "done"
        task["current_step"] = "Installation complete"

    except Exception as e:
        task["status"] = "failed"
        task["current_step"] = f"Failed: {str(e)[:100]}"
        task["error"] = str(e)
        logger.error("Background install failed for %s: %s", package_id, e)

router = APIRouter(prefix="/packages", tags=["packages"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class InstallRequest(BaseModel):
    """Install a package by catalog ID or URL."""
    package_id: Optional[str] = None   # Install from catalog
    url: Optional[str] = None          # Install from URL
    force: bool = False                # Overwrite existing


class UninstallRequest(BaseModel):
    """Uninstall a package by ID."""
    package_id: str


class ConfigureRequest(BaseModel):
    """Save API keys / env vars for a package."""
    package_id: str
    env_vars: dict[str, str] = {}   # {"API_KEY": "value", ...}


class ToggleRequest(BaseModel):
    """Enable or disable an installed package."""
    package_id: str
    enabled: bool = True


# ---------------------------------------------------------------------------
# Catalog endpoints
# ---------------------------------------------------------------------------

@router.get("/catalog")
async def get_catalog(q: str = "", type: str = "", limit: int = 50):
    """Browse or search the marketplace catalog."""
    from helm.packages.marketplace import search_catalog
    results = search_catalog(query=q, pkg_type=type or None, limit=limit)
    return {"ok": True, "packages": results, "count": len(results)}


@router.get("/search")
async def search(q: str = "", type: str = "", limit: int = 50):
    """Search catalog (alias for /catalog with query params)."""
    from helm.packages.marketplace import search_catalog
    results = search_catalog(query=q, pkg_type=type or None, limit=limit)
    return {"ok": True, "packages": results, "count": len(results)}


@router.post("/catalog/refresh")
async def refresh_catalog():
    """Force refresh catalog from remote."""
    from helm.packages.marketplace import get_catalog
    catalog = get_catalog(force_refresh=True)
    return {"ok": True, "count": len(catalog)}


@router.get("/updates")
async def check_updates(force: bool = False):
    """Check for available package updates."""
    from helm.packages.marketplace import check_updates as _check
    updates = _check(force=force)
    return {"ok": True, "updates": updates, "count": len(updates)}


@router.get("/setup/{package_id}")
async def package_setup_info(package_id: str):
    """Get setup information for a catalog package (API keys, OAuth, etc.)."""
    from helm.packages.marketplace import get_package_setup_info
    setup = get_package_setup_info(package_id)
    if not setup:
        raise HTTPException(status_code=404, detail=f"No setup info for '{package_id}'")
    return {"ok": True, "package_id": package_id, "setup": setup}


@router.post("/configure")
async def configure_package(req: ConfigureRequest):
    """
    Save environment variables for a package (API keys, tokens, etc.).
    Updates the .env file and restarts the MCP server if applicable.
    """
    pkg_id = req.package_id
    env_vars = req.env_vars

    if not env_vars:
        raise HTTPException(status_code=400, detail="No env_vars provided")

    # Update .env file
    try:
        from helm.paths import user_data_dir
        env_path = user_data_dir() / ".env"

        # Read existing .env
        existing = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

        # Merge new values
        for key, value in env_vars.items():
            if value:  # Only set non-empty values
                existing[key] = value
                # Also set in current process environment
                import os
                os.environ[key] = value

        # Write back .env
        lines = [f"{k}={v}" for k, v in sorted(existing.items())]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        logger.info("Packages: updated env vars for %s: %s", pkg_id, list(env_vars.keys()))

        # If this is an MCP server, reload all servers so it picks up new env vars
        result = {"ok": True, "package_id": pkg_id, "configured_keys": list(env_vars.keys())}
        try:
            from helm.mcp.manager import MCPManager
            mgr = MCPManager.get_instance()
            if mgr and hasattr(mgr, "reload_servers"):
                await mgr.reload_servers()
                result["reloaded"] = True
        except Exception as e:
            logger.warning("Packages: could not reload MCP servers after config: %s", e)

        return result

    except Exception as e:
        logger.error("Packages: failed to configure %s: %s", pkg_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Installed packages
# ---------------------------------------------------------------------------

@router.get("/installed")
async def list_installed():
    """List all installed packages, enriched with catalog setup info."""
    from helm.packages.installer import list_installed as _list
    packages = _list()

    # Enrich with setup info from catalog (so frontend knows OAuth vs api_key)
    # and check connected state for OAuth MCPs
    try:
        from helm.packages.marketplace import get_catalog_entry
        for pkg in packages:
            pkg_id = pkg.get("id", "")
            entry = get_catalog_entry(pkg_id)
            setup = entry.get("setup") if entry else None

            # Fallback: if no catalog setup, try known OAuth MCPs
            # e.g. "github-oauth" → check hardcoded "github" OAuth config
            if not setup:
                base = pkg_id.lower().replace("-oauth", "").replace("_oauth", "")
                from helm.web_routes.plugins_routes import _KNOWN_OAUTH_MCPS
                known = _KNOWN_OAUTH_MCPS.get(base) or _KNOWN_OAUTH_MCPS.get(pkg_id.lower())
                if known and known.get("auth"):
                    kauth = known["auth"]
                    setup = {
                        "type": "oauth",
                        "token_env": kauth.get("token_env", ""),
                        "client_id": kauth.get("client_id", ""),
                        "provider": kauth.get("proxy_provider", base),
                    }

            if setup:
                pkg["setup"] = setup
                # Check if OAuth token exists (connected)
                token_env = setup.get("token_env", "")
                if token_env:
                    try:
                        from helm.token_vault import load_token
                        token = load_token(token_env)
                        pkg["connected"] = bool(token and token.strip())
                    except Exception:
                        pkg["connected"] = bool(os.environ.get(token_env, ""))
    except Exception:
        pass

    return {"ok": True, "packages": packages, "count": len(packages)}


@router.get("/info/{package_id}")
async def package_info(package_id: str):
    """Get info for a specific installed package."""
    from helm.packages.installer import get_package_info
    info = get_package_info(package_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Package '{package_id}' not found")
    return {"ok": True, "package": info}


@router.get("/history")
async def install_history(limit: int = 50):
    """Get install/uninstall transaction history."""
    from helm.packages.installer import get_install_history
    history = get_install_history(limit=limit)
    return {"ok": True, "history": history, "count": len(history)}


# ---------------------------------------------------------------------------
# Install / Uninstall
# ---------------------------------------------------------------------------

@router.post("/install")
async def install_package(req: InstallRequest):
    """Install a package from catalog ID, URL, or uploaded file.

    Returns a task_id for tracking background install progress, or
    requires_manual_setup=True with setup info when no auto-install is possible.
    """
    if req.package_id:
        from helm.packages.marketplace import get_download_url, get_catalog_entry
        url = get_download_url(req.package_id)
        package_id = req.package_id

        if not url:
            # No downloadable file — check what we can do
            entry = get_catalog_entry(package_id)
            if not entry:
                raise HTTPException(
                    status_code=404,
                    detail=f"Package '{package_id}' not found in catalog"
                )

            install_cmds = entry.get("install_commands") or []
            if not install_cmds:
                # Nothing to auto-run — return setup info for the frontend to show
                setup = entry.get("setup") or {}
                return JSONResponse({
                    "ok": False,
                    "requires_manual_setup": True,
                    "package_id": package_id,
                    "setup": setup,
                    "detail": entry.get("install_instructions") or (
                        f"'{package_id}' requires manual installation. "
                        "Check the package page for instructions."
                    ),
                })
            # Has install_commands but no .raprpkg — run commands only (url=None)

    elif req.url:
        url = req.url
        package_id = req.url.split("/")[-1].replace(".raprpkg", "")
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'package_id' or 'url'"
        )

    # Create a background task
    task_id = uuid.uuid4().hex[:12]
    _install_tasks[task_id] = {
        "task_id": task_id,
        "package_id": package_id,
        "status": "running",
        "progress": 0,
        "current_step": "Starting install...",
        "steps": [],
        "error": None,
        "install_result": None,
    }

    # Run in background thread
    thread = threading.Thread(
        target=_run_install_background,
        args=(task_id, package_id, url, req.force),
        daemon=True,
    )
    thread.start()

    return {"ok": True, "task_id": task_id, "package_id": package_id, "status": "running"}


@router.get("/install/status/{task_id}")
async def install_status(task_id: str):
    """Get the progress of a background install task."""
    task = _install_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Install task not found")
    return task


@router.post("/install/upload")
async def install_from_upload(
    file: UploadFile = File(...),
    force: bool = Form(False),
):
    """Install a .raprpkg file uploaded directly."""
    from helm.packages.installer import install_package as _install
    from helm.packages import HelmPackError

    if not file.filename or not file.filename.endswith(".raprpkg"):
        raise HTTPException(
            status_code=400,
            detail="File must have .raprpkg extension"
        )

    # Save to temp file
    tmp_dir = tempfile.mkdtemp(prefix="packages_upload_")
    tmp_path = pathlib.Path(tmp_dir) / file.filename

    try:
        with open(str(tmp_path), "wb") as f:
            content = await file.read()
            # Size check (50MB)
            if len(content) > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large (max 50MB)")
            f.write(content)

        result = _install(tmp_path, force=force)
        return result

    except HelmPackError as e:
        logger.error("RAPR Packages upload install error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("RAPR Packages upload unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


@router.post("/toggle")
async def toggle_package(req: ToggleRequest):
    """Enable or disable an installed skill package."""
    pkg_id = req.package_id
    enabled = req.enabled

    try:
        from helm.packages.skill_installer import toggle_skill
        result = toggle_skill(pkg_id, enabled)
        return result
    except Exception as e:
        logger.error("Toggle failed for %s: %s", pkg_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uninstall")
async def uninstall_package(req: UninstallRequest):
    """Uninstall a package by ID."""
    from helm.packages.installer import uninstall_package as _uninstall
    from helm.packages import HelmPackError

    try:
        result = _uninstall(req.package_id)
        return result

    except HelmPackError as e:
        logger.error("RAPR Packages uninstall error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("RAPR Packages uninstall unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
