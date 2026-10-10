"""Run a chat message through an ACP agent, keeping one agent process per session."""

from __future__ import annotations

from helm import acp, acp_agents
from helm.config import logger

PREFIX = "acp:"


def is_acp(ai: str | None) -> bool:
    return bool(ai) and ai.startswith(PREFIX)


async def run_turn(sess: dict, text: str, sid: str, label: str) -> str:
    """Send one message to the session's ACP agent. Returns the reply (or an error line)."""
    agent_id = (sess.get("ai") or "")[len(PREFIX):]
    agent = acp_agents.get(agent_id)
    if not agent:
        return f"(error: the ACP agent '{agent_id}' isn't set up any more)"
    client = sess.get("_acp_client")
    try:
        if client is None:
            client = acp.AcpClient(agent["command"], cwd=sess.get("cwd") or ".",
                                   on_permission=acp.approval_permission(agent["name"], sid))
            await client.start()
            sess["_acp_client"] = client
        return await client.prompt(text)
    except Exception as exc:
        logger.warning("ACP agent %s failed: %s", agent_id, exc)
        sess.pop("_acp_client", None)
        return f"(error: {exc})"
