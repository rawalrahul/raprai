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
