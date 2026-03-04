"""
helm/web_routes/plugins_routes.py — Plugin management API endpoints.

Endpoints:
    GET  /plugins                             → List all plugins with enabled/connected status
    POST /plugins/{plugin_id}/toggle          → Enable or disable a plugin
    GET  /plugins/{plugin_id}/oauth/start     → Start OAuth flow (redirects to provider)
    GET  /plugins/{plugin_id}/oauth/start/{provider} → Start OAuth for multi-provider plugin
    GET  /plugins/oauth/callback              → OAuth callback handler
    POST /plugins/{plugin_id}/disconnect      → Clear stored tokens
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

from helm.plugins import list_plugins, set_plugin_enabled, _registry
from helm.plugin_oauth import (
    start_oauth, start_oauth_provider, handle_callback,
    check_connected, disconnect,
)

router = APIRouter()


@router.get("/plugins")
async def get_plugins():
    """Return all plugins with their current enabled/disabled/connected state."""
    plugins = list_plugins()
    # Enrich with connection status
    for p in plugins:
        info = _registry.get(p["id"])
        if info:
            p["connected"] = check_connected(info)
            auth = info.get("auth", {})
            p["auth_type"] = auth.get("type", "api_key")
            p["has_providers"] = bool(auth.get("providers"))
            p["providers"] = list(auth.get("providers", {}).keys())
    return JSONResponse({"plugins": plugins})


@router.post("/plugins/{plugin_id}/toggle")
async def toggle_plugin(plugin_id: str, request: Request):
    """Toggle a plugin on or off.  Body: {"enabled": true|false}"""
    if plugin_id.lower() not in _registry:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    body = await request.json()
    enabled = bool(body.get("enabled", False))
    set_plugin_enabled(plugin_id, enabled)
    return JSONResponse({"ok": True, "plugin_id": plugin_id, "enabled": enabled})


@router.get("/plugins/{plugin_id}/oauth/start")
async def oauth_start(plugin_id: str):
    """Initiate OAuth flow — returns JSON with authorize_url or redirects."""
    info = _registry.get(plugin_id.lower())
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    result = start_oauth(info)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    if "providers" in result:
        return JSONResponse(result)  # Frontend should show provider picker

    # Redirect user to the provider's authorization page
    return RedirectResponse(url=result["authorize_url"])


@router.get("/plugins/{plugin_id}/oauth/start/{provider}")
async def oauth_start_provider(plugin_id: str, provider: str):
    """Initiate OAuth flow for a specific provider (e.g., linear or jira)."""
    info = _registry.get(plugin_id.lower())
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    result = start_oauth_provider(info, provider.lower())
    if "error" in result:
        return JSONResponse(result, status_code=400)

    return RedirectResponse(url=result["authorize_url"])


@router.get("/plugins/oauth/callback")
async def oauth_callback(code: str = "", state: str = "", error: str = ""):
    """OAuth callback — exchanges code for token and shows success/failure page."""
    if error:
        return HTMLResponse(_callback_page(False, f"Authorization denied: {error}"))

    if not code or not state:
        return HTMLResponse(_callback_page(False, "Missing code or state parameter"))

    result = handle_callback(code, state)
    if "error" in result:
        return HTMLResponse(_callback_page(False, result["error"]))

    plugin_id = result.get("plugin_id", "")

    # Auto-enable the plugin on successful connection
    set_plugin_enabled(plugin_id, True)

    return HTMLResponse(_callback_page(True, f"Successfully connected! Plugin '{plugin_id}' is now enabled."))


@router.post("/plugins/{plugin_id}/disconnect")
async def plugin_disconnect(plugin_id: str):
    """Clear stored OAuth tokens for a plugin."""
    info = _registry.get(plugin_id.lower())
    if not info:
        return JSONResponse({"error": f"Plugin '{plugin_id}' not found"}, status_code=404)

    result = disconnect(info)
    # Also disable the plugin
    set_plugin_enabled(plugin_id, False)
    return JSONResponse(result)


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
  // Notify the opener (Settings page) to refresh plugin list
  if (window.opener) {{
    try {{ window.opener.postMessage({{type:'plugin-oauth-done', success:{str(success).lower()}}}, '*'); }} catch(e) {{}}
  }}
  // Auto-close after 3 seconds on success
  {"setTimeout(()=>window.close(), 3000);" if success else ""}
</script>
</body></html>"""
