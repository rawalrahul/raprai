"""
helm/web_routes/plugins_routes.py — Plugin management API endpoints.

Endpoints:
    GET  /plugins                             → List all plugins with status
    POST /plugins/{plugin_id}/toggle          → Enable or disable a plugin
    GET  /plugins/{plugin_id}/connect         → Show token-paste connect page
    POST /plugins/{plugin_id}/save-token      → Save a pasted token
    GET  /plugins/{plugin_id}/oauth/start     → Start OAuth flow (if credentials configured)
    GET  /plugins/{plugin_id}/oauth/start/{provider} → Start OAuth for multi-provider plugin
    GET  /plugins/oauth/callback              → OAuth callback handler
    POST /plugins/{plugin_id}/disconnect      → Clear stored tokens
"""

import html as html_mod
import os

import requests as http_requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

from helm.config import logger
from helm.plugins import list_plugins, set_plugin_enabled, _registry
from helm.plugin_oauth import (
    start_oauth, start_oauth_provider, handle_callback,
    handle_token_direct, check_connected, disconnect,
)

router = APIRouter()


# ── List ────────────────────────────────────────────────────────────────────

@router.get("/plugins")
async def get_plugins():
    """Return all plugins with their current enabled/disabled/connected state."""
    plugins = list_plugins()
    for p in plugins:
        info = _registry.get(p["id"])
        if info:
            p["connected"] = check_connected(info)
            auth = info.get("auth", {})
            p["auth_type"] = auth.get("type", "api_key")
            # Check if this plugin has connectable auth (token paste or OAuth)
            p["connectable"] = auth.get("type") in ("token", "oauth2")
            # Multi-token plugins
            p["has_multi_tokens"] = bool(auth.get("tokens"))
    return JSONResponse({"plugins": plugins})


# ── Toggle ──────────────────────────────────────────────────────────────────

@router.post("/plugins/{plugin_id}/toggle")
async def toggle_plugin(plugin_id: str, request: Request):
    """Toggle a plugin on or off.  Body: {"enabled": true|false}"""
    if plugin_id.lower() not in _registry:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    body = await request.json()
    enabled = bool(body.get("enabled", False))
    set_plugin_enabled(plugin_id, enabled)
    return JSONResponse({"ok": True, "plugin_id": plugin_id, "enabled": enabled})


# ── Connect Page (Token Paste) ──────────────────────────────────────────────

