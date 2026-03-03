"""
voice_routes.py — POST /transcribe endpoint for Web UI voice input.

Accepts audio (webm/ogg/wav) via multipart upload, transcribes with Whisper,
and returns the text.
"""

import asyncio
import tempfile
import os
import logging

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

logger = logging.getLogger("helm")

router = APIRouter()


def _ensure_ffmpeg():
    """Make sure ffmpeg is on PATH. Uses static-ffmpeg as fallback on Windows."""
    import shutil, subprocess, sys
    if shutil.which("ffmpeg"):
        return
    try:
        import static_ffmpeg
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "static-ffmpeg", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        import static_ffmpeg
    static_ffmpeg.add_paths()


def _transcribe(audio_path: str) -> str:
    """Run Whisper transcription (blocking — call from thread pool)."""
    _ensure_ffmpeg()

    try:
        import whisper
    except ImportError:
        import subprocess, sys
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "openai-whisper", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        import whisper

    model = whisper.load_model("base")
    result = model.transcribe(audio_path, fp16=False)
    return (result.get("text") or "").strip()


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Receive an audio blob from the browser, transcribe via Whisper, return text."""
    tmp_dir = tempfile.mkdtemp(prefix="helm_voice_web_")
    # Browser MediaRecorder typically sends webm/opus
    ext = "webm"
    ct = file.content_type or ""
    if "ogg" in ct:
        ext = "ogg"
    elif "wav" in ct:
        ext = "wav"
    elif "mp4" in ct or "m4a" in ct:
        ext = "m4a"

    audio_path = os.path.join(tmp_dir, f"recording.{ext}")
    try:
        data = await file.read()
        with open(audio_path, "wb") as f:
            f.write(data)

        transcript = await asyncio.get_event_loop().run_in_executor(
            None, _transcribe, audio_path
        )
        return JSONResponse({"text": transcript})
    except Exception as exc:
        logger.warning("Web voice transcription error: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=500)
    finally:
        # Cleanup temp files
        try:
            os.remove(audio_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass
