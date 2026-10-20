"""
helm/voice_live.py — "Live" voice: talk to Kelvin like on a phone call.

When an OpenAI or Gemini API key is set, the browser can talk to a
speech-to-speech model directly: it hears you as you speak, answers in about
half a second, and stops the moment you interrupt. Kelvin is the voice; real
work (code, files, anything a session does) is handed to your RAPR sessions
through the `run_task` tool, and Kelvin reads you the result.

RAPR never sends your API key to the browser. It asks the provider for a
short-lived token that only opens one voice session, and gives the browser that.

  • OpenAI Realtime (WebRTC): POST /v1/realtime/client_secrets → "ek_…"
  • Gemini Live (WebSocket): POST /v1alpha/auth_tokens → "auth_tokens/…"
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import urllib.error
import urllib.request
from typing import Optional

OPENAI_MODEL = "gpt-realtime-mini"
OPENAI_VOICE = "marin"
GEMINI_MODEL = "gemini-3.1-flash-live-preview"
GEMINI_VOICE = "Puck"

INSTRUCTIONS = (
    "You are Kelvin, the voice of RAPR AI, a friendly penguin who runs the user's AI "
    "coding assistants (Claude Code, Codex, Gemini and others) on their computer. "
    "Talk like a person on a call: short, warm sentences, no lists, no markdown, no "
    "reading code aloud. Chat and simple questions you answer yourself. Anything that "
    "needs their files, code, the computer or real work: call run_task with a clear "
    "instruction (and `ai` if they named one), say in a few words that you're on it, "
    "and when the result arrives, tell them the gist in one to three sentences. "
    "Never invent results you haven't received."
)

RUN_TASK = {
    "name": "run_task",
    "description": ("Hand a task to the user's AI sessions in RAPR (coding, files, research, "
                    "computer use). The result is sent back to you when it's ready."),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "What to do, in plain words."},
            "ai": {"type": "string", "description": "An AI the user named (claude, codex, gemini…), if any."},
        },
        "required": ["task"],
    },
}


def _key(*names: str) -> str:
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return ""


def openai_key() -> str:
    return _key("OPENAI_API_KEY")


def gemini_key() -> str:
    return _key("GEMINI_API_KEY", "GOOGLE_API_KEY")


def providers() -> dict:
    """Which Live providers have a key set."""
    return {"openai": bool(openai_key()), "gemini": bool(gemini_key())}


def pick(preferred: Optional[str]) -> Optional[str]:
    have = providers()
    if preferred in have and have[preferred]:
        return preferred
    return next((p for p in ("gemini", "openai") if have[p]), None)


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise RuntimeError(f"{exc.code}: {detail}") from None


def openai_session(voice: str = "") -> dict:
    model = os.environ.get("OPENAI_REALTIME_MODEL", OPENAI_MODEL)
    voice = voice or os.environ.get("OPENAI_REALTIME_VOICE", OPENAI_VOICE)
    body = {
        "expires_after": {"anchor": "created_at", "seconds": 600},
        "session": {
            "type": "realtime",
            "model": model,
            "instructions": INSTRUCTIONS,
            "audio": {"output": {"voice": voice},
                      "input": {"turn_detection": {"type": "semantic_vad"}}},
            "tools": [{"type": "function", **RUN_TASK}],
        },
    }
    data = _post("https://api.openai.com/v1/realtime/client_secrets", body,
                 {"Authorization": f"Bearer {openai_key()}"})
    return {"provider": "openai", "token": data["value"], "model": model,
            "calls_url": "https://api.openai.com/v1/realtime/calls"}


def gemini_session(voice: str = "") -> dict:
    model = os.environ.get("GEMINI_LIVE_MODEL", GEMINI_MODEL)
    now = _dt.datetime.now(_dt.timezone.utc)
    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = _post("https://generativelanguage.googleapis.com/v1alpha/auth_tokens",
                 {"uses": 1, "expireTime": iso(now + _dt.timedelta(minutes=30)),
                  "newSessionExpireTime": iso(now + _dt.timedelta(minutes=2))},
                 {"x-goog-api-key": gemini_key()})
    token = data["name"]
    return {
        "provider": "gemini", "token": token, "model": model,
        "ws_url": ("wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage."
                   f"v1alpha.GenerativeService.BidiGenerateContentConstrained?access_token={token}"),
        "setup": {"setup": {
            "model": f"models/{model}",
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {
                    "voiceName": voice or os.environ.get("GEMINI_LIVE_VOICE", GEMINI_VOICE)}}},
            },
            "systemInstruction": {"parts": [{"text": INSTRUCTIONS}]},
            "tools": [{"functionDeclarations": [RUN_TASK]}],
            "inputAudioTranscription": {},
            "outputAudioTranscription": {},
        }},
    }


def new_session(preferred: Optional[str] = None, voice: str = "") -> dict:
    provider = pick(preferred)
    if provider is None:
        raise LookupError("Add an OpenAI or Gemini API key in Settings to use Live voice.")
    return openai_session(voice) if provider == "openai" else gemini_session(voice)


def task_message(task: str, ai: Optional[str], has_session: bool) -> str:
    """The chat message a run_task call becomes: to the named AI, else the
    focused session, else Kelvin's smart routing."""
    task = (task or "").strip()
    ai = (ai or "").strip().lower().lstrip("@")
    if ai and ai != "kelvin":
        return f"@{ai} {task}"
    return task if has_session else f"@kelvin {task}"