def _lookup_plugin_or_catalog(plugin_id: str) -> dict | None:
    """Look up plugin info from registry first, then fall back to marketplace catalog.

    This allows marketplace-installed MCP packages (e.g. figma-oauth, slack-oauth)
    to use the same connect/OAuth flow as legacy plugins.
    """
    info = _registry.get(plugin_id.lower())
    if info:
        return info
    # Fall back to marketplace catalog (for marketplace-installed MCPs)
    try:
        from helm.packages.marketplace import get_catalog_entry
        entry = get_catalog_entry(plugin_id)
        if entry and entry.get("setup"):
            # Build a plugin-compatible info dict from catalog entry
            setup = entry["setup"]
            cat_info = {
                "id": entry.get("id") or entry.get("slug", plugin_id),
                "name": entry.get("name", plugin_id),
                "emoji": entry.get("emoji", "🔌"),
                "description": entry.get("description", ""),
            }
            # Map catalog setup → plugin auth format
            if setup.get("type") == "oauth":
                cat_info["auth"] = {
                    "type": "oauth2",
                    "authorize_url": setup.get("authorize_url", ""),
                    "token_url": setup.get("token_url", ""),
                    "scopes": setup.get("scopes", ""),
                    "pkce": setup.get("pkce", False),
                    "client_id": setup.get("client_id", ""),
                    "env_client_id": setup.get("env_client_id", ""),
                    "env_client_secret": setup.get("env_client_secret", ""),
                    "token_env": setup.get("token_env", ""),
                    "proxy_exchange": setup.get("proxy_exchange", False),
                    # Provider name for the proxy (e.g. "github" even if
                    # the catalog slug is "github-oauth").
                    "proxy_provider": setup.get("provider", ""),
                }
                # Merge env_vars into auth if present
                for ev in setup.get("env_vars", []):
                    if isinstance(ev, dict):
                        key = ev.get("key", "")
                        if "CLIENT_ID" in key:
                            cat_info["auth"]["env_client_id"] = key
                        elif "CLIENT_SECRET" in key:
                            cat_info["auth"]["env_client_secret"] = key
                        elif not cat_info["auth"].get("token_env"):
                            cat_info["auth"]["token_env"] = key
            elif setup.get("type") in ("token", "api_key"):
                token_env = ""
                for ev in setup.get("env_vars", []):
                    if isinstance(ev, dict):
                        token_env = ev.get("key", "")
                        break
                    elif isinstance(ev, str):
                        token_env = ev
                        break
                cat_info["auth"] = {
                    "type": "token",
                    "token_env": token_env,
                    "token_label": setup.get("env_vars", [{}])[0].get("label", "API Token") if setup.get("env_vars") and isinstance(setup["env_vars"][0], dict) else "API Token",
                    "token_url": setup.get("setup_url", ""),
                    "token_hint": setup.get("env_vars", [{}])[0].get("placeholder", "") if setup.get("env_vars") and isinstance(setup["env_vars"][0], dict) else "",
                }
            return cat_info
    except Exception as e:
        logger.warning("Catalog lookup for plugin '%s' failed: %s", plugin_id, e)
    return None


@router.get("/plugins/{plugin_id}/connect")
async def connect_page(plugin_id: str):
    """Show a connect page where users paste their token/API key.

    For OAuth2 plugins with a client_id available (embedded or env var),
    auto-redirect to the OAuth flow instead of showing the token-paste page.
    """
    info = _lookup_plugin_or_catalog(plugin_id)
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    # Auto-redirect OAuth2 plugins that have a client_id ready
    auth = info.get("auth", {})
    if auth.get("type") == "oauth2":
        # Check if client_id is available (embedded or env var)
        client_id = auth.get("client_id", "")
        if not client_id:
            client_id_env = auth.get("env_client_id", "")
            client_id = os.environ.get(client_id_env, "") if client_id_env else ""
        if client_id:
            # Client ID available — redirect straight to OAuth flow
            return RedirectResponse(url=f"/plugins/{plugin_id}/oauth/start")

    return HTMLResponse(_connect_page(info))


def _validate_token(info: dict, token_value: str) -> dict:
    """Validate a token against the plugin's validate config.

    Returns {"ok": True} or {"ok": False, "error": "..."}.
    Skips validation (returns ok) if no validate config is defined.
    """
    validate = info.get("validate")
    if not validate:
        return {"ok": True}

    url = validate.get("url", "")
    if not url:
        return {"ok": True}

    # Build headers with token substitution
    headers = {}
    for k, v in validate.get("headers", {}).items():
        headers[k] = v.replace("{token}", token_value)

    method = validate.get("method", "GET").upper()
    body = validate.get("body", "")

    try:
        if method == "POST":
            resp = http_requests.post(url, headers=headers,
                                      data=body.replace("{token}", token_value)
                                      if body else None,
                                      timeout=10)
        else:
            resp = http_requests.get(url, headers=headers, timeout=10)

        # Check expected status
        expect = validate.get("expect_status", 200)
        if isinstance(expect, list):
            valid_statuses = expect
        else:
            valid_statuses = [expect]

        if resp.status_code in valid_statuses:
            return {"ok": True}

        # Token rejected
        if resp.status_code == 401:
            return {"ok": False, "error": "Invalid token — authentication failed (401)"}
        elif resp.status_code == 403:
            return {"ok": False, "error": "Token rejected — insufficient permissions (403)"}
        else:
            return {"ok": False,
                    "error": f"Token validation failed (HTTP {resp.status_code})"}

    except http_requests.exceptions.ConnectionError:
        return {"ok": False,
                "error": "Could not reach the API — check your network connection"}
    except http_requests.exceptions.Timeout:
        return {"ok": False,
                "error": "API request timed out — try again later"}
    except Exception as exc:
        logger.warning("Token validation error for %s: %s",
                       info.get("id", "?"), exc)
        # Don't block saving on unexpected validation errors
        return {"ok": True}


