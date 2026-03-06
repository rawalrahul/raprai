"""
helm/plugin_oauth.py — OAuth 2.0 flow handler for RAPR AI plugins.

Handles the authorize → callback → token exchange cycle.
Stores tokens in .env via update_env() so they persist across restarts.
Supports standard OAuth2 and PKCE flows.

Flow:
  1. User clicks "Connect" in Settings UI
  2. Frontend calls GET /plugins/{id}/oauth/start
  3. Backend builds authorize URL with state, optional PKCE code_verifier
  4. User is redirected to provider (Slack, GitHub, etc.)
  5. Provider redirects back to GET /plugins/oauth/callback?code=...&state=...
  6. Backend exchanges code for token
  7. Token stored in .env and os.environ
  8. Frontend shows "Connected" status
"""

import hashlib
import os
import secrets
import base64
import json
import time
from urllib.parse import urlencode

import requests as http_requests

from helm.config import logger

# In-memory cache for pending OAuth flows: state -> {plugin_id, code_verifier, ...}
# Also persisted to SQLite for resilience across restarts.
_pending_flows: dict[str, dict] = {}


def _ensure_oauth_table():
    """Create the oauth_pending_flows table if it doesn't exist."""
    try:
        from helm.db import get_db
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS oauth_pending_flows (
                state TEXT PRIMARY KEY,
                flow_data TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        db.commit()
    except Exception:
        pass


def _persist_flow(state: str, flow_data: dict):
    """Save a pending OAuth flow to SQLite."""
    try:
        _ensure_oauth_table()
        from helm.db import get_db
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO oauth_pending_flows (state, flow_data, created_at) VALUES (?, ?, ?)",
            (state, json.dumps(flow_data), time.time()),
        )
        db.commit()
    except Exception:
        pass


def _pop_flow(state: str) -> dict | None:
    """Pop a pending flow from memory + DB. Returns None if not found."""
    flow = _pending_flows.pop(state, None)
    # Also try DB
    try:
        from helm.db import get_db
        db = get_db()
        row = db.execute(
            "SELECT flow_data FROM oauth_pending_flows WHERE state = ?", (state,)
        ).fetchone()
        db.execute("DELETE FROM oauth_pending_flows WHERE state = ?", (state,))
        db.commit()
        if row and not flow:
            flow = json.loads(row["flow_data"])
    except Exception:
        pass
    return flow


def _cleanup_stale_flows():
    """Remove OAuth flows older than 15 minutes."""
    cutoff = time.time() - 900  # 15 minutes
    # Clean memory
    stale = [s for s, f in _pending_flows.items()
             if f.get("_created_at", 0) < cutoff]
    for s in stale:
        _pending_flows.pop(s, None)
    # Clean DB
    try:
        from helm.db import get_db
        db = get_db()
        db.execute("DELETE FROM oauth_pending_flows WHERE created_at < ?", (cutoff,))
        db.commit()
    except Exception:
        pass


