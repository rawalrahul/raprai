"""
helm/mcp/manager.py — Multi-server MCP manager.

Orchestrates multiple MCPClient instances, maintains a unified tool
registry, and provides the interface for AI runners (Ollama, etc.).

Public API:
    get_manager()                       → MCPManager singleton
    MCPManager.load_and_start(path)     → start all enabled servers
    MCPManager.call_tool(name, args)    → route to correct server
    MCPManager.get_ollama_tool_defs()   → tool definitions for Ollama
    MCPManager.get_system_prompt_summary() → concise summary for AI prompt
"""

import asyncio
import atexit
from typing import Optional

from helm.config import logger
from .client import MCPClient
from .chrome_client import ChromeBrowserClient
from .config import load_config


# Max tools to expose per server in Ollama's tool array.
# Servers with more tools get a {server}_list_tools + {server}_call fallback.
_MAX_TOOLS_PER_SERVER = 15


class MCPManager:
    """Singleton orchestrator for multiple MCP servers."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}       # server_id → MCPClient
        self._tool_map: dict[str, tuple[str, str]] = {} # prefixed_name → (server_id, real_name)
        self._chrome_client: ChromeBrowserClient = ChromeBrowserClient()
        self._initialized = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def load_and_start(self, config_path: Optional[str] = None) -> None:
        """Load config and start all enabled MCP servers."""
        config = load_config(config_path)
        if not config:
            logger.info("MCP manager: no servers to start")
            return

        # Start enabled servers concurrently
        tasks = []
        for server_id, cfg in config.items():
            if not cfg["enabled"]:
                continue
            # WebSocket-based servers (e.g. chrome) connect on their own —
            # they are not subprocess-based and don't need to be started here.
            if cfg.get("type") == "websocket":
                logger.info("MCP '%s': websocket server — waiting for extension to connect",
                            server_id)
                continue
            client = MCPClient(
                server_id=server_id,
                command=cfg["command"],
                env=cfg["env"],
            )
            self._clients[server_id] = client
            tasks.append(self._start_client(server_id, client))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            succeeded = sum(1 for r in results if r is True)
            logger.info("MCP manager: %d/%d servers started successfully",
                        succeeded, len(tasks))

        # Build unified tool registry
        self._rebuild_tool_map()
        self._initialized = True

        # Sync MCP configs to each CLI's native location so they discover
        # tools on their own — as if the user configured them directly.
        try:
            self.sync_native_mcp_configs()
        except Exception as exc:
            logger.warning("MCP config sync failed (non-fatal): %s", exc)

    async def _start_client(self, server_id: str, client: MCPClient) -> bool:
        """Start a single client, return True on success."""
        try:
            return await client.start()
        except Exception as exc:
            logger.error("MCP '%s': start failed: %s", server_id, exc)
            return False

    def _rebuild_tool_map(self):
        """Build the unified tool map from all running servers."""
        self._tool_map.clear()
        for server_id, client in self._clients.items():
            if not client.is_running():
                continue
            for tool in client.get_tools():
                real_name = tool.get("name", "")
                prefixed = f"{server_id}_{real_name}"
                self._tool_map[prefixed] = (server_id, real_name)

        # Include Chrome browser tools if extension is connected
        if self._chrome_client.is_running():
            for tool in self._chrome_client.get_tools():
                real_name = tool.get("name", "")
                prefixed = f"chrome_{real_name}"
                self._tool_map[prefixed] = ("chrome", real_name)

    async def reload_servers(self, config_path: Optional[str] = None) -> None:
        """Reload MCP configuration: stop removed servers, start new ones.

        Compares running servers against the current config file and
        reconciles the difference without restarting unchanged servers.
        """
        from .config import load_config
        config = load_config(config_path)

        current_ids = set(self._clients.keys())
        desired_ids = {sid for sid, cfg in config.items() if cfg["enabled"]}

        # Stop servers that were removed or disabled
        to_stop = current_ids - desired_ids
        for sid in to_stop:
            client = self._clients.pop(sid, None)
            if client:
                try:
                    await client.stop()
                    logger.info("MCP '%s': stopped (removed from config)", sid)
                except Exception as exc:
                    logger.warning("MCP '%s': stop error during reload: %s", sid, exc)

        # Start new servers (skip websocket-based servers)
        to_start = desired_ids - current_ids
        tasks = []
        for sid in to_start:
            cfg = config[sid]
            if cfg.get("type") == "websocket":
                continue
            client = MCPClient(
                server_id=sid,
                command=cfg["command"],
                env=cfg["env"],
            )
            self._clients[sid] = client
            tasks.append(self._start_client(sid, client))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            succeeded = sum(1 for r in results if r is True)
            logger.info("MCP reload: %d/%d new servers started", succeeded, len(tasks))

        # Rebuild tool map
        self._rebuild_tool_map()

        # Re-sync native configs after reload
        try:
            self.sync_native_mcp_configs()
        except Exception as exc:
            logger.warning("MCP config sync failed (non-fatal): %s", exc)

        logger.info("MCP reload complete: %d servers active", len(self._clients))

    async def shutdown(self):
        """Stop all MCP servers."""
        for server_id, client in self._clients.items():
            try:
                await client.stop()
                logger.info("MCP '%s': stopped", server_id)
            except Exception as exc:
                logger.warning("MCP '%s': stop error: %s", server_id, exc)
        # Disconnect Chrome extension
        try:
            await self._chrome_client.stop()
        except Exception:
            pass
        self._clients.clear()
        self._tool_map.clear()
        self._initialized = False

    def _shutdown_sync(self):
        """Synchronous cleanup for atexit."""
        for client in self._clients.values():
            try:
                client._stop_sync()
            except Exception:
                pass
        try:
            self._chrome_client._stop_sync()
        except Exception:
            pass

    # ── Tool routing ──────────────────────────────────────────────────────

    async def call_tool(self, prefixed_name: str, arguments: dict | None = None) -> str:
        """Route a tool call to the correct MCP server.

        Args:
            prefixed_name: e.g. "slack_send_message" or "chrome_list_tabs"
            arguments: tool arguments
        """
        # Direct lookup first
        if prefixed_name in self._tool_map:
            server_id, real_name = self._tool_map[prefixed_name]
            # Route to Chrome extension client
            if server_id == "chrome":
                if self._chrome_client.is_running():
                    return await self._chrome_client.call_tool(real_name, arguments)
                return "Error: Chrome extension is not connected."
            client = self._clients.get(server_id)
            if client and client.is_running():
                return await client.call_tool(real_name, arguments)
            return f"Error: MCP server '{server_id}' is not running."

        # Handle {server}_list_tools
        for server_id in self._clients:
            if prefixed_name == f"{server_id}_list_tools":
                client = self._clients[server_id]
                if not client.is_running():
                    return f"Error: MCP server '{server_id}' is not running."
                tools = client.get_tools()
                lines = [f"Tools for {server_id} ({len(tools)} total):"]
                for t in tools:
                    name = t.get("name", "")
                    desc = (t.get("description") or "")[:100]
                    lines.append(f"  • {server_id}_{name} — {desc}")
                return "\n".join(lines)

            # Handle {server}_call (generic fallback for unlisted tools)
            if prefixed_name == f"{server_id}_call":
                client = self._clients[server_id]
                if not client.is_running():
                    return f"Error: MCP server '{server_id}' is not running."
                tool_name = (arguments or {}).pop("tool_name", "")
                if not tool_name:
                    return (f"Error: 'tool_name' is required for {server_id}_call. "
                            f"Use {server_id}_list_tools to see available tools.")
                return await client.call_tool(tool_name, arguments)

        # Unknown tool
        available_servers = [sid for sid, c in self._clients.items() if c.is_running()]
        return (f"Error: Unknown MCP tool '{prefixed_name}'.\n"
                f"Active servers: {', '.join(available_servers) or 'none'}")

    # ── Ollama integration ────────────────────────────────────────────────

    def get_ollama_tool_defs(self) -> list[dict]:
        """Generate Ollama-compatible tool definitions for all running MCP servers.

        For servers with <= MAX_TOOLS_PER_SERVER: register each tool individually.
        For servers with more: register the top tools + a list_tools + a call fallback.
        """
        defs = []

        for server_id, client in self._clients.items():
            if not client.is_running():
                continue

            tools = client.get_tools()
            if not tools:
                continue

            if len(tools) <= _MAX_TOOLS_PER_SERVER:
                # Register each tool individually
                for tool in tools:
                    defs.append(self._make_ollama_tool(server_id, tool))
            else:
                # Too many tools — expose top ones + discovery/fallback
                for tool in tools[:_MAX_TOOLS_PER_SERVER]:
                    defs.append(self._make_ollama_tool(server_id, tool))

                # Add {server}_list_tools for discovery
                defs.append({
                    "type": "function",
                    "function": {
                        "name": f"{server_id}_list_tools",
                        "description": (
                            f"List ALL available tools for {server_id}. "
                            f"This server has {len(tools)} tools — use this to "
                            f"find the exact tool name you need."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                })

                # Add {server}_call as generic fallback
                defs.append({
                    "type": "function",
                    "function": {
                        "name": f"{server_id}_call",
                        "description": (
                            f"Call any {server_id} tool by name. Use this for tools "
                            f"not listed in the main tool list. First use "
                            f"{server_id}_list_tools to find the exact tool name."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": f"The exact tool name from {server_id}_list_tools",
                                },
                            },
                            "required": ["tool_name"],
                        },
                    },
                })

        # Include Chrome browser tools if extension is connected
        if self._chrome_client.is_running():
            for tool in self._chrome_client.get_tools():
                defs.append(self._make_ollama_tool("chrome", tool))

        return defs

    @staticmethod
    def _make_ollama_tool(server_id: str, mcp_tool: dict) -> dict:
        """Convert an MCP tool definition to an Ollama tool definition."""
        real_name = mcp_tool.get("name", "")
        description = mcp_tool.get("description", "") or f"{server_id} tool: {real_name}"
        input_schema = mcp_tool.get("inputSchema", {})

        # Build parameters from MCP input schema
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        return {
            "type": "function",
            "function": {
                "name": f"{server_id}_{real_name}",
                "description": f"[{server_id}] {description}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def get_system_prompt_summary(self) -> str:
        """Concise summary of available MCP services for the system prompt."""
        running = {sid: c for sid, c in self._clients.items() if c.is_running()}
        if not running:
            return ""

        lines = [
            "## Available External Services (MCP)",
            "You have access to these services via tools. Use them for ANY relevant request.",
            "",
        ]
        for server_id, client in running.items():
            count = client.get_tool_count()
            summary = client.get_tool_summary_short()
            lines.append(f"**{server_id}** — {summary}")

            # If server has many tools, remind model about discovery
            if count > _MAX_TOOLS_PER_SERVER:
                lines.append(
                    f"  (Use `{server_id}_list_tools` to see all {count} tools, "
                    f"or `{server_id}_call` for unlisted tools)"
                )

        # Include Chrome browser tools
        if self._chrome_client.is_running():
            summary = self._chrome_client.get_tool_summary_short()
            lines.append(f"**chrome** — Browser automation: {summary}")

        lines.append("")
        lines.append(
            "ALWAYS use these tools for requests about these services. "
            "NEVER say you can't access them."
        )
        return "\n".join(lines)

    def get_text_tool_descriptions(self) -> str:
        """Generate tool descriptions for text-based tool calling (non-Ollama AIs).

        Returns a markdown block with tool names, descriptions, parameters,
        and example <tool_call> usage — suitable for injection into prompts.
        """
        running = {sid: c for sid, c in self._clients.items() if c.is_running()}
        if not running:
            return ""

        lines = []
        for server_id, client in running.items():
            tools = client.get_tools()
            if not tools:
                continue

            lines.append(f"### {server_id}")
            # Show top tools (same cap as Ollama)
            shown = tools[:_MAX_TOOLS_PER_SERVER]
            for tool in shown:
                real_name = tool.get("name", "")
                prefixed = f"{server_id}_{real_name}"
                desc = (tool.get("description") or "")[:200]
                lines.append(f"- **{prefixed}**: {desc}")

                # Show required parameters
                schema = tool.get("inputSchema", {})
                required = schema.get("required", [])
                props = schema.get("properties", {})
                if required:
                    param_parts = []
                    for p in required[:5]:
                        ptype = props.get(p, {}).get("type", "string")
                        param_parts.append(f"`{p}` ({ptype})")
                    lines.append(f"  Required: {', '.join(param_parts)}")

            remaining = len(tools) - len(shown)
            if remaining > 0:
                lines.append(
                    f"- ... and {remaining} more tools. Use "
                    f"`{server_id}_list_tools` to discover them."
                )
            lines.append("")

        # Include Chrome browser tools in text descriptions
        if self._chrome_client.is_running():
            lines.append("### chrome (Browser Automation)")
            for tool in self._chrome_client.get_tools():
                real_name = tool.get("name", "")
                prefixed = f"chrome_{real_name}"
                desc = (tool.get("description") or "")[:200]
                lines.append(f"- **{prefixed}**: {desc}")
                schema = tool.get("inputSchema", {})
                required = schema.get("required", [])
                props = schema.get("properties", {})
                if required:
                    param_parts = []
                    for p in required[:5]:
                        ptype = props.get(p, {}).get("type", "string")
                        param_parts.append(f"`{p}` ({ptype})")
                    lines.append(f"  Required: {', '.join(param_parts)}")
            lines.append("")

        return "\n".join(lines)

    # ── Query helpers ─────────────────────────────────────────────────────

    def get_client(self, server_id: str) -> Optional[MCPClient]:
        """Get a specific MCP client by ID."""
        return self._clients.get(server_id)

    def get_chrome_client(self) -> ChromeBrowserClient:
        """Get the Chrome browser extension client."""
        return self._chrome_client

    def list_servers(self) -> list[dict]:
        """Return summary list for Settings UI."""
        servers = [
            {
                "id": sid,
                "running": client.is_running(),
                "tool_count": client.get_tool_count(),
                "summary": client.get_tool_summary_short(),
            }
            for sid, client in self._clients.items()
        ]
        # Always include the Chrome browser server
        servers.append({
            "id": "chrome",
            "running": self._chrome_client.is_running(),
            "tool_count": self._chrome_client.get_tool_count(),
            "summary": (self._chrome_client.get_tool_summary_short()
                        if self._chrome_client.is_running()
                        else "Waiting for Chrome extension to connect"),
            "type": "websocket",
        })
        return servers

    def has_running_servers(self) -> bool:
        return (any(c.is_running() for c in self._clients.values())
                or self._chrome_client.is_running())

    def _get_subprocess_servers(self) -> dict[str, dict]:
        """Return running subprocess-based servers as {id: {command, args, env}}.

        Websocket servers (e.g. Chrome) are excluded — CLIs can't connect to those.
        """
        servers: dict[str, dict] = {}
        for sid, client in self._clients.items():
            if not client.is_running():
                continue
            cmd = client.command
            if not cmd:
                continue
            entry: dict = {
                "command": cmd[0],
                "args": cmd[1:] if len(cmd) > 1 else [],
            }
            if client.extra_env:
                entry["env"] = client.extra_env
            servers[sid] = entry
        return servers

    def export_claude_mcp_config(self, tmp_dir: str) -> str | None:
        """Write a temp JSON config for Claude CLI's --mcp-config flag.

        Returns the path to the temp JSON file, or None if no servers qualify.
        """
        import json, os

        mcp_servers = self._get_subprocess_servers()
        if not mcp_servers:
            return None

        config = {"mcpServers": mcp_servers}
        path = os.path.join(tmp_dir, "_claude_mcp.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f)
        logger.info("Claude MCP config written: %s (%d servers)", path, len(mcp_servers))
        return path

    def sync_native_mcp_configs(self) -> None:
        """Write MCP server configs to each CLI's native config location.

        This lets every CLI discover tools as if the user configured them
        directly — the CLI never knows it's running through RAPR AI.

        Targets:
          Gemini  → ~/.gemini/settings.json  (mcpServers key)
          Codex   → ~/.codex/config.toml     ([[mcp.servers.NAME]] sections)

        Claude uses --mcp-config at invocation time (handled by export_claude_mcp_config).
        Ollama has its own native tool calling via the API.
        """
        import json, os

        servers = self._get_subprocess_servers()
        if not servers:
            logger.info("sync_native_mcp_configs: no subprocess MCP servers — skipping")
            return

        home = os.path.expanduser("~")

        # ── Gemini: ~/.gemini/settings.json ─────────────────────────────
        try:
            gemini_dir = os.path.join(home, ".gemini")
            os.makedirs(gemini_dir, exist_ok=True)
            gemini_path = os.path.join(gemini_dir, "settings.json")

            # Preserve existing settings
            existing: dict = {}
            if os.path.isfile(gemini_path):
                try:
                    with open(gemini_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}

            # Build mcpServers — same format as Claude (Gemini uses identical schema)
            existing["mcpServers"] = servers
            with open(gemini_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
                f.write("\n")
            logger.info("Gemini MCP config synced: %s (%d servers)", gemini_path, len(servers))
        except Exception as exc:
            logger.warning("Failed to sync Gemini MCP config: %s", exc)

        # ── Codex: ~/.codex/config.toml ─────────────────────────────────
        try:
            codex_dir = os.path.join(home, ".codex")
            os.makedirs(codex_dir, exist_ok=True)
            codex_path = os.path.join(codex_dir, "config.toml")

            # Read existing config to preserve non-MCP settings
            existing_lines: list[str] = []
            if os.path.isfile(codex_path):
                with open(codex_path, "r", encoding="utf-8") as f:
                    existing_lines = f.readlines()

            # Strip existing [mcp_servers.*] blocks (we'll rewrite them)
            cleaned: list[str] = []
            in_mcp_block = False
            for line in existing_lines:
                stripped = line.strip()
                if stripped.startswith("[mcp_servers."):
                    in_mcp_block = True
                    continue
                if in_mcp_block:
                    # End of block: next section header or blank line after content
                    if stripped.startswith("[") or (stripped == "" and cleaned and cleaned[-1].strip() == ""):
                        in_mcp_block = False
                        if stripped.startswith("["):
                            cleaned.append(line)
                    continue
                cleaned.append(line)

            # Append MCP server blocks
            # Codex format: [mcp_servers.NAME]
            #               command = "cmd"
            #               args = ["arg1", "arg2"]
            #
            #               [mcp_servers.NAME.env]
            #               KEY = "val"
            mcp_lines: list[str] = []
            for sid, srv in servers.items():
                mcp_lines.append(f"\n[mcp_servers.{sid}]")
                mcp_lines.append(f'command = "{srv["command"]}"')
                if srv.get("args"):
                    args_str = ", ".join(f'"{a}"' for a in srv["args"])
                    mcp_lines.append(f"args = [{args_str}]")
                if srv.get("env"):
                    mcp_lines.append(f"\n[mcp_servers.{sid}.env]")
                    for k, v in srv["env"].items():
                        mcp_lines.append(f'{k} = "{v}"')
                mcp_lines.append("")

            with open(codex_path, "w", encoding="utf-8") as f:
                f.write("".join(cleaned))
                if mcp_lines:
                    f.write("\n".join(mcp_lines))
                    f.write("\n")
            logger.info("Codex MCP config synced: %s (%d servers)", codex_path, len(servers))
        except Exception as exc:
            logger.warning("Failed to sync Codex MCP config: %s", exc)

    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if a tool name belongs to an MCP server."""
        if tool_name in self._tool_map:
            return True
        for server_id in self._clients:
            if tool_name in (f"{server_id}_list_tools", f"{server_id}_call"):
                return True
        return False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager = MCPManager()


def get_manager() -> MCPManager:
    """Return the singleton MCPManager instance."""
    return _manager


# Auto-cleanup on process exit
atexit.register(lambda: _manager._shutdown_sync())
