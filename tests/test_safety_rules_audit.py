"""Approval rules (ask / deny / allow) and the audit log."""
import asyncio
import importlib
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
