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
import pathlib
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

def _run_install_background(task_id: str, package_id: str, url: str, force: bool):
    """Run the full install in a background thread with progress tracking."""
    task = _install_tasks[task_id]

    try:
        # Step 1: Download and install the package files
        task["current_step"] = "Downloading package..."
        task["progress"] = 10

        from helm.packages.installer import install_package as _install
        result = _install(url, force=force)

        task["progress"] = 40
        task["current_step"] = "Package files installed"
        task["install_result"] = result

        # Step 2: Run install_commands from catalog (for CLI skills)
        from helm.packages.marketplace import get_catalog_entry
        entry = get_catalog_entry(package_id)
        install_cmds = []
        if entry:
            install_cmds = entry.get("install_commands") or []

        if install_cmds:
            total_cmds = len(install_cmds)
            for i, cmd_info in enumerate(install_cmds):
                cmd = cmd_info.get("cmd", "")
                label = cmd_info.get("label", f"Running: {cmd[:40]}...")
                check_cmd = cmd_info.get("check_cmd", "")

                if not cmd:
                    continue

                # Check if already installed
                if check_cmd:
                    task["current_step"] = f"Checking: {label}..."
                    try:
                        check_result = subprocess.run(
                            check_cmd, shell=True, capture_output=True, timeout=15
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
                    proc = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=300
                    )
                    if proc.returncode == 0:
                        task["steps"][-1]["status"] = "done"
                    else:
                        error_msg = (proc.stderr or proc.stdout or "").strip()[-200:]
                        task["steps"][-1]["status"] = "failed"
                        task["steps"][-1]["detail"] = error_msg
                        logger.warning("Install command failed for %s: %s → %s", package_id, cmd, error_msg)
                except subprocess.TimeoutExpired:
                    task["steps"][-1]["status"] = "failed"
                    task["steps"][-1]["detail"] = "Timed out after 5 minutes"
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
            entry = get_catalog_entry(pkg.get("id", ""))
            if entry and entry.get("setup"):
                pkg["setup"] = entry["setup"]
                # Check if OAuth token exists (connected)
                setup = entry["setup"]
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

    Returns a task_id for tracking background install progress.
    """
    if req.package_id:
        from helm.packages.marketplace import get_download_url
        url = get_download_url(req.package_id)
        if not url:
            raise HTTPException(
                status_code=404,
                detail=f"Package '{req.package_id}' not found in catalog"
            )
        package_id = req.package_id
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
