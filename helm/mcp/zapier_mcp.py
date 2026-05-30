"""
helm/mcp/zapier_mcp.py — Zapier MCP connector (Tier 2 universal connector).

Zapier MCP is a *meta-connector*: one integration unlocks ~8000 apps /
~30000 actions. It is core runtime infrastructure, NOT a marketplace package.

Each user creates their own Zapier MCP server at https://mcp.zapier.com and
pastes its URL here. The URL embeds the user's API key, so it is treated as a
secret and stored in the encrypted token vault (env: ZAPIER_MCP_URL).

Zapier MCP is a hosted HTTP (streamable-HTTP / SSE) endpoint. Our MCPClient
speaks stdio JSON-RPC only, so we bridge through the `mcp-remote` npm proxy:

    npx -y mcp-remote ${ZAPIER_MCP_URL}

This keeps Zapier on the exact same subprocess path as every other MCP server,
so it is auto-discovered by the in-tool manager AND synced into each native CLI
(Claude / Gemini / Codex) by manager.sync_native_mcp_configs().

Public API:
    ZAPIER_MCP_URL_ENV               env key holding the per-user server URL
    is_connected()        -> bool
    status()              -> dict
    connect(url)          -> awaitable[dict]
    disconnect()          -> awaitable[dict]
"""

import json
import os
from urllib.parse import urlparse

from helm.config import logger

# ── Constants ────────────────────────────────────────────────────────────────

ZAPIER_MCP_URL_ENV = "ZAPIER_MCP_URL"
SERVER_ID = "zapier"

# The user's server URL embeds the secret, so we keep it out of mcp_servers.json
# (which is plaintext on disk) by referencing the vault-managed env var instead.
# config.load_config() resolves ${VAR} in the command string at start time.
_SERVER_COMMAND = "npx -y mcp-remote ${" + ZAPIER_MCP_URL_ENV + "}"

# Hosts Zapier serves MCP from. We only accept these to avoid pointing the
# bridge at an arbitrary attacker-supplied endpoint.
_ALLOWED_HOSTS = {"mcp.zapier.com"}


# ── URL validation ───────────────────────────────────────────────────────────

def _validate_url(url: str) -> str | None:
    """Return an error string if the URL is not a valid Zapier MCP URL, else None."""
    if not url:
        return "No URL provided."
    try:
        parsed = urlparse(url)
    except Exception:
        return "URL could not be parsed."
    if parsed.scheme != "https":
        return "Zapier MCP URL must use https://."
    if parsed.hostname not in _ALLOWED_HOSTS:
        return (f"URL host must be mcp.zapier.com (got '{parsed.hostname or '?'}'). "
                f"Copy the server URL from https://mcp.zapier.com.")
    if not parsed.path or parsed.path == "/":
        return "URL is missing the server path. Copy the full URL from mcp.zapier.com."
    return None


# ── mcp_servers.json registration ────────────────────────────────────────────

def _config_path() -> str:
    from helm.paths import PROJECT_ROOT
    return str(PROJECT_ROOT / "mcp_servers.json")


def _write_server_entry(enabled: bool) -> None:
    """Ensure mcp_servers.json contains the zapier entry with the given enabled flag.

    Writes the raw JSON directly (preserving other servers) so the entry exists
    even if it was never present before. The command references ${ZAPIER_MCP_URL}
    so the secret stays in the vault, not in this plaintext file.
    """
    path = _config_path()
    raw: dict = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raw = {}
        except Exception as exc:
            logger.warning("zapier_mcp: could not read %s (%s) — recreating", path, exc)
            raw = {}

    raw[SERVER_ID] = {
        "type": "subprocess",
        "command": _SERVER_COMMAND,
        "enabled": bool(enabled),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info("zapier_mcp: wrote server entry (enabled=%s) to %s", enabled, path)


# ── State ────────────────────────────────────────────────────────────────────

def _stored_url() -> str:
    """Return the stored Zapier MCP URL (vault or env), or empty string."""
    val = os.environ.get(ZAPIER_MCP_URL_ENV, "")
    if val and val != "vault-managed":
        return val
    try:
        from helm.token_vault import load_token
        return load_token(ZAPIER_MCP_URL_ENV) or ""
    except Exception:
        return ""


def is_connected() -> bool:
    """True if a Zapier MCP server URL is stored."""
    return bool(_stored_url())


def status() -> dict:
    """Return current connector status for the Settings UI."""
    connected = is_connected()
    running = False
    tool_count = 0
    try:
        from helm.mcp.manager import get_manager
        client = get_manager().get_client(SERVER_ID)
        if client:
            running = client.is_running()
            tool_count = client.get_tool_count()
    except Exception:
        pass
    return {
        "id": SERVER_ID,
        "connected": connected,
        "running": running,
        "tool_count": tool_count,
    }


# ── Connect / disconnect ─────────────────────────────────────────────────────

async def connect(url: str) -> dict:
    """Connect to a user's Zapier MCP server.

    Stores the URL in the vault, registers + enables the zapier MCP server,
    and reloads the manager so the tools become available immediately.
    """
    url = (url or "").strip()
    err = _validate_url(url)
    if err:
        return {"ok": False, "error": err}

    # Store the secret URL in the encrypted vault (+ .env placeholder).
    from helm.token_vault import store_token
    from helm.web_routes.app import update_env
    store_token(ZAPIER_MCP_URL_ENV, url)          # also sets os.environ
    update_env(ZAPIER_MCP_URL_ENV, "vault-managed")

    # Register + enable the MCP server, then reload the manager.
    _write_server_entry(enabled=True)
    try:
        from helm.mcp.manager import get_manager
        await get_manager().reload_servers()
    except Exception as exc:
        logger.error("zapier_mcp: reload after connect failed: %s", exc)
        return {"ok": False,
                "error": f"Saved URL but failed to start the Zapier MCP server: {exc}"}

    st = status()
    if not st["running"]:
        return {"ok": False,
                "error": "Zapier MCP server did not start. Verify the URL is correct "
                         "and that Node.js/npx is installed (mcp-remote bridge).",
                **st}
    logger.info("zapier_mcp: connected — %d tools", st["tool_count"])
    return {"ok": True, **st}


async def disconnect() -> dict:
    """Disconnect: clear the stored URL, disable + stop the server."""
    from helm.token_vault import delete_token
    from helm.web_routes.app import update_env
    delete_token(ZAPIER_MCP_URL_ENV)
    update_env(ZAPIER_MCP_URL_ENV, "")
    os.environ.pop(ZAPIER_MCP_URL_ENV, None)

    _write_server_entry(enabled=False)
    try:
        from helm.mcp.manager import get_manager
        await get_manager().reload_servers()
    except Exception as exc:
        logger.warning("zapier_mcp: reload after disconnect failed: %s", exc)

    logger.info("zapier_mcp: disconnected")
    return {"ok": True, "connected": False, "running": False}
