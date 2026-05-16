"""helm/web_routes/council_routes.py — Council REST endpoints."""

import asyncio
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import helm.state as _st
from helm.council.models import make_council, make_council_message
from helm.council.executor import run_council

router = APIRouter()


class StartCouncilRequest(BaseModel):
    topic: str
    participant_session_ids: list
    moderator_session_id: str
    max_rounds: int = 10


class InjectRequest(BaseModel):
    message: str


@router.post("/api/council/start")
async def start_council(req: StartCouncilRequest):
    # Validate sessions exist
    mod_sess = _st.sessions.get(req.moderator_session_id)
    if not mod_sess:
        return JSONResponse({"error": "Moderator session not found"}, status_code=400)

    participants = []
    for sid in req.participant_session_ids:
        sess = _st.sessions.get(sid)
        if not sess:
            return JSONResponse({"error": f"Session {sid} not found"}, status_code=400)
        ai = sess.get("ai") or "shell"
        participants.append({
            "session_id": sid,
            "ai": ai,
            "name": sess.get("name", ai),
            "color": sess.get("color", "#6b7280"),
            "emoji": sess.get("emoji", "🤖"),
        })

    council_id = f"council-{uuid4().hex[:8]}"
    mod_ai = mod_sess.get("ai") or "shell"

    council = make_council(
        id=council_id,
        topic=req.topic,
        cwd=mod_sess.get("cwd", "."),
        moderator_ai=mod_ai,
        moderator_session_id=req.moderator_session_id,
        participants=participants,
        max_rounds=req.max_rounds,
    )
    _st.councils[council_id] = council

    asyncio.create_task(run_council(council_id))

    return JSONResponse({"council_id": council_id})


@router.delete("/api/council/{council_id}/stop")
async def stop_council(council_id: str):
    council = _st.councils.get(council_id)
    if not council:
        return JSONResponse({"error": "Council not found"}, status_code=404)
    council["status"] = "stopped"
    return JSONResponse({"ok": True})


@router.post("/api/council/{council_id}/inject")
async def inject_message(council_id: str, req: InjectRequest):
    council = _st.councils.get(council_id)
    if not council:
        return JSONResponse({"error": "Council not found"}, status_code=404)
    msg = make_council_message("user", req.message)
    council["messages"].append(msg)
    return JSONResponse({"ok": True})


@router.get("/api/council/list")
async def list_councils():
    active = list(_st.councils.values())
    history = list(_st.council_history)
    return JSONResponse({"active": active, "history": history})
