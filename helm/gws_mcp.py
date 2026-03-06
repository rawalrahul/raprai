"""
helm/gws_mcp.py — Backward-compatibility wrapper.

This module is kept for any code that imports from helm.gws_mcp directly.
All functionality has been moved to helm/mcp/ (the generalized MCP manager).

The google_workspace MCP server is now configured in mcp_servers.json.
"""

from helm.config import logger


def get_client():
    """Return the google_workspace MCPClient from the MCP manager."""
    try:
        from helm.mcp import get_manager
        return get_manager().get_client("google_workspace")
    except Exception:
        logger.debug("gws_mcp.get_client(): MCP manager not available")
        return None


def is_available() -> bool:
    """Check if google_workspace MCP server is configured."""
    client = get_client()
    return client is not None


async def ensure_running() -> bool:
    """Start the google_workspace MCP server if not running."""
    client = get_client()
    if client is None:
        return False
    return await client.start()


async def call_tool(tool_name: str, arguments: dict | None = None) -> str:
    """Call a google_workspace MCP tool."""
    client = get_client()
    if client is None:
        return "Error: Google Workspace MCP server not configured in mcp_servers.json"
    return await client.call_tool(tool_name, arguments)


async def shutdown():
    """Stop the google_workspace server (handled by MCP manager now)."""
    from helm.mcp import get_manager
    client = get_manager().get_client("google_workspace")
    if client:
        await client.stop()