def get_callback_url() -> str:
    """Build the OAuth callback URL based on configured host/port."""
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = os.environ.get("WEB_PORT", "3456")
    # For OAuth callbacks, use localhost (provider redirects to user's browser)
    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    return f"http://{display_host}:{port}/plugins/oauth/callback"


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def start_oauth(plugin_info: dict) -> dict:
    """Build the authorization URL for an OAuth plugin.

    Returns: {"authorize_url": "https://...", "state": "..."}
    """
    auth = plugin_info.get("auth", {})
    if auth.get("type") != "oauth2":
        return {"error": "Plugin does not support OAuth"}

    # Handle multi-provider plugins (like Linear/Jira)
    # For now, use the top-level auth config; providers handled separately
    authorize_url = auth.get("authorize_url", "")
    if not authorize_url:
        # Check if it's a multi-provider plugin
        providers = auth.get("providers", {})
        if providers:
            # Return list of providers for frontend to choose
            return {"providers": list(providers.keys())}
        return {"error": "No authorize_url configured"}

    plugin_id = plugin_info.get("id", "")
    client_id_env = auth.get("env_client_id", "")
    client_id = os.environ.get(client_id_env, "")

    if not client_id:
        return {
            "error": f"Missing {client_id_env} in .env.",
            "needs_setup": True,
            "plugin_id": plugin_id,
            "plugin_name": plugin_info.get("name", plugin_id),
            "plugin_emoji": plugin_info.get("emoji", ""),
            "setup_url": plugin_info.get("setup_url", ""),
            "setup_steps": plugin_info.get("setup_steps", []),
            "env_client_id": client_id_env,
            "env_client_secret": auth.get("env_client_secret", ""),
            "callback_url": get_callback_url(),
        }

    # Generate state token
    state = secrets.token_urlsafe(32)

    # Build params
    params = {
        "client_id": client_id,
        "redirect_uri": get_callback_url(),
        "state": state,
        "response_type": "code",
    }

    # Add scopes
    scopes = auth.get("scopes", "")
    if scopes:
        params["scope"] = scopes

    # PKCE support
    flow_data = {"plugin_id": plugin_id, "auth": auth}
    if auth.get("pkce"):
        verifier, challenge = generate_pkce_pair()
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"
        flow_data["code_verifier"] = verifier

    # Extra params (e.g., Google's access_type=offline)
    extra = auth.get("extra_params", {})
    if extra:
        params.update(extra)

    # Store pending flow (memory + DB)
    flow_data["_created_at"] = time.time()
    _pending_flows[state] = flow_data
    _persist_flow(state, flow_data)
    _cleanup_stale_flows()

    url = f"{authorize_url}?{urlencode(params)}"
    logger.info("OAuth: starting flow for %s (state=%s...)", plugin_id, state[:8])
    return {"authorize_url": url, "state": state}


def start_oauth_provider(plugin_info: dict, provider_key: str) -> dict:
    """Start OAuth for a specific provider in a multi-provider plugin."""
    auth = plugin_info.get("auth", {})
    providers = auth.get("providers", {})
    provider = providers.get(provider_key)
    if not provider:
        return {"error": f"Unknown provider: {provider_key}"}

    # Build a synthetic plugin_info with provider-specific auth
    synth = {**plugin_info, "auth": {**provider, "type": "oauth2"}}
    synth["auth"]["_provider_key"] = provider_key
    # Carry provider-specific setup info
    setup_key = f"setup_url_{provider_key}"
    steps_key = f"setup_steps_{provider_key}"
    if setup_key in plugin_info:
        synth["setup_url"] = plugin_info[setup_key]
    if steps_key in plugin_info:
        synth["setup_steps"] = plugin_info[steps_key]
    synth["name"] = f"{plugin_info.get('name', '')} ({provider_key.title()})"
    return start_oauth(synth)


