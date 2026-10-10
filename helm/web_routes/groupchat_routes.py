"""helm/web_routes/groupchat_routes.py — Group chat REST endpoints."""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import helm.state as _st
import helm.groupchat as gc

router = APIRouter()


class CreateGroupRequest(BaseModel):
    name: str = ""
    about: str = ""
    member_session_ids: list[str] = []
    # AIs to add even if no session is open for them (e.g. "claude", "gemini");
    # an open session of that AI is reused, otherwise one is started.
    member_ais: list[str] = []


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    about: Optional[str] = None
    member_session_ids: Optional[list[str]] = None


class SendRequest(BaseModel):
    text: str


def _err(msg: str, code: int = 400) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=code)


def _known_ai(ai: str) -> bool:
    if ai == "claude" or ai in _st.integrations:
        return True
    if ai.startswith("acp:"):
        from helm import acp_agents
        return acp_agents.get(ai[4:]) is not None
    return False


def _sessions_for_ais(ais: list[str], taken: set[str]) -> tuple[list[dict], Optional[str]]:
    """One session per AI: reuse an open one not already picked, else start a new one."""
    from helm.session_mgr import make_session, session_cwd
    out = []
    for ai in dict.fromkeys(a.strip() for a in ais if a and a.strip()):
        if not _known_ai(ai):
            return [], f"{ai} isn't installed in RAPR"
        sess = next((s for s in _st.sessions.values()
                     if s.get("ai") == ai and s.get("status") != "stopped" and s["id"] not in taken), None)
        if sess is None:
            sess = make_session(ai, cwd=session_cwd())
        taken.add(sess["id"])
        out.append(sess)
    return out, None


def _resolve_members(session_ids: list[str], ais: list[str]) -> tuple[list[dict], Optional[str]]:
    """Sessions picked directly, plus a session for each AI picked."""
    picked, err = _member_sessions(session_ids, allow_empty=True)
    if err:
        return [], err
    more, err = _sessions_for_ais(ais, {s["id"] for s in picked})
    if err:
        return [], err
    members = picked + more
    if not members:
        return [], "Pick at least one AI"
    if len(members) > gc.MAX_MEMBERS:
        return [], f"A group can have at most {gc.MAX_MEMBERS} members"
    return members, None


def _member_sessions(session_ids: list[str], allow_empty: bool = False) -> tuple[list[dict], Optional[str]]:
    """Resolve and validate session ids for group membership."""
    seen, out = set(), []
    for sid in session_ids:
        if sid in seen:
            continue
        seen.add(sid)
        sess = _st.sessions.get(sid)
        if not sess:
            return [], f"Session {sid} not found"
        if not sess.get("ai"):
            return [], f"{sess.get('name', sid)} is a shell session; only AI sessions can join a group"
        out.append(sess)
    if not out and not allow_empty:
        return [], "Pick at least one AI session"
    if len(out) > gc.MAX_MEMBERS:
        return [], f"A group can have at most {gc.MAX_MEMBERS} members"
    return out, None


def _summary(g: dict) -> dict:
    last = g["messages"][-1] if g["messages"] else None
    s = {k: v for k, v in gc._public(g).items() if k != "messages"}
    s["message_count"] = len(g["messages"])
    if last:
        who = "You" if last["role"] == "user" else last.get("author_name", "")
        s["last_message"] = f"{who}: {last['content'][:120]}" if who else last["content"][:120]
    return s


@router.get("/api/groups")
async def list_groups():
    gc.load_groups()
    items = sorted(gc.groups.values(), key=lambda g: g.get("updated_at", 0), reverse=True)
    return JSONResponse({"groups": [_summary(g) for g in items]})


@router.get("/api/groups/{group_id}")
async def get_group(group_id: str):
    gc.load_groups()
    g = gc.groups.get(group_id)
    if not g:
        return _err("Group not found", 404)
    return JSONResponse({"group": gc._public(g)})


@router.post("/api/groups")
async def create_group(req: CreateGroupRequest):
    gc.load_groups()
    sessions, err = _resolve_members(req.member_session_ids, req.member_ais)
    if err:
        return _err(err)
    group = gc.make_group(req.name, req.about, sessions)
    from helm.broadcast import push_state
    await push_state()   # sessions started for the group show up in the sidebar
    gc.save_groups()
    await gc.broadcast_group(group)
    return JSONResponse({"group": gc._public(group)})


