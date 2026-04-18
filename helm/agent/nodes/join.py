"""
helm/agent/nodes/join.py — Join node executor.

Waits for all parent branches to complete and merges their outputs.
Context passed in is already built from all parents by build_node_context.
The join node simply labels and re-emits it.

node["join_separator"]: string between sections (default "\\n\\n---\\n\\n")
"""


async def execute_join_node(node: dict, context: str) -> str:
    """Merge all parent outputs into a single labelled summary."""
    if not context:
        return "(join: no parent outputs to merge)"
    label = node.get("task", "").strip()
    if label:
        return f"{label}\n\n{context}"
    return context
