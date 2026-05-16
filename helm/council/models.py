"""helm/council/models.py — CouncilSession + CouncilMessage data structures."""

from uuid import uuid4
from helm.history import ts


def make_council(id: str, topic: str, cwd: str, moderator_ai: str,
                 moderator_session_id: str, participants: list, max_rounds: int = 10) -> dict:
    return {
        "id": id,
        "status": "pending",
        "topic": topic,
        "cwd": cwd,
        "moderator_ai": moderator_ai,
        "moderator_session_id": moderator_session_id,
        "participants": participants,
        "messages": [],
        "rounds": 0,
        "max_rounds": max_rounds,
        "created_at": ts(),
        "completed_at": None,
        "consensus_summary": None,
    }


def make_council_message(role: str, content: str, participant: dict | None = None) -> dict:
    return {
        "id": f"cmsg-{uuid4().hex[:8]}",
        "role": role,
        "participant_ai": participant["ai"] if participant else None,
        "participant_name": participant["name"] if participant else None,
        "content": content,
        "timestamp": ts(),
    }


def build_transcript(messages: list) -> str:
    lines = []
    for m in messages:
        if m["role"] == "participant":
            lines.append(f"[{m['participant_name']} ({m['participant_ai']})]: {m['content']}")
        elif m["role"] == "moderator":
            lines.append(f"[Moderator]: {m['content']}")
        elif m["role"] == "user":
            lines.append(f"[User]: {m['content']}")
        elif m["role"] == "system":
            lines.append(f"[System]: {m['content']}")
    return "\n\n".join(lines)
