"""
tests/agent/test_phase3.py — Tests for B9: SET_VAR extended parsing.

Covers quoted single-line values, heredoc blocks, and plain values.
"""


def test_setvar_plain():
    from helm.agent.context import extract_var_assignments
    result = extract_var_assignments("SET_VAR: name = hello world")
    assert result == {"name": "hello world"}


def test_setvar_quoted_with_equals():
    from helm.agent.context import extract_var_assignments
    result = extract_var_assignments('SET_VAR: query = "SELECT * FROM table WHERE x=1"')
    assert result == {"query": "SELECT * FROM table WHERE x=1"}


def test_setvar_heredoc():
    from helm.agent.context import extract_var_assignments
    text = "SET_VAR: blob <<END\nline1\nline2\nEND"
    result = extract_var_assignments(text)
    assert result == {"blob": "line1\nline2"}


def test_setvar_mixed():
    from helm.agent.context import extract_var_assignments
    text = 'SET_VAR: a = simple\nSET_VAR: b = "quoted = value"\nSET_VAR: c <<STOP\nmulti\nline\nSTOP'
    result = extract_var_assignments(text)
    assert result == {"a": "simple", "b": "quoted = value", "c": "multi\nline"}


def test_setvar_quoted_escaped():
    """Quoted value with escaped double-quote inside."""
    from helm.agent.context import extract_var_assignments
    result = extract_var_assignments(r'SET_VAR: msg = "say \"hello\" now"')
    assert result == {"msg": 'say \\"hello\\" now'}


def test_setvar_empty_output():
    from helm.agent.context import extract_var_assignments
    assert extract_var_assignments("") == {}
    assert extract_var_assignments(None) == {}


def test_setvar_heredoc_leading_trailing_blank_lines():
    """Heredoc body with surrounding blank lines — should strip them."""
    from helm.agent.context import extract_var_assignments
    text = "SET_VAR: data <<EOF\n\nfirst\nsecond\n\nEOF"
    result = extract_var_assignments(text)
    assert result == {"data": "first\nsecond"}


# ---------------------------------------------------------------------------
# B14: manager_max_iter floor to 1
# ---------------------------------------------------------------------------

def test_manager_max_iter_zero_floors_to_one():
    """manager_max_iter=0 should behave same as 1 (not silent auto-approve)."""
    from helm.agent.nodes.manager import _resolve_max_iter
    assert _resolve_max_iter(0) == 1
    assert _resolve_max_iter(1) == 1
    assert _resolve_max_iter(5) == 5
    assert _resolve_max_iter(None) is None   # skip manager
    assert _resolve_max_iter(False) is None  # skip manager


# ---------------------------------------------------------------------------
# B17: TERMINAL_STATES constant in models.py
# ---------------------------------------------------------------------------

def test_terminal_states_constant_exists():
    from helm.agent.models import TERMINAL_STATES
    assert "completed" in TERMINAL_STATES
    assert "failed" in TERMINAL_STATES
    assert "timed_out" in TERMINAL_STATES


def test_is_run_done_uses_terminal_states():
    from helm.agent.models import is_run_done, TERMINAL_STATES
    # Build minimal run dict
    for status in TERMINAL_STATES:
        nodes = [{"status": status}]
        run = {"nodes": nodes}
        assert is_run_done(run), f"Expected done for status={status}"


# ---------------------------------------------------------------------------
# B15: WAL mode + asyncio.Lock for save_run race condition
# ---------------------------------------------------------------------------

def test_concurrent_save_run_no_error():
    """Concurrent save_run calls must not raise SQLite errors."""
    import asyncio
    from helm.agent.storage import save_run

    run = {
        "id": "test_race_001",
        "agent_id": "a1",
        "status": "running",
        "trigger": "ui",
        "nodes": [],
        "started_at": 1735689600.0,
        "vars": {},
    }

    async def _run():
        # Fire multiple concurrent saves — should all succeed without SQLite errors
        await asyncio.gather(*[save_run(dict(run)) for _ in range(5)])

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# B5: Cap _telegram_notified_runs with FIFO eviction
# ---------------------------------------------------------------------------

def test_telegram_notified_runs_capped():
    from helm.agent.nodes import input_node
    input_node._telegram_notified_queue.clear()
    input_node._telegram_notified_set.clear()
    for i in range(1100):
        input_node._notified_add(f"run:{i}")
    assert len(input_node._telegram_notified_set) == input_node._NOTIFIED_MAX
    assert len(input_node._telegram_notified_queue) == input_node._NOTIFIED_MAX
    assert not input_node._notified_contains("run:0")
    assert input_node._notified_contains("run:1099")


def test_telegram_notified_remove_allows_rerun():
    from helm.agent.nodes import input_node
    input_node._telegram_notified_queue.clear()
    input_node._telegram_notified_set.clear()
    input_node._notified_add("run1:node1")
    assert input_node._notified_contains("run1:node1")
    input_node._notified_remove("run1:node1")
    assert not input_node._notified_contains("run1:node1")


# ---------------------------------------------------------------------------
# B19: manager_reset_vars flag in node definition allowlist
# ---------------------------------------------------------------------------

def test_manager_reset_vars_in_node_definition():
    from helm.agent.models import node_definition
    node = {
        "id": "n1", "title": "Mgr", "task": "approve", "type": "manager",
        "ai": "claude", "children": [], "x": 0.0, "y": 0.0,
        "manager_reset_vars": True,
    }
    defn = node_definition(node)
    assert defn.get("manager_reset_vars") is True


# ---------------------------------------------------------------------------
# B8: Cycle detection in workflow graph
# ---------------------------------------------------------------------------

def test_has_cycle_detects_simple_cycle():
    from helm.web_routes.agent_routes import _has_cycle
    nodes = [
        {"id": "a", "children": ["b"]},
        {"id": "b", "children": ["a"]},
    ]
    assert _has_cycle(nodes) is True


def test_has_cycle_no_cycle():
    from helm.web_routes.agent_routes import _has_cycle
    nodes = [
        {"id": "a", "children": ["b"]},
        {"id": "b", "children": ["c"]},
        {"id": "c", "children": []},
    ]
    assert _has_cycle(nodes) is False


def test_has_cycle_three_node_cycle():
    from helm.web_routes.agent_routes import _has_cycle
    nodes = [
        {"id": "a", "children": ["b"]},
        {"id": "b", "children": ["c"]},
        {"id": "c", "children": ["a"]},
    ]
    assert _has_cycle(nodes) is True


# ---------------------------------------------------------------------------
# B18: Webhook rate limiting
# ---------------------------------------------------------------------------

def test_webhook_rate_limit_constants():
    from helm.web_routes.agent_routes import _WEBHOOK_MIN_INTERVAL, _webhook_last_trigger
    assert _WEBHOOK_MIN_INTERVAL > 0
    assert isinstance(_webhook_last_trigger, dict)
