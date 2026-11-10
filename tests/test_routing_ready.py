"""Auto (and a first message sent before any AI was picked) only chooses AIs
that are ready: an installed Claude Code, set-up integrations, or ones with a
running session. It used to count every known integration, installed or not,
and never counted Claude Code unless a Claude chat was already open."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.state as _st
from helm.web_routes import routing_routes, session_routes


def _setup(monkeypatch, installed, integrations, sessions=None):
    monkeypatch.setattr(_st, "integrations", integrations)
    monkeypatch.setattr(_st, "sessions", sessions or {})
    monkeypatch.setattr(session_routes, "_find_cli", lambda name: name in installed)
    monkeypatch.setattr(session_routes, "_integration_ready", lambda key, info: info.get("ok", False))


def test_only_ready_ais_are_offered(monkeypatch):
    _setup(monkeypatch, {"claude"}, {"ollama": {"ok": False}, "codex": {"ok": True}})
    assert routing_routes._ready_ais() == ["claude", "codex"]


def test_claude_is_offered_without_an_open_chat(monkeypatch):
    _setup(monkeypatch, {"claude"}, {})
    assert routing_routes._ready_ais() == ["claude"]


def test_a_running_session_counts(monkeypatch):
    _setup(monkeypatch, set(), {"ollama": {"ok": False}},
           {"s1": {"ai": "ollama", "status": "running"}, "s2": {"ai": "codex", "status": "stopped"}})
    assert routing_routes._ready_ais() == ["ollama"]


def test_nothing_ready_means_no_pick(monkeypatch):
    _setup(monkeypatch, set(), {"ollama": {"ok": False}})
    from helm import smart_routing as sr
    assert sr.decide("hello", routing_routes._ready_ais()).ai is None
