"""
helm/helmpack/plugin_installer.py — Install/uninstall plugin packages.

Plugins are extracted to helm/plugins/{id}/ and hot-loaded via load_plugins().
"""

import pathlib
import shutil
from typing import Optional

from helm.config import logger
from helm.helmpack import HelmPackManifest, InstallError


def _get_plugins_install_dir() -> pathlib.Path:
    """Return the plugins directory (helm/plugins/)."""
    from helm.paths import HELM_DIR
    plugins_dir = HELM_DIR / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir


def install_plugin(
    manifest: HelmPackManifest,
    staging_dir: pathlib.Path,
    force: bool = False,
) -> dict:
    """
    Install a plugin package from the staging directory.

    Returns: {"ok": True, "install_path": "...", "plugin_id": "..."}
    Raises: InstallError on failure
    """
    plugin_id = manifest.id
    install_base = _get_plugins_install_dir()
    install_dir = install_base / plugin_id

    # Check for conflict
    if install_dir.exists() and not force:
        existing_manifest = install_dir / "manifest.json"
        if existing_manifest.exists():
            raise InstallError(
                f"Plugin '{plugin_id}' already installed. Use force=True to overwrite."
            )

    # Find manifest.json in staging directory
    staging_manifest = _find_file(staging_dir, "manifest.json")
    if not staging_manifest:
        raise InstallError("No manifest.json found in package")

    # Create backup if updating
    backup_dir: Optional[pathlib.Path] = None
    if install_dir.exists():
        backup_dir = install_dir.with_suffix(".bak")
        if backup_dir.exists():
            shutil.rmtree(str(backup_dir))
        shutil.copytree(str(install_dir), str(backup_dir))

    try:
        # Clean target and copy files
        if install_dir.exists():
            shutil.rmtree(str(install_dir))
        install_dir.mkdir(parents=True, exist_ok=True)

        # Copy manifest.json
        shutil.copy2(str(staging_manifest), str(install_dir / "manifest.json"))

        # Copy instructions.md (required for plugins to work)
        instructions = _find_file(staging_dir, "instructions.md")
        if instructions:
            shutil.copy2(str(instructions), str(install_dir / "instructions.md"))

        # Copy any additional files
        staging_root = staging_manifest.parent
        for item in staging_root.iterdir():
            dest = install_dir / item.name
            if dest.exists():
                continue  # already copied
            if item.is_dir():
                shutil.copytree(str(item), str(dest))
            else:
                shutil.copy2(str(item), str(dest))

        # Merge plugin-specific manifest fields (emoji, auth, env_vars)
        _merge_plugin_manifest(manifest, install_dir)

        # Hot-reload plugin registry
        try:
            from helm.plugins import load_plugins
            load_plugins()
        except Exception as e:
            logger.warning("Plugin hot-reload failed: %s", e)

        # Clean up backup on success
        if backup_dir and backup_dir.exists():
            shutil.rmtree(str(backup_dir))

        return {
            "ok": True,
            "install_path": str(install_dir),
            "plugin_id": plugin_id,
        }

    except Exception as e:
        # Rollback
        if backup_dir and backup_dir.exists():
            if install_dir.exists():
                shutil.rmtree(str(install_dir))
            shutil.move(str(backup_dir), str(install_dir))
            try:
                from helm.plugins import load_plugins
                load_plugins()
            except Exception:
                pass
        raise InstallError(f"Plugin installation failed: {e}") from e


def uninstall_plugin(package_id: str) -> dict:
    """Remove an installed plugin and hot-reload the registry."""
    install_dir = _get_plugins_install_dir() / package_id

    if not install_dir.exists():
        return {"ok": True, "message": f"Plugin '{package_id}' not found (already removed)"}

    try:
        shutil.rmtree(str(install_dir))
    except Exception as e:
        raise InstallError(f"Failed to remove plugin directory: {e}") from e

    # Hot-reload
    try:
        from helm.plugins import load_plugins
        load_plugins()
    except Exception as e:
        logger.warning("Plugin hot-reload after uninstall failed: %s", e)

    return {"ok": True, "removed": package_id}


def _merge_plugin_manifest(manifest: HelmPackManifest, install_dir: pathlib.Path):
    """Ensure the installed manifest.json has the helmpack metadata merged in."""
    import json
    manifest_path = install_dir / "manifest.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Ensure required fields from helmpack manifest
        data.setdefault("id", manifest.id)
        data.setdefault("name", manifest.name)
        data.setdefault("description", manifest.description)
        data.setdefault("version", manifest.version)
        if manifest.plugin:
            data.setdefault("emoji", manifest.plugin.get("emoji", "🔌"))
            data.setdefault("category", manifest.plugin.get("category", "general"))
            if "auth" in manifest.plugin:
                data.setdefault("auth", manifest.plugin["auth"])
            if "env_vars" in manifest.plugin:
                data.setdefault("env_vars", manifest.plugin["env_vars"])
        manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Failed to merge plugin manifest fields: %s", e)


def _find_file(staging_dir: pathlib.Path, filename: str) -> Optional[pathlib.Path]:
    """Find a file in the staging directory (handles nested structures)."""
    direct = staging_dir / filename
    if direct.exists():
        return direct

    # One level deep (ZIP may have a wrapper directory)
    for child in staging_dir.iterdir():
        if child.is_dir():
            nested = child / filename
            if nested.exists():
                return nested

    # Case-insensitive fallback
    for f in staging_dir.rglob("*"):
        if f.name.lower() == filename.lower():
            return f

    return None
