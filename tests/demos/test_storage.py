import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def _make_storage(tmp):
    """Patch HELM_DIR so storage uses a temp directory."""
    import helm.demos.storage as s
    s.DEMOS_DIR = Path(tmp) / "demos"
    s.RAW_DIR = s.DEMOS_DIR / "raw"
    s.PROCESSED_DIR = s.DEMOS_DIR / "processed"
    s.LIBRARY_FILE = s.DEMOS_DIR / "library.json"
    return s


def test_create_demo_returns_expected_fields():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        meta = s.create_demo("screen recording.mp4")
        assert meta["status"] == "uploading"
        assert meta["title"] == "screen_recording"
        assert meta["source_filename"] == "screen recording.mp4"
        assert meta["demo_id"]
        assert meta["uploaded_at"]


def test_create_demo_creates_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        meta = s.create_demo("test.mp4")
        demo_id = meta["demo_id"]
        assert (s.RAW_DIR / demo_id).is_dir()
        assert (s.PROCESSED_DIR / demo_id).is_dir()
        assert (s.RAW_DIR / demo_id / "meta.json").exists()


def test_list_demos_returns_empty_when_no_demos():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        assert s.list_demos() == []


def test_list_demos_returns_created_demos():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        s.create_demo("a.mp4")
        s.create_demo("b.mp4")
        demos = s.list_demos()
        assert len(demos) == 2


def test_update_meta_persists():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        meta = s.create_demo("test.mp4")
        demo_id = meta["demo_id"]
        s.update_meta(demo_id, {"status": "ready", "duration_s": 42.5})
        result = s.get_demo(demo_id)
        assert result["status"] == "ready"
        assert result["duration_s"] == 42.5


def test_delete_demo_removes_dirs_and_library_entry():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        meta = s.create_demo("test.mp4")
        demo_id = meta["demo_id"]
        s.delete_demo(demo_id)
        assert not (s.RAW_DIR / demo_id).exists()
        assert not (s.PROCESSED_DIR / demo_id).exists()
        assert all(d["demo_id"] != demo_id for d in s.list_demos())


def test_save_and_read_actions():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        meta = s.create_demo("test.mp4")
        demo_id = meta["demo_id"]
        actions = [{"step": 1, "timestamp": "0:01", "action": "click", "target": "button", "content": "", "intent": "Click"}]
        s.save_actions(demo_id, actions)
        result = s.get_demo(demo_id)
        assert result["actions"] == actions


def test_get_demo_returns_none_for_unknown_id():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        assert s.get_demo("nonexistent") is None


def test_title_strips_extension_and_replaces_spaces():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        meta = s.create_demo("my screen recording 2.mp4")
        assert meta["title"] == "my_screen_recording_2"


def test_update_meta_raises_for_unknown_id():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        try:
            s.update_meta("nonexistent1", {"status": "ready"})
            assert False, "Should have raised KeyError"
        except KeyError:
            pass


def test_get_demo_raises_for_invalid_demo_id():
    with tempfile.TemporaryDirectory() as tmp:
        s = _make_storage(tmp)
        try:
            s.get_demo("../../etc/passwd")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
