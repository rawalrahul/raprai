"""Graph repair helpers for generated and saved agents."""

from __future__ import annotations

import re


NODE_TYPES = {
    "ai",
    "shell",
    "http",
    "file",
    "deliver",
    "input",
    "condition",
    "loop",
    "transform",
    "join",
    "manager",
}


def repair_agent_graph(description: str, nodes: list[dict]) -> bool:
    """
    Repair common LLM-generated graph mistakes in-place.

    Returns True when the graph was changed.
    """
    before = _signature(nodes)
    if not nodes:
        return False

    workflow_nodes = [n for n in nodes if n.get("type") != "manager"]
    for index, node in enumerate(workflow_nodes):
        repair_agent_node(description, node, index)

    if description_needs_initial_input(description) and not any(
        n.get("type") == "input" for n in workflow_nodes
    ):
        first = workflow_nodes[0] if workflow_nodes else None
        if first:
            first["type"] = "input"
            first["title"] = _short_title(first.get("title") or "Collect User Input")
            first["task"] = initial_input_question(description)
            first["ai"] = "claude"
            first.setdefault("input_timeout", 3600)

    clean_child_edges(nodes)
    repair_loop_fanout(nodes)
    remove_cycle_edges(nodes)
    connect_sequential_if_sparse(nodes)
    clean_child_edges(nodes)
    return before != _signature(nodes)


def repair_agent_node(description: str, node: dict, index: int = 0) -> None:
    """Repair one generated node definition in-place."""
    text = node_text(node)
    node_type = str(node.get("type", "ai")).lower()
    if node_type not in NODE_TYPES:
        node_type = "ai"

    true_input = looks_like_input_step(text)
    if true_input:
        node_type = "input"
        if not node.get("task") or looks_like_fake_input_instruction(node.get("task", "")):
            node["task"] = initial_input_question(description)
    elif node_type == "input":
        node_type = "ai"
    elif loop_intent(text):
        node_type = "loop"
        node.setdefault("loop_max", 10)
    elif node_type == "loop" and not loop_intent(text):
        node_type = "ai"
    elif any(word in text for word in ("condition", "decide whether", "branch")):
        node_type = "condition"

    node["type"] = node_type
    node["ai"] = choose_node_ai(node_type, text, node.get("ai"))

    if node_type == "ai" and any(
        word in text for word in ("validate", "quality", "review", "check", "rank", "score")
    ):
        task = node.get("task", "")
        if "RETRY_PARENT:" not in task:
            node["task"] = (
                task.rstrip()
                + "\n\nIf the previous output is weak, incomplete, irrelevant, missing required details, or not usable, output exactly: RETRY_PARENT: <clear reason>."
            )
        node.setdefault("retry_max", 2)

    if node_type in {"shell", "http"}:
        node.setdefault("timeout", 60)
    if node_type == "input":
        node.setdefault("input_timeout", 3600)
        if index == 0 and description_needs_initial_input(description):
            if looks_like_fake_input_instruction(node.get("task", "")):
                node["task"] = initial_input_question(description)


def clean_child_edges(nodes: list[dict]) -> None:
    """Remove invalid, duplicate, self, and manager child edges."""
    valid_ids = {n["id"] for n in nodes if n.get("type") != "manager"}
    manager_ids = {n["id"] for n in nodes if n.get("type") == "manager"}
    for node in nodes:
        if node.get("type") == "manager":
            continue
        seen = set()
        cleaned = []
        for child_id in node.get("children", []):
            if (
                child_id == node.get("id")
                or child_id in manager_ids
                or child_id not in valid_ids
                or child_id in seen
            ):
                continue
            cleaned.append(child_id)
            seen.add(child_id)
        node["children"] = cleaned[:3]


def repair_loop_fanout(nodes: list[dict]) -> None:
    """
    Convert accidental loop fan-out into loop body plus after-loop chain.

    A loop node with multiple children usually means "run the first child for
    each item, then continue with the remaining workflow". The executor models
    that by cloning the first child; those clones should point at the after-loop
    continuation so it waits for all clones.
    """
    by_id = {n["id"]: n for n in nodes if n.get("type") != "manager"}
    for node in nodes:
        if node.get("type") != "loop":
            continue
        children = [cid for cid in node.get("children", []) if cid in by_id]
        if len(children) <= 1:
            continue
        body_id = children[0]
        after_ids = children[1:]
        body = by_id.get(body_id)
        if not body:
            continue
        node["children"] = [body_id]
        merged = []
        for cid in list(body.get("children", [])) + after_ids:
            if cid != node.get("id") and cid != body_id and cid in by_id and cid not in merged:
                merged.append(cid)
        body["children"] = merged[:3]


