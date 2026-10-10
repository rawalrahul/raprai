"""
helm/acp.py — Talk to any agent that speaks the Agent Client Protocol (ACP).

ACP is a standard for an editor or app to drive a coding agent: JSON-RPC 2.0
messages, one per line, over the agent's stdin/stdout. Speaking it means
RAPR gets the agent's text, tool activity and permission questions as data,
instead of scraping a terminal. Any ACP agent can be plugged in by its command.

Flow: initialize → session/new → session/prompt. While a prompt runs the agent
sends session/update notifications (text chunks) and may ask
session/request_permission; that question is answered through `on_permission`,
and it's refused if nobody answers. The prompt ends with a stop reason.
"""

from __future__ import annotations

import asyncio
import itertools
import json
from typing import Awaitable, Callable, Optional

PROTOCOL_VERSION = 1
PermissionFn = Callable[[dict], Awaitable[str]]   # returns an option id, or "" to deny


class AcpError(RuntimeError):
    pass


class AcpClient:
    def __init__(self, command: list[str], cwd: str, on_permission: Optional[PermissionFn] = None,
                 on_update: Optional[Callable[[dict], None]] = None):
        self.command = command
        self.cwd = cwd
        self.on_permission = on_permission
        self.on_update = on_update
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._reader: Optional[asyncio.Task] = None
        self._text: list[str] = []
        self.session_id: Optional[str] = None
        self.agent_info: dict = {}

    async def start(self) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            *self.command, cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        self._reader = asyncio.create_task(self._read())
        init = await self._call("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False},
        })
        if init.get("protocolVersion") != PROTOCOL_VERSION:
            raise AcpError(f"agent speaks ACP version {init.get('protocolVersion')}, RAPR speaks {PROTOCOL_VERSION}")
        self.agent_info = init.get("agentInfo") or {}
        new = await self._call("session/new", {"cwd": self.cwd, "mcpServers": []})
        self.session_id = new["sessionId"]

    async def prompt(self, text: str, timeout: float = 600.0) -> str:
        """Send one message; returns the agent's reply text."""
        if not self.session_id:
            raise AcpError("not started")
        self._text = []
        result = await asyncio.wait_for(self._call("session/prompt", {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": text}],
        }), timeout=timeout)
        self.last_stop_reason = result.get("stopReason", "end_turn")
        return "".join(self._text)

    async def close(self) -> None:
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.stdin.close()
                await asyncio.wait_for(self.proc.wait(), timeout=5)
            except Exception:
                self.proc.kill()
        if self._reader:
            self._reader.cancel()

    # ── JSON-RPC plumbing ───────────────────────────────────────────────────

    async def _call(self, method: str, params: dict) -> dict:
        rid = next(self._ids)
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        await self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        return await fut

    async def _send(self, msg: dict) -> None:
        if not self.proc or not self.proc.stdin:
            raise AcpError("agent is not running")
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()

    async def _read(self) -> None:
        assert self.proc and self.proc.stdout
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                for fut in self._pending.values():
                    if not fut.done():
                        fut.set_exception(AcpError("the agent stopped"))
                return
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue            # not protocol output; ignore
            if "method" in msg and "id" in msg:
                asyncio.create_task(self._handle_request(msg))
            elif "method" in msg:
                self._handle_notification(msg)
            elif "id" in msg:
                fut = self._pending.pop(msg["id"], None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(AcpError((msg["error"] or {}).get("message", "agent error")))
                    else:
                        fut.set_result(msg.get("result") or {})

    def _handle_notification(self, msg: dict) -> None:
        if msg["method"] != "session/update":
            return
        update = (msg.get("params") or {}).get("update") or {}
        if self.on_update:
            self.on_update(update)
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content") or {}
            if content.get("type") == "text":
                self._text.append(content.get("text", ""))

    async def _handle_request(self, msg: dict) -> None:
        if msg["method"] != "session/request_permission":
            await self._send({"jsonrpc": "2.0", "id": msg["id"],
                              "error": {"code": -32601, "message": "method not supported"}})
            return
        params = msg.get("params") or {}
        option = ""
        if self.on_permission:
            try:
                option = await self.on_permission(params)
            except Exception:
                option = ""
        if option:
            outcome = {"outcome": "selected", "optionId": option}
        else:
            outcome = {"outcome": "cancelled"}
        await self._send({"jsonrpc": "2.0", "id": msg["id"], "result": {"outcome": outcome}})


def approval_permission(label: str, session_id: str = "", timeout: float = 300.0) -> PermissionFn:
    """A permission handler that asks you through RAPR's normal approvals.

    The agent's options are mapped to allow / reject; if you don't answer in
    time, the request is refused.
    """
    async def ask(params: dict) -> str:
        import helm.approval as appr
        tool = (params.get("toolCall") or {}).get("title") or "an action"
        options = params.get("options") or []
        allow = next((o["optionId"] for o in options if str(o.get("kind", "")).startswith("allow")), "")
        reject = next((o["optionId"] for o in options if str(o.get("kind", "")).startswith("reject")), "")
        req = appr.create_request(session_id, "acp_permission", f"{label} wants to: {tool}",
                                  details=[o.get("name", "") for o in options])
        if req["status"] != "pending":           # decided by one of your rules
            return allow if req["status"] == "approved" else reject
        await appr.broadcast_approval(req)
        outcome = await appr.wait(req["id"], timeout=timeout)
        return allow if outcome == "approved" else reject
    return ask
