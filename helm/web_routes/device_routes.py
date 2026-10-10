"""
helm/web_routes/device_routes.py — Device linking API endpoints.

Endpoints:
    GET  /device/status     — Check if app is linked to raprai.com
    POST /device/activate   — Activate with an activation code
    GET  /device/connections — Get synced connections
    POST /device/sync       — Force sync connections from raprai.com
    POST /device/unlink     — Unlink (stop syncing and sending usage counts)

Linking is optional; RAPR works without it.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from helm.config import logger

router = APIRouter(prefix="/device", tags=["device"])


class ActivateRequest(BaseModel):
    code: str


@router.get("/status")
async def device_status():
    """Check if the app is linked to a raprai.com account."""
    from helm.device_link import get_link_status
    status = get_link_status()
    return {"ok": True, **status}


@router.post("/activate")
async def activate(req: ActivateRequest):
    """Activate the app using an activation code from raprai.com."""
    from helm.device_link import activate_with_code
    result = activate_with_code(req.code)
    return result


@router.get("/connections")
async def get_connections():
    """Get synced connections (cached locally)."""
    from helm.device_link import get_synced_connections, get_device_token
    token = get_device_token()
    if not token:
        return {"ok": False, "error": "App not linked", "connections": {}}
    connections = get_synced_connections()
    return {"ok": True, "connections": connections}


@router.post("/sync")
async def force_sync():
    """Force sync connections from raprai.com."""
    from helm.device_link import sync_connections
    result = sync_connections(force=True)
    return result


@router.post("/unlink")
async def unlink():
    """Unlink the app from raprai.com."""
    from helm.device_link import unlink_device
    unlink_device()
    return {"ok": True}
