"""helm/web_routes/brief_routes.py — your brief, the Needs-you list and what your AIs can reach."""

import asyncio
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.approval as appr
from helm import brief, reach

router = APIRouter()


@router.get("/api/brief")
async def get_brief():
    return JSONResponse({"brief": brief.latest(), "running": brief._lock.locked()})


@router.post("/api/brief/run")
async def run_brief():
    """Put a brief together now (in the background; it arrives as a 'brief' event)."""
    if brief._lock.locked():
        return JSONResponse({"ok": True, "already": True})
    asyncio.create_task(brief.run("manual"))
    return JSONResponse({"ok": True})


@router.get("/api/brief/settings")
async def get_settings():
    return JSONResponse(brief.load_settings())


@router.put("/api/brief/settings")
async def put_settings(request: Request):
    try:
        saved = brief.save_settings(await request.json())
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse(saved)


@router.post("/api/brief/item/{n}/do")
async def do_item(n: int):
    sess, msg = await brief.start_item(n, source="web")
    if not sess:
        return JSONResponse({"error": msg}, status_code=400)
    return JSONResponse({"ok": True, "session_id": sess["id"]})


@router.post("/api/brief/item/{n}/skip")
async def skip_item(n: int):
    if not brief.set_status(n, "dismissed"):
        return JSONResponse({"error": f"no item {n}"}, status_code=404)
    await brief._broadcast(brief.latest())
    return JSONResponse({"ok": True})


@router.get("/api/needs")
async def needs():
    """Everything waiting for you: approvals, your brief's open items, recent scheduled results."""
    latest = brief.latest()
    open_items = [i for i in (latest or {}).get("items", [])
                  if i.get("status", "open") == "open" and i["kind"] != "approval"]
    return JSONResponse({
        "approvals": appr.pending(),
        "brief": {"id": latest["id"], "created": latest["created"], "checked": latest.get("checked", []),
                  "items": open_items} if latest else None,
        "results": brief.schedule_results(since=time.time() - 2 * 86400)[-10:][::-1],
        "running": brief._lock.locked(),
    })


@router.get("/api/reach")
async def get_reach(refresh: int = 0):
    data = await asyncio.to_thread(reach.discover, bool(refresh))
    return JSONResponse({**data, "summary": reach.summary(data),
                         "suggestions": brief.suggestions(data)})
