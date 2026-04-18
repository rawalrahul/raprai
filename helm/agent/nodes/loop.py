"""Loop node helpers."""

import re


def parse_list_from_output(output: str, max_items: int = 10) -> list[str]:
    """Parse numbered, bulleted, or newline-delimited text into items."""
    items = []
    for line in (output or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^(\d+[\.)]\s*|[-*]\s*)", "", line).strip()
        if cleaned:
            items.append(cleaned)
        if len(items) >= max_items:
            break
    return items