@router.post("/plugins/{plugin_id}/save-token")
async def save_token(plugin_id: str, request: Request):
    """Save a token pasted by the user. Body: {"token_env": "...", "value": "..."}"""
    info = _lookup_plugin_or_catalog(plugin_id)
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    body = await request.json()
    token_env = body.get("token_env", "")
    value = body.get("value", "").strip()

    if not token_env or not value:
        return JSONResponse({"error": "Missing token_env or value"}, status_code=400)

    # Validate that this token_env belongs to this plugin
    auth = info.get("auth", {})
    valid_envs = set()
    if auth.get("token_env"):
        valid_envs.add(auth["token_env"])
    if auth.get("fallback_token", {}).get("token_env"):
        valid_envs.add(auth["fallback_token"]["token_env"])
    for t in auth.get("tokens", []):
        valid_envs.add(t["token_env"])
    for ev in info.get("env_vars", []):
        valid_envs.add(ev)

    if token_env not in valid_envs:
        return JSONResponse({"error": f"Invalid token_env for this plugin"}, status_code=400)

    # Validate the token against the API before saving
    validation = _validate_token(info, value)
    if not validation["ok"]:
        return JSONResponse({
            "error": validation["error"],
            "validation_failed": True,
        }, status_code=400)

    # Save to encrypted vault (+ .env placeholder for backward compat)
    from helm.token_vault import store_token
    from helm.web_routes.app import update_env
    store_token(token_env, value)
    update_env(token_env, "vault-managed")

    # Auto-enable the plugin
    set_plugin_enabled(plugin_id, True)

    # Reload MCP servers so they pick up the new token
    try:
        from helm.mcp.manager import MCPManager
        mgr = MCPManager.get_instance()
        if mgr and hasattr(mgr, "reload_servers"):
            import asyncio
            asyncio.ensure_future(mgr.reload_servers())
    except Exception:
        pass

    return JSONResponse({"ok": True, "plugin_id": plugin_id, "connected": True})


# ── OAuth Flow (for plugins with client credentials configured) ─────────────

@router.get("/plugins/{plugin_id}/oauth/start")
async def oauth_start(plugin_id: str):
    """Initiate OAuth flow — redirects to provider if credentials are configured,
    otherwise falls back to the connect (token paste) page."""
    info = _lookup_plugin_or_catalog(plugin_id)
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    auth = info.get("auth", {})
    if auth.get("type") != "oauth2":
        # Not an OAuth plugin — redirect to token paste page
        return RedirectResponse(url=f"/plugins/{plugin_id}/connect")

    result = start_oauth(info)
    if result.get("needs_setup"):
        # OAuth credentials not configured — show token paste page instead
        return RedirectResponse(url=f"/plugins/{plugin_id}/connect")
    if "error" in result:
        return HTMLResponse(_callback_page(False, result["error"]))
    if "providers" in result:
        return JSONResponse(result)

    return RedirectResponse(url=result["authorize_url"])


@router.get("/plugins/{plugin_id}/oauth/start/{provider}")
async def oauth_start_provider(plugin_id: str, provider: str):
    """Initiate OAuth flow for a specific provider (e.g., linear or jira)."""
    info = _lookup_plugin_or_catalog(plugin_id)
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    result = start_oauth_provider(info, provider.lower())
    if result.get("needs_setup"):
        return RedirectResponse(url=f"/plugins/{plugin_id}/connect")
    if "error" in result:
        return HTMLResponse(_callback_page(False, result["error"]))

    return RedirectResponse(url=result["authorize_url"])


