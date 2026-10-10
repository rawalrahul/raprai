"""
helm/acp_agents.py — The ACP agents you've added (Settings → Agents over ACP).

An agent is a name and the command that starts it, for example
  {"id": "gemini-acp", "name": "Gemini (ACP)", "command": "gemini --acp"}
Each one can then be started as a session, "acp:<id>", like any other AI.
Stored in user data/acp_agents.json.
"""

from __future__ import annotations

import json
import re
import shlex

from helm.config import logger


def _path():
    from helm.paths import user_data_dir
    return user_data_dir() / "acp_agents.json"


def load() -> list[dict]:
    try:
        return json.loads(_path().read_text(encoding="utf-8")).get("agents", [])
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.warning("ACP agent list unreadable: %s", exc)
        return []


def get(agent_id: str) -> dict | None:
    return next((a for a in load() if a["id"] == agent_id), None)


def validate(agent: dict) -> dict:
    aid = str(agent.get("id", "")).strip().lower()
    name = str(agent.get("name", "")).strip()
    command = agent.get("command", "")
    if isinstance(command, str):
        try:
            command = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f"{name or aid}: command can't be read ({exc})")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", aid):
        raise ValueError("id must be lowercase letters, digits and dashes (max 40)")
    if not name:
        raise ValueError(f"{aid}: give the agent a name")
    if not command:
        raise ValueError(f"{aid}: give the command that starts the agent")
    return {"id": aid, "name": name[:60], "command": list(command), "emoji": str(agent.get("emoji") or "🧩")[:4]}


def save(agents: list[dict]) -> None:
    clean = [validate(a) for a in agents]
    ids = [a["id"] for a in clean]
    if len(ids) != len(set(ids)):
        raise ValueError("two agents have the same id")
    _path().write_text(json.dumps({"agents": clean}, indent=2, ensure_ascii=False), encoding="utf-8")
