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


def substitute_vars(text: str, run: dict) -> str:
    """Replace {{var:key}} placeholders with values from run['vars']."""
    vars_store = run.get("vars") or {}
    def _replace(m):
        key = m.group(1).strip()
        return vars_store.get(key, m.group(0))
    return _re.sub(r"\{\{var:([^}]+)\}\}", _replace, text)


def extract_var_assignments(output: str) -> dict:
    """
    Parse SET_VAR: key = value lines from node output.
    Returns dict of assignments.
    """
    result = {}
    for line in (output or "").splitlines():
        m = _re.match(r"SET_VAR\s*:\s*(\w+)\s*=\s*(.+)", line.strip(), _re.IGNORECASE)
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
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
