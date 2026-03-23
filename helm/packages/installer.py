"""
helm/packages/installer.py — RAPR Packages install/uninstall orchestrator.

Routes packages to the correct type-specific installer, tracks transactions
in SQLite, and handles rollback on failure.

Public API:
    install_package(source, force=False) → dict
    uninstall_package(package_id) → dict
    list_installed() → list[dict]
    get_package_info(package_id) → dict | None
"""

import json
import pathlib
import shutil
import time
import uuid
from typing import Optional

from helm.config import logger
from helm.packages import (
    PackageType, HelmPackManifest, HelmPackError,
    InstallError, ConflictError,
)
from helm.packages.package import HelmPackage


# ---------------------------------------------------------------------------
# Transaction tracking (SQLite)
# ---------------------------------------------------------------------------

def _record_install(manifest: HelmPackManifest, install_path: str, pkg_hash: str):
    """Record a successful installation in the packages table."""
    try:
        from helm.db import get_db
        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO packages
               (id, type, name, version, description, author,
                install_path, package_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                manifest.id,
                manifest.type.value,
                manifest.name,
                manifest.version,
                manifest.description,
                manifest.author,
                install_path,
                pkg_hash,
            ),
        )
        db.commit()
    except Exception as e:
        logger.warning("Failed to record package install: %s", e)


def _record_uninstall(package_id: str):
    """Remove a package from the installed packages table."""
    try:
        from helm.db import get_db
        db = get_db()
        db.execute("DELETE FROM packages WHERE id = ?", (package_id,))
        db.commit()
    except Exception as e:
        logger.warning("Failed to record package uninstall: %s", e)


