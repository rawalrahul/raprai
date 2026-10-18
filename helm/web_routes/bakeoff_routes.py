"""helm/web_routes/bakeoff_routes.py — start a bake-off, read the board, merge or discard, share the result."""

import asyncio
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import helm.arena as arena
import helm.bakeoff as bakeoff
import helm.bakeoff_history as history
import helm.state as _st
from helm.config import logger

router = APIRouter()
_runs: dict[str, bakeoff.BakeOff] = {}
_tasks: dict[str, asyncio.Task] = {}
_procs: dict[str, object] = {}   # attempt folder -> its running AI process


class StartBody(BaseModel):
    repo: str
    task: str
    ais: list[str]
    test_command: Optional[str] = None


class MergeBody(BaseModel):
    attempt: int


class PublishBody(BaseModel):
    include_task: bool = False
    task: Optional[str] = None
    category: Optional[str] = None


def _model_for(ai: str) -> Optional[str]:
    """The model a session with this AI is set to, if any (the bake-off uses the same one)."""
    sess = next((s for s in _st.sessions.values() if s.get("ai") == ai), None)
    return (sess or {}).get("model")


async def _real_runner(ai: str, prompt: str, cwd: str) -> str:
    """Run one AI the same way a session does, in the copy's folder."""
    from helm.council.runner import _build_cmd_for_session, _run_subprocess_blocking
    sess = {"id": "bakeoff", "ai": ai, "cwd": cwd, "model": _model_for(ai)}
    cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: _run_subprocess_blocking(
            cmd, cwd, stdin_text, extra_env, on_start=lambda p: _procs.__setitem__(cwd, p)))
    finally:
        _procs.pop(cwd, None)


def _stop_running(b: bakeoff.BakeOff) -> None:
    """Stop AIs still working on a bake-off's copies (e.g. it was discarded mid-run)."""
    for a in b.attempts:
        proc = _procs.pop(a.path, None)
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass


def _runner():
    return _real_runner


def _save(b: bakeoff.BakeOff) -> None:
    """Keep the result in history (numbers only); a failure here never breaks the bake-off."""
    try:
        history.save(bakeoff.result(b))
    except Exception as exc:
        logger.warning("bakeoff: could not save result %s: %s", b.id, exc)


async def _run_and_save(b: bakeoff.BakeOff) -> None:
    await bakeoff.run(b, _runner())
    if b.status == "done":
        _save(b)


def _result(bid: str) -> Optional[dict]:
    """A finished bake-off's result, from this run or from history."""
    b = _runs.get(bid)
    if b is not None:
        return {**bakeoff.result(b), "arena_url": (history.get(bid) or {}).get("arena_url")}
    return history.get(bid)


@router.post("/api/bakeoff")
async def start(body: StartBody):
    try:
        b = bakeoff.create(body.repo, body.task, body.ais, test_command=body.test_command or None)
    except (ValueError, RuntimeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    for a in b.attempts:
        a.model = _model_for(a.ai)
    _runs[b.id] = b
    _tasks[b.id] = asyncio.create_task(_run_and_save(b))
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
    _save(b)
    return JSONResponse({"ok": True, "files_changed": n})


@router.post("/api/bakeoff/{bid}/discard")
async def discard(bid: str):
    b = _runs.get(bid)
    if not b:
        return JSONResponse({"error": "not found"}, status_code=404)
    finished = b.status == "done"   # one stopped partway isn't a result
    _stop_running(b)
    bakeoff.discard(b)
    if finished:
        _save(b)
    return JSONResponse({"ok": True})


@router.get("/api/bakeoffs")
async def past():
    """Recent finished bake-offs, newest first."""
    try:
        return JSONResponse({"bakeoffs": history.recent(30)})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/bakeoff/{bid}/share")
async def share(bid: str, include_task: bool = False, task: Optional[str] = None, category: Optional[str] = None):
    """What sharing this result looks like: the post text and exactly what Publish would send."""
    r = _result(bid)
    if not r:
        return JSONResponse({"error": "not found"}, status_code=404)
    sent = arena.payload(r, include_task=include_task, task=task, category=category)
    return JSONResponse({
        "result": r,
        "text": arena.share_text(r, task=sent.get("task"), url=r.get("arena_url")),
        "payload": sent,
        "categories": list(bakeoff.CATEGORIES),
        "arena": arena.arena_url(),
        "arena_url": r.get("arena_url"),
        "can_publish": r["status"] in ("merged", "discarded"),
    })


@router.post("/api/bakeoff/{bid}/publish")
async def publish(bid: str, body: PublishBody):
    """Publish the result to RAPR Arena. Only what /share showed as "payload" is sent."""
    r = _result(bid)
    if not r:
        return JSONResponse({"error": "not found"}, status_code=404)
    if r["status"] not in ("merged", "discarded"):
        return JSONResponse({"error": "merge a winner (or discard them all) before publishing"}, status_code=400)
    if r.get("arena_url"):
        return JSONResponse({"url": r["arena_url"], "already": True})
    sent = arena.payload(r, include_task=body.include_task, task=body.task, category=body.category)
    try:
        out = await asyncio.get_running_loop().run_in_executor(None, arena.publish, sent)
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    try:
        history.set_arena_url(bid, out["url"])
    except Exception as exc:
        logger.warning("bakeoff: could not keep Arena link for %s: %s", bid, exc)
    return JSONResponse({"url": out["url"],
                         "text": arena.share_text(r, task=sent.get("task"), url=out["url"])})
