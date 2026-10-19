"""Voice messages from WhatsApp, Discord and Slack: transcribed, then handled
like typed text (Whisper itself is faked)."""
import asyncio
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.chat_bridge as cb
import helm.chat_router as router
import helm.voice as voice


@pytest.fixture
def fake_whisper(monkeypatch):
    heard = {}

    def fake_transcribe(path):
        with open(path, "rb") as f:
            heard["audio"] = f.read()
        heard["ext"] = os.path.splitext(path)[1]
        return heard.get("say", "Hey Kelvin, hello")
    monkeypatch.setattr(voice, "transcribe_file", fake_transcribe)
    handled = []

    async def fake_handle(channel, text):
        handled.append((channel, text))
        return [f"reply to {text}"]
    monkeypatch.setattr(router, "handle", fake_handle)
    return heard, handled


def _bridge(sent, allowed=("1",)):
    async def send(chat, text):
        sent.append((chat, text))
    return cb.ChatBridge("discord", send, list(allowed))


def test_voice_message_is_transcribed_and_handled_like_text(fake_whisper):
    heard, handled = fake_whisper
    sent = []
    asyncio.run(_bridge(sent).on_voice("1", "c", b"OggS-audio", "ogg"))
    assert heard == {"audio": b"OggS-audio", "ext": ".ogg"}
    assert handled == [("discord", "Hey Kelvin, hello")]
    assert [t for _, t in sent] == ["🎤 Transcribing voice message…", "🎤 Transcript: Hey Kelvin, hello",
                                    "reply to Hey Kelvin, hello"]


def test_voice_from_a_stranger_is_not_transcribed(fake_whisper):
    heard, handled = fake_whisper
    sent = []
    asyncio.run(_bridge(sent).on_voice("999", "c", b"x"))
    assert heard == {} and handled == [] and sent == []


def test_silent_or_failed_voice_messages_say_so(fake_whisper, monkeypatch):
    heard, handled = fake_whisper
    heard["say"] = ""
    sent = []
    asyncio.run(_bridge(sent).on_voice("1", "c", b"x"))
    assert "no speech detected" in sent[-1][1] and handled == []

    def boom(path):
        raise RuntimeError("ffmpeg missing")
    monkeypatch.setattr(voice, "transcribe_file", boom)
    sent.clear()
    asyncio.run(_bridge(sent).on_voice("1", "c", b"x"))
    assert "ffmpeg missing" in sent[-1][1] and handled == []


@pytest.mark.parametrize("mime, name, ext", [
    ("audio/ogg; codecs=opus", "", "ogg"), ("audio/webm", "", "webm"),
    ("audio/mp4", "", "m4a"), ("audio/mpeg", "", "mp3"), ("audio/ogg", "voice-message.ogg", "ogg"),
    ("", "clip.M4A", "m4a"), ("", "", "ogg"),
])
def test_audio_ext(mime, name, ext):
    assert voice.audio_ext(mime, name) == ext


def test_discord_picks_the_audio_attachment():
    from helm.chat_adapters.discord_app import _audio_attachment
    pic = SimpleNamespace(content_type="image/png", size=10, filename="a.png")
    note = SimpleNamespace(content_type="audio/ogg", size=10, filename="voice-message.ogg")
    huge = SimpleNamespace(content_type="audio/ogg", size=10**9, filename="long.ogg")
    assert _audio_attachment(SimpleNamespace(attachments=[pic, note])) is note
    assert _audio_attachment(SimpleNamespace(attachments=[pic, huge])) is None
    assert _audio_attachment(SimpleNamespace(attachments=[])) is None


def test_slack_finds_audio_clips_only_in_file_shares():
    from helm.chat_adapters.slack_app import audio_file
    clip = {"mimetype": "audio/webm", "subtype": "slack_audio", "size": 100,
            "url_private_download": "https://files.slack.com/x"}
    doc = {"mimetype": "application/pdf", "size": 100, "url_private_download": "https://files.slack.com/y"}
    assert audio_file({"subtype": "file_share", "files": [doc, clip]}) is clip
    assert audio_file({"subtype": "file_share", "files": [doc]}) is None
    assert audio_file({"subtype": "message_changed", "files": [clip]}) is None
    assert audio_file({"text": "hi"}) is None


def test_whatsapp_voice_note_is_transcribed_and_answered(fake_whisper, monkeypatch):
    import helm.whatsapp_bridge as wa
    wa._ensure_magic()
    wa._ensure_proto_aliases()
    from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
    heard, handled = fake_whisper
    msg = Message()
    msg.audioMessage.mimetype = "audio/ogg; codecs=opus"
    msg.audioMessage.PTT = True

    class Src(SimpleNamespace):
        def HasField(self, name):
            return False
    chat = SimpleNamespace(User="15550001111", Server="s.whatsapp.net")
    ev = SimpleNamespace(Message=msg, Info=SimpleNamespace(ID="m1", MessageSource=Src(
        Chat=chat, Sender=SimpleNamespace(User="15550001111"), IsFromMe=False, IsGroup=False)))

    class Client:
        async def download_any(self, m):
            assert m is msg
            return b"OggS-note"
    sent = []

    async def fake_send(text, to=None):
        sent.append(text)
    monkeypatch.setattr(wa, "send_text", fake_send)
    monkeypatch.setenv("WHATSAPP_ALLOWED_NUMBERS", "15550001111")
    asyncio.run(wa._on_message(Client(), ev))
    assert heard["audio"] == b"OggS-note" and heard["ext"] == ".ogg"
    assert handled == [("whatsapp", "Hey Kelvin, hello")]
    assert sent[-1] == "reply to Hey Kelvin, hello"
