"""RAPR AI as an MCP server for Claude Code, Cursor, Codex and other MCP clients.

    claude mcp add --scope user rapr -- rapr mcp          # Claude Code, installed RAPR
    codex mcp add rapr -- rapr mcp                        # Codex (set tool_timeout_sec, see the guide)
    claude mcp add --scope user rapr -- python /path/to/raprai/rapr_mcp.py   # from source

See helm/mcp_server.py and the "Use RAPR from your coding agent" section of docs/guide.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helm.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
