"""Chat apps (Discord, Slack) through the shared bridge, with a fake chat app."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.chat_bridge as cb
import helm.groupchat as gc
import helm.state as _st


def test_only_allowed_users_get_answers(monkeypatch):
    sent = []

    async def send(chat, text):
        sent.append((chat, text))

    async def fake_handle(channel, text):
        return [f"{channel} got: {text}"]
    import helm.chat_router as router
    monkeypatch.setattr(router, "handle", fake_handle)

    bridge = cb.ChatBridge("discord", send, ["111"])
    asyncio.run(bridge.on_message("999", "chan-1", "hello"))      # stranger
    asyncio.run(bridge.on_message("111", "chan-1", "hello"))      # you
    assert sent == [("chan-1", "discord got: hello")]


def test_nobody_is_allowed_when_no_ids_are_set(monkeypatch):
    sent = []

    async def send(chat, text):
        sent.append(text)
    bridge = cb.ChatBridge("slack", send, [])
    asyncio.run(bridge.on_message("anyone", "c", "hi"))
    assert sent == []


def test_long_replies_are_split():
    parts = cb.chunks("x" * 4000, 1900)
    assert [len(p) for p in parts] == [1900, 1900, 200]


def test_command_errors_are_reported_not_raised(monkeypatch):
    sent = []

    async def send(chat, text):
        sent.append(text)

    async def boom(channel, text):
        raise RuntimeError("disk full")
    import helm.chat_router as router
    monkeypatch.setattr(router, "handle", boom)
    asyncio.run(cb.ChatBridge("slack", send, ["1"]).on_message("1", "c", "x"))
    assert "disk full" in sent[0]


def test_group_messages_reach_the_chat_the_app_last_used(monkeypatch):
    monkeypatch.setattr(gc, "_channel_senders", {})
    sent = []

    async def send(chat, text):
        sent.append((chat, text))

    async def fake_handle(channel, text):
        return []
    import helm.chat_router as router
    monkeypatch.setattr(router, "handle", fake_handle)
    bridge = cb.ChatBridge("discord", send, ["1"])
    bridge.register()
    asyncio.run(bridge.on_message("1", "chan-9", "hi"))
    asyncio.run(bridge.relay_group({}, "Claude: hello"))
    assert sent == [("chan-9", "Claude: hello")]


def test_adapters_import_without_their_libraries():
    import helm.chat_adapters.startup as st
    assert callable(st.start_configured)
    assert st.start_configured() == []     # no tokens in the test environment
