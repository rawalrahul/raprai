import sys, os, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import helm.state as _st
from helm.agent.models import make_agent, make_node, make_run
from helm.agent.executor import execute_agent_run

def test_run_timeout_marks_run_failed():
    node = make_node("Slow", "sleep 10", node_type="shell")
    node["timeout"] = 30
    agent = make_agent("Timeout Test", nodes=[node])
    agent["run_timeout"] = 0.1
    agent["id"] = "ag-timeout-test"
    _st.agents[agent["id"]] = agent

    run = make_run(agent, trigger="ui")
    _st.agent_runs[run["id"]] = run

    asyncio.run(execute_agent_run(run["id"]))
    assert run["status"] == "failed"
    assert run.get("timed_out") is True


from helm.agent.context import substitute_vars, extract_var_assignments

def test_substitute_vars_replaces_placeholder():
    run = {"vars": {"city": "Delhi", "role": "Python Dev"}}
    prompt = "Find {{var:role}} jobs in {{var:city}}"
    result = substitute_vars(prompt, run)
    assert result == "Find Python Dev jobs in Delhi"

def test_substitute_vars_missing_key_leaves_placeholder():
    run = {"vars": {}}
    prompt = "Hello {{var:name}}"
    result = substitute_vars(prompt, run)
    assert "{{var:name}}" in result

def test_extract_var_assignments():
    output = "I found 5 jobs.\nSET_VAR: count = 5\nSET_VAR: city = Mumbai"
    assignments = extract_var_assignments(output)
    assert assignments == {"count": "5", "city": "Mumbai"}

def test_extract_var_assignments_none():
    output = "Nothing special here"
    assert extract_var_assignments(output) == {}


from helm.agent.nodes.transform import execute_transform_node

def test_transform_json_extract():
    node = make_node("Extract", "", node_type="transform")
    node["transform_op"] = "json_extract"
    node["transform_key"] = "name"
    result = asyncio.run(
        execute_transform_node(node, context='{"name": "Rahul", "age": 30}')
    )
    assert result == "Rahul"

def test_transform_regex_extract():
    node = make_node("Regex", "", node_type="transform")
    node["transform_op"] = "regex_extract"
    node["transform_pattern"] = r"\d+"
    result = asyncio.run(
        execute_transform_node(node, context="There are 42 results found")
    )
    assert result == "42"

def test_transform_template():
    node = make_node("Template", "Hello {{input}}, welcome", node_type="transform")
    node["transform_op"] = "template"
    result = asyncio.run(
        execute_transform_node(node, context="Rahul")
    )
    assert "Hello Rahul" in result

def test_transform_truncate():
    node = make_node("Truncate", "", node_type="transform")
    node["transform_op"] = "truncate"
    node["transform_length"] = 10
    result = asyncio.run(
        execute_transform_node(node, context="Hello World this is long")
    )
    assert len(result) <= 10

def test_transform_missing_op():
    node = make_node("Bad", "", node_type="transform")
    result = asyncio.run(
        execute_transform_node(node, context="anything")
    )
    assert "error" in result.lower()

def test_shell_node_var_substitution():
    """Var substitution should work in shell node task text."""
    from helm.agent.context import substitute_vars
    run = {"vars": {"output_dir": "/tmp/results"}}
    task = "mkdir -p {{var:output_dir}}"
    result = substitute_vars(task, run)
    assert result == "mkdir -p /tmp/results"
