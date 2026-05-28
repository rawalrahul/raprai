import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from helm.demos.playbook import actions_to_markdown, save_playbook


_SAMPLE_ACTIONS = [
    {"step": 1, "timestamp": "0:03", "action": "keyboard_shortcut",
     "target": "Chrome address bar", "content": "Ctrl+L", "intent": "Focus URL bar"},
    {"step": 2, "timestamp": "0:05", "action": "type",
     "target": "address bar", "content": "gmail.com", "intent": "Navigate to Gmail"},
    {"step": 3, "timestamp": "0:08", "action": "click",
     "target": "Sign in button", "content": "", "intent": "Open login"},
]


def test_actions_to_markdown_contains_title():
    md = actions_to_markdown("my_demo", _SAMPLE_ACTIONS)
    assert "# my_demo" in md


def test_actions_to_markdown_contains_all_steps():
    md = actions_to_markdown("test", _SAMPLE_ACTIONS)
    assert "1." in md
    assert "2." in md
    assert "3." in md


def test_actions_to_markdown_shows_content():
    md = actions_to_markdown("test", _SAMPLE_ACTIONS)
    assert "Ctrl+L" in md
    assert "gmail.com" in md


def test_actions_to_markdown_shows_intent():
    md = actions_to_markdown("test", _SAMPLE_ACTIONS)
    assert "Focus URL bar" in md
    assert "Navigate to Gmail" in md


def test_actions_to_markdown_empty_content_not_shown():
    md = actions_to_markdown("test", _SAMPLE_ACTIONS)
    # step 3 has empty content — no backtick-wrapped empty string
    lines = md.split("\n")
    step3_line = next((l for l in lines if l.startswith("3.")), "")
    assert "``" not in step3_line


def test_save_playbook_creates_file_in_correct_path():
    import helm.demos.playbook as p
    with tempfile.TemporaryDirectory() as tmp:
        p.PLAYBOOKS_DIR = Path(tmp)
        path = p.save_playbook("my_demo", _SAMPLE_ACTIONS)
        assert path.exists()
        assert path.name == "v1.md"
        assert "my_demo" in str(path)
        content = path.read_text(encoding="utf-8")
        assert "# my_demo" in content
