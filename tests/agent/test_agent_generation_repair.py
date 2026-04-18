import os
import sys
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from helm.web_routes.agent_routes import (
    _agent_requires_initial_input,
    _ensure_manager_node,
    _extract_agent_input_file_text,
    _repair_generated_agent_graph,
)
from helm.agent.runner import _prepare_initial_input_node
from helm.agent.repair import repair_agent_graph


def test_repair_converts_fake_resume_prompt_to_input_node():
    nodes = [
        {
            "id": "n1",
            "title": "Resume and Job Search Criteria",
            "task": "Ask the user to provide their resume and job preferences.",
            "type": "ai",
            "ai": "claude",
            "children": ["n2"],
            "x": 100,
            "y": 100,
        },
        {
            "id": "n2",
            "title": "Analyze Profile",
            "task": "Analyze the resume.",
            "type": "ai",
            "ai": "claude",
            "children": [],
            "x": 300,
            "y": 100,
        },
    ]
    _repair_generated_agent_graph("Create a job finder agent that needs a resume.", nodes)
    assert nodes[0]["type"] == "input"
    assert "resume" in nodes[0]["task"].lower()
    assert "upload" in nodes[0]["task"].lower()


def test_repair_connects_sequential_nodes_when_children_missing():
    nodes = [
        {"id": "n1", "title": "Input", "task": "Ask user", "type": "input", "ai": "claude", "children": [], "x": 100, "y": 100},
        {"id": "n2", "title": "Search", "task": "Search web", "type": "ai", "ai": "claude", "children": [], "x": 300, "y": 100},
        {"id": "n3", "title": "Rank", "task": "Rank results", "type": "ai", "ai": "claude", "children": [], "x": 500, "y": 100},
    ]
    _repair_generated_agent_graph("Create a job finder agent that needs a resume.", nodes)
    assert nodes[0]["children"] == ["n2"]
    assert nodes[1]["children"] == ["n3"]


def test_repair_does_not_turn_processing_steps_into_input_nodes():
    nodes = [
        {
            "id": "n1",
            "title": "Collect User Profile",
            "task": "Request the user's resume text, target job titles, preferred locations, salary expectations, and companies to avoid.",
            "type": "input",
            "ai": "claude",
            "children": ["n2"],
            "x": 100,
            "y": 100,
        },
        {
            "id": "n2",
            "title": "Generate Search Strategy",
            "task": "Analyze the resume to extract key skills and projects, then generate optimized job search queries based on the user's profile and preferences.",
            "type": "input",
            "ai": "claude",
            "children": [],
            "x": 300,
            "y": 100,
        },
    ]
    _repair_generated_agent_graph("Create a job finder agent that needs a resume.", nodes)
    assert nodes[0]["type"] == "input"
    assert nodes[1]["type"] == "ai"


def test_repair_loop_fanout_and_cycle_into_executable_chain():
    nodes = [
        {
            "id": "n1",
            "title": "Collect User Profile",
            "task": "Request the user's resume text.",
            "type": "input",
            "ai": "claude",
            "children": ["n2"],
            "x": 100,
            "y": 100,
        },
        {
            "id": "n2",
            "title": "Generate Search Strategy",
            "task": "Analyze the resume and generate search queries.",
            "type": "input",
            "ai": "claude",
            "children": ["loop"],
            "x": 300,
            "y": 100,
        },
        {
            "id": "loop",
            "title": "Job Search Loop",
            "task": "Iterate through the generated search queries.",
            "type": "loop",
            "ai": "claude",
            "children": ["search", "rank"],
            "x": 500,
            "y": 100,
        },
        {
            "id": "search",
            "title": "Execute Job Search",
            "task": "Perform a deep web search for the current query and extract requirements for each listing.",
            "type": "loop",
            "ai": "claude",
            "children": ["loop"],
            "x": 700,
            "y": 100,
        },
        {
            "id": "rank",
            "title": "Rank and Analyze Matches",
            "task": "Score jobs against the resume and draft tailored notes.",
            "type": "input",
            "ai": "claude",
            "children": [],
            "x": 900,
            "y": 100,
        },
    ]
    changed = repair_agent_graph("Create a job finder agent that needs a resume.", nodes)
    by_id = {n["id"]: n for n in nodes}
    assert changed is True
    assert by_id["n2"]["type"] == "ai"
    assert by_id["search"]["type"] == "ai"
    assert by_id["rank"]["type"] == "ai"
    assert by_id["loop"]["children"] == ["search"]
    assert by_id["search"]["children"] == ["rank"]