async def _reload_mcp_after_connect():
    """Reload MCP servers after a token is saved so they pick up new credentials."""
    try:
        from helm.mcp.manager import MCPManager
        mgr = MCPManager.get_instance()
        if mgr and hasattr(mgr, "reload_servers"):
            await mgr.reload_servers()
    except Exception as e:
        logger.warning("MCP reload after connect failed: %s", e)


@router.get("/plugins/oauth/callback")
async def oauth_callback(
    code: str = "", state: str = "", error: str = "",
    token: str = "", refresh_token: str = "",
):
    """OAuth callback — handles both:
    1. code + state: local token exchange (app exchanges code for token)
    2. token + state: proxy-exchanged token (proxy already did the exchange)
    """
    if error:
        return HTMLResponse(_callback_page(False, f"Authorization denied: {error}"))

    # Proxy-exchanged token: proxy already exchanged the code for a token
    if token and state:
        result = handle_token_direct(token, state, refresh_token)
        if "error" in result:
            return HTMLResponse(_callback_page(False, result["error"]))
        plugin_id = result.get("plugin_id", "")
        set_plugin_enabled(plugin_id, True)
        await _reload_mcp_after_connect()
        return HTMLResponse(_callback_page(True, f"Successfully connected! Plugin '{plugin_id}' is now enabled."))

    # Local exchange: app exchanges code for token
    if not code or not state:
        return HTMLResponse(_callback_page(False, "Missing code or state parameter"))

    result = handle_callback(code, state)
    if "error" in result:
        return HTMLResponse(_callback_page(False, result["error"]))

    plugin_id = result.get("plugin_id", "")
    set_plugin_enabled(plugin_id, True)
    await _reload_mcp_after_connect()

    return HTMLResponse(_callback_page(True, f"Successfully connected! Plugin '{plugin_id}' is now enabled."))


# ── Disconnect ──────────────────────────────────────────────────────────────

@router.post("/plugins/{plugin_id}/disconnect")
async def plugin_disconnect(plugin_id: str):
    """Clear stored tokens for a plugin."""
    info = _lookup_plugin_or_catalog(plugin_id)
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    result = disconnect(info)
    set_plugin_enabled(plugin_id, False)
    return JSONResponse(result)


# ── HTML Pages ──────────────────────────────────────────────────────────────

