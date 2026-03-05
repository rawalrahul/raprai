"""
helm/web_routes/context_routes.py — API endpoints for context window management.

Endpoints:
  GET  /context/<session_id>   — context usage info for a session
  POST /context/<session_id>/compact — force-compact a session's context
"""

from fastapi import APIRouter

import helm.state as _st
from helm.context_manager import context_info_for_session, force_compact

router = APIRouter(tags=["context"])


@router.get("/context/{session_id}")
async def get_context_info(session_id: str):
    """Return context window usage info for a session."""
    sess = _st.sessions.get(session_id)
    if not sess:
        return {"error": "Session not found"}
    return context_info_for_session(sess)


@router.post("/context/{session_id}/compact")
async def compact_context(session_id: str):
    """Force-compact a session's context (summarise older messages)."""
    sess = _st.sessions.get(session_id)
    if not sess:
        return {"error": "Session not found"}
    result = await force_compact(sess, source="web")
    info = context_info_for_session(sess)
    return {"message": result, **info}
