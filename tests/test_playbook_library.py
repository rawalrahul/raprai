"""Playbook library: browse, read, switch on/off, export."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.playbook_library as lib
from helm.learning import playbook as pb


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(pb, "_PLAYBOOKS_DIR", tmp_path)
    for tt, name, status in (("code.debug", "fix_flaky_tests", "active"),
                             ("code.write", "add_endpoint", "draft"),
                             ("research", "old_note", "disabled")):
        d = tmp_path / tt / name
        d.mkdir(parents=True)
        (d / "meta.json").write_text(json.dumps({"name": name, "task_type": tt, "status": status,
                                                  "version": 2, "success_rate": 0.9, "sample_count": 4,
                                                  "source_task_ids": ["t1"]}))
        (d / "current.md").write_text(f"# {name}\nSteps...")
    return tmp_path


def test_lists_every_status(root):
    items = {i["name"]: i["status"] for i in lib.list_all()}
    assert items == {"fix_flaky_tests": "active", "add_endpoint": "draft", "old_note": "disabled"}


def test_read_and_switch(root):
    assert lib.read("code.debug", "fix_flaky_tests").startswith("# fix_flaky_tests")
    lib.set_status("code.debug", "fix_flaky_tests", "disabled")
    assert {i["name"]: i["status"] for i in lib.list_all()}["fix_flaky_tests"] == "disabled"
    # Disabled playbooks are not returned by the learning code's active lookup.
    assert all(p["name"] != "fix_flaky_tests" for p in pb.list_playbooks("code.debug"))


def test_bad_names_and_statuses_are_refused(root):
    with pytest.raises(ValueError):
        lib.read("..", "x")
    with pytest.raises(ValueError):
        lib.set_status("code.debug", "fix_flaky_tests", "deleted")


def test_export_bundle_includes_content(root):
    bundle = lib.export_bundle()
    assert bundle["format"] == "rapr-playbooks-1"
    assert all(p["content"] for p in bundle["playbooks"])
