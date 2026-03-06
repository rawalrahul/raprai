"""
helm/helmpack/mcp_installer.py — Install/uninstall MCP server packages.

MCP servers are merged into mcp_servers.json and hot-started via
MCPManager.reload_servers().
"""

import json
import pathlib
from typing import Optional

from helm.config import logger
from helm.helmpack import HelmPackManifest, InstallError


def _get_mcp_config_path() -> pathlib.Path:
    """Return path to mcp_servers.json."""
    from helm.paths import PROJECT_ROOT
    return PROJECT_ROOT / "mcp_servers.json"


def _load_mcp_config() -> dict:
    """Load existing mcp_servers.json or return empty dict."""
    path = _get_mcp_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read mcp_servers.json: %s", e)
        return {}


def _save_mcp_config(config: dict) -> None:
    """Write mcp_servers.json."""
    path = _get_mcp_config_path()
    path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def install_mcp(
    manifest: HelmPackManifest,
    staging_dir: pathlib.Path,
    force: bool = False,
) -> dict:
    """
    Install an MCP server package.

    Merges the server entry into mcp_servers.json and optionally copies
    server files (scripts, etc.) to a local directory.

    Returns: {"ok": True, "server_id": "...", "command": "..."}
    Raises: InstallError on failure
    """
    server_id = manifest.id
    mcp_cfg = manifest.mcp

    if not mcp_cfg:
        raise InstallError("Manifest missing 'mcp' configuration section")

    command = mcp_cfg.get("command")
    if not command:
        raise InstallError("MCP manifest missing 'command' field")

    # Normalize command to string for mcp_servers.json
    if isinstance(command, list):
        command_str = " ".join(str(c) for c in command)
    else:
        command_str = str(command)

    env_vars = mcp_cfg.get("env", {})

    # Load existing config
    config = _load_mcp_config()

    # Check for conflict
    if server_id in config and not force:
        raise InstallError(
            f"MCP server '{server_id}' already configured. Use force=True to overwrite."
        )

    # Backup existing config
    backup: Optional[dict] = None
    if server_id in config:
        backup = config[server_id].copy()

    try:
        # Copy any server files (scripts, etc.) to a persistent location
        server_files_dir = _get_server_files_dir(server_id)
        _copy_server_files(staging_dir, server_files_dir, manifest)

        # Resolve command path if it references a local script
        command_str = _resolve_command(command_str, server_files_dir)

        # Add/update entry in mcp_servers.json
        config[server_id] = {
            "command": command_str,
            "env": env_vars,
            "enabled": True,
            "_helmpack": {
                "package_id": manifest.id,
                "version": manifest.version,
                "name": manifest.name,
            },
        }
        _save_mcp_config(config)

        # Hot-reload MCP servers
        try:
            _reload_mcp_servers()
        except Exception as e:
            logger.warning("MCP hot-reload failed: %s", e)

        return {
            "ok": True,
            "server_id": server_id,
            "command": command_str,
        }

    except InstallError:
        raise
    except Exception as e:
        # Rollback
        if backup is not None:
            config[server_id] = backup
        else:
            config.pop(server_id, None)
        _save_mcp_config(config)
        raise InstallError(f"MCP installation failed: {e}") from e


def uninstall_mcp(package_id: str) -> dict:
    """Remove an MCP server entry and stop the running server."""
    config = _load_mcp_config()

    if package_id not in config:
        return {"ok": True, "message": f"MCP server '{package_id}' not found (already removed)"}

    # Remove from config
    config.pop(package_id)
    _save_mcp_config(config)

    # Remove server files
    server_files_dir = _get_server_files_dir(package_id)
    if server_files_dir.exists():
        import shutil
        try:
            shutil.rmtree(str(server_files_dir))
        except Exception as e:
            logger.warning("Failed to remove MCP server files: %s", e)

    # Hot-reload (will stop the removed server)
    try:
        _reload_mcp_servers()
    except Exception as e:
        logger.warning("MCP hot-reload after uninstall failed: %s", e)

    return {"ok": True, "removed": package_id}


def _get_server_files_dir(server_id: str) -> pathlib.Path:
    """Return directory for MCP server's local files."""
    from helm.paths import user_data_dir
    d = user_data_dir() / "mcp_packages" / server_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _copy_server_files(
    staging_dir: pathlib.Path,
    dest_dir: pathlib.Path,
    manifest: HelmPackManifest,
) -> None:
    """Copy server files (scripts, configs) from staging to persistent storage."""
    import shutil

    # Find the content root (might be nested one level in ZIP)
    content_root = staging_dir
    for child in staging_dir.iterdir():
        if child.is_dir() and (child / "manifest.json").exists():
            content_root = child
            break

    # Copy everything except manifest.json
    for item in content_root.iterdir():
        if item.name == "manifest.json":
            continue
        dest = dest_dir / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(str(dest))
            shutil.copytree(str(item), str(dest))
        else:
            shutil.copy2(str(item), str(dest))


def _resolve_command(command_str: str, server_files_dir: pathlib.Path) -> str:
    """If command references a local script (e.g. ./server.py), resolve to absolute path."""
    parts = command_str.split()
    if not parts:
        return command_str

    first = parts[0]
    # Check if it's a relative path that we should resolve
    if first.startswith("./") or first.startswith("../"):
        resolved = server_files_dir / first
        if resolved.exists():
            parts[0] = str(resolved.resolve())
            return " ".join(parts)

    # Check if the script exists in our server files dir
    potential = server_files_dir / first
    if potential.exists() and potential.is_file():
        parts[0] = str(potential.resolve())
        return " ".join(parts)

    return command_str


def _reload_mcp_servers():
    """Trigger MCP manager to reload configuration."""
    import asyncio
    from helm.mcp import get_manager

    manager = get_manager()

    # Use reload_servers if available (we'll add this method)
    if hasattr(manager, "reload_servers"):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(manager.reload_servers())
        finally:
            loop.close()
    else:
        # Fallback: full restart
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(manager.shutdown())
            loop.run_until_complete(manager.load_and_start())
        finally:
            loop.close()
