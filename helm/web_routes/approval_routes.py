"""
helm/web_routes/approval_routes.py — Approval queue API endpoints.

Provides REST endpoints for:
  - Listing pending approvals
  - Resolving (approve/deny) an approval request
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.state as _st
import helm.approval as _appr

router = APIRouter()


# ---------------------------------------------------------------------------
# Pending approvals
# ---------------------------------------------------------------------------

@router.get("/approval/pending")
async def get_pending():
    """Return all currently pending approval requests."""
    return JSONResponse(_appr.pending())


# ---------------------------------------------------------------------------
# Resolve an approval
# ---------------------------------------------------------------------------

@router.post("/approval/{req_id}")
async def resolve_approval(req_id: str, request: Request):
    """Approve or deny a pending request. Body: {"status": "approved"|"denied"}"""
    body = await request.json()
    status = body.get("status")
    if status not in ("approved", "denied"):
        return JSONResponse({"error": "status must be 'approved' or 'denied'"}, status_code=400)

    ok = _appr.resolve(req_id, status, source="web")
    if not ok:
        return JSONResponse({"error": "Request not found or already resolved"}, status_code=404)

    # Broadcast resolution to all WS clients
    req = _st.approval_queue.get(req_id)
    if req:
        await _appr.broadcast_resolution(req)

    return JSONResponse({"ok": True, "status": status})
