"""
helm/agent/context.py — Context injection for agent nodes.

Each child node receives the full output of all its parent nodes,
formatted with clear separators, prepended to its own task prompt.
"""

from .models import parent_nodes


def build_node_context(run: dict, node: dict) -> str:
    """
    Build context string from all parent nodes' outputs.

    Returns an empty string if there are no parents or no parent output.
    The returned string is prepended to the node's task prompt.
    """
    if node.get("type") == "manager":
        parents = [
            n for n in run["nodes"]
            if n.get("type") != "manager" and n.get("output")
        ]
    else:
        parents = parent_nodes(run["nodes"], node["id"], include_manager=False)
    parts = []
    if node.get("type") != "manager" and not parents and run.get("input_data"):
        parts.append(
            f"=== User Input ===\n"
            f"{run['input_data']}\n"
            f"=== End User Input ==="
        )

    for parent in parents:
        # Prefer summary if output was long, fall back to full output
        text = parent.get("output_summary") or parent.get("output") or ""
        if not text:
            continue
        ai_label = parent.get("ai", "ai")
        title = parent.get("title", "Previous Step")
        parts.append(
            f'=== Output from "{title}" ({ai_label}) ===\n'
            f"{text}\n"
            f"=== End ==="
        )

    # Prepend loop item if present (Task 9)
    loop_item = node.get("_loop_item")
    if loop_item:
        parts.insert(0, f"=== Current Item ===\n{loop_item}\n=== End ===")

    if not parts:
        return ""

    return "\n\n".join(parts)


import re as _re

# Pre-compiled regex patterns for performance
_VAR_SUB_PATTERN = _re.compile(r"\{\{var:([^}]+)\}\}")
_HEREDOC_PATTERN = _re.compile(
    r"SET_VAR\s*:\s*(\w+)\s*<<(\w+)\n(.*?)\n\2",
    _re.IGNORECASE | _re.DOTALL,
)
_QUOTED_VAR_PATTERN = _re.compile(
    r'SET_VAR\s*:\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"',
    _re.IGNORECASE,
)
_PLAIN_VAR_PATTERN = _re.compile(
    r"SET_VAR\s*:\s*(\w+)\s*=\s*(.+)",
    _re.IGNORECASE,
)


def substitute_vars(text: str, run: dict) -> str:
    """Replace {{var:key}} placeholders with values from run['vars']."""
    vars_store = run.get("vars") or {}
    def _replace(m):
        key = m.group(1).strip()
        return vars_store.get(key, m.group(0))
    return _VAR_SUB_PATTERN.sub(_replace, text)


def extract_var_assignments(output: str) -> dict:
    """
    Parse SET_VAR directives from node output. Supports three forms:

    1. Plain:   SET_VAR: key = plain value
    2. Quoted:  SET_VAR: key = "value with = signs and spaces"
                (outer quotes stripped; escaped \" kept as-is)
    3. Heredoc: SET_VAR: key <<DELIM
                line1
                line2
                DELIM
                (value = body between delimiter lines, leading/trailing
                blank lines stripped)

    Returns a dict of {key: value} assignments.
    """
    if not output:
        return {}

    result = {}
    # Track character spans consumed by heredoc matches so pass 2 skips them.
    heredoc_spans: list[tuple[int, int]] = []

    # Pass 1 — heredoc blocks (multi-line, must go first).
    for m in _HEREDOC_PATTERN.finditer(output):
        key = m.group(1)
        body = m.group(3)
        # Strip leading/trailing blank lines from body.
        lines = body.split("\n")
        # Remove leading blank lines.
        while lines and not lines[0].strip():
            lines.pop(0)
        # Remove trailing blank lines.
        while lines and not lines[-1].strip():
            lines.pop()
        result[key] = "\n".join(lines)
        heredoc_spans.append((m.start(), m.end()))

    def _in_heredoc(pos: int) -> bool:
        return any(start <= pos < end for start, end in heredoc_spans)

    # Pass 2 — line-by-line for quoted and plain forms.
    offset = 0
    for line in output.splitlines(keepends=True):
        line_start = offset
        offset += len(line)
        # Skip lines that are part of a heredoc block.
        if _in_heredoc(line_start):
            continue
        stripped = line.strip()
        # Quoted form: SET_VAR: key = "..."
        m = _QUOTED_VAR_PATTERN.match(stripped)
        if m:
            result[m.group(1)] = m.group(2)
            continue
        # Plain form: SET_VAR: key = value
        m = _PLAIN_VAR_PATTERN.match(stripped)
        if m:
            result[m.group(1)] = m.group(2).strip()

    return result


def build_node_prompt(run: dict, node: dict) -> str:
    """
    Build the full prompt for a node: parent context + node task.
    """
    context = build_node_context(run, node)
    task = node.get("task", "").strip()
    feedback = node.pop("_feedback", "")

    base = f"{context}\n\n---\n\nYour task:\n{task}" if context else task
    if feedback:
        base += feedback
    return substitute_vars(base, run)   # apply var substitution
