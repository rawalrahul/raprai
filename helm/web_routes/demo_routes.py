"""
helm/web_routes/demo_routes.py — Demo upload, analysis, and replication endpoints.
"""

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from helm.config import logger
from helm.demos import storage as demo_storage
from helm.demos.analysis import analyze_demo

router = APIRouter(prefix="/api/demos", tags=["demos"])


@router.get("/")
async def demos_list():
    try:
        return {"ok": True, "demos": demo_storage.list_demos()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/upload")
async def demos_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        filename = file.filename or "video.mp4"
        meta = demo_storage.create_demo(filename)
        demo_id = meta["demo_id"]

        ext = Path(filename).suffix.lstrip(".") or "mp4"
        video_path = demo_storage.RAW_DIR / demo_id / f"video.{ext}"
        video_path.write_bytes(await file.read())

        duration = _get_duration(video_path)
        demo_storage.update_meta(demo_id, {"duration_s": duration})

        background_tasks.add_task(analyze_demo, demo_id, meta["title"])
        return {"ok": True, "demo_id": demo_id, "title": meta["title"], "status": "analyzing"}
    except Exception as e:
        logger.error("demo upload error: %s", e)
        return {"ok": False, "error": str(e)}


@router.get("/{demo_id}")
async def demos_get(demo_id: str):
    demo = demo_storage.get_demo(demo_id)
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")
    return {"ok": True, **demo}


@router.post("/{demo_id}/run")
async def demos_run(demo_id: str):
    try:
        demo = demo_storage.get_demo(demo_id)
        if not demo:
            raise HTTPException(status_code=404, detail="Demo not found")
        playbook_path = demo.get("playbook_path")
        if not playbook_path or not Path(playbook_path).exists():
            return {"ok": False, "error": "No playbook available — run analysis first"}
        playbook_text = Path(playbook_path).read_text(encoding="utf-8")
        from helm.session_mgr import focused_session
        sess = focused_session()
        if not sess:
            return {"ok": False, "error": "No active session to run demo in"}
        import asyncio
        from helm.ai_runner.core import process_message
        asyncio.create_task(
            process_message(sess, f"Execute this playbook step by step:\n\n{playbook_text}", {})
        )
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/{demo_id}/regenerate")
async def demos_regenerate(demo_id: str, background_tasks: BackgroundTasks):
    try:
        demo = demo_storage.get_demo(demo_id)
        if not demo:
            raise HTTPException(status_code=404, detail="Demo not found")
        demo_storage.update_meta(demo_id, {"status": "analyzing", "error_message": None})
        background_tasks.add_task(analyze_demo, demo_id, demo.get("title", demo_id))
        return {"ok": True, "status": "analyzing"}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.delete("/{demo_id}")
async def demos_delete(demo_id: str):
    try:
        demo_storage.delete_demo(demo_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _get_duration(video_path: Path) -> float | None:
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except Exception:
        pass
    return None
