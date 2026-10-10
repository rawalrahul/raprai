"""Headless mode (servers) and Kelvin's report on WhatsApp."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.headless as hl


def test_explicit_flag(monkeypatch):
    monkeypatch.setenv("RAPR_HEADLESS", "1")
    assert hl.is_headless()
    monkeypatch.setenv("RAPR_HEADLESS", "no")
    assert not hl.is_headless()


def test_linux_without_display_is_headless(monkeypatch):
    monkeypatch.delenv("RAPR_HEADLESS", raising=False)
    monkeypatch.setattr(hl.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert hl.is_headless()
    monkeypatch.setenv("DISPLAY", ":0")
    assert not hl.is_headless()


def test_desktop_is_not_headless(monkeypatch):
    monkeypatch.delenv("RAPR_HEADLESS", raising=False)
    monkeypatch.setattr(hl.sys, "platform", "win32")
    assert not hl.is_headless()


def test_kelvin_report_skips_desktop_lines_when_headless(monkeypatch):
    import helm.state as _st
    import helm.kelvin_report as kr
    monkeypatch.setattr(_st, "scheduled_tasks", {}, raising=False)
    monkeypatch.setenv("RAPR_HEADLESS", "1")
    text = kr.kelvin_report()
    assert "Keep PC awake" not in text and "Desktop Kelvin" not in text
    assert text.startswith("🐧 Kelvin is on.")
    monkeypatch.setenv("RAPR_HEADLESS", "0")
    assert "Desktop Kelvin" in kr.kelvin_report()


def test_whatsapp_kelvin_command(monkeypatch):
    import helm.whatsapp_bridge as wa
    monkeypatch.setenv("RAPR_HEADLESS", "1")
    replies = asyncio.run(wa.handle_text("/kelvin"))
    assert replies and replies[0].startswith("🐧 Kelvin is on.")
    assert "/kelvin" in wa.HELP


def test_whatsapp_approvals(monkeypatch, tmp_path):
    import helm.whatsapp_bridge as wa
    import helm.approval as appr
    import helm.audit as audit
    import helm.state as _st
    monkeypatch.setattr(_st, "approval_queue", {}, raising=False)
    monkeypatch.setattr(audit, "_path", lambda: tmp_path / "audit.jsonl")
    req = appr.create_request("s1", "pipeline_step", "Run git push to main", details=["git push origin main"])
    rid = req["id"]
    assert rid in wa.approval_text(req) and "/approve" in wa.approval_text(req)
    assert "Nothing" not in asyncio.run(wa.handle_text("/approvals"))[0]
    assert "Approved" in asyncio.run(wa.handle_text(f"/approve {rid}"))[0]
    assert req["status"] == "approved" and req["resolved_by"] == "whatsapp"
    assert "No pending" in asyncio.run(wa.handle_text(f"/deny {rid}"))[0]
    assert asyncio.run(wa.handle_text("/approvals"))[0] == "Nothing is waiting for approval."
