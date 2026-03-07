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

import pathlib
import shutil
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from helm.config import logger

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

        # If this is an MCP server, try to restart it
        result = {"ok": True, "package_id": pkg_id, "configured_keys": list(env_vars.keys())}
        try:
            from helm.mcp.config import load_config
            mcp_cfg = load_config()
            mcp_id = pkg_id.replace("-", "_")
            if mcp_id in mcp_cfg or pkg_id in mcp_cfg:
                server_id = mcp_id if mcp_id in mcp_cfg else pkg_id
                from helm.mcp.manager import MCPManager
                mgr = MCPManager.get_instance()
                if mgr:
                    await mgr.restart_server(server_id)
                    result["restarted"] = server_id
        except Exception as e:
            logger.warning("Packages: could not restart MCP after config: %s", e)

        return result

    except Exception as e:
        logger.error("Packages: failed to configure %s: %s", pkg_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Installed packages
# ---------------------------------------------------------------------------

@router.get("/installed")
async def list_installed():
    """List all installed packages."""
    from helm.packages.installer import list_installed as _list
    packages = _list()
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
    """Install a package from catalog ID, URL, or uploaded file."""
    from helm.packages.installer import install_package as _install
    from helm.packages import RAPRPackagesError

    try:
        if req.package_id:
            # Install from catalog
            from helm.packages.marketplace import get_download_url
            url = get_download_url(req.package_id)
            if not url:
                raise HTTPException(
                    status_code=404,
                    detail=f"Package '{req.package_id}' not found in catalog"
                )
            result = _install(url, force=req.force)

        elif req.url:
            # Install from URL
            result = _install(req.url, force=req.force)

        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either 'package_id' or 'url'"
            )

        return result

    except RAPRPackagesError as e:
        logger.error("RAPR Packages install error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("RAPR Packages install unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install/upload")
async def install_from_upload(
    file: UploadFile = File(...),
    force: bool = Form(False),
):
    """Install a .raprpkg file uploaded directly."""
    from helm.packages.installer import install_package as _install
    from helm.packages import RAPRPackagesError

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

    except RAPRPackagesError as e:
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


@router.post("/uninstall")
async def uninstall_package(req: UninstallRequest):
    """Uninstall a package by ID."""
    from helm.packages.installer import uninstall_package as _uninstall
    from helm.packages import RAPRPackagesError

    try:
        result = _uninstall(req.package_id)
        return result

    except RAPRPackagesError as e:
        logger.error("RAPR Packages uninstall error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("RAPR Packages uninstall unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
