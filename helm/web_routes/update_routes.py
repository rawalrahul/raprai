"""
helm/web_routes/update_routes.py — Auto-update API endpoints.

Endpoints:
    GET  /update/check       — Check for a new version
    GET  /update/status      — Current update status
    POST /update/now         — Source installs: rerun the installer in the background
    GET  /update/log         — Output of the last update started from the web UI
    POST /update/settings    — Turn the automatic check on or off
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/update", tags=["update"])


@router.get("/check")
async def check_update(force: bool = False):
    """Check if a new version of RAPR AI is available."""
    from helm.updater import check_for_app_update
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
    """Get the current update check status."""
    from helm.updater import get_update_status
    return {"ok": True, **get_update_status()}


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
