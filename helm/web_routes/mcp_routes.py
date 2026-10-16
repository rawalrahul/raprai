"""
helm/web_routes/mcp_routes.py — MCP server management API endpoints.

Endpoints:
    GET  /mcp/servers              → List ALL configured MCP servers with status
    POST /mcp/servers/{id}/toggle  → Enable or disable an MCP server
    POST /mcp/call                 → Call an MCP tool (used by code-executing AIs)
    GET  /mcp/custom/add           → Add-MCP popup page
    POST /mcp/custom               → Add any MCP server (URL or command) and connect it
    POST /mcp/custom/import        → Add servers from a pasted mcpServers JSON
    POST /mcp/custom/{id}/connect  → Reconnect / sign in again
    GET  /mcp/custom/{id}/status   → Connecting / sign-in link / running / error
    DELETE /mcp/custom/{id}        → Remove a custom server and its stored secrets
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

    # Servers the user added themselves: label, sign-in state, last error.
    try:
        from helm.mcp import custom_mcp
        custom_info = {c["id"]: c for c in custom_mcp.list_servers()}
    except Exception as exc:
        logger.warning("custom MCP list failed: %s", exc)
        custom_info = {}

    # Enrich each server with setup/connected info for OAuth MCPs
    for srv in all_servers:
        sid = srv["id"]

        if sid in custom_info and config.get(sid, {}).get("custom"):
            c = custom_info[sid]
            srv.update({
                "custom": True,
                "label": c["label"],
                "transport": c["transport"],
                "auth": c["auth"],
                "host": c["host"],
                "command": c["command"],
                "enabled": c["enabled"],
                "connecting": c["connecting"],
                "auth_url": c["auth_url"],
                "auth_code": c["auth_code"],
                "error": c["error"],
            })
            continue

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

        # Composio is the other Tier-2 universal connector: connected via a
        # pasted MCP server URL (managed OAuth for 100+ apps), not a toggle.
        if sid == "composio":
            srv["connector"] = "composio"
            srv["connected"] = False
            try:
                from helm.mcp.composio_mcp import is_connected as _cmp_connected
                srv["connected"] = _cmp_connected()
            except Exception as exc:
                logger.warning("composio status check failed: %s", exc)
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
        if server_id == "zapier":
            hint = "Use the Connect button to set up Zapier first."
        elif config[server_id].get("custom"):
            hint = "Some saved details are missing. Remove it and add it again."
        else:
            hint = f"Set the required value(s) first: {missing}."
        return JSONResponse(
            {"ok": False, "error": f"'{server_id}' needs configuration. {hint}",
             "needs_config": True},
            status_code=400,
        )

    # Custom servers live in their own store and connect in the background
    # (a sign-in can take minutes).
    if config[server_id].get("custom"):
        from helm.mcp import custom_mcp
        custom_mcp.set_enabled(server_id, enabled)
        if enabled:
            res = await custom_mcp.connect(server_id)
            return JSONResponse({**res, "enabled": True})
        await _get_mgr().stop_server(server_id)
        return JSONResponse({"ok": True, "enabled": False, "running": False})

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


# ── Composio (Tier-2 universal connector) ────────────────────────────────────
# Composio MCP is core infrastructure like Zapier: one connection unlocks 100+
# apps with managed OAuth. The user pastes their personal Composio MCP server URL
# (from mcp.composio.dev); we store it encrypted and bridge it in as a regular
# MCP server. See helm/mcp/composio_mcp.py.

@router.get("/mcp/composio/status")
async def composio_status():
    """Return Composio connector status: connected / running / tool_count."""
    from helm.mcp.composio_mcp import status
    return JSONResponse(status())


@router.get("/mcp/composio/connect")
async def composio_connect_page():
    """Show the connect page where the user pastes their Composio MCP server URL."""
    from helm.mcp.composio_mcp import is_connected
    return HTMLResponse(_composio_connect_page(is_connected()))


@router.post("/mcp/composio/connect")
async def composio_connect(request: Request):
    """Save the user's Composio MCP URL, start the server. Body: {"url": "https://..."}"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)
    url = (body.get("url") or "").strip()
    from helm.mcp.composio_mcp import connect
    result = await connect(url)
    return JSONResponse(result, status_code=200 if result.get("ok") else 400)


