"""Approval rules (ask / deny / allow) and the audit log."""
import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.approval as appr
import helm.approval_rules as rules
import helm.audit as audit
import helm.state as _st


@pytest.fixture
def data(tmp_path, monkeypatch):
    import helm.paths as paths
    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(rules, "_path", lambda: tmp_path / "approval_rules.json")
    monkeypatch.setattr(audit, "_path", lambda: tmp_path / "audit.jsonl")
    monkeypatch.setattr(_st, "approval_queue", {}, raising=False)
    return tmp_path


def test_rule_validation():
    assert rules.validate({"id": "a", "match": "git push", "action": "DENY"})["action"] == "deny"
    for bad in ({"id": "", "match": "x"}, {"id": "a", "match": ""},
                {"id": "a", "match": "x", "action": "maybe"}, {"id": "a", "match": "("}):
        with pytest.raises(ValueError):
            rules.validate(bad)


def test_first_enabled_matching_rule_wins():
    rs = [{"id": "off", "match": "push", "action": "deny", "enabled": False},
          {"id": "main", "match": "push.*main", "action": "deny", "enabled": True},
          {"id": "any", "match": "push", "action": "allow", "enabled": True}]
    assert rules.evaluate("git push origin main", rs)["id"] == "main"
    assert rules.evaluate("git push origin dev", rs)["id"] == "any"
    assert rules.evaluate("ls", rs) is None


def test_deny_rule_refuses_without_asking(data):
    rules.save_rules([{"id": "no-main", "match": r"push.*\bmain\b", "action": "deny"}])
    req = appr.create_request("s1", "pipeline_step", "Run git push origin main")
    assert req["status"] == "denied" and req["resolved_by"] == "rule:no-main"
    assert asyncio.run(appr.wait(req["id"], timeout=1)) == "denied"
    assert appr.pending() == []
    assert appr.resolve(req["id"], "approved") is False   # already decided
    events = [e["event"] for e in audit.read()]
    assert events == ["rule_applied"]


def test_allow_rule_approves(data):
    rules.save_rules([{"id": "tests", "match": "pytest", "action": "allow"}])
    req = appr.create_request("s1", "pipeline_step", "Run pytest")
    assert req["status"] == "approved"


def test_ask_rule_and_default_still_ask(data):
    rules.save_rules([{"id": "careful", "match": "deploy", "action": "ask"}])
    req = appr.create_request("s1", "pipeline_step", "Deploy to production")
    assert req["status"] == "pending"
    assert appr.resolve(req["id"], "approved", source="web")
    entries = audit.read()
    assert [e["event"] for e in entries] == ["approval_resolved", "approval_requested"]
    assert entries[0]["source"] == "web" and entries[0]["action"] == "approved"


def test_duplicate_rule_ids_are_refused(data):
    with pytest.raises(ValueError, match="same id"):
        rules.save_rules([{"id": "x", "match": "a", "action": "ask"},
                          {"id": "x", "match": "b", "action": "deny"}])


def test_rules_file_is_saved_and_validated(data):
    rules.save_rules([{"id": "x", "match": "rm", "action": "deny", "description": "no rm"}])
    assert json.loads((data / "approval_rules.json").read_text())["rules"][0]["match"] == "rm"
    with pytest.raises(ValueError):
        rules.save_rules([{"id": "x", "match": "rm", "action": "nope"}])


def test_audit_filter_and_csv(data):
    audit.record("approval_requested", id="a1", description="Run rm -rf build", action="pipeline_step")
    audit.record("approval_resolved", id="a1", action="denied", source="telegram")
    audit.record("approval_requested", id="a2", description="Deploy", action="pipeline_step")
    assert len(audit.read(event="approval_requested")) == 2
    assert [e["id"] for e in audit.read(query="rm -rf")] == ["a1"]
    csv_text = audit.to_csv(audit.read())
    assert csv_text.splitlines()[0].startswith("ts,event,id,action,description")
    assert "telegram" in csv_text


