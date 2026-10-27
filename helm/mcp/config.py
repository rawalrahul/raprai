"""
helm/mcp/config.py — Load MCP server configuration from mcp_servers.json.

Supports ${VAR_NAME} syntax to pull values from os.environ / .env.
"""

import json
import os
import re
from typing import Optional

from helm.config import logger


_ENV_VAR_RE = re.compile(r'\$\{(\w+)\}')


def _resolve_env(value: str) -> str:
    """Replace ${VAR_NAME} with os.environ[VAR_NAME], leave as-is if not set."""
    def _replace(m):
        var = m.group(1)
        resolved = os.environ.get(var, "")
        if not resolved:
            logger.debug("mcp/config: env var ${%s} not set", var)
        return resolved
    return _ENV_VAR_RE.sub(_replace, value)


def _resolve_env_dict(env: dict) -> dict:
    """Resolve all ${VAR} references in an env dict."""
    return {k: _resolve_env(v) if isinstance(v, str) else v
            for k, v in env.items()}


def _bundled_path() -> str:
    """The servers RAPR ships with (replaced by every update)."""
    from helm.paths import PROJECT_ROOT
    return str(PROJECT_ROOT / "mcp_servers.json")


def user_config_path() -> str:
    """Your servers and on/off switches. In the data folder, because an update
    replaces the app folder (and the bundled app unpacks it fresh each start)."""
    from helm.paths import user_data_dir
    return str(user_data_dir() / "mcp_servers.json")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("MCP config: invalid JSON in %s: %s", path, exc)
        return {}
    except OSError as exc:
        logger.error("MCP config: failed to read %s: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        logger.error("MCP config: expected a JSON object in %s", path)
        return {}
    return raw


def read_user_raw() -> dict:
    return _read_json(user_config_path())


def write_user_raw(raw: dict) -> None:
    path = user_config_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def read_raw() -> dict:
    """The shipped servers with yours on top, field by field (yours win)."""
    raw = _read_json(_bundled_path())
    for sid, entry in read_user_raw().items():
        raw[sid] = {**raw.get(sid, {}), **entry} if isinstance(entry, dict) else entry
    return raw


def remove_server(server_id: str) -> bool:
    """Remove a server you installed. Ones installed before your servers moved to
    the data folder are still in the app folder's file, so look there too."""
    removed = False
    user = read_user_raw()
    if user.pop(server_id, None) is not None:
        write_user_raw(user)
        removed = True
    legacy = _read_json(_bundled_path())
    if legacy.pop(server_id, None) is not None:
        try:
            with open(_bundled_path(), "w", encoding="utf-8") as f:
                json.dump(legacy, f, indent=2, ensure_ascii=False)
                f.write("\n")
            removed = True
        except OSError as exc:
            logger.warning("MCP config: couldn't remove %s from %s: %s", server_id, _bundled_path(), exc)
    return removed


def load_config(config_path: Optional[str] = None) -> dict:
    """Load and parse mcp_servers.json.

    Returns: {server_id: {"command": [...], "env": {...}, "enabled": bool}}

    If config file doesn't exist, returns empty dict (no servers).
    """
    raw = _read_json(config_path) if config_path else read_raw()

    servers = {}
    for server_id, cfg in raw.items():
        if not isinstance(cfg, dict):
            logger.warning("MCP config: skipping '%s' — expected object", server_id)
            continue

        server_type = cfg.get("type", "subprocess")
        enabled = cfg.get("enabled", False)
        status = "enabled" if enabled else "disabled"

        # WebSocket servers (the removed Chrome extension) have no command
        if server_type == "websocket":
            servers[server_id] = {
                "type": "websocket",
                "command": [],
                "env": {},
                "enabled": enabled,
            }
            logger.info("MCP config: loaded '%s' [%s] — type=websocket",
                         server_id, status)
            continue

        command_str = cfg.get("command", "").strip()
        if not command_str:
            logger.warning("MCP config: skipping '%s' — no command", server_id)
            continue

        # Detect ${VAR} references whose env value is missing/empty. A command
        # like "npx -y mcp-remote ${ZAPIER_MCP_URL}" with no URL set would
        # otherwise launch the bridge with an empty target and fail cryptically.
        # Such a server is "unconfigured": keep it listed (so the UI can show a
        # Connect action) but force it un-startable so nothing tries to run it.
        referenced = _ENV_VAR_RE.findall(command_str)
        missing = [v for v in referenced if not os.environ.get(v, "").strip()]
        needs_config = bool(missing)

        # Keep the unresolved template for logging — the resolved form may embed
        # secrets (e.g. Zapier MCP URL contains an API key).
        log_command_str = command_str

        # Resolve ${VAR} references in the command itself (e.g. a hosted MCP
        # URL that embeds a per-user secret kept in the vault, not on disk).
        command_str = _resolve_env(command_str).strip()
        if not command_str:
            logger.warning("MCP config: skipping '%s' — command resolved to empty "
                           "(missing env var?)", server_id)
            continue

        # Parse command string into list
        # Handle quoted args if needed, but simple split works for most cases
        command = command_str.split()

        # Resolve environment variables
        env = _resolve_env_dict(cfg.get("env", {}))

        # Filter out empty env values (unresolved vars)
        env = {k: v for k, v in env.items() if v}

        servers[server_id] = {
            "type": "subprocess",
            "command": command,
            "env": env,
            # Unconfigured servers are never reported as enabled, so neither the
            # auto-starter nor a reload will try to launch them.
            "enabled": enabled and not needs_config,
            "needs_config": needs_config,
            "missing_env": missing,
        }

        if needs_config:
            logger.info("MCP config: '%s' needs configuration — missing env: %s "
                        "(not started)", server_id, ", ".join(missing))
        else:
            logger.info("MCP config: loaded '%s' [%s] — %s",
                         server_id, status, log_command_str)

    # Servers the user added in the Packages panel (kept in the user data
    # folder so they survive updates). Built-in ids win on a clash.
    try:
        from .custom_mcp import runtime_configs
        for server_id, cfg in runtime_configs().items():
            if server_id not in servers:
                servers[server_id] = cfg
    except Exception as exc:
        logger.warning("MCP config: could not load custom servers: %s", exc)

    logger.info("MCP config: %d servers loaded, %d enabled",
                len(servers), sum(1 for s in servers.values() if s["enabled"]))

    return servers


def save_config(config: dict, config_path: Optional[str] = None) -> None:
    """Save the on/off switches from a load_config() result.

    By default they go in your file in the data folder (see user_config_path).
    """
    if config_path:
        raw = _read_json(config_path)
        for server_id, cfg in config.items():
            if server_id in raw:
                raw[server_id]["enabled"] = cfg.get("enabled", False)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return

    # Only the switches go in your file; the shipped entries stay as shipped.
    known = read_raw()
    user = read_user_raw()
    for server_id, cfg in config.items():
        if server_id in known:
            user.setdefault(server_id, {})["enabled"] = cfg.get("enabled", False)
    write_user_raw(user)
    logger.info("MCP config: saved to %s", user_config_path())
