"""Every approval outcome is logged and announced, whichever way it was decided.

A request that timed out was neither written to the audit log nor announced, so its
banner stayed up; one decided with /approve in WhatsApp, Discord or Slack wasn't
announced to the web UI either.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.approval as appr
import helm.approval_rules as approval_rules
import helm.audit as audit


def _setup(tmp_path, monkeypatch):
    import helm.paths as paths
    import helm.state as _st
    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(_st, "approval_queue", {}, raising=False)
    monkeypatch.setattr(audit, "_path", lambda: tmp_path / "audit.jsonl")
    monkeypatch.setattr(approval_rules, "evaluate", lambda text: None)
    sent = []

    async def fake_broadcast(msg):
        sent.append(msg)
    monkeypatch.setattr("helm.broadcast.broadcast", fake_broadcast)
    return sent


def test_timeout_is_audited_and_announced(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch)

    async def go():
        req = appr.create_request("s1", "test", "delete everything")
        outcome = await appr.wait(req["id"], timeout=0.05)
        await asyncio.sleep(0.01)
        return req, outcome
    req, outcome = asyncio.run(go())

    assert outcome == "timeout" and req["status"] == "timeout"
    resolved = [e for e in audit.read() if e["event"] == "approval_resolved"]
    assert resolved and resolved[-1]["action"] == "timeout"
    assert [m["type"] for m in sent] == ["approval_resolved"]


def test_resolve_from_any_channel_is_announced_once(tmp_path, monkeypatch):
    sent = _setup(tmp_path, monkeypatch)

    async def go():
        req = appr.create_request("s1", "test", "send an email")
        waiter = asyncio.create_task(appr.wait(req["id"], timeout=5))
        await asyncio.sleep(0)
        assert appr.resolve(req["id"], "approved", source="whatsapp")
        outcome = await waiter
        await asyncio.sleep(0.01)
        return outcome
    assert asyncio.run(go()) == "approved"
    assert [m["type"] for m in sent] == ["approval_resolved"]
