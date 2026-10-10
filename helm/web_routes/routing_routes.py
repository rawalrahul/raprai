"""helm/web_routes/routing_routes.py — "Auto" routing preview."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helm import smart_routing as sr

router = APIRouter()


class RouteRequest(BaseModel):
    text: str
    preferred: str | None = None


@router.post("/api/routing/decide")
async def decide_route(req: RouteRequest):
    """Which AI would Auto pick for this task, and why (nothing is run)."""
    decision = sr.decide(
        req.text or "",
        sr.available_from_state(),
        allowed=sr.allowed_from_budget,
        preferred=req.preferred or None,
    )
    return JSONResponse(decision.as_dict())
