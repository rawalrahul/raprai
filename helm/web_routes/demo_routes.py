"""
helm/web_routes/demo_routes.py — Demo upload, analysis, and replication endpoints.
"""

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

import helm.state as _st
from helm.config import logger
from helm.demos import storage as demo_storage
from helm.demos.analysis import analyze_demo

try:
    import static_ffmpeg as _static_ffmpeg
    _static_ffmpeg.add_paths()
except Exception:
    pass

router = APIRouter(prefix="/api/demos", tags=["demos"])


@router.get("/")
async def demos_list():
    try:
        return {"ok": True, "demos": demo_storage.list_demos()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_ALLOWED_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
_MAX_VIDEO_BYTES = 500 * 1024 * 1024  # 500 MB


@router.post("/upload")
async def demos_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        filename = file.filename or "video.mp4"
        meta = demo_storage.create_demo(filename)
        demo_id = meta["demo_id"]

        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_EXTS:
            demo_storage.delete_demo(demo_id)
            return {"ok": False, "error": f"Unsupported file type: {suffix or '(none)'}"}
        ext = suffix.lstrip(".") or "mp4"
        video_path = demo_storage.RAW_DIR / demo_id / f"video.{ext}"
        content = await file.read(_MAX_VIDEO_BYTES + 1)
        if len(content) > _MAX_VIDEO_BYTES:
            demo_storage.delete_demo(demo_id)
            return {"ok": False, "error": "File exceeds 500 MB limit"}
        video_path.write_bytes(content)

        duration = _get_duration(video_path)
        demo_storage.update_meta(demo_id, {"duration_s": duration})

        background_tasks.add_task(analyze_demo, demo_id, meta["title"])
        return {"ok": True, "demo_id": demo_id, "title": meta["title"], "status": "analyzing"}
    except Exception as e:
        logger.error("demo upload error: %s", e)
        return {"ok": False, "error": str(e)}


@router.get("/{demo_id}")
async def demos_get(demo_id: str):
    _check_id(demo_id)
    demo = demo_storage.get_demo(demo_id)
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")
    return {"ok": True, **demo}


@router.post("/{demo_id}/run")
async def demos_run(demo_id: str, background_tasks: BackgroundTasks):
    try:
        _check_id(demo_id)
        demo = demo_storage.get_demo(demo_id)
        if not demo:
            raise HTTPException(status_code=404, detail="Demo not found")
        playbook_path = demo.get("playbook_path")
        if not playbook_path or not Path(playbook_path).exists():
            return {"ok": False, "error": "No playbook available — run analysis first"}
        playbook_text = Path(playbook_path).read_text(encoding="utf-8")
        sid = _st.focused_id
        sess = _st.sessions.get(sid) if sid else None
        if not sess:
            return {"ok": False, "error": "No active session to run demo in"}
        from helm.ai_runner.core import process_message
        prompt = f"Execute this playbook step by step:\n\n{playbook_text}"
        background_tasks.add_task(process_message, prompt, "web", sid)
        return {"ok": True, "session_id": sid}
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/{demo_id}/regenerate")
async def demos_regenerate(demo_id: str, background_tasks: BackgroundTasks):
    try:
        _check_id(demo_id)
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
        _check_id(demo_id)
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


def _check_id(demo_id: str) -> None:
    from helm.demos.storage import _validate_id
    try:
        _validate_id(demo_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
