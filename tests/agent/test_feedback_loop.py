import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from helm.agent.executor import _extract_retry_request, _should_retry_node


def test_extract_retry_request_found():
    output = "The data looks incomplete.\nRETRY_PARENT: Missing job salary information"
    assert _extract_retry_request(output) == "Missing job salary information"


def test_extract_retry_request_not_found():
    assert _extract_retry_request("Here are the top 5 jobs for you.") is None


def test_extract_retry_request_case_insensitive():
    assert _extract_retry_request("retry_parent: need more detail") == "need more detail"


def test_should_retry_below_max():
    run = {"node_retries": {}}
    node = {"id": "abc", "retry_max": 2}
    assert _should_retry_node(run, node) is True
    assert _should_retry_node(run, node) is True
    assert _should_retry_node(run, node) is False


def test_should_not_retry_if_no_retry_max():
    run = {"node_retries": {}}
    node = {"id": "xyz"}
    assert _should_retry_node(run, node) is False