def _log_transaction(package_id: str, action: str, status: str,
                     detail: str = "", txn_id: Optional[str] = None,
                     package_type: str = "") -> str:
    """Log a package install/uninstall transaction. Returns txn_id."""
    txn_id = txn_id or uuid.uuid4().hex[:12]
    try:
        from helm.db import get_db
        db = get_db()
        db.execute(
            """INSERT INTO package_installs
               (transaction_id, package_id, package_type, operation, status, error_message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (txn_id, package_id, package_type or "unknown", action, status, detail or None),
        )
        db.commit()
    except Exception as e:
        logger.warning("Failed to log package transaction: %s", e)
    return txn_id


# ---------------------------------------------------------------------------
# Install orchestrator
# ---------------------------------------------------------------------------

def install_package(
    source: str | pathlib.Path,
    force: bool = False,
) -> dict:
    """
    Install a .raprpkg package from a file path or URL.

    Args:
        source: Path to .raprpkg file, or URL to download
        force: Overwrite existing packages

    Returns: {"ok": True, "package_id": "...", "type": "...", "txn_id": "..."}
    Raises: HelmPackError on failure
    """
    source = str(source)
    txn_id = uuid.uuid4().hex[:12]

    # Download if URL
    if source.startswith(("http://", "https://")):
        source = _download_package(source)

    source_path = pathlib.Path(source)
    if not source_path.exists():
        raise InstallError(f"Package file not found: {source}")

    # Open and validate package
    pkg = HelmPackage(source_path)
    errors = pkg.validate()
    if errors:
        raise InstallError(f"Package validation failed: {'; '.join(errors)}")

    manifest = pkg.manifest
    pkg_hash = pkg.compute_hash()
    manifest.package_hash = pkg_hash

    _log_transaction(manifest.id, "install", "started", txn_id=txn_id,
                     package_type=manifest.type.value)

    # Extract to staging directory
    from helm.paths import packages_staging_dir
    staging = packages_staging_dir() / f"{manifest.id}_{txn_id}"

    try:
        pkg.extract_to(staging)

        # Route to type-specific installer
        result = _install_by_type(manifest, staging, force)

        # Record success
        install_path = result.get("install_path", "")
        _record_install(manifest, install_path, pkg_hash)
        _log_transaction(manifest.id, "install", "success", txn_id=txn_id,
                         package_type=manifest.type.value)

        logger.info(
            "RAPR Packages: installed %s (%s v%s) → %s",
            manifest.id, manifest.type.value, manifest.version, install_path,
        )

        return {
            "ok": True,
            "package_id": manifest.id,
            "name": manifest.name,
            "type": manifest.type.value,
            "version": manifest.version,
            "txn_id": txn_id,
            **result,
        }

    except HelmPackError as e:
        _log_transaction(manifest.id, "install", "failed", str(e), txn_id,
                         package_type=manifest.type.value)
        raise
    except Exception as e:
        _log_transaction(manifest.id, "install", "failed", str(e), txn_id,
                         package_type=manifest.type.value)
        raise InstallError(f"Installation failed: {e}") from e
    finally:
        # Clean up staging
        if staging.exists():
            try:
                shutil.rmtree(str(staging))
            except Exception:
                pass


def _install_by_type(
    manifest: HelmPackManifest,
    staging_dir: pathlib.Path,
    force: bool,
) -> dict:
    """Route installation to the correct type-specific handler."""
    if manifest.type == PackageType.SKILL:
        from helm.packages.skill_installer import install_skill
        return install_skill(manifest, staging_dir, force)

    elif manifest.type == PackageType.PLUGIN:
        from helm.packages.plugin_installer import install_plugin
        return install_plugin(manifest, staging_dir, force)

    elif manifest.type == PackageType.MCP:
        from helm.packages.mcp_installer import install_mcp
        return install_mcp(manifest, staging_dir, force)

    else:
        raise InstallError(f"Unknown package type: {manifest.type}")


# ---------------------------------------------------------------------------
# Uninstall orchestrator
# ---------------------------------------------------------------------------

def uninstall_package(package_id: str) -> dict:
    """
    Uninstall a package by ID.

    Looks up the package type in the DB and routes to the correct handler.

    Returns: {"ok": True, "package_id": "...", "type": "..."}
    Raises: InstallError on failure
    """
    txn_id = uuid.uuid4().hex[:12]

    # Look up package info
    info = get_package_info(package_id)
    if not info:
        return {"ok": True, "message": f"Package '{package_id}' not found (already removed)"}

    pkg_type = info.get("type", "")
    _log_transaction(package_id, "uninstall", "started", txn_id=txn_id,
                     package_type=pkg_type)

    try:
        if pkg_type == "skill":
            from helm.packages.skill_installer import uninstall_skill
            result = uninstall_skill(package_id)

        elif pkg_type == "plugin":
            from helm.packages.plugin_installer import uninstall_plugin
            result = uninstall_plugin(package_id)

        elif pkg_type == "mcp":
            from helm.packages.mcp_installer import uninstall_mcp
            result = uninstall_mcp(package_id)

        else:
            raise InstallError(f"Unknown package type: {pkg_type}")

        _record_uninstall(package_id)
        _log_transaction(package_id, "uninstall", "success", txn_id=txn_id,
                         package_type=pkg_type)

        logger.info("RAPR Packages: uninstalled %s (%s)", package_id, pkg_type)

        return {
            "ok": True,
            "package_id": package_id,
            "type": pkg_type,
            "txn_id": txn_id,
            **result,
        }

    except HelmPackError as e:
        _log_transaction(package_id, "uninstall", "failed", str(e), txn_id,
                         package_type=pkg_type)
        raise
    except Exception as e:
        _log_transaction(package_id, "uninstall", "failed", str(e), txn_id,
                         package_type=pkg_type)
        raise InstallError(f"Uninstall failed: {e}") from e


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_installed() -> list[dict]:
    """Return all installed packages."""
    try:
        from helm.db import get_db
        db = get_db()
        rows = db.execute(
            """SELECT id, type, name, version, description, author,
                      install_path, package_hash, installed_at
               FROM packages ORDER BY name"""
        ).fetchall()
        return [
            {
                "id": r["id"],
                "type": r["type"],
                "name": r["name"],
                "version": r["version"],
                "description": r["description"],
                "author": r["author"],
                "install_path": r["install_path"],
                "installed_at": r["installed_at"],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Failed to list installed packages: %s", e)
        return []


def get_package_info(package_id: str) -> Optional[dict]:
    """Return info for a specific installed package, or None."""
    try:
        from helm.db import get_db
        db = get_db()
        row = db.execute(
            "SELECT * FROM packages WHERE id = ?", (package_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "type": row["type"],
            "name": row["name"],
            "version": row["version"],
            "description": row["description"],
            "author": row["author"],
            "install_path": row["install_path"],
            "package_hash": row["package_hash"],
            "installed_at": row["installed_at"],
        }
    except Exception as e:
        logger.warning("Failed to get package info: %s", e)
        return None


def get_install_history(limit: int = 50) -> list[dict]:
    """Return recent install/uninstall transactions."""
    try:
        from helm.db import get_db
        db = get_db()
        rows = db.execute(
            """SELECT transaction_id, package_id, package_type, operation,
                      status, started_at, error_message
               FROM package_installs
               ORDER BY started_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("Failed to get install history: %s", e)
        return []


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download_package(url: str) -> str:
    """Download a .raprpkg file from a URL. Returns local path."""
    import requests

    from helm.paths import packages_cache_dir
    cache = packages_cache_dir()

    # Generate filename from URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    filename = pathlib.Path(parsed.path).name
    if not filename.endswith(".raprpkg"):
        filename = f"download_{uuid.uuid4().hex[:8]}.raprpkg"

    dest = cache / filename

    try:
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()

        # Size check (50MB limit)
        content_length = int(resp.headers.get("content-length", 0))
        if content_length > 50 * 1024 * 1024:
            raise InstallError(f"Package too large: {content_length} bytes (max 50MB)")

        with open(str(dest), "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("RAPR Packages: downloaded %s → %s", url, dest)
        return str(dest)

    except InstallError:
        raise
    except Exception as e:
        raise InstallError(f"Failed to download package from {url}: {e}") from e
