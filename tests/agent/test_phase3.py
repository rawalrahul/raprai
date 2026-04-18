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
