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
    parents = parent_nodes(run["nodes"], node["id"])
    if not parents:
        return ""

    parts = []
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

    if not parts:
        return ""

    return "\n\n".join(parts)


def build_node_prompt(run: dict, node: dict) -> str:
    """
    Build the full prompt for a node: parent context + node task.
    """
    context = build_node_context(run, node)
    task = node.get("task", "").strip()

    if context:
        return f"{context}\n\n---\n\nYour task:\n{task}"
    return task
