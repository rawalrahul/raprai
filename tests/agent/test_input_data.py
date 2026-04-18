import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from helm.agent.context import build_node_prompt
from helm.agent.models import make_agent, make_node, make_run, ensure_manager_node, ready_nodes


def test_run_has_input_data():
    agent = make_agent("Test", nodes=[make_node("Step 1", "analyze")])
    run = make_run(agent, trigger="ui", input_data="My resume text here")
    assert run["input_data"] == "My resume text here"


def test_run_input_data_defaults_none():
    agent = make_agent("Test", nodes=[make_node("Step 1", "analyze")])
    run = make_run(agent, trigger="ui")
    assert run.get("input_data") is None


def test_input_data_injected_into_root_node_prompt():
    agent = make_agent("Test", nodes=[make_node("Step 1", "analyze the document")])
    run = make_run(agent, trigger="ui", input_data="Resume: John Doe, 5 years Python")
    prompt = build_node_prompt(run, run["nodes"][0])
    assert "Resume: John Doe" in prompt
    assert "analyze the document" in prompt


def test_manager_supervision_edge_does_not_block_root_input_context():
    step = make_node("Step 1", "analyze the document", node_id="n1")
    agent = make_agent("Test", nodes=[step])
    ensure_manager_node(agent["nodes"])
    run = make_run(agent, trigger="ui", input_data="Resume: John Doe, 5 years Python")
    root = [n for n in run["nodes"] if n["id"] == "n1"][0]
    prompt = build_node_prompt(run, root)
    assert "Resume: John Doe" in prompt
    assert root in ready_nodes(run["nodes"])


def test_manager_waits_until_worker_nodes_finish():
    step = make_node("Step 1", "analyze", node_id="n1")
    agent = make_agent("Test", nodes=[step])
    ensure_manager_node(agent["nodes"])
    run = make_run(agent, trigger="ui")
    manager = [n for n in run["nodes"] if n["type"] == "manager"][0]
    assert manager not in ready_nodes(run["nodes"])
    run["nodes"][0]["status"] = "completed"
    assert manager in ready_nodes(run["nodes"])


def test_input_data_not_injected_into_child_nodes():
    parent = make_node("Step 1", "analyze", node_id="p1")
    child = make_node("Step 2", "summarize", node_id="c1")
    parent["children"] = ["c1"]
    agent = make_agent("Test", nodes=[parent, child])
    run = make_run(agent, trigger="ui", input_data="some input")
    prompt = build_node_prompt(run, run["nodes"][1])
    assert "=== User Input ===" not in prompt
