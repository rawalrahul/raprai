"""
helm/mcp/chrome_client.py  --  WebSocket-based MCP client for Chrome browser extension.

Unlike the subprocess-based MCPClient, this client communicates with a Chrome
extension that connects via WebSocket.  The extension executes browser automation
tools (list tabs, navigate, click, type, screenshot, etc.) and returns results
over the same WebSocket.

Public interface mirrors MCPClient so MCPManager can treat it identically:
    is_running()          -> bool
    get_tools()           -> list[dict]
    get_tool_names()      -> list[str]
    get_tool_count()      -> int
    get_tool_summary_short() -> str
    call_tool(name, args) -> str
    stop()                -> None
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from helm.config import logger


# ---------------------------------------------------------------------------
# Browser tool definitions (registered when extension connects)
# ---------------------------------------------------------------------------

CHROME_TOOLS: list[dict] = [
    {
        "name": "list_tabs",
        "description": "List all open browser tabs with their tab IDs, URLs, titles, and active status.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "navigate",
        "description": "Navigate a browser tab to a URL.  Creates a new tab if tab_id is omitted.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to navigate to"},
                "tab_id": {"type": "integer", "description": "Tab ID (optional, creates new tab if omitted)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "read_page",
        "description": "Get a simplified DOM structure of the page including interactive elements, headings, and links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": [],
        },
    },
    {
        "name": "click",
        "description": "Click an element on the page using a CSS selector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the element to click"},
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text into an input field identified by a CSS selector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the input element"},
                "text": {"type": "string", "description": "Text to type into the field"},
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "find_element",
        "description": "Find an interactive element on the page by natural language description (e.g. 'login button', 'search bar').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural language description of the element to find"},
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": ["description"],
        },
    },
    {
        "name": "screenshot",
        "description": "Capture a screenshot of the currently visible browser tab.  Returns a base64-encoded PNG image.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_page_text",
        "description": "Extract all visible text content from the page (innerText).  Useful for summarizing or reading articles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": [],
        },
    },
    {
        "name": "close_tab",
        "description": "Close a specific browser tab by its tab ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "integer", "description": "ID of the tab to close"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "new_tab",
        "description": "Open a new browser tab, optionally navigating to a URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open (optional, defaults to blank tab)"},
            },
            "required": [],
        },
    },
    {
        "name": "extract_table",
        "description": "Extract data from an HTML table element into a JSON array of row objects.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the <table> element"},
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "fill_form",
        "description": "Fill multiple form fields at once.  Accepts a dict mapping CSS selectors to values.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": "Map of CSS selectors to values, e.g. {\"#email\": \"me@example.com\", \"#name\": \"Alice\"}",
                },
                "tab_id": {"type": "integer", "description": "Tab ID (optional, uses active tab)"},
            },
            "required": ["fields"],
        },
    },
]


class ChromeBrowserClient:
    """WebSocket-based MCP client for a Chrome extension.

    The Chrome extension connects to RAPR AI via ``/ws/chrome``.
    When attached, tool calls are forwarded as JSON-RPC 2.0 requests
    over the WebSocket and the extension executes them using Chrome APIs.
    """

    server_id = "chrome"

    def __init__(self):
        self._ws = None                                     # WebSocket connection
        self._tools: list[dict] = list(CHROME_TOOLS)        # static tool defs
        self._pending: dict[int, asyncio.Future] = {}       # msg_id -> Future
        self._msg_id: int = 0
        self._connected_at: Optional[datetime] = None
        self._extension_info: dict = {}

    # ── Public interface (mirrors MCPClient) ────────────────────────────

    def is_running(self) -> bool:
        return self._ws is not None

    def get_tools(self) -> list[dict]:
        return list(self._tools)

    def get_tool_names(self) -> list[str]:
        return [t.get("name", "") for t in self._tools]

    def get_tool_count(self) -> int:
        return len(self._tools)

    def get_tool_summary_short(self) -> str:
        if not self._tools:
            return "0 tools"
        names = [t.get("name", "") for t in self._tools]
        shown = names[:8]
        extra = f", ... (+{len(names) - 8} more)" if len(names) > 8 else ""
        return f"{len(names)} tools: {', '.join(shown)}{extra}"

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> str:
        """Send a tool call to the Chrome extension and wait for the result."""
        if not self.is_running():
            return "Error: Chrome extension is not connected.  Open the extension popup and click Connect."

        # Validate tool name
        valid_names = self.get_tool_names()
        if tool_name not in valid_names:
            close = [n for n in valid_names if tool_name.lower() in n.lower()]
            suggestion = f" Did you mean: {', '.join(close[:3])}?" if close else ""
            return f"Error: Unknown Chrome tool '{tool_name}'.{suggestion}"

        self._msg_id += 1
        msg_id = self._msg_id

        request = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }

        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[msg_id] = future

        try:
            await self._ws.send_json(request)
        except Exception as exc:
            self._pending.pop(msg_id, None)
            logger.error("Chrome MCP: send failed: %s", exc)
            return f"Error: Failed to send tool call to Chrome extension: {exc}"

        try:
            result = await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            return f"Error: Chrome tool '{tool_name}' timed out (60s)."

        # Parse MCP content blocks
        if isinstance(result, dict) and "error" in result:
            err = result["error"]
            return f"Error: {err.get('message', str(err))}"

        content = result.get("content", []) if isinstance(result, dict) else []
        texts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "text")
                if btype == "text":
                    texts.append(block.get("text", ""))
                else:
                    texts.append(json.dumps(block, indent=2))
            elif isinstance(block, str):
                texts.append(block)

        output = "\n".join(texts) if texts else "(no output)"

        # Truncate very long outputs
        if len(output) > 50000:
            output = output[:50000] + "\n...(truncated)"

        return output

    async def stop(self):
        """Disconnect the Chrome extension."""
        self.detach()

    def _stop_sync(self):
        """Synchronous cleanup for atexit."""
        self._ws = None
        self._pending.clear()
        self._connected_at = None

    # ── WebSocket attachment ────────────────────────────────────────────

    def attach(self, websocket, extension_info: dict | None = None):
        """Attach a WebSocket connection from the Chrome extension."""
        self._ws = websocket
        self._connected_at = datetime.now()
        self._extension_info = extension_info or {}
        logger.info("Chrome MCP: extension attached (%d tools available)",
                     len(self._tools))

    def detach(self):
        """Detach the WebSocket connection."""
        was_connected = self._ws is not None
        self._ws = None
        self._connected_at = None
        self._extension_info = {}
        # Cancel all pending requests
        for msg_id, future in self._pending.items():
            if not future.done():
                future.set_exception(
                    RuntimeError("Chrome extension disconnected")
                )
        self._pending.clear()
        if was_connected:
            logger.info("Chrome MCP: extension detached")

    def resolve_response(self, msg_id: int, result: dict):
        """Resolve a pending tool call with the extension's response."""
        future = self._pending.pop(msg_id, None)
        if future and not future.done():
            future.set_result(result)

    def resolve_error(self, msg_id: int, error: dict):
        """Resolve a pending tool call with an error."""
        future = self._pending.pop(msg_id, None)
        if future and not future.done():
            future.set_result({"error": error})

    # ── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "connected": self.is_running(),
            "tool_count": self.get_tool_count(),
            "connected_at": self._connected_at.isoformat() if self._connected_at else None,
            "extension_info": self._extension_info,
        }