def _connect_page(info: dict) -> str:
    """Generate a beautiful connect page where users paste their token."""
    auth = info.get("auth", {})
    name = html_mod.escape(info.get("name", "Plugin"))
    emoji = info.get("emoji", "")
    plugin_id = html_mod.escape(info.get("id", ""))

    # Determine token fields to show
    token_fields = []

    # Check for multi-token plugins (e.g., Linear/Jira, Zapier)
    if auth.get("tokens"):
        for t in auth["tokens"]:
            token_fields.append(t)
    # Check for fallback_token on OAuth plugins (e.g., Canva, Google)
    elif auth.get("fallback_token"):
        token_fields.append(auth["fallback_token"])
    # Standard single-token plugins
    elif auth.get("token_env"):
        token_fields.append({
            "token_env": auth["token_env"],
            "token_label": auth.get("token_label", "API Token"),
            "token_url": auth.get("token_url", ""),
            "token_hint": auth.get("token_hint", ""),
        })

    # Build token input fields
    fields_html = ""
    for i, tf in enumerate(token_fields):
        t_label = html_mod.escape(tf.get("token_label", "Token"))
        t_env = html_mod.escape(tf.get("token_env", ""))
        t_url = tf.get("token_url", "")
        t_hint = html_mod.escape(tf.get("token_hint", ""))
        scopes = html_mod.escape(auth.get("scopes_hint", ""))
        is_connected = bool(os.environ.get(tf.get("token_env", ""), ""))

        url_link = ""
        if t_url:
            url_link = (f'<a href="{html_mod.escape(t_url)}" target="_blank" '
                        f'rel="noopener" class="token-link">Get your {t_label} &rarr;</a>')

        status_badge = ""
        if is_connected:
            status_badge = '<span class="badge-connected">Connected</span>'

        fields_html += f"""
        <div class="token-field" id="field-{i}">
          <div class="field-header">
            <label>{t_label} {status_badge}</label>
            {url_link}
          </div>
          {"<div class='field-hint'>" + t_hint + "</div>" if t_hint else ""}
          {"<div class='field-scopes'>" + scopes + "</div>" if scopes else ""}
          <div class="input-row">
            <input type="password" id="token-{i}" data-env="{t_env}"
                   placeholder="Paste your {t_label.lower()} here..."
                   {"value='••••••••'" if is_connected else ""}
                   autocomplete="off" spellcheck="false" />
            <button class="btn-eye" onclick="toggleVis({i})" title="Show/hide">&#128065;</button>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head><title>RAPR AI — Connect {name}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    display:flex;align-items:center;justify-content:center;min-height:100vh;
    margin:0;background:#0d0d0d;color:#e0e0e0;padding:20px}}
  .card{{background:#1a1a1a;border-radius:16px;padding:36px;max-width:480px;
    width:100%;box-shadow:0 4px 24px rgba(0,0,0,0.5)}}
  .header{{text-align:center;margin-bottom:28px}}
  .emoji{{font-size:44px;margin-bottom:8px}}
  h2{{font-size:20px;font-weight:600;margin-bottom:4px}}
  .subtitle{{color:#888;font-size:13px}}
  .token-field{{margin-bottom:20px}}
  .field-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
  .field-header label{{font-size:13px;font-weight:600;color:#ddd;display:flex;align-items:center;gap:8px}}
  .badge-connected{{background:#065f46;color:#34d399;font-size:10px;padding:2px 8px;
    border-radius:10px;font-weight:500}}
  .token-link{{font-size:12px;color:#a78bfa;text-decoration:none;transition:color .15s}}
  .token-link:hover{{color:#c4b5fd}}
  .field-hint{{font-size:12px;color:#777;margin-bottom:8px;line-height:1.4}}
  .field-scopes{{font-size:11px;color:#666;margin-bottom:8px;font-style:italic}}
  .input-row{{display:flex;gap:6px}}
  .input-row input{{flex:1;background:#111;border:1px solid #333;border-radius:8px;
    padding:10px 14px;color:#e0e0e0;font-size:13px;font-family:monospace;outline:none;
    transition:border-color .15s}}
  .input-row input:focus{{border-color:#7c3aed}}
  .btn-eye{{background:#222;border:1px solid #333;border-radius:8px;width:40px;
    cursor:pointer;font-size:16px;color:#888;transition:all .15s}}
  .btn-eye:hover{{background:#333;color:#ccc}}
  .actions{{display:flex;flex-direction:column;gap:10px;margin-top:24px}}
  .btn-save{{padding:12px 20px;background:#7c3aed;color:#fff;border:none;
    border-radius:10px;font-size:14px;font-weight:500;cursor:pointer;transition:background .15s}}
  .btn-save:hover{{background:#6d28d9}}
  .btn-save:disabled{{background:#333;color:#666;cursor:not-allowed}}
  .btn-close{{padding:10px 20px;background:transparent;color:#888;border:1px solid #333;
    border-radius:10px;font-size:13px;cursor:pointer;transition:all .15s}}
  .btn-close:hover{{color:#e0e0e0;border-color:#555}}
  .msg{{text-align:center;padding:10px;border-radius:8px;font-size:13px;margin-top:12px;display:none}}
  .msg.ok{{display:block;background:#052e16;color:#34d399;border:1px solid #065f46}}
  .msg.err{{display:block;background:#450a0a;color:#f87171;border:1px solid #7f1d1d}}
  .spinner{{display:inline-block;width:16px;height:16px;border:2px solid #fff3;
    border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;
    vertical-align:middle;margin-right:6px}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
</style></head>
<body>
<div class="card">
  <div class="header">
    <div class="emoji">{emoji}</div>
    <h2>Connect {name}</h2>
    <div class="subtitle">Paste your token to connect</div>
  </div>

  {fields_html}

  <div class="actions">
    <button class="btn-save" id="btn-save" onclick="saveTokens()">Save &amp; Connect</button>
    <button class="btn-close" onclick="window.close()">Cancel</button>
  </div>
  <div class="msg" id="msg"></div>
</div>

<script>
function toggleVis(i) {{
  const inp = document.getElementById('token-'+i);
  inp.type = inp.type === 'password' ? 'text' : 'password';
}}

async function saveTokens() {{
  const btn = document.getElementById('btn-save');
  const msg = document.getElementById('msg');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Validating...';
  msg.className = 'msg';

  const inputs = document.querySelectorAll('.input-row input');
  let saved = 0, errors = [];

  for (const inp of inputs) {{
    const val = inp.value.trim();
    if (!val || val === '••••••••') continue;
    const env = inp.dataset.env;
    try {{
      const resp = await fetch('/plugins/{plugin_id}/save-token', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{token_env: env, value: val}})
      }});
      const data = await resp.json();
      if (data.ok) saved++;
      else errors.push(data.error || 'Unknown error');
    }} catch(e) {{
      errors.push(e.message);
    }}
  }}

  if (errors.length) {{
    msg.className = 'msg err';
    msg.textContent = errors.join('; ');
    btn.disabled = false;
    btn.textContent = 'Save & Connect';
  }} else if (saved > 0) {{
    msg.className = 'msg ok';
    msg.textContent = 'Connected successfully!';
    btn.textContent = 'Connected!';
    // Notify parent window
    if (window.opener) {{
      try {{ window.opener.postMessage({{type:'plugin-oauth-done', success:true}}, '*'); }} catch(e) {{}}
    }}
    setTimeout(() => window.close(), 1500);
  }} else {{
    msg.className = 'msg err';
    msg.textContent = 'Please paste at least one token.';
    btn.disabled = false;
    btn.textContent = 'Save & Connect';
  }}
}}
</script>
</body></html>"""


