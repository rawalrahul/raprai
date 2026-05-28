import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from helm.demos.analysis import extract_json_array


def test_extract_plain_json_array():
    text = '[{"step": 1, "action": "click", "target": "btn", "content": "", "timestamp": "0:01", "intent": "x"}]'
    result = extract_json_array(text)
    assert len(result) == 1
    assert result[0]["step"] == 1


def test_extract_json_wrapped_in_markdown_code_block():
    text = '```json\n[{"step": 1, "action": "click", "target": "btn", "content": "", "timestamp": "0:01", "intent": "x"}]\n```'
    result = extract_json_array(text)
    assert result[0]["action"] == "click"


def test_extract_json_wrapped_in_plain_code_block():
    text = '```\n[{"step":1,"action":"type","target":"field","content":"hello","timestamp":"0:02","intent":"y"}]\n```'
    result = extract_json_array(text)
    assert result[0]["content"] == "hello"


def test_extract_json_with_prose_before_and_after():
    text = 'Here are the actions:\n[{"step":1,"action":"click","target":"x","content":"","timestamp":"0:01","intent":"z"}]\nDone.'
    result = extract_json_array(text)
    assert result[0]["target"] == "x"


def test_extract_multiple_steps():
    text = '[{"step":1,"action":"click","target":"a","content":"","timestamp":"0:01","intent":"i1"},{"step":2,"action":"type","target":"b","content":"hi","timestamp":"0:02","intent":"i2"}]'
    result = extract_json_array(text)
    assert len(result) == 2
    assert result[1]["content"] == "hi"


def test_extract_raises_on_no_array():
    with pytest.raises(ValueError, match="No JSON array"):
        extract_json_array("Here is some text with no JSON array.")


def test_extract_raises_on_invalid_json():
    with pytest.raises(Exception):
        extract_json_array("[{broken json")
