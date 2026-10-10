"""helm/web_routes/playbook_routes.py — browse and switch on/off the playbooks RAPR learned."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helm import playbook_library as lib

router = APIRouter()


class StatusBody(BaseModel):
    status: str


@router.get("/api/playbooks/library")
async def library():
    return JSONResponse({"playbooks": lib.list_all(), "statuses": list(lib.STATUSES)})


@router.get("/api/playbooks/library/{task_type}/{name}")
async def playbook_text(task_type: str, name: str):
    try:
        text = lib.read(task_type, name)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    if text is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"content": text})


@router.post("/api/playbooks/library/{task_type}/{name}/status")
async def playbook_status(task_type: str, name: str, body: StatusBody):
    try:
        meta = lib.set_status(task_type, name, body.status)
    except (ValueError, FileNotFoundError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"status": meta["status"]})


@router.get("/api/playbooks/export")
async def export():
    return JSONResponse(lib.export_bundle())
