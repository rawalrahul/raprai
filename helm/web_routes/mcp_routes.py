"""
helm/web_routes/mcp_routes.py — MCP server management API endpoints.

Endpoints:
    GET  /mcp/servers              → List ALL configured MCP servers with status
    POST /mcp/servers/{id}/toggle  → Enable or disable an MCP server
    POST /mcp/call                 → Call an MCP tool (used by code-executing AIs)
"""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse

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

    # Built-in servers that should not appear in the packages panel
    # (they're internal infrastructure, not user-installable packages)
    _HIDDEN_SERVERS = {"chrome"}

    # Import known OAuth MCPs so we can enrich servers with setup/connected
    try:
        from helm.web_routes.plugins_routes import _KNOWN_OAUTH_MCPS
    except Exception:
        _KNOWN_OAUTH_MCPS = {}

    all_servers = []
    for server_id, cfg in config.items():
        # Skip internal servers — they're not marketplace items
        if server_id in _HIDDEN_SERVERS:
            continue

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

    # Enrich each server with setup/connected info for OAuth MCPs
    for srv in all_servers:
        sid = srv["id"]

        # Zapier is the Tier-2 universal connector: connected via a pasted MCP
        # server URL, not a toggle. Flag it so the UI shows a Connect button.
        # Set the connector flag unconditionally so the UI always renders the
        # Connect card, even if the status lookup below fails.
        if sid == "zapier":
            srv["connector"] = "zapier"
            srv["connected"] = False
            try:
                from helm.mcp.zapier_mcp import is_connected as _zap_connected
                srv["connected"] = _zap_connected()
            except Exception as exc:
                logger.warning("zapier status check failed: %s", exc)
            continue

        base = sid.lower().replace("-oauth", "").replace("_oauth", "").replace("-", "_")
        setup = None
        token_env = ""

        # 1) Check hardcoded known OAuth MCPs
        known = (_KNOWN_OAUTH_MCPS.get(base)
                 or _KNOWN_OAUTH_MCPS.get(sid.lower())
                 or _KNOWN_OAUTH_MCPS.get(sid.lower().replace("-", "_"))
                 or _KNOWN_OAUTH_MCPS.get(sid.lower().replace("_", "-")))
        if known and known.get("auth"):
            kauth = known["auth"]
            setup = {
                "type": "oauth",
                "token_env": kauth.get("token_env", ""),
                "client_id": kauth.get("client_id", ""),
                "provider": kauth.get("proxy_provider", base),
            }
            token_env = kauth.get("token_env", "")

        # 2) Fallback: check marketplace catalog
        if not setup:
            try:
                from helm.packages.marketplace import get_catalog_entry
                entry = get_catalog_entry(sid) or get_catalog_entry(
                    sid.lower().replace("_", "-"))
                if entry and entry.get("setup"):
                    cat_setup = entry["setup"]
                    setup = {
                        "type": cat_setup.get("type", ""),
                        "token_env": cat_setup.get("token_env", ""),
                        "client_id": cat_setup.get("client_id", ""),
                        "provider": cat_setup.get("provider", base),
                    }
                    token_env = cat_setup.get("token_env", "")
            except Exception:
                pass

        if setup:
            srv["setup"] = setup
            # Check if OAuth token exists → connected
            if token_env:
                try:
                    from helm.token_vault import load_token
                    token = load_token(token_env)
                    srv["connected"] = bool(token and token.strip())
                except Exception:
                    import os
                    srv["connected"] = bool(os.environ.get(token_env, ""))

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

    # Refuse to enable a server that still needs configuration (e.g. Zapier
    # before its MCP URL is pasted). Starting it would launch the bridge with
    # an empty target and fail with a cryptic error.
    if enabled and config[server_id].get("needs_config"):
        missing = ", ".join(config[server_id].get("missing_env", [])) or "credentials"
        hint = ("Use the Connect button to set up Zapier first."
                if server_id == "zapier"
                else f"Set the required value(s) first: {missing}.")
        return JSONResponse(
            {"ok": False, "error": f"'{server_id}' needs configuration. {hint}",
             "needs_config": True},
            status_code=400,
        )

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


# ── Zapier (Tier-2 universal connector) ──────────────────────────────────────
# Zapier MCP is core infrastructure: one connection unlocks ~8000 apps. The user
# pastes their personal Zapier MCP server URL (from mcp.zapier.com); we store it
# encrypted and bridge it in as a regular MCP server. See helm/mcp/zapier_mcp.py.

@router.get("/mcp/zapier/status")
async def zapier_status():
    """Return Zapier connector status: connected / running / tool_count."""
    from helm.mcp.zapier_mcp import status
    return JSONResponse(status())


@router.get("/mcp/zapier/connect")
async def zapier_connect_page():
    """Show the connect page where the user pastes their Zapier MCP server URL."""
    from helm.mcp.zapier_mcp import is_connected
    return HTMLResponse(_zapier_connect_page(is_connected()))


@router.post("/mcp/zapier/connect")
async def zapier_connect(request: Request):
    """Save the user's Zapier MCP URL, start the server. Body: {"url": "https://..."}"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)
    url = (body.get("url") or "").strip()
    from helm.mcp.zapier_mcp import connect
    result = await connect(url)
    return JSONResponse(result, status_code=200 if result.get("ok") else 400)


@router.post("/mcp/zapier/disconnect")
async def zapier_disconnect():
    """Disconnect Zapier: clear the stored URL and stop the server."""
    from helm.mcp.zapier_mcp import disconnect
    return JSONResponse(await disconnect())


def _zapier_connect_page(connected: bool) -> str:
    """Render the Zapier MCP connect page (single URL field)."""
    badge = ('<span class="badge">Connected</span>' if connected else "")
    return f"""<!DOCTYPE html>
