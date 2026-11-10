"""helm/web_routes/routing_routes.py — "Auto" routing preview."""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helm import smart_routing as sr

router = APIRouter()


class RouteRequest(BaseModel):
    text: str
    preferred: str | None = None


def _ready_ais() -> list[str]:
    """AIs Auto may pick: ones with a running session, and integrations that
    are installed and set up. Every known integration used to count, so Auto
    could pick an AI that isn't installed and fail three times first."""
    import helm.state as _st
    from helm.web_routes.session_routes import _find_cli, _integration_ready
    running = {s["ai"] for s in _st.sessions.values() if s.get("ai") and s.get("status") != "stopped"}
    ready = set(running)
    # Claude Code is built in, not one of the integrations.
    if "claude" not in ready and _find_cli("claude"):
        ready.add("claude")
    for key, info in list(_st.integrations.items()):
        if key in running:
            continue
        try:
            if _integration_ready(key, info):
                ready.add(key)
        except Exception:
            continue
    return sorted(ready)


@router.post("/api/routing/decide")
async def decide_route(req: RouteRequest):
    """Which AI would Auto pick for this task, and why (nothing is run)."""
    available = await asyncio.to_thread(_ready_ais)
    decision = sr.decide(
        req.text or "",
        available,
        allowed=sr.allowed_from_budget,
        preferred=req.preferred or None,
    )
    return JSONResponse(decision.as_dict())