def remove_cycle_edges(nodes: list[dict]) -> None:
    """Remove back-edges so ready-node scheduling cannot deadlock."""
    by_id = {n["id"]: n for n in nodes if n.get("type") != "manager"}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: dict) -> None:
        node_id = node["id"]
        if node_id in visited:
            return
        visiting.add(node_id)
        kept = []
        for child_id in node.get("children", []):
            child = by_id.get(child_id)
            if not child:
                continue
            if child_id in visiting:
                continue
            visit(child)
            if child_id not in kept:
                kept.append(child_id)
        node["children"] = kept[:3]
        visiting.discard(node_id)
        visited.add(node_id)

    for node in list(by_id.values()):
        visit(node)


def connect_sequential_if_sparse(nodes: list[dict]) -> None:
    """Connect generated nodes in visual/order sequence when edges are missing."""
    workflow_nodes = [n for n in nodes if n.get("type") != "manager"]
    if len(workflow_nodes) < 2:
        return
    total_edges = sum(len(n.get("children", [])) for n in workflow_nodes)
    if total_edges >= len(workflow_nodes) - 1:
        return
    for index, node in enumerate(workflow_nodes[:-1]):
        if not node.get("children"):
            node["children"] = [workflow_nodes[index + 1]["id"]]


def node_text(node: dict) -> str:
    return f"{node.get('title', '')} {node.get('task', '')}".lower()


def looks_like_input_step(text: str) -> bool:
    text = str(text or "").lower()
    explicit_phrases = (
        "ask the user",
        "ask user",
        "collect user input",
        "request user input",
        "user input",
        "upload",
        "paste",
        "provide their resume",
        "provide resume",
        "provide cv",
    )
    if any(phrase in text for phrase in explicit_phrases):
        return True
    action_re = re.compile(r"\b(ask|collect|request|upload|paste)\b")
    if any(word in text for word in ("resume", "cv", "profile")) and action_re.search(text):
        return True
    if any(word in text for word in ("human", "user")) and any(
        word in text for word in ("approve", "confirm", "clarify")
    ) and action_re.search(text):
        return True
    return False


def looks_like_fake_input_instruction(task: str) -> bool:
    text = str(task).lower()
    return any(
        phrase in text
        for phrase in ("ask the user", "ask user", "collect from the user", "user should provide")
    )


def loop_intent(text: str) -> bool:
    text = str(text or "").lower()
    if "current query" in text or "current item" in text:
        return False
    return any(phrase in text for phrase in ("loop", "iterate", "for each"))


def description_needs_initial_input(description: str) -> bool:
    text = str(description or "").lower()
    return any(
        word in text
        for word in (
            "resume",
            "cv",
            "profile",
            "preferences",
            "requirements",
            "user input",
            "ask the user",
            "provide their",
            "upload",
            "paste",
        )
    )


def initial_input_question(description: str) -> str:
    text = str(description or "").lower()
    if "resume" in text or "cv" in text or "job" in text:
        return (
            "Please upload your resume file or paste the resume contents. Also provide target job title, preferred location or remote preference, experience level, salary expectations, and any companies or roles to avoid."
        )
    return "Please provide the information needed to start this workflow."


def choose_node_ai(node_type: str, text: str, requested_ai: str | None) -> str:
    if node_type != "ai":
        return "claude"
    if any(
        word in text
        for word in ("web", "research", "search", "discover", "scrape", "job listings", "market", "source")
    ):
        return "gemini"
    if requested_ai in {"claude", "gemini", "ollama"}:
        return requested_ai
    return "claude"


def _short_title(title: str) -> str:
    title = str(title or "Collect User Input").strip()
    return title[:60] or "Collect User Input"


def _signature(nodes: list[dict]) -> tuple:
    return tuple(
        (
            n.get("id"),
            n.get("title"),
            n.get("type"),
            n.get("ai"),
            n.get("task"),
            tuple(n.get("children", [])),
            n.get("retry_max"),
            n.get("loop_max"),
        )
        for n in nodes
    )