@router.post("/mcp/composio/disconnect")
async def composio_disconnect():
    """Disconnect Composio: clear the stored URL and stop the server."""
    from helm.mcp.composio_mcp import disconnect
    return JSONResponse(await disconnect())


def _composio_connect_page(connected: bool) -> str:
    """Render the Composio MCP connect page (single URL field)."""
    badge = ('<span class="badge">Connected</span>' if connected else "")
    return f"""<!DOCTYPE html>
<html><head><title>RAPR AI — Connect Composio</title>
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
    <div class="emoji">&#128279;</div>
    <h2>Connect Composio{badge}</h2>
    <div class="subtitle">One connection unlocks 100+ apps with managed OAuth</div>
  </div>
  <div class="steps">
    1. Go to <a href="https://mcp.composio.dev" target="_blank" rel="noopener">mcp.composio.dev</a>
       and create an MCP server.<br>
    2. Connect the apps/toolkits you want RAPR AI to use (Gmail, Slack, Notion, ...).<br>
    3. Copy the <b>Server URL</b> (it contains your secret).<br>
    4. Paste it below.
  </div>
  <label>Composio MCP Server URL</label>
  <input type="password" id="url" placeholder="https://mcp.composio.dev/composio/server/.../mcp"
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
  if(!url || url==='••••••••'){{ msg.className='msg err'; msg.textContent='Paste your Composio MCP server URL.'; return; }}
  btn.disabled=true; btn.innerHTML='<span class="spinner"></span>Connecting...'; msg.className='msg';
  try{{
    const r=await fetch('/mcp/composio/connect',{{method:'POST',
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


# ── Custom MCP servers ("Add any MCP") ───────────────────────────────────────
# The user adds any MCP server (a hosted URL or a local command), signs in, and
# every AI in RAPR can use its tools. See helm/mcp/custom_mcp.py.

@router.get("/mcp/custom")
async def custom_list():
    from helm.mcp import custom_mcp
    return JSONResponse({"servers": custom_mcp.list_servers()})


@router.get("/mcp/custom/add")
async def custom_add_page():
    """Popup page with the Add-MCP form."""
    return HTMLResponse(_custom_add_page())


@router.post("/mcp/custom")
async def custom_add(request: Request):
    """Add a server and start connecting it. Body: see custom_mcp.add_server()."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)
    from helm.mcp import custom_mcp
    res = custom_mcp.add_server(body if isinstance(body, dict) else {})
    if not res.get("ok"):
        return JSONResponse(res, status_code=400)
    conn = await custom_mcp.connect(res["id"])
    return JSONResponse({"ok": True, "ids": [res["id"]], "status": {res["id"]: conn}})


@router.post("/mcp/custom/import")
async def custom_import(request: Request):
    """Add every server in a pasted MCP config. Body: {"json": "<text>"}"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)
    from helm.mcp import custom_mcp
    res = custom_mcp.import_json(str((body or {}).get("json", "")))
    if not res.get("ok"):
        return JSONResponse(res, status_code=400)
    res["status"] = {sid: await custom_mcp.connect(sid) for sid in res["ids"]}
    return JSONResponse(res)


@router.post("/mcp/custom/{server_id}/connect")
async def custom_connect(server_id: str):
    """(Re)connect a custom server — also how the user signs in again."""
    from helm.mcp import custom_mcp
    res = await custom_mcp.connect(server_id)
    return JSONResponse(res, status_code=200 if res.get("ok") else 400)


@router.get("/mcp/custom/{server_id}/status")
async def custom_status(server_id: str):
    from helm.mcp import custom_mcp
    if not custom_mcp.is_custom(server_id):
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"id": server_id, **custom_mcp.status(server_id)})


@router.delete("/mcp/custom/{server_id}")
async def custom_remove(server_id: str):
    from helm.mcp import custom_mcp
    res = await custom_mcp.remove_server(server_id)
    return JSONResponse(res, status_code=200 if res.get("ok") else 404)


def _custom_add_page() -> str:
    """Render the Add-MCP popup (remote URL / local command / pasted JSON)."""
    return """<!DOCTYPE html>
