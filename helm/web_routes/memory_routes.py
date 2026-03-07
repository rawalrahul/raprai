"""
helm/web_routes/memory_routes.py — API endpoints for shared AI memory.

Endpoints:
    GET    /memory                — list memories (with optional category filter)
    GET    /memory/search         — search memories by keyword
    GET    /memory/stats          — memory stats for sidebar badge
    POST   /memory                — add a memory
    PUT    /memory/<id>           — edit a memory
    DELETE /memory/<id>           — delete a memory
    POST   /memory/<id>/pin       — pin/unpin a memory
    POST   /memory/<id>/archive   — archive a memory
    POST   /memory/<id>/unarchive — restore an archived memory
    POST   /memory/decay          — manually trigger memory decay
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/memory", tags=["memory"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AddMemoryRequest(BaseModel):
    content: str
    category: str = "fact"
    source_ai: str = ""
    session_id: str = ""


class EditMemoryRequest(BaseModel):
    content: str = ""
    category: str = ""


class PinRequest(BaseModel):
    pinned: bool = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_all(category: str = "", include_archived: bool = False, limit: int = 100):
    """List memories with optional category filter."""
    from helm.memory import list_memories
    memories = list_memories(category=category, include_archived=include_archived, limit=limit)
    return {"ok": True, "memories": memories, "count": len(memories)}


@router.get("/search")
async def search(q: str = "", limit: int = 20):
    """Search memories by keyword."""
    from helm.memory import search_memories
    results = search_memories(query=q, limit=limit)
    return {"ok": True, "memories": results, "count": len(results)}


@router.get("/stats")
async def stats():
    """Memory stats for sidebar badge."""
    from helm.memory import memory_stats
    return {"ok": True, **memory_stats()}


@router.post("")
async def add(req: AddMemoryRequest):
    """Add a new memory."""
    from helm.memory import add_memory
    try:
        mid = add_memory(
            content=req.content,
            category=req.category,
            source_ai=req.source_ai,
            session_id=req.session_id,
        )
        return {"ok": True, "id": mid}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@router.put("/{memory_id}")
async def edit(memory_id: int, req: EditMemoryRequest):
    """Edit an existing memory."""
    from helm.memory import edit_memory
    ok = edit_memory(memory_id, content=req.content, category=req.category)
    return {"ok": ok}


@router.delete("/{memory_id}")
async def delete(memory_id: int):
    """Delete a memory."""
    from helm.memory import delete_memory
    ok = delete_memory(memory_id)
    return {"ok": ok}


@router.post("/{memory_id}/pin")
async def pin(memory_id: int, req: PinRequest):
    """Pin or unpin a memory."""
    from helm.memory import pin_memory
    ok = pin_memory(memory_id, pinned=req.pinned)
    return {"ok": ok}


@router.post("/{memory_id}/archive")
async def archive(memory_id: int):
    """Archive a memory."""
    from helm.memory import archive_memory
    ok = archive_memory(memory_id)
    return {"ok": ok}


@router.post("/{memory_id}/unarchive")
async def unarchive(memory_id: int):
    """Restore an archived memory back to active status."""
    from helm.memory import unarchive_memory
    ok = unarchive_memory(memory_id)
    return {"ok": ok}


@router.post("/decay")
async def trigger_decay():
    """Manually trigger memory decay (normally runs on heartbeat cycle)."""
    from helm.memory import apply_memory_decay
    result = apply_memory_decay()
    return {"ok": True, **result}
