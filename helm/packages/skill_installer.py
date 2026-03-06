"""
helm/packages/skill_installer.py — Install/uninstall skill packages.

Skills are extracted to the primary writable skills directory and
hot-loaded via scan_skills().
"""

import pathlib
import shutil
from typing import Optional

from helm.config import logger
from helm.packages import HelmPackManifest, InstallError


def _get_skills_install_dir() -> pathlib.Path:
    """Return the primary writable skills directory."""
    from helm.paths import user_data_dir
    skills_dir = user_data_dir() / ".skills" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


def install_skill(
    manifest: HelmPackManifest,
    staging_dir: pathlib.Path,
    force: bool = False,
) -> dict:
    """
    Install a skill package from the staging directory.

    Returns: {"ok": True, "install_path": "...", "skill_name": "..."}
    Raises: InstallError on failure
    """
    skill_id = manifest.id
    install_base = _get_skills_install_dir()
    install_dir = install_base / skill_id

    # Check for conflict
    if install_dir.exists() and not force:
        # Check if it was installed by helmpack (not manually)
        existing_manifest = install_dir / "manifest.json"
        if existing_manifest.exists():
            raise InstallError(
                f"Skill '{skill_id}' already installed. Use force=True to overwrite."
            )

    # Find SKILL.md in staging directory
    skill_md = _find_skill_md(staging_dir)
    if not skill_md:
        raise InstallError("No SKILL.md found in package")

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

        # Copy SKILL.md
        dest_skill_md = install_dir / "SKILL.md"
        shutil.copy2(str(skill_md), str(dest_skill_md))

        # Copy manifest.json
        manifest_src = staging_dir / "manifest.json"
        if manifest_src.exists():
            shutil.copy2(str(manifest_src), str(install_dir / "manifest.json"))

        # Copy any additional files (scripts/, examples/, etc.)
        for item in staging_dir.iterdir():
            if item.name in ("manifest.json",) or item.name == skill_md.name:
                continue
            dest = install_dir / item.name
            if item.is_dir():
                shutil.copytree(str(item), str(dest))
            else:
                shutil.copy2(str(item), str(dest))

        # Hot-reload skill registry
        try:
            from helm.skills import scan_skills
            scan_skills()
        except Exception as e:
            logger.warning("Skill hot-reload failed: %s", e)

        # Clean up backup on success
        if backup_dir and backup_dir.exists():
            shutil.rmtree(str(backup_dir))

        return {
            "ok": True,
            "install_path": str(install_dir),
            "skill_name": skill_id,
        }

    except Exception as e:
        # Rollback
        if backup_dir and backup_dir.exists():
            if install_dir.exists():
                shutil.rmtree(str(install_dir))
            shutil.move(str(backup_dir), str(install_dir))
            try:
                from helm.skills import scan_skills
                scan_skills()
            except Exception:
                pass
        raise InstallError(f"Skill installation failed: {e}") from e


def uninstall_skill(package_id: str) -> dict:
    """Remove an installed skill and hot-reload the registry."""
    install_dir = _get_skills_install_dir() / package_id

    if not install_dir.exists():
        return {"ok": True, "message": f"Skill '{package_id}' not found (already removed)"}

    try:
        shutil.rmtree(str(install_dir))
    except Exception as e:
        raise InstallError(f"Failed to remove skill directory: {e}") from e

    # Hot-reload
    try:
        from helm.skills import scan_skills
        scan_skills()
    except Exception as e:
        logger.warning("Skill hot-reload after uninstall failed: %s", e)

    return {"ok": True, "removed": package_id}


def _find_skill_md(staging_dir: pathlib.Path) -> Optional[pathlib.Path]:
    """Find SKILL.md in the staging directory (handles nested structures)."""
    # Direct
    direct = staging_dir / "SKILL.md"
    if direct.exists():
        return direct

    # One level deep (ZIP may have a wrapper directory)
    for child in staging_dir.iterdir():
        if child.is_dir():
            nested = child / "SKILL.md"
            if nested.exists():
                return nested

    # Case-insensitive fallback
    for f in staging_dir.rglob("*"):
        if f.name.lower() == "skill.md":
            return f

    return None