def _callback_page(success: bool, message: str) -> str:
    """Generate a simple HTML page shown after OAuth callback."""
    color = "#10b981" if success else "#ef4444"
    icon = "&#10003;" if success else "&#10007;"
    return f"""<!DOCTYPE html>
<html>
<head><title>RAPR AI — Plugin Connection</title>
<style>
  body {{ font-family: -apple-system, sans-serif; display:flex; align-items:center;
    justify-content:center; min-height:100vh; margin:0; background:#0d0d0d; color:#e0e0e0; }}
  .card {{ background:#1a1a1a; border-radius:16px; padding:40px; text-align:center;
    max-width:400px; box-shadow: 0 4px 24px rgba(0,0,0,0.4); }}
  .icon {{ font-size:48px; color:{color}; margin-bottom:16px; }}
  h2 {{ margin:0 0 12px; font-size:20px; }}
  p {{ color:#999; font-size:14px; line-height:1.5; }}
  .btn {{ display:inline-block; margin-top:20px; padding:10px 24px; background:{color};
    color:#fff; border-radius:8px; text-decoration:none; font-size:14px; cursor:pointer;
    border:none; }}
  .btn:hover {{ opacity:0.9; }}
</style></head>
<body>
<div class="card">
  <div class="icon">{icon}</div>
  <h2>{"Connected!" if success else "Connection Failed"}</h2>
  <p>{message}</p>
  <button class="btn" onclick="window.close()">Close Window</button>
</div>
<script>
  if (window.opener) {{
    try {{ window.opener.postMessage({{type:'plugin-oauth-done', success:{str(success).lower()}}}, '*'); }} catch(e) {{}}
  }}
  {"setTimeout(()=>window.close(), 3000);" if success else ""}
</script>
</body></html>"""
