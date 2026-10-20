"""
helm/tts_local.py — Natural-sounding speech on this PC, free: Kokoro.

Kokoro (82M parameters, Apache-2.0) sounds close to a person and runs on an
ordinary CPU through ONNX, with no graphics card and no API key. The first time
voice is used RAPR installs kokoro-onnx and downloads the model (~120 MB) into
the data folder, in the background; until then the browser's own voice speaks.

Replies are spoken a sentence at a time (the browser asks for each sentence),
so the first words play while the rest is still being made.
"""

from __future__ import annotations

import io
import os
import re
import threading
from typing import Optional

from helm.config import logger

MODEL_URL = ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
             "model-files-v1.0/kokoro-v1.0.int8.onnx")
VOICES_URL = ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/"
              "model-files-v1.0/voices-v1.0.bin")

DEFAULT_VOICE = "af_heart"      # Kelvin's voice
# A few of Kokoro's clearest English voices, for giving each AI its own.
VOICES = ["af_heart", "am_michael", "bf_emma", "am_fenrir", "af_bella", "bm_george",
          "af_nicole", "am_puck"]

_engine = None
_state = {"status": "off", "error": None}       # off | preparing | ready | error
_lock = threading.Lock()


def _dir():
    from helm.paths import user_data_dir
    d = user_data_dir() / "voice"
    d.mkdir(parents=True, exist_ok=True)
    return d


def enabled() -> bool:
    return os.environ.get("RAPR_LOCAL_TTS", "1").strip().lower() not in ("0", "false", "off", "no")


def status() -> dict:
    return {"status": _state["status"], "error": _state["error"], "voices": VOICES}


def is_ready() -> bool:
    return _engine is not None


def _download(url: str, dest) -> None:
    import urllib.request
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def _load() -> None:
    """Install, download and load Kokoro. Blocking; runs once."""
    global _engine
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        import subprocess, sys
        from helm.subprocess_utils import hidden_kwargs
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "kokoro-onnx", "soundfile", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **hidden_kwargs(),
        )
    from kokoro_onnx import Kokoro
    model, voices = _dir() / "kokoro-v1.0.int8.onnx", _dir() / "voices-v1.0.bin"
    for url, dest in ((MODEL_URL, model), (VOICES_URL, voices)):
        if not dest.exists():
            logger.info("voice: downloading %s", dest.name)
            _download(url, dest)
    _engine = Kokoro(str(model), str(voices))


def prepare(background: bool = True) -> dict:
    """Get Kokoro ready (install + download + load) if it isn't yet."""
    if not enabled() or _engine is not None or _state["status"] == "preparing":
        return status()

    def run():
        with _lock:
            if _engine is not None:
                return
            _state.update(status="preparing", error=None)
            try:
                _load()
                _state.update(status="ready")
                logger.info("voice: Kokoro is ready")
            except Exception as exc:
                logger.warning("voice: Kokoro unavailable: %s", exc)
                _state.update(status="error", error=str(exc))

    if background:
        threading.Thread(target=run, daemon=True, name="kokoro-prepare").start()
        _state["status"] = "preparing"
    else:
        run()
    return status()


def synthesize(text: str, voice: str = "", speed: float = 1.05) -> bytes:
    """WAV bytes for `text`. Blocking; call from a thread pool."""
    if _engine is None:
        raise RuntimeError("Kokoro is not ready")
    import soundfile as sf
    voice = voice if voice in VOICES else DEFAULT_VOICE
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, rate = _engine.create(text, voice=voice, speed=speed, lang=lang)
    buf = io.BytesIO()
    sf.write(buf, samples, rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Text that sounds right when read aloud
# ---------------------------------------------------------------------------

_CODE_BLOCK = re.compile(r"```.*?(?:```|$)", re.DOTALL)
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def speakable(text: str) -> str:
    """Markdown → plain spoken text: code blocks become a short note, links
    their label, and symbols that sound silly read aloud are dropped."""
    t = text or ""
    t = _CODE_BLOCK.sub(" (code is in the chat) ", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)            # [label](url)
    t = re.sub(r"https?://\S+", "a link", t)
    t = re.sub(r"^\s{0,3}(#{1,6}|>|[-*+]|\d+\.)\s+", "", t, flags=re.MULTILINE)
    t = re.sub(r"(\*\*|__|\*|_|~~)(.+?)\1", r"\2", t)
    t = re.sub(r"^\s*\|.*\|\s*$", "", t, flags=re.MULTILINE)      # tables
    t = _EMOJI.sub("", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", ".\n", t)
    return re.sub(r"\.{2,}(?!\.)", ".", t).strip()


def voice_for(ai: Optional[str]) -> str:
    """A stable Kokoro voice per AI; Kelvin (no AI) gets the default."""
    if not ai or ai == "kelvin":
        return DEFAULT_VOICE
    h = 0
    for ch in ai:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return VOICES[h % len(VOICES)]
