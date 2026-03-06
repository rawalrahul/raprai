"""
helm/web_routes/mcp_routes.py — MCP server management API endpoints.

Endpoints:
    GET  /mcp/servers              → List ALL configured MCP servers with status
    POST /mcp/servers/{id}/toggle  → Enable or disable an MCP server
    POST /mcp/call                 → Call an MCP tool (used by code-executing AIs)
"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from helm.config import logger

router = APIRouter()


def _get_mgr():
    """Lazy-load MCP manager to avoid circular imports."""
    from helm.mcp import get_manager
    return get_manager()


# ── List servers ─────────────────────────────────────────────────────────────

@router.get("/mcp/servers")
async def list_mcp_servers():
    """Return ALL configured MCP servers (running + stopped) with status."""
    from helm.mcp.config import load_config

    mgr = _get_mgr()

    # Get all servers from config (including disabled ones)
    config = load_config()
    running_servers = mgr.list_servers() if mgr else []
    running_map = {s["id"]: s for s in running_servers}

    all_servers = []
    for server_id, cfg in config.items():
        if server_id in running_map:
            # Server is loaded in manager — use live status
            info = running_map[server_id]
            info["enabled"] = cfg.get("enabled", False)
            all_servers.append(info)
        else:
            # Server is configured but not loaded (disabled)
            all_servers.append({
                "id": server_id,
                "running": False,
                "enabled": cfg.get("enabled", False),
                "tool_count": 0,
                "summary": "Not started",
            })

    return JSONResponse({"servers": all_servers})


# ── Toggle server ────────────────────────────────────────────────────────────

@router.post("/mcp/servers/{server_id}/toggle")
async def toggle_mcp_server(server_id: str, request: Request):
    """Enable or disable an MCP server.  Body: {"enabled": true|false}"""
    body = await request.json()
    enabled = bool(body.get("enabled", False))

    # Update the JSON config file
    from helm.mcp.config import load_config, save_config
    config = load_config()
    if server_id not in config:
        return JSONResponse({"error": f"MCP server '{server_id}' not found"}, status_code=404)

    config[server_id]["enabled"] = enabled
    save_config(config)

    mgr = _get_mgr()

    if enabled:
        # Start the server
        from helm.mcp.client import MCPClient
        client = mgr.get_client(server_id)
        if not client:
            cfg = config[server_id]
            client = MCPClient(
                server_id=server_id,
                command=cfg["command"],
                env=cfg["env"],
            )
            mgr._clients[server_id] = client
        if not client.is_running():
            try:
                ok = await client.start()
                if ok:
                    mgr._rebuild_tool_map()
                    logger.info("MCP '%s': started via toggle (%d tools)",
                                server_id, client.get_tool_count())
                else:
                    return JSONResponse({"ok": False, "error": "Server failed to start"})
            except Exception as exc:
                return JSONResponse({"ok": False, "error": str(exc)})
    else:
        # Stop the server
        client = mgr.get_client(server_id)
        if client and client.is_running():
            await client.stop()
            mgr._rebuild_tool_map()
            logger.info("MCP '%s': stopped via toggle", server_id)

    return JSONResponse({
        "ok": True,
        "enabled": enabled,
        "running": mgr.get_client(server_id).is_running() if mgr.get_client(server_id) else False,
    })


# ── Call tool (HTTP API for code-executing AIs) ─────────────────────────────

@router.post("/mcp/call")
async def call_mcp_tool(request: Request):
    """Execute an MCP tool call. Used by code-executing AIs (Codex, Gemini).

    Body: {"name": "google_workspace_gmail_users_messages_list", "arguments": {"userId": "me"}}
    Returns: {"ok": true, "result": "...tool output..."}

    Also supports unprefixed names — will auto-resolve to the correct server.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)

    name = body.get("name", "").strip()
    arguments = body.get("arguments") or {}

    if not name:
        return JSONResponse({"ok": False, "error": "Missing 'name' field"}, status_code=400)

    # Log every request for debugging
    logger.info("MCP API call request: name='%s', args=%s", name, str(arguments)[:200])

    # Check built-in tools first (create_presentation, create_pdf, create_document)
    from helm.builtin_tools import is_builtin_tool, execute_builtin_tool
    if is_builtin_tool(name):
        try:
            import helm.state as _st
            cwd = "."
            for s in _st.sessions.values():
                if s.get("cwd"):
                    cwd = s["cwd"]
                    break
            result = await asyncio.wait_for(execute_builtin_tool(name, arguments, cwd), timeout=120)
            logger.info("Built-in tool: %s → %d chars", name, len(result))
            return JSONResponse({"ok": True, "result": result})
        except Exception as exc:
            logger.error("Built-in tool error: %s — %s", name, exc)
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    # MCP tools
    mgr = _get_mgr()
    if not mgr or not mgr.has_running_servers():
        return JSONResponse({"ok": False, "error": "No MCP servers running"}, status_code=503)

    # Try exact match first
    if mgr.is_mcp_tool(name):
        return await _execute_tool(mgr, name, arguments)

    # Try fuzzy matching
    resolved = _resolve_tool_name(mgr, name)
    if resolved:
        logger.info("MCP API: resolved '%s' → '%s'", name, resolved)
        return await _execute_tool(mgr, resolved, arguments)

    # Not found
    logger.warning("MCP API: unknown tool '%s'", name)
    available = [sid for sid, c in mgr._clients.items() if c.is_running()]
    return JSONResponse({
        "ok": False,
        "error": f"Unknown tool: '{name}'",
        "hint": f"Active servers: {', '.join(available)}. "
                f"Built-in: create_presentation, create_pdf, create_document.",
    }, status_code=404)


def _resolve_tool_name(mgr, name: str) -> str | None:
    """Try to resolve an unknown tool name by:
    1. Checking if it matches without the server prefix
    2. Checking if a server prefix needs to be added
    3. Fuzzy substring matching
    """
    # Check if any server has this as a raw tool name
    for server_id, client in mgr._clients.items():
        if not client.is_running():
            continue
        for tool in client.get_tools():
            real_name = tool.get("name", "")
            prefixed = f"{server_id}_{real_name}"
            # AI sent unprefixed name
            if name == real_name:
                return prefixed
            # AI sent name with wrong casing
            if name.lower() == prefixed.lower():
                return prefixed
            if name.lower() == real_name.lower():
                return prefixed

    return None


async def _execute_tool(mgr, name: str, arguments: dict) -> JSONResponse:
    """Execute a resolved MCP tool call."""
    try:
        result = await asyncio.wait_for(mgr.call_tool(name, arguments), timeout=30)
        logger.info("MCP API call: %s → %d chars", name, len(result))
        return JSONResponse({"ok": True, "result": result})
    except asyncio.TimeoutError:
        return JSONResponse({"ok": False, "error": f"Tool '{name}' timed out"}, status_code=504)
    except Exception as exc:
        logger.error("MCP API call error: %s — %s", name, exc)
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
