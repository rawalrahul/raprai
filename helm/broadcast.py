"""
helm/broadcast.py — WebSocket broadcast and push helpers.

_broadcast sends JSON to every connected WS client.
_push_message records a message and broadcasts it.
_push_state broadcasts full session state.
_push_thinking broadcasts the thinking/spinner state.
"""

import json
from typing import Optional

from fastapi import WebSocket

import helm.state as _st
from helm.config import logger
from helm.history import save_message_to_log, save_last_state, ts
from helm.kelvin_status import status as _kelvin_status
from helm.session_mgr import focused_session, sessions_state_payload


# ---------------------------------------------------------------------------
# Core broadcast
# ---------------------------------------------------------------------------

async def broadcast(data: dict):
    """Push a JSON message to every connected WebSocket client."""
    # Kelvin's tray badge must keep up even when no browser is open.
    _kelvin_status.observe(data)
    if not _st.ws_clients:
        return
    payload = json.dumps(data, default=str)
    dead: set[WebSocket] = set()
    for ws in _st.ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _st.ws_clients.difference_update(dead)


_broadcast = broadcast  # legacy alias


# ---------------------------------------------------------------------------
# Structured push helpers
# ---------------------------------------------------------------------------

async def push_message(role: str, content: str, ai: Optional[str] = None,
                       source: str = "web", session_id: Optional[str] = None,
                       log: bool = True):
    """Record a chat message and broadcast it to all WS clients."""
    sess = _st.sessions.get(session_id) if session_id else None
    msg = {
        "type": "message", "role": role, "content": content, "ai": ai,
        "source": source, "timestamp": ts(),
        "session_id": session_id,
        "session_name":  sess["name"]  if sess else None,
        "session_emoji": sess["emoji"] if sess else None,
    }
    _st.chat_history.append(msg)
    if len(_st.chat_history) > 200:
        del _st.chat_history[:-200]
    if log:
        save_message_to_log(msg, session_id=session_id)
    await broadcast(msg)


_push_message = push_message  # legacy alias


async def push_state():
    """Save state and broadcast it to all connected clients."""
    save_last_state()
    fs = focused_session()
    await broadcast({
        "type": "state",
        "sessions": sessions_state_payload(),
        "focused_id":     _st.focused_id,
        "focused_ai":     fs["ai"]  if fs else None,
        "focused_cwd":    fs["cwd"] if fs else _st.last_cwd,
        "focused_status": fs["status"] if fs else None,
    })


_push_state = push_state  # legacy alias


async def push_thinking(active: bool, ai: Optional[str] = None,
                        session_id: Optional[str] = None):
    """Broadcast thinking/spinner state. session_id lets the client track per-session state."""
    effective_ai = ai
    if not effective_ai and session_id:
        s = _st.sessions.get(session_id)
        if s:
            effective_ai = s["ai"]
    if not effective_ai:
        fs = focused_session()
        effective_ai = fs["ai"] if fs else None
    await broadcast({
        "type": "thinking",
        "active": active,
        "ai": effective_ai,
        "session_id": session_id,
    })


_push_thinking = push_thinking  # legacy alias


async def push_agent_error(message: str, session_id: Optional[str] = None,
                           source: str = ""):
    """Tell clients an AI run failed for good (after retries and fallbacks).

    The web UI uses this to show Kelvin's error state; the human-readable
    explanation still arrives as a normal system message. Users who opted in
    also get Kelvin's error sticker on Telegram.
    """
    from helm.kelvin_stickers import error_sticker_for_task
    error_sticker_for_task(source)
    await broadcast({
        "type": "agent_error",
        "message": message[:300],
        "session_id": session_id,
    })
