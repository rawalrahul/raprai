"""
helm/mcp — Multi-server MCP (Model Context Protocol) manager.

Manages multiple MCP server subprocesses, discovers their tools,
and routes tool calls from AI models to the correct server.

Public API:
    get_manager()   → MCPManager singleton
"""

from .manager import get_manager

__all__ = ["get_manager"]