<html><head><title>RAPR AI — Connect Zapier</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    display:flex;align-items:center;justify-content:center;min-height:100vh;
    background:#0d0d0d;color:#e0e0e0;padding:20px}}
  .card{{background:#1a1a1a;border-radius:16px;padding:36px;max-width:520px;width:100%;
    box-shadow:0 4px 24px rgba(0,0,0,.5)}}
  .header{{text-align:center;margin-bottom:24px}}
  .emoji{{font-size:44px;margin-bottom:8px}}
  h2{{font-size:20px;font-weight:600;margin-bottom:4px}}
  .subtitle{{color:#888;font-size:13px}}
  .badge{{background:#065f46;color:#34d399;font-size:10px;padding:2px 8px;border-radius:10px;
    margin-left:8px;vertical-align:middle}}
  .steps{{font-size:12px;color:#888;line-height:1.7;background:#111;border:1px solid #262626;
    border-radius:10px;padding:14px 16px;margin-bottom:18px}}
  .steps a{{color:#a78bfa;text-decoration:none}}
  label{{font-size:13px;font-weight:600;color:#ddd;display:block;margin-bottom:6px}}
  input{{width:100%;background:#111;border:1px solid #333;border-radius:8px;padding:10px 14px;
    color:#e0e0e0;font-size:13px;font-family:monospace;outline:none}}
  input:focus{{border-color:#7c3aed}}
  .actions{{display:flex;flex-direction:column;gap:10px;margin-top:22px}}
  .btn-save{{padding:12px 20px;background:#7c3aed;color:#fff;border:none;border-radius:10px;
    font-size:14px;font-weight:500;cursor:pointer}}
  .btn-save:hover{{background:#6d28d9}}
  .btn-save:disabled{{background:#333;color:#666;cursor:not-allowed}}
  .btn-close{{padding:10px 20px;background:transparent;color:#888;border:1px solid #333;
    border-radius:10px;font-size:13px;cursor:pointer}}
  .msg{{text-align:center;padding:10px;border-radius:8px;font-size:13px;margin-top:12px;display:none}}
  .msg.ok{{display:block;background:#052e16;color:#34d399;border:1px solid #065f46}}
  .msg.err{{display:block;background:#450a0a;color:#f87171;border:1px solid #7f1d1d}}
  .spinner{{display:inline-block;width:16px;height:16px;border:2px solid #fff3;border-top-color:#fff;
    border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:6px}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
</style></head>
<body>
<div class="card">
  <div class="header">
    <div class="emoji">&#9889;</div>
    <h2>Connect Zapier{badge}</h2>
    <div class="subtitle">One connection unlocks 8,000+ apps</div>
  </div>
  <div class="steps">
    1. Go to <a href="https://mcp.zapier.com" target="_blank" rel="noopener">mcp.zapier.com</a>
       and create an MCP server.<br>
    2. Add the apps/actions you want RAPR AI to use.<br>
    3. Click <b>Connect</b> and copy the <b>Server URL</b> (it contains your API key).<br>
    4. Paste it below.
  </div>
  <label>Zapier MCP Server URL</label>
  <input type="password" id="url" placeholder="https://mcp.zapier.com/api/mcp/s/.../mcp"
         autocomplete="off" spellcheck="false" {'value="••••••••"' if connected else ''} />
  <div class="actions">
    <button class="btn-save" id="btn" onclick="save()">Save &amp; Connect</button>
    <button class="btn-close" onclick="window.close()">Cancel</button>
  </div>
  <div class="msg" id="msg"></div>
</div>
<script>
function csrf(){{ const m=document.cookie.match(/(?:^|; )hq_csrf=([^;]+)/); return m?decodeURIComponent(m[1]):''; }}
async function save() {{
  const btn=document.getElementById('btn'), msg=document.getElementById('msg');
  const url=document.getElementById('url').value.trim();
  if(!url || url==='••••••••'){{ msg.className='msg err'; msg.textContent='Paste your Zapier MCP server URL.'; return; }}
  btn.disabled=true; btn.innerHTML='<span class="spinner"></span>Connecting...'; msg.className='msg';
  try{{
    const r=await fetch('/mcp/zapier/connect',{{method:'POST',
      headers:{{'Content-Type':'application/json','x-csrf-token':csrf()}},
      body:JSON.stringify({{url}})}});
    const d=await r.json();
    if(d.ok){{
      msg.className='msg ok'; msg.textContent='Connected! '+(d.tool_count||0)+' tools available.';
      btn.textContent='Connected!';
      if(window.opener){{ try{{window.opener.postMessage({{type:'plugin-oauth-done',success:true}},'*');}}catch(e){{}} }}
      setTimeout(()=>window.close(),1500);
    }} else {{
      msg.className='msg err'; msg.textContent=d.error||'Connection failed.';
      btn.disabled=false; btn.textContent='Save & Connect';
    }}
  }}catch(e){{ msg.className='msg err'; msg.textContent=e.message; btn.disabled=false; btn.textContent='Save & Connect'; }}
}}
</script>
</body></html>"""
