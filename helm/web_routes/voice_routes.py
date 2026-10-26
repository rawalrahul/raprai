"""
voice_routes.py — Web UI voice I/O.

  POST /transcribe  — speech-to-text: audio (webm/ogg/wav) -> Whisper -> text.
  POST /tts         — text-to-speech: text -> audio. ElevenLabs if a key is set,
                      else Kokoro on this PC (natural, free), else pyttsx3 / OS voices.
  GET  /tts/status  — which TTS backend is active, and which Live providers.
  POST /tts/prepare — install/download Kokoro and Whisper in the background.
  POST /voice/live/session — a short-lived token for Live voice (OpenAI / Gemini).
  POST /voice/live/task    — Live voice hands a task to RAPR; returns the reply.
"""

import asyncio
import tempfile
import os
import re
import logging

from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger("helm")

router = APIRouter()


from helm.voice import ensure_ffmpeg as _ensure_ffmpeg, transcribe_file as _transcribe  # noqa: E402,F401


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
    """Return the active TTS backend name: 'elevenlabs', 'kokoro' or 'offline'."""
    from helm import tts_local
    if _eleven_key():
        return "elevenlabs"
    return "kokoro" if tts_local.is_ready() else "offline"


# ElevenLabs voice ids are short alphanumeric tokens. Validate before putting the
# caller-supplied value into the request URL path (prevents path injection / hitting
# other API routes).
_VOICE_ID_RE = re.compile(r"[A-Za-z0-9]{15,40}")


def _tts_elevenlabs(text: str, voice: str = "") -> bytes:
    """Synthesize speech via ElevenLabs. Returns MP3 bytes. Blocking."""
    import json
    import urllib.parse
    import urllib.request

    voice_id = voice or _ELEVEN_DEFAULT_VOICE
    if not _VOICE_ID_RE.fullmatch(voice_id):
        raise ValueError("Invalid ElevenLabs voice id")
    # Encode the path segment defensively even after validation.
    safe_voice = urllib.parse.quote(voice_id, safe="")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{safe_voice}"
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
            logger.debug('pyttsx3: stopping the engine failed', exc_info=True)
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
    from helm import tts_local, voice_live
    return JSONResponse({"backend": tts_backend(), "local": tts_local.status(),
                         "live": voice_live.providers()})


@router.post("/tts/prepare")
async def tts_prepare():
    """Start getting the local voice ready (Kokoro + Whisper), without waiting."""
    from helm import tts_local
    from helm.voice import warm_up
    warm_up()
    return JSONResponse({"backend": tts_backend(), "local": tts_local.prepare()})


@router.post("/voice/live/session")
async def live_session(request: Request):
    """A one-session token for Live voice. Body: {"provider": "openai"|"gemini"}."""
    from helm import voice_live
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        data = await asyncio.get_running_loop().run_in_executor(
            None, voice_live.new_session, body.get("provider"), (body.get("voice") or "").strip())
        return JSONResponse(data)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        logger.warning("Live voice session failed: %s", exc)
        return JSONResponse({"error": f"Couldn't start Live voice: {exc}"}, status_code=502)


@router.post("/voice/live/task")
async def live_task(request: Request):
    """Kelvin (Live voice) hands a task to RAPR. Body: {"task": "...", "ai": "codex"?}.
    Runs it like a typed message and returns the reply for Kelvin to summarise."""
    import helm.state as _st
    from helm import voice_live
    from helm.ai_runner import process_message
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    task = (body.get("task") or "").strip()
    if not task:
        return JSONResponse({"error": "No task"}, status_code=400)
    sess = _st.sessions.get(_st.focused_id) if _st.focused_id else None
    has_session = bool(sess and sess.get("status") != "stopped")
    text = voice_live.task_message(task, body.get("ai"), has_session)
    try:
        reply = await process_message(text, source="web")
    except Exception as exc:
        reply = f"The task failed: {exc}"
    return JSONResponse({"reply": reply or "(no output)"})


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
    from helm import tts_local
    text = tts_local.speakable(text)
    if not text:
        return JSONResponse({"error": "Nothing to say"}, status_code=400)

    loop = asyncio.get_event_loop()
    try:
        if _eleven_key():
            audio = await loop.run_in_executor(None, _tts_elevenlabs, text, voice)
            media = "audio/mpeg"
        elif tts_local.is_ready():
            kvoice = voice if voice in tts_local.VOICES else tts_local.voice_for(body.get("ai"))
            audio = await loop.run_in_executor(None, tts_local.synthesize, text, kvoice)
            media = "audio/wav"
        else:
            tts_local.prepare()            # natural voice next time; OS voice for now
            audio = await loop.run_in_executor(None, _tts_offline, text)
            media = "audio/wav"
        return Response(content=audio, media_type=media)
    except Exception as exc:
        logger.warning("TTS error (%s): %s", tts_backend(), exc)
        return JSONResponse({"error": str(exc)}, status_code=500)
