"""
helm/web_routes/memory_routes.py — API endpoints for shared AI memory.

Endpoints:
    GET    /memory                        — list memories (with optional category filter)
    GET    /memory/search                 — search memories by keyword
    GET    /memory/stats                  — memory stats for sidebar badge
    POST   /memory                        — add a memory
    PUT    /memory/<id>                   — edit a memory
    DELETE /memory/<id>                   — delete a memory
    POST   /memory/<id>/pin              — pin/unpin a memory
    POST   /memory/<id>/archive          — archive a memory
    POST   /memory/<id>/unarchive        — restore an archived memory
    POST   /memory/decay                 — manually trigger memory decay
    GET    /memory/transfer/export-prompt — generate knowledge-transfer prompt
    POST   /memory/transfer/import       — import AI response as memories
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import re

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


# ---------------------------------------------------------------------------
# Knowledge Transfer — export prompt & import response
# ---------------------------------------------------------------------------

@router.get("/transfer/export-prompt")
async def export_prompt():
    """Generate a knowledge-extraction prompt the user can paste into any AI.

    The prompt asks the other AI to dump everything it knows about the user
    in a structured format that our import endpoint can parse.
    """
    from helm.memory import list_memories
    from helm.personalization import get_user_name, get_ai_name

    user_name = get_user_name()
    name_context = f" (the user's name is {user_name})" if user_name else ""

    # Include existing memory summary so the external AI can avoid duplicates
    existing = list_memories(include_archived=False, limit=200)
    existing_summary = ""
    if existing:
        items = [f"- [{m['category']}] {m['content']}" for m in existing[:30]]
        existing_summary = (
            "\n\nIMPORTANT: I already have these memories stored, so do NOT repeat "
            "any of these — only give me NEW information:\n"
            + "\n".join(items)
        )

    prompt = f"""I'm transferring my knowledge to another AI tool{name_context}. Please help me by listing EVERYTHING you know about me, my preferences, my projects, and any important context from our conversations.

Format your response EXACTLY like this — each item on its own line, starting with a category tag in brackets. Use ONLY these categories: [preference], [fact], [project], [person], [decision], [instruction]

Example format:
[preference] Prefers Python over JavaScript for backend work
[fact] GitHub username is octocat
[project] Working on a React dashboard with TypeScript
[person] Alex is the team lead for the backend team
[decision] Chose PostgreSQL over MongoDB for the main database
[instruction] Always include type hints in Python code

Rules:
1. One memory per line, each starting with a category tag
2. Be specific and concise — each line should be a standalone fact
3. Include coding preferences, tools, languages, frameworks
4. Include project details, architecture decisions, tech stack
5. Include people, roles, and team structure
6. Include any instructions or rules I've given you
7. Include personal preferences and working style
8. Do NOT include conversation-specific context that wouldn't be useful long-term
9. Do NOT include anything you're uncertain about
10. Aim for 20-50 specific, useful memories{existing_summary}

Please list everything now:"""

    return {"ok": True, "prompt": prompt}


class ImportRequest(BaseModel):
    response: str
    source: str = "external-ai"


@router.post("/transfer/import")
async def import_response(req: ImportRequest):
    """Parse an AI's knowledge-dump response and import as memories.

    Expects the response to contain lines like:
        [category] content text here

    Lines that don't match this pattern are skipped.
    Returns the count of new memories added.
    """
    from helm.memory import add_memory, VALID_CATEGORIES

    lines = req.response.strip().splitlines()
    # Match lines like: [preference] Some content here
    pattern = re.compile(r"^\s*\[(\w+)\]\s*(.+)$")

    added = 0
    skipped = 0
    duplicates = 0
    errors = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        m = pattern.match(line)
        if not m:
            skipped += 1
            continue

        category = m.group(1).lower()
        content = m.group(2).strip()

        if not content or len(content) < 5:
            skipped += 1
            continue

        if category not in VALID_CATEGORIES:
            # Try to map common variations
            cat_map = {
                "preferences": "preference",
                "facts": "fact",
                "projects": "project",
                "people": "person",
                "persons": "person",
                "decisions": "decision",
                "instructions": "instruction",
                "rule": "instruction",
                "rules": "instruction",
                "style": "preference",
                "tool": "fact",
                "tools": "fact",
            }
            category = cat_map.get(category, "fact")

        try:
            mid = add_memory(
                content=content,
                category=category,
                source_ai=req.source,
                session_id="knowledge-transfer",
            )
            # add_memory returns existing ID if dedup matched
            # We can't easily tell if it was new or dedup'd, so just count
            added += 1
        except ValueError as e:
            errors.append(str(e))
        except Exception:
            errors.append(f"Failed to save: {content[:50]}...")

    return {
        "ok": True,
        "added": added,
        "skipped": skipped,
        "errors": errors[:5],  # cap error list
        "message": f"Imported {added} memories ({skipped} lines skipped)",
    }
