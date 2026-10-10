"""helm/web_routes/acp_routes.py — the ACP agents you've added."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helm import acp_agents

router = APIRouter()


class AgentsBody(BaseModel):
    agents: list[dict]


@router.get("/api/acp-agents")
async def list_agents():
    return JSONResponse({"agents": acp_agents.load()})


@router.put("/api/acp-agents")
async def save_agents(body: AgentsBody):
    try:
        acp_agents.save(body.agents)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"ok": True, "agents": acp_agents.load()})