def test_audit_survives_a_corrupt_line(data):
    (data / "audit.jsonl").write_text('{"ts": 1, "event": "x"}\nnot json\n{"ts": 2, "event": "y"}\n')
    assert [e["event"] for e in audit.read()] == ["y", "x"]


def _lines(data):
    return (data / "audit.jsonl").read_text().splitlines()


def _write(data, lines):
    (data / "audit.jsonl").write_text("\n".join(lines) + "\n")


def _three(data):
    for i in range(3):
        audit.record("approval_requested", id=f"a{i}", description=f"step {i}")


def test_audit_chain_verifies(data):
    assert audit.verify() == {"ok": True, "entries": 0, "legacy": 0, "head": "", "problem": None, "anchor": None}
    _three(data)
    v = audit.verify()
    assert v["ok"] and v["entries"] == 3 and v["head"] == json.loads(_lines(data)[-1])["h"]
    assert json.loads(_lines(data)[1])["prev"] == json.loads(_lines(data)[0])["h"]
    assert (data / ".audit_key").exists()


def test_audit_edit_is_detected(data):
    _three(data)
    lines = _lines(data)
    lines[1] = lines[1].replace("step 1", "step one")
    _write(data, lines)
    v = audit.verify()
    assert not v["ok"] and v["problem"] == {"line": 2, "reason": "entry was edited"}


def test_audit_removed_or_reordered_line_is_detected(data):
    _three(data)
    lines = _lines(data)
    _write(data, [lines[0], lines[2]])
    assert audit.verify()["problem"]["line"] == 2
    _write(data, [lines[1], lines[0], lines[2]])
    assert audit.verify()["problem"]["line"] == 1


def test_audit_inserted_unsigned_line_is_detected(data):
    _three(data)
    lines = _lines(data)
    _write(data, lines[:2] + ['{"ts": 5, "event": "approval_resolved"}'] + lines[2:])
    assert audit.verify()["problem"] == {"line": 3, "reason": "unsigned entry after signing began"}


def test_audit_resigning_without_the_key_fails(data):
    _three(data)
    (data / ".audit_key").write_text("00" * 32)
    assert audit.verify()["problem"]["line"] == 1


def test_audit_legacy_lines_then_chain(data):
    (data / "audit.jsonl").write_text('{"ts": 1, "event": "x"}\n{"ts": 2, "event": "y"}\n')
    audit.record("approval_resolved", id="a1", action="approved")
    v = audit.verify()
    assert v["ok"] and v["legacy"] == 2 and v["entries"] == 1
    assert [e["event"] for e in audit.read()] == ["approval_resolved", "y", "x"]


def test_audit_chain_continues_after_outside_append(data):
    audit.record("approval_requested", id="a1")
    audit._head.clear()   # as after a restart
    audit.record("approval_resolved", id="a1", action="approved")
    assert audit.verify()["entries"] == 2


def test_audit_search_ignores_hashes(data):
    audit.record("approval_requested", id="a1", description="deploy")
    h = json.loads(_lines(data)[0])["h"]
    assert audit.read(query=h[:8]) == []


def _anchor(sent=None):
    sent = [] if sent is None else sent
    async def send(text):
        sent.append(text)
        return ["Telegram"]
    return asyncio.run(audit.anchor_now(send)), sent


def test_anchor_sends_only_when_the_log_grew(data):
    assert _anchor() == (None, [])            # empty log: nothing to send
    _three(data)
    text, sent = _anchor()
    head = audit.verify()["head"]
    assert len(sent) == 1 and "3 signed entries" in text and head in text
    assert audit.last_anchor()["entries"] == 3 and audit.last_anchor()["head"] == head
    assert _anchor() == (None, [])            # unchanged: stay quiet
    audit.record("approval_resolved", id="a1", action="approved")
    assert "4 signed entries" in _anchor()[0]
    assert audit.verify()["anchor"]["entries"] == 4


def test_anchor_catches_lines_cut_from_the_end(data):
    _three(data)
    _anchor()
    _write(data, _lines(data)[:2])
    v = audit.verify()
    assert not v["ok"] and "1 entries removed from the end" in v["problem"]["reason"]


