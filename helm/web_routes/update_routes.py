"""
helm/web_routes/update_routes.py — Auto-update API endpoints.

Endpoints:
    GET  /update/check       — Check for a new version
    GET  /update/status      — Current update/download status
    POST /update/download    — Start downloading the update installer
    POST /update/apply       — Launch the installer and restart
    POST /update/now         — Source installs: rerun the installer in the background
    GET  /update/log         — Output of the last update started from the web UI
    POST /update/settings    — Turn the automatic check on or off
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from helm.config import logger

router = APIRouter(prefix="/update", tags=["update"])


class DownloadRequest(BaseModel):
    url: Optional[str] = None  # Override download URL (normally auto-detected)


class ApplyRequest(BaseModel):
    installer_path: Optional[str] = None  # Override path (normally auto-detected)


@router.get("/check")
async def check_update(force: bool = False):
    """Check if a new version of RAPR AI is available."""
    from helm.updater import check_for_app_update, get_update_status
    from helm.version import APP_VERSION

    update = check_for_app_update(force=force)
    if update:
        return {
            "ok": True,
            "update_available": True,
            **update,
        }
    return {
        "ok": True,
        "update_available": False,
        "current_version": APP_VERSION,
    }


@router.get("/status")
async def update_status():
    """Get current update check and download status."""
    from helm.updater import get_update_status
    return {"ok": True, **get_update_status()}


@router.post("/download")
async def download_update(req: DownloadRequest):
    """Start downloading the update installer in the background."""
    from helm.updater import check_for_app_update, download_update_async, get_update_status

    status = get_update_status()

    # If already downloading, return current progress
    if status["download"]["status"] == "downloading":
        return {"ok": True, "message": "Download already in progress", "download": status["download"]}

    # If already downloaded, return the path
    if status["download"]["status"] == "ready":
        return {"ok": True, "message": "Update already downloaded", "download": status["download"]}

    # Determine download URL
    url = req.url
    if not url:
        update = check_for_app_update()
        if not update:
            return {"ok": False, "error": "No update available"}
        url = update.get("download_url", "")

    if not url:
        return {"ok": False, "error": "No download URL found for the update"}

    # Start background download
    download_update_async(url)

    return {"ok": True, "message": "Download started", "download_url": url}


@router.post("/apply")
async def apply_update(req: ApplyRequest):
    """Launch the downloaded installer to apply the update."""
    from helm.updater import apply_update as _apply

    result = _apply(installer_path=req.installer_path)
    return result


class SettingsRequest(BaseModel):
    auto_check: bool


@router.post("/now")
async def update_now():
    """Source installs: update in the background; RAPR restarts by itself."""
    from helm.updater import start_source_update
    return start_source_update()


@router.get("/log")
async def update_log():
    from helm.updater import read_update_log
    return {"ok": True, **read_update_log()}


@router.post("/settings")
async def update_settings(req: SettingsRequest):
    """UPDATE_CHECK=0 stops the automatic check; "Check now" still works."""
    import os
    from helm.web_routes.app import update_env
    value = "1" if req.auto_check else "0"
    update_env("UPDATE_CHECK", value)
    os.environ["UPDATE_CHECK"] = value
    return {"ok": True, "auto_check": req.auto_check}
