"""
voice_routes.py — Web UI voice I/O.

  POST /transcribe  — speech-to-text: audio (webm/ogg/wav) -> Whisper -> text.
  POST /tts         — text-to-speech: text -> audio. Offline by default
                      (pyttsx3 / OS voices, no API key), ElevenLabs if a key is set.
  GET  /tts/status  — which TTS backend is active.
"""

import asyncio
import tempfile
import os
import logging

from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger("helm")

router = APIRouter()


def _ensure_ffmpeg():
    """Make sure ffmpeg is on PATH. Uses static-ffmpeg as fallback on Windows."""
    import shutil, subprocess, sys
    from helm.subprocess_utils import hidden_kwargs
    if shutil.which("ffmpeg"):
        return
    try:
        import static_ffmpeg
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "static-ffmpeg", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **hidden_kwargs(),
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
        from helm.subprocess_utils import hidden_kwargs
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "openai-whisper", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **hidden_kwargs(),
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


# ---------------------------------------------------------------------------
# Text-to-speech (voice out)
# ---------------------------------------------------------------------------

# Default ElevenLabs voice ("Rachel") + low-latency model. Only used when an
# ELEVENLABS_API_KEY is configured; otherwise we stay fully offline (no key).
_ELEVEN_DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"
_ELEVEN_MODEL = "eleven_turbo_v2_5"

# Cap TTS input so a runaway request can't block the worker for minutes.
_TTS_MAX_CHARS = 5000


def _eleven_key() -> str:
    return (os.environ.get("ELEVENLABS_API_KEY") or "").strip()


def tts_backend() -> str:
    """Return the active TTS backend name: 'elevenlabs' or 'offline'."""
    return "elevenlabs" if _eleven_key() else "offline"


def _tts_elevenlabs(text: str, voice: str = "") -> bytes:
    """Synthesize speech via ElevenLabs. Returns MP3 bytes. Blocking."""
    import json
    import urllib.request

    voice_id = voice or _ELEVEN_DEFAULT_VOICE
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": _ELEVEN_MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "xi-api-key": _eleven_key(),
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _tts_offline(text: str) -> bytes:
    """Synthesize speech offline via pyttsx3 (OS voices). Returns WAV bytes.

    Lazy-installs pyttsx3 the same way the STT path lazy-installs Whisper.
    Uses the platform's native engine (SAPI5 / NSSpeechSynthesizer / espeak),
    so no model download and no API key.
    """
    try:
        import pyttsx3
    except ImportError:
        import subprocess, sys
        from helm.subprocess_utils import hidden_kwargs
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyttsx3", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **hidden_kwargs(),
        )
        import pyttsx3

    tmp_dir = tempfile.mkdtemp(prefix="helm_tts_")
    out_path = os.path.join(tmp_dir, "speech.wav")
    try:
        # Fresh engine per call — pyttsx3 engines are not reusable across threads.
        engine = pyttsx3.init()
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(out_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


@router.get("/tts/status")
async def tts_status():
    """Report which TTS backend will be used (for the UI to label the control)."""
    return JSONResponse({"backend": tts_backend()})


@router.post("/tts")
async def text_to_speech(request: Request):
    """Synthesize speech from text. Body: {"text": "...", "voice": "<optional>"}.

    Returns audio bytes (MP3 for ElevenLabs, WAV for offline). The browser plays
    the blob directly. Offline by default to preserve the no-API-keys ethos.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    if len(text) > _TTS_MAX_CHARS:
        text = text[:_TTS_MAX_CHARS]
    voice = (body.get("voice") or "").strip()

    loop = asyncio.get_event_loop()
    try:
        if _eleven_key():
            audio = await loop.run_in_executor(None, _tts_elevenlabs, text, voice)
            media = "audio/mpeg"
        else:
            audio = await loop.run_in_executor(None, _tts_offline, text)
            media = "audio/wav"
        return Response(content=audio, media_type=media)
    except Exception as exc:
        logger.warning("TTS error (%s): %s", tts_backend(), exc)
        return JSONResponse({"error": str(exc)}, status_code=500)
