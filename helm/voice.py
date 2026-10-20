"""
helm/voice.py — Speech-to-text for voice messages, shared by every chat app.

Telegram, WhatsApp, Discord, Slack and the web app's mic all hand audio here.
Whisper runs locally (installed on first use, like ffmpeg), so voice messages
cost nothing and never leave this PC. The model is loaded once and kept, so
only the first message waits for it.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading


def ensure_ffmpeg() -> None:
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


_models: dict = {}
_model_lock = threading.Lock()
_PROMPT = "Hey Kelvin."   # nudges Whisper to spell the wake word "Kelvin" (not "Calvin")


def _pip(package: str) -> None:
    import subprocess, sys
    from helm.subprocess_utils import hidden_kwargs
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package, "-q"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        **hidden_kwargs(),
    )


def _model():
    """The Whisper model, loaded once and kept (loading takes seconds).

    faster-whisper first: about 4x faster on a CPU than openai-whisper and no
    PyTorch download. openai-whisper stays as the fallback for installs that
    already have it. VOICE_STT_MODEL picks the size (default "base").
    """
    name = os.environ.get("VOICE_STT_MODEL", "base").strip() or "base"
    with _model_lock:
        if name in _models:
            return _models[name]
        try:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                _pip("faster-whisper")
                from faster_whisper import WhisperModel
            model = ("faster", WhisperModel(name, device="cpu", compute_type="int8"))
        except Exception:
            ensure_ffmpeg()
            try:
                import whisper
            except ImportError:
                _pip("openai-whisper")
                import whisper
            model = ("openai", whisper.load_model(name))
        _models[name] = model
        return model


def decode_16k(audio_path: str):
    """Audio file → 16 kHz mono float32 samples, the input Whisper wants.

    faster-whisper's own decoder passes PyAV an option (metadata_errors) that
    PyAV 15+ removed, so every voice note failed; this decodes with PyAV
    directly instead. Any format PyAV reads works (WhatsApp/Telegram Opus,
    Discord Ogg, Slack WebM/MP4, WAV…)."""
    import av
    import numpy as np
    resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    with av.open(audio_path, mode="r") as container:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            frame.pts = None
            chunks.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(frame))
        chunks.extend(f.to_ndarray().reshape(-1) for f in resampler.resample(None))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def transcribe_file(audio_path: str) -> str:
    """Transcribe an audio file (any format ffmpeg reads) with Whisper. Blocking."""
    kind, model = _model()
    if kind == "faster":
        segments, _info = model.transcribe(decode_16k(audio_path), beam_size=1, vad_filter=True,
                                           initial_prompt=_PROMPT)
        return " ".join(s.text.strip() for s in segments).strip()
    result = model.transcribe(audio_path, fp16=False, initial_prompt=_PROMPT)
    return (result.get("text") or "").strip()


def warm_up() -> None:
    """Load the model in the background so the first voice message is quick."""
    threading.Thread(target=lambda: _safe(_model), daemon=True, name="whisper-warmup").start()


def _safe(fn):
    try:
        fn()
    except Exception as exc:
        from helm.config import logger
        logger.warning("voice: Whisper unavailable: %s", exc)


async def transcribe_bytes(data: bytes, ext: str = "ogg") -> str:
    """Transcribe audio bytes off the event loop. `ext` is the file type (ogg, m4a…)."""
    tmp_dir = tempfile.mkdtemp(prefix="helm_voice_")
    path = os.path.join(tmp_dir, f"voice.{(ext or 'ogg').lstrip('.')}")
    try:
        with open(path, "wb") as f:
            f.write(data)
        return await asyncio.get_running_loop().run_in_executor(None, transcribe_file, path)
    finally:
        try:
            os.remove(path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


def audio_ext(mime: str = "", filename: str = "") -> str:
    """File extension for an audio attachment, from its mime type or name."""
    name_ext = os.path.splitext(filename or "")[1].lstrip(".").lower()
    if name_ext:
        return name_ext
    mime = (mime or "").lower()
    for key, ext in (("ogg", "ogg"), ("opus", "ogg"), ("webm", "webm"), ("wav", "wav"),
                     ("mp4", "m4a"), ("m4a", "m4a"), ("aac", "aac"), ("mpeg", "mp3"), ("mp3", "mp3")):
        if key in mime:
            return ext
    return "ogg"


async def transcript_for_chat(data: bytes, ext: str, say) -> str | None:
    """Transcribe a chat app's voice message, telling the chat how it went via
    `say(text)`. Returns the transcript, or None when there's nothing to send on."""
    from helm.config import logger
    await say("🎤 Transcribing voice message…")
    try:
        text = await transcribe_bytes(data, ext)
    except Exception as exc:
        logger.warning("Voice transcription error: %s", exc)
        await say(f"⚠️ Voice transcription failed: {exc}")
        return None
    if not text:
        await say("⚠️ Could not transcribe audio — no speech detected.")
        return None
    await say(f"🎤 Transcript: {text}")
    return text