@router.patch("/api/groups/{group_id}")
async def update_group(group_id: str, req: UpdateGroupRequest):
    gc.load_groups()
    g = gc.groups.get(group_id)
    if not g:
        return _err("Group not found", 404)
    if req.name is not None and req.name.strip():
        g["name"] = req.name.strip()
    if req.about is not None:
        g["about"] = req.about.strip()
    if req.member_session_ids is not None:
        # Keep members that are not open right now (by their stored session id),
        # snapshot newly added sessions.
        current = {m["session_id"]: m for m in g["members"]}
        new_members, to_resolve = [], []
        for sid in dict.fromkeys(req.member_session_ids):
            if sid in current and sid not in _st.sessions:
                new_members.append(current[sid])
            else:
                to_resolve.append(sid)
        sessions, err = _member_sessions(to_resolve) if to_resolve else ([], None)
        if err:
            return _err(err)
        for s in sessions:
            old = current.get(s["id"])
            m = gc.member_from_session(s)
            if old:
                m["id"] = old["id"]  # keep authorship of earlier messages
            new_members.append(m)
        if not new_members:
            return _err("A group needs at least one member")
        if len(new_members) > gc.MAX_MEMBERS:
            return _err(f"A group can have at most {gc.MAX_MEMBERS} members")
        g["members"] = new_members
    gc.save_groups()
    await gc.broadcast_group(g)
    return JSONResponse({"group": gc._public(g)})


@router.delete("/api/groups/{group_id}")
async def delete_group(group_id: str):
    gc.load_groups()
    g = gc.groups.get(group_id)
    if not g:
        return _err("Group not found", 404)
    await gc.stop_group(g)
    gc.groups.pop(group_id, None)
    for channel, gid in list(gc.active_groups.items()):
        if gid == group_id:
            gc.active_groups.pop(channel, None)
    gc.save_groups()
    await gc._broadcast({"type": "group_deleted", "group_id": group_id})
    return JSONResponse({"ok": True})


@router.post("/api/groups/{group_id}/send")
async def send_to_group(group_id: str, req: SendRequest):
    gc.load_groups()
    g = gc.groups.get(group_id)
    if not g:
        return _err("Group not found", 404)
    text = (req.text or "").strip()
    if not text:
        return _err("Message is empty")
    msg = await gc.send_user_message(g, text)
    return JSONResponse({"message": msg})


@router.post("/api/groups/{group_id}/stop")
async def stop_group(group_id: str):
    gc.load_groups()
    g = gc.groups.get(group_id)
    if not g:
        return _err("Group not found", 404)
    await gc.stop_group(g)
    return JSONResponse({"ok": True})


@router.delete("/api/groups/{group_id}/messages")
async def clear_group(group_id: str):
    gc.load_groups()
    g = gc.groups.get(group_id)
    if not g:
        return _err("Group not found", 404)
    await gc.stop_group(g)
    g["messages"] = []
    gc.save_groups()
    await gc.broadcast_group(g)
    return JSONResponse({"ok": True})


class CrewGroupRequest(BaseModel):
    crew_id: str
    session_ids: list[str] = []
    member_ais: list[str] = []
    name: str = ""


@router.get("/api/crews")
async def list_crews():
    from helm import crews
    return JSONResponse({"crews": [crews.public(c) for c in crews.CREWS]})


@router.post("/api/groups/from-crew")
async def create_group_from_crew(req: CrewGroupRequest):
    from helm import crews
    gc.load_groups()
    crew = crews.get(req.crew_id)
    if not crew:
        return _err("Unknown crew")
    picked = len(set(req.session_ids)) + len(set(req.member_ais))
    if picked < len(crew["roles"]):
        return _err(f"the {crew['name']} crew needs {len(crew['roles'])} AIs, you picked {picked}")
    sessions, err = _resolve_members(req.session_ids, req.member_ais)
    if err:
        return _err(err)
    try:
        pairs = crews.assign(crew, sessions)
    except ValueError as exc:
        return _err(str(exc))
    from helm.broadcast import push_state
    await push_state()
    group = gc.make_group(req.name.strip() or crew["name"], crew["about"],
                          [s for _, s in pairs],
                          roles=[(r["name"], r["prompt"]) for r, _ in pairs])
    gc.save_groups()
    await gc.broadcast_group(group)
    return JSONResponse({"group": gc._public(group)})
