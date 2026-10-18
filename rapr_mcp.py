"""RAPR AI as an MCP server for Claude Code, Cursor, Codex and other MCP clients.

    claude mcp add rapr -- rapr mcp                       # installed RAPR
    claude mcp add rapr -- python /path/to/raprai/rapr_mcp.py   # from source

See helm/mcp_server.py and the "Use RAPR from Claude Code, Cursor or Codex" section of docs/guide.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helm.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
