"""Better voice: Kokoro speech on this PC, Whisper loaded once, and Live voice
tokens for OpenAI Realtime / Gemini Live (network calls faked)."""
import asyncio
import json
import os
import pathlib
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm import tts_local, voice, voice_live
import helm.web_routes.voice_routes as vr


class Req:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def run(coro):
    return asyncio.run(coro)


def body(resp):
    return json.loads(resp.body)


# ── Speaking text ──────────────────────────────────────────────────────────────

def test_speakable_drops_markdown_code_links_and_emoji():
    text = ("## Done\nI fixed `login()`. **It was** a missing await 🎉\n\n```py\nawait x()\n```\n"
            "- see [the docs](https://x.dev/a) or https://x.dev/b")
    out = tts_local.speakable(text)
    assert "```" not in out and "**" not in out and "#" not in out and "🎉" not in out
    assert "code is in the chat" in out and "the docs" in out and "https" not in out
    assert out.startswith("Done") and "login()" in out


def test_each_ai_keeps_its_voice_and_kelvin_has_the_default():
    assert tts_local.voice_for(None) == tts_local.voice_for("kelvin") == tts_local.DEFAULT_VOICE
    assert tts_local.voice_for("codex") == tts_local.voice_for("codex") in tts_local.VOICES


# ── Whisper is loaded once ─────────────────────────────────────────────────────

def test_whisper_model_is_loaded_once_and_reused(monkeypatch, tmp_path):
    loads = []

    class FakeModel:
        def __init__(self, name, **kw):
            loads.append((name, kw))

        def transcribe(self, path, **kw):
            assert kw["initial_prompt"] == "Hey Kelvin." and kw["vad_filter"]
            return iter([types.SimpleNamespace(text=" Hey Kelvin,"), types.SimpleNamespace(text=" hi ")]), None
    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    monkeypatch.setattr(voice, "_models", {})
    monkeypatch.setenv("VOICE_STT_MODEL", "base")
    f = tmp_path / "a.wav"
    f.write_bytes(b"RIFF")
    assert voice.transcribe_file(str(f)) == "Hey Kelvin, hi"
    assert voice.transcribe_file(str(f)) == "Hey Kelvin, hi"
    assert loads == [("base", {"device": "cpu", "compute_type": "int8"})]


# ── /tts picks the best voice it has ───────────────────────────────────────────