def test_anchor_catches_a_resigned_log(data):
    _three(data)
    _anchor()
    lines = [json.loads(x) for x in _lines(data)]
    key = audit._key()
    prev = ""
    for e in lines:   # an attacker with the key edits and re-signs everything
        e["description"] = e["description"].upper()
        e["prev"] = prev
        e["h"] = audit._sign(key, e)
        prev = e["h"]
    _write(data, [json.dumps(e) for e in lines])
    v = audit.verify()
    assert not v["ok"] and v["problem"]["line"] == 3 and "rewritten" in v["problem"]["reason"]


def test_broken_log_warns_once_a_day_and_keeps_the_good_anchor(data):
    _three(data)
    _anchor()
    good = audit.last_anchor()
    lines = _lines(data)
    _write(data, [lines[0].replace("step 0", "step zero")] + lines[1:])
    text, _ = _anchor()
    assert text.startswith("⚠️") and "entry was edited" in text
    after = audit.last_anchor()
    assert (after["entries"], after["head"]) == (good["entries"], good["head"]) and after["ts"] >= good["ts"]


def test_anchor_works_with_no_chat_app(data):
    _three(data)
    assert "3 signed entries" in asyncio.run(audit.anchor_now(None))
    assert audit.last_anchor()["sent_to"] == []
    assert audit.verify()["anchor"]["sent_to"] == []
    _write(data, _lines(data)[:1])
    assert "removed from the end" in audit.verify()["problem"]["reason"]


def test_anchor_goes_to_every_linked_app(data, monkeypatch):
    import helm.groupchat as gc
    import helm.whatsapp_bridge as wa
    got = []

    class Bot:
        async def send_message(self, chat_id, text):
            got.append(("telegram", chat_id))

    class Bridge:
        def __init__(self, name, last_chat):
            self.name, self.last_chat = name, last_chat

        async def relay_group(self, group, text):
            got.append((self.name, self.last_chat))

    async def wa_send(text, to=None):
        got.append(("whatsapp", None))

    monkeypatch.setattr(_st, "telegram_app", type("A", (), {"bot": Bot()})(), raising=False)
    monkeypatch.setattr(_st, "telegram_chat_id", 42, raising=False)
    monkeypatch.setattr(wa, "state", {"status": "connected"})
    monkeypatch.setattr(wa, "send_text", wa_send)
    monkeypatch.setattr(gc, "_channel_senders", {"discord": Bridge("discord", "c1").relay_group,
                                                 "slack": Bridge("slack", None).relay_group})
    assert asyncio.run(audit.send_to_chat_apps("hi")) == ["Telegram", "WhatsApp", "Discord"]
    assert got == [("telegram", 42), ("whatsapp", None), ("discord", "c1")]


def test_nothing_linked_sends_nowhere(data, monkeypatch):
    import helm.groupchat as gc
    import helm.whatsapp_bridge as wa
    monkeypatch.setattr(_st, "telegram_app", None, raising=False)
    monkeypatch.setattr(wa, "state", {"status": "disconnected"})
    monkeypatch.setattr(gc, "_channel_senders", {})
    assert asyncio.run(audit.send_to_chat_apps("hi")) == []


def test_anchor_loop_anchors_locally_and_audit_anchor_0_stops_sending(data, monkeypatch):
    _three(data)
    sent = []
    async def send(text):
        sent.append(text)
        return ["Telegram"]
    monkeypatch.setattr(audit, "send_to_chat_apps", send)
    monkeypatch.setenv("AUDIT_ANCHOR", "0")
    sleeps = []
    async def fake_sleep(s):
        sleeps.append(s)
        if len(sleeps) > 1:
            raise asyncio.CancelledError
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(audit.anchor_loop())
    assert sleeps == [120, 3600] and sent == []
    assert audit.last_anchor()["entries"] == 3 and audit.last_anchor()["sent_to"] == []