def test_repair_removes_generated_human_review_input_when_manager_exists():
    nodes = [
        {
            "id": "n1",
            "title": "Collect User Profile",
            "task": "Request the user's resume text.",
            "type": "input",
            "ai": "claude",
            "children": ["n2"],
            "x": 100,
            "y": 100,
        },
        {
            "id": "n2",
            "title": "Human Review and Format Selection",
            "task": "Present the top matches to the user for approval and ask them to choose a delivery format.",
            "type": "input",
            "ai": "claude",
            "children": ["n3"],
            "x": 300,
            "y": 100,
        },
        {
            "id": "n3",
            "title": "Final Job Delivery",
            "task": "Deliver the final job report.",
            "type": "ai",
            "ai": "claude",
            "children": [],
            "x": 500,
            "y": 100,
        },
    ]
    _repair_generated_agent_graph("Create a job finder agent that needs a resume.", nodes)
    assert nodes[0]["type"] == "input"
    assert nodes[1]["type"] == "ai"


def test_ensure_manager_node_adds_supervisory_manager_to_workflow():
    nodes = [
        {"id": "n1", "title": "Input", "task": "Collect input", "type": "input", "ai": "claude", "children": ["n2"], "x": 100, "y": 100},
        {"id": "n2", "title": "Work", "task": "Do the work", "type": "ai", "ai": "claude", "children": [], "x": 300, "y": 100},
    ]
    _ensure_manager_node(nodes)
    managers = [n for n in nodes if n["type"] == "manager"]
    assert len(managers) == 1
    manager = managers[0]
    assert set(manager["children"]) == {"n1", "n2"}
    assert nodes[1]["children"] == []
    assert manager["y"] < nodes[0]["y"]
    assert "happy" in manager["task"].lower()


def test_ensure_manager_node_uses_agent_name_as_manager_title():
    nodes = [
        {"id": "n1", "title": "Work", "task": "Do the work", "type": "ai", "ai": "claude", "children": [], "x": 100, "y": 100},
    ]
    _ensure_manager_node(nodes, manager_title="Job Finder")
    manager = [n for n in nodes if n["type"] == "manager"][0]
    assert manager["title"] == "Job Finder"


def test_ensure_manager_node_reuses_existing_manager_and_connects_roots():
    nodes = [
        {"id": "n1", "title": "Start", "task": "Start", "type": "ai", "ai": "claude", "children": ["n2", "n3"], "x": 100, "y": 100},
        {"id": "n2", "title": "Branch A", "task": "A", "type": "ai", "ai": "claude", "children": [], "x": 300, "y": 60},
        {"id": "n3", "title": "Branch B", "task": "B", "type": "ai", "ai": "claude", "children": [], "x": 300, "y": 160},
        {"id": "mgr", "title": "Manager", "task": "Review", "type": "manager", "ai": "claude", "children": ["n1"], "x": 500, "y": 100},
    ]
    _ensure_manager_node(nodes)
    manager = [n for n in nodes if n["type"] == "manager"][0]
    assert manager["id"] == "mgr"
    assert set(manager["children"]) == {"n1", "n2", "n3"}
    assert nodes[1]["children"] == []
    assert nodes[2]["children"] == []


def test_repair_uses_gemini_for_research_nodes():
    nodes = [
        {"id": "n1", "title": "Web Research", "task": "Research job listings on the web.", "type": "ai", "ai": "claude", "children": [], "x": 100, "y": 100}
    ]
    _repair_generated_agent_graph("Create a job finder agent.", nodes)
    assert nodes[0]["ai"] == "gemini"


