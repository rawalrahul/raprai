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


def load_config(config_path: Optional[str] = None) -> dict:
    """Load and parse mcp_servers.json.

    Returns: {server_id: {"command": [...], "env": {...}, "enabled": bool}}

    If config file doesn't exist, returns empty dict (no servers).
    """
    if not config_path:
        # Default location: project root (same level as .env)
        from helm.paths import PROJECT_ROOT
        config_path = str(PROJECT_ROOT / "mcp_servers.json")

    if not os.path.isfile(config_path):
        logger.info("MCP config not found at %s — no MCP servers configured", config_path)
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("MCP config: invalid JSON in %s: %s", config_path, exc)
        return {}
    except Exception as exc:
        logger.error("MCP config: failed to read %s: %s", config_path, exc)
        return {}

    if not isinstance(raw, dict):
        logger.error("MCP config: expected JSON object at top level")
        return {}

    servers = {}
    for server_id, cfg in raw.items():
        if not isinstance(cfg, dict):
            logger.warning("MCP config: skipping '%s' — expected object", server_id)
            continue

        command_str = cfg.get("command", "").strip()
        if not command_str:
            logger.warning("MCP config: skipping '%s' — no command", server_id)
            continue

        # Parse command string into list
        # Handle quoted args if needed, but simple split works for most cases
        command = command_str.split()

        # Resolve environment variables
        env = _resolve_env_dict(cfg.get("env", {}))

        # Filter out empty env values (unresolved vars)
        env = {k: v for k, v in env.items() if v}

        enabled = cfg.get("enabled", False)

        servers[server_id] = {
            "command": command,
            "env": env,
            "enabled": enabled,
        }

        status = "enabled" if enabled else "disabled"
        logger.info("MCP config: loaded '%s' [%s] — %s",
                     server_id, status, command_str)

    logger.info("MCP config: %d servers loaded, %d enabled",
                len(servers), sum(1 for s in servers.values() if s["enabled"]))

    return servers


def save_config(config: dict, config_path: Optional[str] = None) -> None:
    """Write MCP server configuration back to mcp_servers.json.

    Accepts the same format returned by load_config() — converts back to
    the user-friendly JSON format with command strings.
    """
    if not config_path:
        from helm.paths import PROJECT_ROOT
        config_path = str(PROJECT_ROOT / "mcp_servers.json")

    # Read existing raw config to preserve original env var references
    raw = {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        pass

    # Update enabled flags
    for server_id, cfg in config.items():
        if server_id in raw:
            raw[server_id]["enabled"] = cfg.get("enabled", False)

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
            f.write("\n")
        logger.info("MCP config: saved to %s", config_path)
    except Exception as exc:
        logger.error("MCP config: failed to save %s: %s", config_path, exc)
