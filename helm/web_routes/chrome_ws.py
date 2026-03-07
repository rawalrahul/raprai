"""
helm/web_routes/chrome_ws.py  --  WebSocket endpoint for Chrome browser extension.

The Chrome extension connects here to register itself as the "chrome" MCP
server.  Once connected, AI sessions can call browser automation tools
(list_tabs, navigate, click, etc.) through the standard MCP tool-call
pipeline.

Endpoints:
    WS  /ws/chrome     — persistent WebSocket for the Chrome extension
    GET /chrome/status  — connection status + tool count
"""

import asyncio
import json
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

from helm.config import logger
from helm.mcp import get_manager

router = APIRouter()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/chrome")
async def chrome_ws_endpoint(websocket: WebSocket):
    """WebSocket for the RAPR AI Chrome extension.

    Protocol:
      1. Extension sends auth message: {"type":"auth","token":"<MCP_BEARER_TOKEN>"}
      2. Server validates token and responds with auth_response.
      3. Server marks ChromeBrowserClient as attached.
      4. Extension receives tool-call requests and returns results.
      5. On disconnect, tools become unavailable.
    """
    await websocket.accept()

    # ── Step 1: Authenticate ──────────────────────────────────────────────
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_msg = json.loads(raw)
    except asyncio.TimeoutError:
        logger.warning("Chrome WS: auth timeout")
        await websocket.close(code=1000, reason="auth_timeout")
        return
    except Exception as exc:
        logger.warning("Chrome WS: bad auth message: %s", exc)
        await websocket.close(code=1002, reason="invalid_message")
        return

    if auth_msg.get("type") != "auth":
        await websocket.close(code=1002, reason="expected_auth")
        return

    # Validate bearer token
    from helm.web_routes.app import MCP_BEARER_TOKEN
    token = auth_msg.get("token", "")
    if not token or not secrets.compare_digest(token, MCP_BEARER_TOKEN):
        logger.warning("Chrome WS: invalid token")
        await websocket.close(code=1008, reason="unauthorized")
        return

    # ── Step 2: Attach to MCPManager ──────────────────────────────────────
    mgr = get_manager()
    chrome = mgr.get_chrome_client()

    extension_info = {
        "id": auth_msg.get("extension_id", "chrome-ext"),
        "version": auth_msg.get("version", "unknown"),
    }

    chrome.attach(websocket, extension_info)
    mgr._rebuild_tool_map()

    # Send auth success
    await websocket.send_json({
        "type": "auth_response",
        "ok": True,
        "extension_id": extension_info["id"],
        "tools": chrome.get_tool_count(),
    })

    logger.info("Chrome WS: extension connected — %d tools available",
                chrome.get_tool_count())

    # ── Step 3: Message loop ──────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_id = msg.get("id")
            if msg_id is None:
                continue  # skip notifications

            # Route response from extension to pending futures
            if "result" in msg:
                chrome.resolve_response(msg_id, msg.get("result", {}))
            elif "error" in msg:
                chrome.resolve_error(msg_id, msg.get("error", {}))
            # Else: extension sending a request to us (not expected in v1)

    except WebSocketDisconnect:
        logger.info("Chrome WS: extension disconnected")
    except Exception as exc:
        logger.error("Chrome WS: error: %s", exc)
    finally:
        chrome.detach()
        mgr._rebuild_tool_map()
        logger.info("Chrome WS: tools removed from registry")


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@router.get("/chrome/status")
async def chrome_status(request: Request):
    """Return Chrome extension connection status.

    When called from localhost, includes the bearer token so the
    extension popup can auto-fill it (no need for manual copy-paste).
    """
    from helm.web_routes.app import MCP_BEARER_TOKEN

    mgr = get_manager()
    chrome = mgr.get_chrome_client()
    data = chrome.get_status()

    # Only expose token to localhost callers
    client = request.client
    host = client.host if client else ""
    if host in ("127.0.0.1", "::1", "localhost"):
        data["token"] = MCP_BEARER_TOKEN

    return JSONResponse(data)