<html><head><title>RAPR AI — Add MCP server</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    display:flex;justify-content:center;min-height:100vh;background:#0d0d0d;color:#e0e0e0;padding:20px}
  .card{background:#1a1a1a;border-radius:16px;padding:28px;max-width:560px;width:100%;
    box-shadow:0 4px 24px rgba(0,0,0,.5);align-self:flex-start}
  .header{text-align:center;margin-bottom:18px}
  .emoji{font-size:40px;margin-bottom:6px}
  h2{font-size:19px;font-weight:600;margin-bottom:4px}
  .subtitle{color:#888;font-size:12.5px;line-height:1.5}
  .tabs{display:flex;gap:4px;background:#111;border:1px solid #262626;border-radius:10px;padding:4px;margin-bottom:16px}
  .tab{flex:1;padding:8px 6px;background:none;border:none;border-radius:7px;color:#999;font-size:12.5px;cursor:pointer}
  .tab.active{background:#7c3aed;color:#fff}
  .pane{display:none}.pane.active{display:block}
  label{font-size:12.5px;font-weight:600;color:#ddd;display:block;margin:12px 0 5px}
  .hint{font-size:11.5px;color:#777;margin-top:5px;line-height:1.5}
  .hint code{background:#111;padding:1px 4px;border-radius:4px;color:#bbb}
  input,select,textarea{width:100%;background:#111;border:1px solid #333;border-radius:8px;padding:9px 12px;
    color:#e0e0e0;font-size:13px;outline:none;font-family:inherit}
  input.mono,textarea{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
  textarea{min-height:170px;resize:vertical}
  input:focus,select:focus,textarea:focus{border-color:#7c3aed}
  .row{display:flex;gap:6px;margin-top:6px}
  .row input{flex:1}
  .row button{background:none;border:1px solid #333;color:#888;border-radius:8px;width:34px;cursor:pointer}
  .add-row{background:none;border:none;color:#a78bfa;font-size:12px;cursor:pointer;margin-top:8px}
  .auth-extra{display:none}.auth-extra.active{display:block}
  .actions{display:flex;flex-direction:column;gap:10px;margin-top:20px}
  .btn-save{padding:12px 20px;background:#7c3aed;color:#fff;border:none;border-radius:10px;font-size:14px;font-weight:500;cursor:pointer}
  .btn-save:hover{background:#6d28d9}
  .btn-save:disabled{background:#333;color:#666;cursor:not-allowed}
  .btn-close{padding:10px 20px;background:transparent;color:#888;border:1px solid #333;border-radius:10px;font-size:13px;cursor:pointer}
  .msg{padding:10px 12px;border-radius:8px;font-size:12.5px;margin-top:12px;display:none;line-height:1.5;white-space:pre-wrap;word-break:break-word}
  .msg.ok{display:block;background:#052e16;color:#34d399;border:1px solid #065f46}
  .msg.err{display:block;background:#450a0a;color:#f87171;border:1px solid #7f1d1d}
  .msg.info{display:block;background:#1e1b4b;color:#c4b5fd;border:1px solid #3730a3}
  .msg a.signin{display:inline-block;margin-top:8px;padding:8px 14px;background:#7c3aed;color:#fff;border-radius:8px;text-decoration:none;font-weight:500}
  .msg .code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:15px;color:#fff;letter-spacing:1px}
  .spinner{display:inline-block;width:14px;height:14px;border:2px solid #fff3;border-top-color:#fff;
    border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:6px}
  @keyframes spin{to{transform:rotate(360deg)}}
</style></head>
<body>
<div class="card">
  <div class="header">
    <div class="emoji">&#128268;</div>
    <h2>Add an MCP server</h2>
    <div class="subtitle">Connect any app that has an MCP server. Once it's connected, every AI in RAPR
      (Claude, Codex, Gemini, Ollama and the rest) can use its tools.</div>
  </div>

  <div class="tabs" role="tablist">
    <button class="tab active" data-pane="remote" onclick="tab(this)">Server URL</button>
    <button class="tab" data-pane="local" onclick="tab(this)">Command</button>
    <button class="tab" data-pane="json" onclick="tab(this)">Paste JSON</button>
  </div>

  <div class="pane active" id="pane-remote">
    <label for="r-name">Name</label>
    <input id="r-name" placeholder="e.g. Buffer, Linear, Notion" autocomplete="off">
    <label for="r-url">MCP server URL</label>
    <input id="r-url" class="mono" placeholder="https://mcp.example.com/mcp" autocomplete="off" spellcheck="false">
    <div class="hint">The app's docs list it, usually ending in <code>/mcp</code> or <code>/sse</code>.</div>
    <label for="r-auth">How do you sign in?</label>
    <select id="r-auth" onchange="authChanged()">
      <option value="oauth">Sign in with my account (opens a sign-in page)</option>
      <option value="bearer">API key or token</option>
      <option value="headers">Custom headers</option>
      <option value="device">Sign in with a code (RAPR runs on a server)</option>
      <option value="none">No sign-in needed</option>
    </select>
    <div class="auth-extra" id="auth-bearer">
      <label for="r-token">API key / token</label>
      <input id="r-token" type="password" class="mono" autocomplete="off" spellcheck="false">
      <div class="hint">Sent as <code>Authorization: Bearer &lt;key&gt;</code>. Stored encrypted on this computer.</div>
    </div>
    <div class="auth-extra" id="auth-headers">
      <label>Headers</label>
      <div id="hdr-rows"></div>
      <button class="add-row" onclick="addRow('hdr-rows','X-API-Key','value')">+ Add header</button>
    </div>
    <div class="auth-extra active" id="auth-oauth">
      <div class="hint">After you click Add, a sign-in page for the app opens. Approve access and come back here.</div>
    </div>
    <div class="auth-extra" id="auth-device">
      <div class="hint">You'll get a link and a code to enter on any device. Use this when RAPR runs on a server
        without a browser. Not every app supports it.</div>
    </div>
  </div>

  <div class="pane" id="pane-local">
    <label for="l-name">Name</label>
    <input id="l-name" placeholder="e.g. GitHub" autocomplete="off">
    <label for="l-cmd">Command</label>
    <input id="l-cmd" class="mono" placeholder="npx -y @modelcontextprotocol/server-github" autocomplete="off" spellcheck="false">
    <div class="hint">RAPR runs this on this computer. Only add commands you trust.</div>
    <label>Environment variables (API keys go here)</label>
    <div id="env-rows"></div>
    <button class="add-row" onclick="addRow('env-rows','GITHUB_PERSONAL_ACCESS_TOKEN','value')">+ Add variable</button>
  </div>

  <div class="pane" id="pane-json">
    <label for="j-text">MCP config JSON</label>
    <textarea id="j-text" spellcheck="false" placeholder='{
  "mcpServers": {
    "my-app": { "url": "https://mcp.example.com/mcp" },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "..." }
    }
  }
}'></textarea>
    <div class="hint">Paste the snippet an app gives you for Claude Desktop, Cursor or VS Code. URL servers without
      headers sign in with your account.</div>
  </div>

  <div class="actions">
    <button class="btn-save" id="btn" onclick="save()">Add &amp; connect</button>
    <button class="btn-close" onclick="window.close()">Close</button>
  </div>
  <div class="msg" id="msg"></div>
</div>
<script>
let pane='remote', pollTimer=null;
function csrf(){ const m=document.cookie.match(/(?:^|; )hq_csrf=([^;]+)/); return m?decodeURIComponent(m[1]):''; }
function esc(s){ return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function tab(b){ pane=b.dataset.pane;
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t===b));
  document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('active',p.id==='pane-'+pane)); }
function authChanged(){ const a=document.getElementById('r-auth').value;
  document.querySelectorAll('.auth-extra').forEach(e=>e.classList.toggle('active',e.id==='auth-'+a));
  if(a==='headers' && !document.querySelector('#hdr-rows .row')) addRow('hdr-rows','X-API-Key','value'); }
function addRow(id,ph1,ph2){ const r=document.createElement('div'); r.className='row';
  r.innerHTML='<input class="mono k" placeholder="'+ph1+'" spellcheck="false"><input class="mono v" type="password" placeholder="'+ph2+'" spellcheck="false"><button title="Remove" onclick="this.parentNode.remove()">&times;</button>';
  document.getElementById(id).appendChild(r); }
function rows(id){ return [...document.querySelectorAll('#'+id+' .row')].map(r=>({name:r.querySelector('.k').value.trim(),value:r.querySelector('.v').value})).filter(p=>p.name||p.value); }
function show(cls,html){ const m=document.getElementById('msg'); m.className='msg '+cls; m.innerHTML=html; }
function busy(on,label){ const b=document.getElementById('btn'); b.disabled=on;
  b.innerHTML=on?'<span class="spinner"></span>'+(label||'Connecting...'):'Add &amp; connect'; }

async function save(){
  let url='/mcp/custom', body;
  if(pane==='remote') body={transport:'remote',name:v('r-name'),url:v('r-url'),auth:v('r-auth'),token:document.getElementById('r-token').value,headers:rows('hdr-rows')};
  else if(pane==='local') body={transport:'local',name:v('l-name'),command:v('l-cmd'),env:rows('env-rows')};
  else { url='/mcp/custom/import'; body={json:document.getElementById('j-text').value}; }
  busy(true,'Adding...'); show('','');
  try{
    const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','x-csrf-token':csrf()},body:JSON.stringify(body)});
    const d=await r.json();
    if(!d.ok){ show('err',esc(d.error||'Could not add the server.')); busy(false); return; }
    busy(true);
    poll(d.ids, d.errors||[]);
  }catch(e){ show('err',esc(e.message)); busy(false); }
}
function v(id){ return document.getElementById(id).value.trim(); }

function poll(ids, importErrors){
  clearTimeout(pollTimer);
  // One request for every server being added (RAPR rate-limits requests).
  fetch('/mcp/custom').then(r=>r.json()).then(d=>{
    const byId={}; (d.servers||[]).forEach(s=>byId[s.id]=s);
    return ids.map(id=>byId[id]||{id,error:'It was removed.'});
  }).catch(()=>ids.map(id=>({id,connecting:true})))
  .then(list=>{
    const pending=list.filter(s=>s.connecting);
    const signin=pending.find(s=>s.auth_url);
    if(signin){
      let h='Sign in to finish connecting <b>'+esc(signin.id)+'</b>.<br>';
      if(signin.auth_code) h+='Enter this code when asked: <span class="code">'+esc(signin.auth_code)+'</span><br>';
      h+='<a class="signin" href="'+esc(signin.auth_url)+'" target="_blank" rel="noopener">Open sign-in page</a>';
      h+='<div class="hint">If a sign-in tab already opened by itself, finish there. This page updates on its own.</div>';
      show('info',h);
    } else if(pending.length){
      show('info','<span class="spinner"></span>Connecting '+pending.map(s=>esc(s.id)).join(', ')+'... (the first time can take a minute)');
    }
    if(pending.length){ pollTimer=setTimeout(()=>poll(ids,importErrors),2000); return; }
    const ok=list.filter(s=>s.running), bad=list.filter(s=>!s.running);
    let html='';
    if(ok.length) html+=ok.map(s=>'&#10003; '+esc(s.id)+': '+(s.tool_count||0)+' tools').join('<br>')+'<br>Every AI in RAPR can use these tools now.';
    if(bad.length) html+=(html?'<br><br>':'')+bad.map(s=>'&#10007; '+esc(s.id)+': '+esc(s.error||'Could not connect.')).join('<br><br>')
      +'<br><br>It stays in your Packages list; use Reconnect there after fixing it.';
    if(importErrors.length) html+='<br><br>Skipped: '+importErrors.map(esc).join('; ');
    show(bad.length?'err':'ok',html);
    busy(false);
    if(window.opener){ try{ window.opener.postMessage({type:'plugin-oauth-done',success:true},'*'); }catch(e){} }
    if(!bad.length && !importErrors.length) setTimeout(()=>window.close(),2500);
  });
}
</script>
</body></html>"""
