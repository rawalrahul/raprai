"""Agent Client Protocol: talk to any ACP agent (tested with a mock agent)."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.acp as acp

MOCK = [sys.executable, os.path.join(os.path.dirname(__file__), "mock_acp_agent.py")]


def run(coro):
    return asyncio.run(coro)


async def _session(on_permission=None, updates=None):
    c = acp.AcpClient(MOCK, cwd=os.getcwd(), on_permission=on_permission,
                      on_update=(updates.append if updates is not None else None))
    await c.start()
    return c


def test_prompt_and_reply():
    async def go():
        updates = []
        c = await _session(updates=updates)
        try:
            reply = await c.prompt("hello agent")
            assert reply == "you said: hello agent"
            assert c.last_stop_reason == "end_turn"
            assert c.agent_info["name"] == "mock"
            assert updates and updates[0]["sessionUpdate"] == "agent_message_chunk"
        finally:
            await c.close()
    run(go())


def test_permission_granted_is_sent_back():
    async def go():
        async def yes(params):
            assert params["toolCall"]["title"] == "delete files"
            return "allow"
        c = await _session(on_permission=yes)
        try:
            assert await c.prompt("please delete the build folder") == "deleted"
        finally:
            await c.close()
    run(go())


def test_no_answer_means_refused():
    async def go():
        c = await _session(on_permission=None)
        try:
            assert await c.prompt("delete everything") == "not allowed"
        finally:
            await c.close()
    run(go())


def test_permission_can_be_declined():
    async def go():
        async def no(params):
            return "reject"
        c = await _session(on_permission=no)
        try:
            assert await c.prompt("delete it") == "not allowed"
        finally:
            await c.close()
    run(go())


def test_a_missing_agent_is_reported():
    async def go():
        c = acp.AcpClient(["definitely-not-a-real-agent-binary"], cwd=os.getcwd())
        with pytest.raises((FileNotFoundError, OSError)):
            await c.start()
    run(go())


def test_permission_goes_through_approvals(monkeypatch):
    import helm.approval as appr
    import helm.state as _st
    import helm.audit as audit
    import helm.approval_rules as rules
    monkeypatch.setattr(_st, "approval_queue", {}, raising=False)
    monkeypatch.setattr(audit, "_path", lambda: __import__("pathlib").Path(os.devnull))
    monkeypatch.setattr(rules, "evaluate", lambda text, rs=None: None)

    async def go():
        handler = acp.approval_permission("Mock agent", "s9", timeout=5)
        c = await _session(on_permission=handler)
        try:
            task = asyncio.create_task(c.prompt("please delete the old build"))
            for _ in range(100):
                await asyncio.sleep(0.02)
                pend = appr.pending()
                if pend:
                    break
            assert pend and "Mock agent wants to: delete files" in pend[0]["description"]
            appr.resolve(pend[0]["id"], "approved", source="telegram")
            assert await task == "deleted"
        finally:
            await c.close()
    run(go())
