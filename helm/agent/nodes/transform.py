"""helm/agent/nodes/transform.py — Deterministic data transformation (no AI, no cost)."""

import json
import re


async def execute_transform_node(node: dict, context: str) -> str:
    op = node.get("transform_op", "").strip()
    if not op:
        return "Error: transform node requires transform_op"

    if op == "json_extract":
        return _json_extract(context, node.get("transform_key", ""))
    elif op == "regex_extract":
        return _regex_extract(context, node.get("transform_pattern", ""))
    elif op == "template":
        return node.get("task", "").replace("{{input}}", context)
    elif op == "truncate":
        length = int(node.get("transform_length", 500))
        return context[:length]
    elif op == "uppercase":
        return context.upper()
    elif op == "lowercase":
        return context.lower()
    elif op == "strip_markdown":
        return _strip_markdown(context)
    else:
        return f"Error: unknown transform_op '{op}'"


def _json_extract(text: str, key_path: str) -> str:
    try:
        data = json.loads(text.strip())
        for k in (key_path.split(".") if key_path else []):
            data = data[int(k)] if isinstance(data, list) else data[k]
        return json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, (dict, list)) else str(data)
    except Exception as exc:
        return f"Error: json_extract failed — {exc}"


def _regex_extract(text: str, pattern: str) -> str:
    if not pattern:
        return "Error: transform_pattern required for regex_extract"
    try:
        m = re.search(pattern, text)
        return m.group(0) if m else "(no match)"
    except re.error as exc:
        return f"Error: invalid regex — {exc}"


def _strip_markdown(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    return text.strip()
