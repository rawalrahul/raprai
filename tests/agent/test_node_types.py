import asyncio
import os
import sys
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from helm.agent.models import make_node, node_definition, node_runtime_snapshot
from helm.agent.nodes.condition import evaluate_condition
from helm.agent.nodes.deliver import execute_deliver_node
from helm.agent.nodes.file import execute_file_node
from helm.agent.nodes.http import execute_http_node
from helm.agent.nodes import input_node as input_node_module
from helm.agent.nodes.loop import parse_list_from_output
from helm.agent.nodes.shell import execute_shell_node


def run(coro):
    return asyncio.run(coro)


def test_node_default_type_is_ai():
    n = make_node("Test", "do something")
    assert n["type"] == "ai"


def test_node_custom_type():
    n = make_node("Shell Step", "ls -la", node_type="shell")
    assert n["type"] == "shell"


def test_node_definition_includes_type():
    n = make_node("HTTP Step", "call api", node_type="http")
    assert node_definition(n)["type"] == "http"


def test_node_definition_preserves_optional_config():
    n = make_node("Review", "check quality", node_type="ai")
    n["retry_max"] = 2
    defn = node_definition(n)
    assert defn["retry_max"] == 2


def test_node_runtime_snapshot_includes_type():
    n = make_node("File Step", "read file", node_type="file")
    assert node_runtime_snapshot(n)["type"] == "file"


def test_shell_node_runs_command():
    node = make_node("Echo", "echo hello_world", node_type="shell")
    result = run(execute_shell_node(node, context=""))
    assert "hello_world" in result


def test_shell_node_captures_stderr_on_failure():
    node = make_node("Bad cmd", "nonexistent_command_xyz", node_type="shell")
    result = run(execute_shell_node(node, context=""))
    assert result


def test_shell_node_timeout():
    node = make_node("Slow", "echo slow", node_type="shell")
    node["timeout"] = 0.01

    class SlowProc:
        async def communicate(self):
            await asyncio.sleep(1)
            return b"", b""

        def kill(self):
            pass

    async def fake_create(*args, **kwargs):
        return SlowProc()

    with patch("asyncio.create_subprocess_shell", fake_create):
        result = run(execute_shell_node(node, context=""))
    assert "timed out" in result.lower()


def test_http_node_missing_url():
    node = make_node("No URL", "", node_type="http")
    node["http_method"] = "GET"
    node["http_url"] = ""
    result = run(execute_http_node(node, context=""))
    assert "error" in result.lower()


def test_file_node_write_and_read():
    path = os.path.join(os.getcwd(), "out.txt")
    m = mock_open(read_data="Hello from agent")
    with patch("builtins.open", m), patch("os.makedirs"):
        write_node = make_node("Write", "Hello from agent", node_type="file")
        write_node["file_op"] = "write"
        write_node["file_path"] = path
        run(execute_file_node(write_node, context=""))

        read_node = make_node("Read", "", node_type="file")
        read_node["file_op"] = "read"
        read_node["file_path"] = path
        result = run(execute_file_node(read_node, context=""))
        assert "Hello from agent" in result


def test_file_node_missing_path():
    node = make_node("No Path", "", node_type="file")
    node["file_op"] = "read"
    node["file_path"] = ""
    result = run(execute_file_node(node, context=""))
    assert "error" in result.lower()


def test_deliver_node_missing_channel():
    node = make_node("Send", "hello", node_type="deliver")
    node["deliver_channel"] = "unknown"
    result = run(execute_deliver_node(node, context="test output"))
    assert "error" in result.lower() or "unsupported" in result.lower()


def test_deliver_node_log_channel():
    node = make_node("Log", "", node_type="deliver")
    node["deliver_channel"] = "log"
    result = run(execute_deliver_node(node, context="test output content"))
    assert "delivered" in result.lower() or "ok" in result.lower()


def test_condition_positive_match():
    result = run(evaluate_condition("Does this text mention Python?", "I love Python programming"))
    assert result is True


def test_condition_negative_match():
    result = run(evaluate_condition("Does this text mention Java?", "I love Python programming"))
    assert result is False


def test_parse_list_newlines():
    assert parse_list_from_output("item one\nitem two\nitem three") == [
        "item one",
        "item two",
        "item three",
    ]


def test_parse_list_numbered():
    items = parse_list_from_output("1. First job\n2. Second job\n3. Third job")
    assert len(items) == 3
    assert "First job" in items[0]


def test_parse_list_bullets():
    items = parse_list_from_output("- Alpha\n- Beta\n- Gamma")
    assert len(items) == 3
    assert "Alpha" in items[0]


def test_input_wait_notifies_telegram_for_ui_run():
    class FakeBot:
        def __init__(self):
            self.messages = []

        async def send_message(self, **kwargs):
            self.messages.append(kwargs)

    class FakeApp:
        def __init__(self):
            self.bot = FakeBot()

    import helm.state as _st

    old_app = _st.telegram_app
    old_chat_id = _st.telegram_chat_id
    app = FakeApp()
    run_id = "run-test-telegram-input"
    notify_key = f"{run_id}:n1"
    input_node_module._telegram_notified_runs.discard(notify_key)
    _st.telegram_app = app
    _st.telegram_chat_id = 12345
    try:
        run(
            input_node_module._notify_telegram_input_needed(
                {"id": run_id, "agent_name": "Job Finder", "trigger": "ui"},
                {"id": "n1", "title": "Resume Upload"},
                "Please upload your resume.",
                "session-1",
            )
        )
    finally:
        _st.telegram_app = old_app
        _st.telegram_chat_id = old_chat_id
        input_node_module._telegram_notified_runs.discard(notify_key)

    assert app.bot.messages
    assert app.bot.messages[0]["chat_id"] == 12345
    assert "Please upload your resume" in app.bot.messages[0]["text"]
