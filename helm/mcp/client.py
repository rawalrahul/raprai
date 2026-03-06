"""
helm/mcp/client.py — Generic MCP client for any MCP server.

Manages a single MCP server subprocess and communicates via
JSON-RPC 2.0 over stdin/stdout (Model Context Protocol).

Generalized from helm/gws_mcp.py to work with any MCP server.
"""

import asyncio
import json
import os
import subprocess
import threading
import time
from typing import Optional

from helm.config import logger


class MCPClient:
    """Manages a single MCP server subprocess."""

    def __init__(self, server_id: str, command: list[str], env: dict | None = None):
        """
        Args:
            server_id: Unique identifier (e.g. "slack", "github", "google_workspace")
            command:   Command to start the server (e.g. ["npx", "-y", "@modelcontextprotocol/server-slack"])
            env:       Extra environment variables to pass to the subprocess
        """
        self.server_id = server_id
        self.command = command
        self.extra_env = env or {}

        self._proc: Optional[subprocess.Popen] = None
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self._msg_id = 0
        self._tools: list[dict] = []
        self._initialized = False

    # ── State queries ─────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return (self._proc is not None
                and self._proc.poll() is None
                and self._initialized)

    # ── JSON-RPC transport (synchronous, called via to_thread) ────────────

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def _send_sync(self, method: str, params: dict | None = None,
                   timeout: float = 30.0) -> dict:
        """Send a JSON-RPC request and read the response (blocking)."""
        with self._sync_lock:
            if not self._proc or self._proc.poll() is not None:
                raise RuntimeError(f"MCP server '{self.server_id}' is not running")

            msg_id = self._next_id()
            request = {"jsonrpc": "2.0", "id": msg_id, "method": method}
            if params is not None:
                request["params"] = params

            line = json.dumps(request) + "\n"
            try:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError(f"MCP '{self.server_id}' stdin broken: {exc}") from exc

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    resp_line = self._proc.stdout.readline()
                except Exception as exc:
                    raise RuntimeError(
                        f"MCP '{self.server_id}' stdout read error: {exc}"
                    ) from exc

                if not resp_line:
                    raise RuntimeError(
                        f"MCP server '{self.server_id}' closed stdout unexpectedly"
                    )

                resp_line = resp_line.strip()
                if not resp_line:
                    continue

                try:
                    resp = json.loads(resp_line)
                except json.JSONDecodeError:
                    continue  # skip non-JSON status messages

                if "id" not in resp:
                    continue  # skip notifications

                if resp.get("id") == msg_id:
                    if "error" in resp:
                        err = resp["error"]
                        raise RuntimeError(
                            f"MCP '{self.server_id}' error {err.get('code', '?')}: "
                            f"{err.get('message', '?')}"
                        )
                    return resp.get("result", {})

            raise TimeoutError(
                f"MCP '{self.server_id}': no response for '{method}' within {timeout}s"
            )

    def _notify_sync(self, method: str, params: dict | None = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self._proc:
            return
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        try:
            self._proc.stdin.write(json.dumps(msg) + "\n")
            self._proc.stdin.flush()
        except Exception:
            pass

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self) -> bool:
        """Start the MCP server subprocess and initialize the protocol."""
        async with self._lock:
            if self.is_running():
                return True

            if not self.command:
                logger.warning("MCP '%s': no command configured", self.server_id)
                return False

            # Build environment: inherit system env + add extras
            proc_env = dict(os.environ)
            proc_env.update(self.extra_env)

            logger.info("MCP '%s': starting — %s", self.server_id, " ".join(self.command))

            try:
                # On Windows, always use shell=True so the shell can resolve
                # commands like gws, npx, node, etc. from PATH (they're often
                # installed as .cmd shims that only the shell can find).
                use_shell = os.name == "nt"
                self._proc = await asyncio.to_thread(
                    lambda: subprocess.Popen(
                        self.command,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=proc_env,
                        shell=use_shell,
                    )
                )
            except FileNotFoundError:
                logger.error("MCP '%s': command not found: %s",
                             self.server_id, self.command[0])
                return False
            except Exception as exc:
                logger.error("MCP '%s': failed to start: %s", self.server_id, exc)
                return False

            # Give the server a moment to start
            await asyncio.sleep(0.5)

            if self._proc.poll() is not None:
                stderr = ""
                try:
                    stderr = self._proc.stderr.read()[:500] if self._proc.stderr else ""
                except Exception:
                    pass
                logger.error("MCP '%s': server exited immediately. stderr: %s",
                             self.server_id, stderr)
                self._proc = None
                return False

            # MCP protocol handshake
            try:
                result = await asyncio.to_thread(
                    self._send_sync, "initialize", {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "rapr-ai", "version": "1.0.0"},
                    },
                    timeout=15.0,
                )
                server_info = result.get("serverInfo", {})
                logger.info("MCP '%s': initialized (server=%s v%s)",
                            self.server_id,
                            server_info.get("name", "?"),
                            server_info.get("version", "?"))

                await asyncio.to_thread(
                    self._notify_sync, "notifications/initialized"
                )

                # Discover tools
                tools_result = await asyncio.to_thread(
                    self._send_sync, "tools/list", {},
                    timeout=15.0,
                )
                self._tools = tools_result.get("tools", [])
                self._initialized = True

                logger.info("MCP '%s': ready — %d tools discovered",
                            self.server_id, len(self._tools))
                return True

            except Exception as exc:
                logger.error("MCP '%s': initialization failed: %s", self.server_id, exc)
                self._stop_sync()
                return False

    def _stop_sync(self):
        """Stop the server subprocess (synchronous)."""
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    self._proc.kill()
                    self._proc.wait(timeout=2)
                except Exception:
                    pass
            except Exception:
                pass
            self._proc = None
        self._initialized = False
        self._tools = []
        self._msg_id = 0

    async def stop(self):
        """Stop the server subprocess."""
        async with self._lock:
            await asyncio.to_thread(self._stop_sync)

    # ── Tool discovery ────────────────────────────────────────────────────

    def get_tools(self) -> list[dict]:
        """Return the full MCP tool definitions (cached after start)."""
        return list(self._tools)

    def get_tool_names(self) -> list[str]:
        return [t.get("name", "") for t in self._tools]

    def get_tool_count(self) -> int:
        return len(self._tools)

    def get_tool_summary_short(self) -> str:
        """e.g. '12 tools: send_message, list_channels, post_file, ...'"""
        if not self._tools:
            return "0 tools"
        names = [t.get("name", "") for t in self._tools]
        shown = names[:8]
        extra = f", ... (+{len(names) - 8} more)" if len(names) > 8 else ""
        return f"{len(names)} tools: {', '.join(shown)}{extra}"

    # ── Tool invocation ───────────────────────────────────────────────────

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> str:
        """Call an MCP tool and return the result as a string.

        Auto-starts the server if not running.
        """
        if not self.is_running():
            started = await self.start()
            if not started:
                return (f"Error: MCP server '{self.server_id}' is not running. "
                        f"Check that the command is installed and configured correctly.")

        # Validate tool name
        valid_names = self.get_tool_names()
        if tool_name not in valid_names:
            close = [n for n in valid_names if tool_name.lower() in n.lower()]
            suggestion = f" Did you mean: {', '.join(close[:3])}?" if close else ""
            return (f"Error: Unknown tool '{tool_name}' on server '{self.server_id}'.{suggestion}\n"
                    f"Available: {', '.join(valid_names[:20])}")

        try:
            result = await asyncio.to_thread(
                self._send_sync, "tools/call", {
                    "name": tool_name,
                    "arguments": arguments or {},
                },
                timeout=60.0,
            )

            # Parse MCP content blocks into text
            content = result.get("content", [])
            texts = []
            for block in content:
                if isinstance(block, dict):
                    btype = block.get("type", "text")
                    if btype == "text":
                        texts.append(block.get("text", ""))
                    elif btype in ("resource", "image"):
                        texts.append(json.dumps(block, indent=2))
                    else:
                        texts.append(json.dumps(block))
                elif isinstance(block, str):
                    texts.append(block)

            output = "\n".join(texts) if texts else "(no output)"

            # Truncate very long outputs
            if len(output) > 12000:
                output = output[:12000] + "\n…(truncated)"

            return output

        except TimeoutError:
            return f"Error: Tool '{tool_name}' on '{self.server_id}' timed out (60s)."
        except RuntimeError as exc:
            logger.error("MCP '%s' call failed (%s): %s", self.server_id, tool_name, exc)
            self._initialized = False
            return f"Error calling {tool_name}: {exc}"
        except Exception as exc:
            logger.error("MCP '%s' unexpected error (%s): %s",
                         self.server_id, tool_name, exc)
            return f"Error calling {tool_name}: {exc}"