def test_tts_uses_kokoro_when_ready(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setattr(tts_local, "_engine", object())
    said = []
    monkeypatch.setattr(tts_local, "synthesize", lambda text, v: said.append((text, v)) or b"WAV")
    resp = run(vr.text_to_speech(Req({"text": "**Hello** there", "ai": "codex"})))
    assert resp.body == b"WAV" and resp.media_type == "audio/wav"
    assert said == [("Hello there", tts_local.voice_for("codex"))]
    assert vr.tts_backend() == "kokoro"


def test_tts_falls_back_to_os_voice_and_starts_preparing_kokoro(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setattr(tts_local, "_engine", None)
    prepared = []
    monkeypatch.setattr(tts_local, "prepare", lambda *a, **k: prepared.append(1))
    monkeypatch.setattr(vr, "_tts_offline", lambda text: b"OSWAV")
    resp = run(vr.text_to_speech(Req({"text": "Hi"})))
    assert resp.body == b"OSWAV" and prepared == [1] and vr.tts_backend() == "offline"


def test_tts_status_reports_local_voice_and_live_keys(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    d = body(run(vr.tts_status()))
    assert d["live"] == {"openai": False, "gemini": True} and "status" in d["local"]


# ── Live voice ─────────────────────────────────────────────────────────────────

@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test")
    for k in ("OPENAI_REALTIME_MODEL", "GEMINI_LIVE_MODEL", "OPENAI_REALTIME_VOICE", "GEMINI_LIVE_VOICE"):
        monkeypatch.delenv(k, raising=False)
    calls = []

    def fake_post(url, body, headers):
        calls.append((url, body, headers))
        return {"value": "ek_123"} if "openai" in url else {"name": "auth_tokens/abc"}
    monkeypatch.setattr(voice_live, "_post", fake_post)
    return calls


def test_openai_live_session_gets_a_short_lived_token(keys):
    d = voice_live.new_session("openai")
    url, sent, headers = keys[0]
    assert url == "https://api.openai.com/v1/realtime/client_secrets"
    assert headers == {"Authorization": "Bearer sk-test"}
    s = sent["session"]
    assert s["type"] == "realtime" and s["model"] == voice_live.OPENAI_MODEL
    assert s["tools"][0]["name"] == "run_task" and s["tools"][0]["type"] == "function"
    assert "Kelvin" in s["instructions"]
    assert d == {"provider": "openai", "token": "ek_123", "model": voice_live.OPENAI_MODEL,
                 "calls_url": "https://api.openai.com/v1/realtime/calls"}
    assert "sk-test" not in json.dumps(d)          # the real key never reaches the browser


def test_gemini_live_session_gets_a_one_use_token_and_setup(keys):
    d = voice_live.new_session("gemini")
    url, sent, headers = keys[0]
    assert url == "https://generativelanguage.googleapis.com/v1alpha/auth_tokens"
    assert headers == {"x-goog-api-key": "AIza-test"} and sent["uses"] == 1
    assert d["ws_url"].endswith("BidiGenerateContentConstrained?access_token=auth_tokens/abc")
    setup = d["setup"]["setup"]
    assert setup["model"] == f"models/{voice_live.GEMINI_MODEL}"
    assert setup["generationConfig"]["responseModalities"] == ["AUDIO"]
    assert setup["tools"][0]["functionDeclarations"][0]["name"] == "run_task"
    assert "AIza-test" not in json.dumps(d)


def test_live_picks_whichever_key_is_set(monkeypatch, keys):
    monkeypatch.delenv("GEMINI_API_KEY")
    assert voice_live.new_session("gemini")["provider"] == "openai"   # asked for Gemini, only OpenAI set
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(LookupError):
        voice_live.new_session(None)


def test_live_session_route_explains_a_missing_key(monkeypatch):
    for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    resp = run(vr.live_session(Req({})))
    assert resp.status_code == 400 and "API key" in body(resp)["error"]


@pytest.mark.parametrize("task, ai, has, msg", [
    ("fix the tests", "", True, "fix the tests"),
    ("fix the tests", "", False, "@kelvin fix the tests"),
    ("fix the tests", "Codex", True, "@codex fix the tests"),
    ("hello", "kelvin", False, "@kelvin hello"),
])
def test_live_tasks_go_to_the_right_place(task, ai, has, msg):
    assert voice_live.task_message(task, ai, has) == msg


def test_live_task_route_runs_it_and_returns_the_reply(monkeypatch):
    import helm.ai_runner as ar
    import helm.state as _st
    monkeypatch.setattr(_st, "sessions", {}, raising=False)
    monkeypatch.setattr(_st, "focused_id", None, raising=False)
    sent = []

    async def fake_process(text, source="web", session_id=None):
        sent.append((text, source))
        return "All 12 tests pass."
    monkeypatch.setattr(ar, "process_message", fake_process)
    d = body(run(vr.live_task(Req({"task": "run the tests"}))))
    assert d == {"reply": "All 12 tests pass."} and sent == [("@kelvin run the tests", "web")]


# ── The real Kokoro model, when it's on this machine ──────────────────────────

KOKORO_DIR = os.environ.get("KOKORO_TEST_DIR", "")


@pytest.mark.skipif(not (KOKORO_DIR and pathlib.Path(KOKORO_DIR, "kokoro-v1.0.int8.onnx").exists()),
                    reason="set KOKORO_TEST_DIR to a folder with the Kokoro model files")
def test_real_kokoro_speaks(monkeypatch):
    monkeypatch.setattr(tts_local, "_dir", lambda: pathlib.Path(KOKORO_DIR))
    monkeypatch.setattr(tts_local, "_engine", None)
    monkeypatch.setitem(tts_local._state, "status", "off")
    tts_local.prepare(background=False)
    assert tts_local.is_ready()
    wav = tts_local.synthesize("Hi, I'm Kelvin.", "af_heart")
    assert wav[:4] == b"RIFF" and len(wav) > 20000
