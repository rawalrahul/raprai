"""helm/web_routes/bakeoff_routes.py — start a bake-off, read the board, merge or discard."""

import asyncio
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import helm.bakeoff as bakeoff
import helm.state as _st

router = APIRouter()
_runs: dict[str, bakeoff.BakeOff] = {}
_tasks: dict[str, asyncio.Task] = {}


class StartBody(BaseModel):
    repo: str
    task: str
    ais: list[str]
    test_command: Optional[str] = None


class MergeBody(BaseModel):
    attempt: int


async def _real_runner(ai: str, prompt: str, cwd: str) -> str:
    """Run one AI the same way a session does, in the copy's folder."""
    from helm.council.runner import _build_cmd_for_session, _run_subprocess_blocking
    sess = next((s for s in _st.sessions.values() if s.get("ai") == ai), None)
    sess = {"id": "bakeoff", "ai": ai, "cwd": cwd, "model": (sess or {}).get("model")}
    cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env))


def _runner():
    return _real_runner


@router.post("/api/bakeoff")
async def start(body: StartBody):
    try:
        b = bakeoff.create(body.repo, body.task, body.ais, test_command=body.test_command or None)
    except (ValueError, RuntimeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    _runs[b.id] = b
    _tasks[b.id] = asyncio.create_task(bakeoff.run(b, _runner()))
    return JSONResponse(b.as_dict())


@router.get("/api/bakeoff/{bid}")
async def board(bid: str):
    b = _runs.get(bid)
    if not b:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(b.as_dict())


@router.post("/api/bakeoff/{bid}/merge")
async def merge(bid: str, body: MergeBody):
    b = _runs.get(bid)
    if not b:
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        n = bakeoff.merge(b, body.attempt)
    except (ValueError, RuntimeError, IndexError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"ok": True, "files_changed": n})


@router.post("/api/bakeoff/{bid}/discard")
async def discard(bid: str):
    b = _runs.get(bid)
    if not b:
        return JSONResponse({"error": "not found"}, status_code=404)
    bakeoff.discard(b)
    return JSONResponse({"ok": True})