def handle_callback(code: str, state: str) -> dict:
    """Exchange authorization code for access token.

    Returns: {"ok": True, "plugin_id": "...", "connected": True}
    """
    flow = _pop_flow(state)
    if not flow:
        return {"error": "Invalid or expired state. Please try connecting again."}

    plugin_id = flow["plugin_id"]
    auth = flow["auth"]

    token_url = auth.get("token_url", "")
    client_id_env = auth.get("env_client_id", "")
    client_secret_env = auth.get("env_client_secret", "")
    client_id = os.environ.get(client_id_env, "")
    client_secret = os.environ.get(client_secret_env, "")

    if not client_id or not client_secret:
        return {"error": f"Missing {client_id_env} or {client_secret_env} in .env"}

    # Build token request
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_callback_url(),
        "client_id": client_id,
        "client_secret": client_secret,
    }

    # PKCE code_verifier
    if "code_verifier" in flow:
        token_data["code_verifier"] = flow["code_verifier"]

    # Some providers need different content types
    headers = {"Accept": "application/json"}

    try:
        resp = http_requests.post(token_url, data=token_data, headers=headers, timeout=15)
        resp.raise_for_status()

        # Handle GitHub's potential non-JSON response
        try:
            token_resp = resp.json()
        except Exception:
            # GitHub sometimes returns form-encoded
            from urllib.parse import parse_qs
            token_resp = {k: v[0] for k, v in parse_qs(resp.text).items()}

    except Exception as exc:
        logger.error("OAuth token exchange failed for %s: %s", plugin_id, exc)
        return {"error": f"Token exchange failed: {exc}"}

    # Extract access token
    access_token = (
        token_resp.get("access_token")
        or token_resp.get("authed_user", {}).get("access_token")  # Slack v2
        or token_resp.get("access_token", "")
    )

    if not access_token:
        logger.error("OAuth: no access_token in response for %s: %s", plugin_id, token_resp)
        return {"error": "No access token received from provider"}

    # Store token in encrypted vault (+ .env for backward compat)
    token_env = auth.get("token_env", "")
    if token_env:
        from helm.token_vault import store_token
        from helm.web_routes.app import update_env
        store_token(token_env, access_token)
        update_env(token_env, "vault-managed")   # placeholder so .env shows it's configured
        logger.info("OAuth: stored encrypted token for %s in vault (%s)", plugin_id, token_env)

    # Store refresh token if present (Google, etc.)
    refresh_token = token_resp.get("refresh_token", "")
    refresh_env = auth.get("refresh_token_env", "")
    if refresh_token and refresh_env:
        from helm.token_vault import store_token
        from helm.web_routes.app import update_env
        store_token(refresh_env, refresh_token)
        update_env(refresh_env, "vault-managed")
        logger.info("OAuth: stored encrypted refresh token for %s in vault (%s)", plugin_id, refresh_env)

    return {"ok": True, "plugin_id": plugin_id, "connected": True}


def _has_token(env_key: str) -> bool:
    """Check if a token exists (vault or os.environ), ignoring placeholders."""
    if not env_key:
        return False
    val = os.environ.get(env_key, "")
    if val and val != "vault-managed":
        return True
    # Try loading from vault (populates os.environ)
    try:
        from helm.token_vault import load_token
        return bool(load_token(env_key))
    except Exception:
        return False


def check_connected(plugin_info: dict) -> bool:
    """Check if a plugin has a valid token stored (vault or env)."""
    auth = plugin_info.get("auth", {})
    auth_type = auth.get("type", "")

    # No-auth plugins (local tools like MS Office): always connected
    if auth_type == "none":
        return True

    # Token-type plugins: check token_env or any of the multi-tokens
    if auth_type == "token":
        if _has_token(auth.get("token_env", "")):
            return True
        for t in auth.get("tokens", []):
            if _has_token(t.get("token_env", "")):
                return True
        return False

    # OAuth2 plugins: check token_env or fallback_token
    if auth_type == "oauth2":
        if _has_token(auth.get("token_env", "")):
            return True
        fb = auth.get("fallback_token", {})
        if _has_token(fb.get("token_env", "")):
            return True
        return False

    # Fallback: check all env_vars
    for env_var in plugin_info.get("env_vars", []):
        if _has_token(env_var):
            return True
    return False


def disconnect(plugin_info: dict) -> dict:
    """Clear stored tokens for a plugin (vault + .env)."""
    auth = plugin_info.get("auth", {})
    from helm.web_routes.app import update_env
    from helm.token_vault import delete_token

    cleared = []

    def _clear(env_key: str):
        if not env_key or env_key in cleared:
            return
        delete_token(env_key)          # remove from encrypted vault
        update_env(env_key, "")        # clear from .env
        os.environ.pop(env_key, None)
        cleared.append(env_key)

    # Clear main token
    _clear(auth.get("token_env", ""))

    # Clear multi-tokens (Linear/Jira, Zapier)
    for t in auth.get("tokens", []):
        _clear(t.get("token_env", ""))

    # Clear fallback token
    _clear(auth.get("fallback_token", {}).get("token_env", ""))

    # Clear refresh token
    _clear(auth.get("refresh_token_env", ""))

    # Multi-provider tokens
    for prov in auth.get("providers", {}).values():
        _clear(prov.get("token_env", ""))

    plugin_id = plugin_info.get("id", "")
    logger.info("OAuth: disconnected %s (cleared: %s)", plugin_id, cleared)
    return {"ok": True, "plugin_id": plugin_id, "disconnected": True}
