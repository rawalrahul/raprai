"""Linked chat apps stay in sync with sessions: a message sent from one app (or the
RAPR app) and the AI's reply reach every other linked chat app."""
import asyncio
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import helm.groupchat as gc
from helm.ai_runner.helpers import mirror_to_chat_apps

SESS = {"id": "s1", "name": "Claude #1", "emoji": "🤖"}


@pytest.fixture
def apps(monkeypatch):
    monkeypatch.setattr(gc, "_channel_senders", {})
    sent = {}
    for ch in ("telegram", "whatsapp", "discord"):
        sent[ch] = []

        def make(c):
            async def send(group, text):
                sent[c].append(text)
            return send
        gc.register_channel(ch, make(ch))
    return sent


@pytest.mark.parametrize("source", ["web", "telegram", "whatsapp", "discord"])
def test_every_other_chat_app_gets_the_exchange(apps, source):
    asyncio.run(mirror_to_chat_apps(SESS, "Fixed the bug ✅", source, prompt_text="fix the login bug"))
    for ch, msgs in apps.items():
        if ch == "telegram":
            assert msgs == []                 # Telegram has its own mirror (tg_progress_notify)
        elif ch == source:
            assert msgs == []                 # the app you asked from already has the reply
        else:
            assert len(msgs) == 1, (ch, msgs)
            assert msgs[0].startswith("🤖 Claude #1\n🧑 You (from ")
            assert "fix the login bug" in msgs[0] and msgs[0].endswith("Fixed the bug ✅")


def test_agent_runs_and_silent_sessions_are_not_mirrored(apps):
    asyncio.run(mirror_to_chat_apps(SESS, "x", "agent", prompt_text="y"))
    asyncio.run(mirror_to_chat_apps({**SESS, "agent_silent_telegram": True}, "x", "web", prompt_text="y"))
    assert all(m == [] for m in apps.values())


def test_long_prompts_are_shortened(apps):
    asyncio.run(mirror_to_chat_apps(SESS, "ok", "web", prompt_text="a" * 2000))
    assert len(apps["whatsapp"][0]) < 700 and "…" in apps["whatsapp"][0]


def test_a_real_session_reply_is_mirrored(tmp_path, monkeypatch, apps):
    """Through RAPR's real message path, with a stand-in AI."""
    if sys.platform == "win32":
        pytest.skip("uses a #! script as a stand-in AI")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "opencode").write_text(f"#!{sys.executable}\nimport sys\nsys.stdin.read()\nprint('Fixed the bug')\n")
    (bindir / "opencode").chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path / "data"))
    import helm.state as st
    from helm.db import init_db
    from helm.integrations import load_integrations
    from helm.session_mgr import make_session
    from helm.ai_runner.core import process_message
    init_db()
    st.integrations.clear()
    load_integrations()
    sess = make_session("opencode", cwd=str(tmp_path))
    out = asyncio.run(asyncio.wait_for(process_message("fix the login bug", source="web", session_id=sess["id"]), 60))
    assert "Fixed the bug" in out
    assert len(apps["whatsapp"]) == 1 and "fix the login bug" in apps["whatsapp"][0]
    assert "Fixed the bug" in apps["whatsapp"][0] and len(apps["discord"]) == 1