def test_repair_adds_retry_marker_to_validation_nodes():
    nodes = [
        {"id": "n1", "title": "Validate Results", "task": "Check if the output is good.", "type": "ai", "ai": "claude", "children": [], "x": 100, "y": 100}
    ]
    _repair_generated_agent_graph("Create a workflow.", nodes)
    assert "RETRY_PARENT:" in nodes[0]["task"]
    assert nodes[0]["retry_max"] == 2


def test_extract_agent_input_file_text_reads_plain_text():
    with patch("builtins.open", mock_open(read_data="Python developer resume")):
        assert "Python developer resume" in _extract_agent_input_file_text("resume.txt", "resume.txt")


def test_saved_job_agent_requires_initial_input_even_if_badly_typed():
    agent = {
        "name": "Job Finder",
        "description": "Find jobs based on resume and preferences.",
        "nodes": [
            {
                "id": "n1",
                "title": "Job Requirements",
                "task": "Understand resume, profile, and job criteria.",
                "type": "ai",
                "ai": "gemini",
                "children": ["n2"],
            },
            {
                "id": "n2",
                "title": "Search Jobs",
                "task": "Search for jobs.",
                "type": "ai",
                "ai": "gemini",
                "children": [],
            },
        ],
    }
    assert _agent_requires_initial_input(agent) is True


def test_regular_agent_does_not_require_initial_input():
    agent = {
        "name": "Research Agent",
        "description": "Research a fixed topic and summarize findings.",
        "nodes": [
            {
                "id": "n1",
                "title": "Research Topic",
                "task": "Research the latest Python packaging best practices.",
                "type": "ai",
                "ai": "gemini",
                "children": ["n2"],
            },
            {
                "id": "n2",
                "title": "Summarize",
                "task": "Provide a concise summary.",
                "type": "ai",
                "ai": "claude",
                "children": [],
            },
        ],
    }
    assert _agent_requires_initial_input(agent) is False


def test_prepare_run_does_not_convert_without_explicit_signal():
    """B4: fuzzy job+resume keyword match removed — no conversion without explicit phrase or flag."""
    run = {
        "agent_name": "Job Finder",
        "input_data": None,
        "nodes": [
            {
                "id": "n1",
                "title": "Job Requirements",
                "task": "Understand resume profile and job criteria.",
                "type": "ai",
                "ai": "gemini",
                "children": ["n2"],
            },
            {
                "id": "n2",
                "title": "Search Jobs",
                "task": "Search jobs.",
                "type": "ai",
                "ai": "gemini",
                "children": [],
            },
        ],
    }
    _prepare_initial_input_node(run)
    assert run["nodes"][0]["type"] == "ai"  # no conversion — vague task, no opt-in


def test_prepare_run_converts_root_when_opt_in_flag_set():
    """B4: needs_resume_input=True on run opts in to input-node conversion."""
    run = {
        "agent_name": "Job Finder",
        "input_data": None,
        "needs_resume_input": True,
        "nodes": [
            {
                "id": "n1",
                "title": "Job Requirements",
                "task": "Understand resume profile and job criteria.",
                "type": "ai",
                "ai": "gemini",
                "children": ["n2"],
            },
            {
                "id": "n2",
                "title": "Search Jobs",
                "task": "Search jobs.",
                "type": "ai",
                "ai": "gemini",
                "children": [],
            },
        ],
    }
    _prepare_initial_input_node(run)
    assert run["nodes"][0]["type"] == "input"
    assert run["nodes"][0]["ai"] == "gemini"
    assert "upload your resume" in run["nodes"][0]["task"].lower()


def test_prepare_run_converts_root_with_explicit_upload_phrase():
    """B4: explicit 'upload your resume' phrase in root task triggers conversion."""
    run = {
        "agent_name": "Job Finder",
        "input_data": None,
        "nodes": [
            {
                "id": "n1",
                "title": "Collect Resume",
                "task": "Please upload your resume or paste its contents.",
                "type": "ai",
                "ai": "gemini",
                "children": [],
            },
        ],
    }
    _prepare_initial_input_node(run)
    assert run["nodes"][0]["type"] == "input"
    assert "upload your resume" in run["nodes"][0]["task"].lower()
