"""
helm/updater.py — Auto-update manager for RAPR AI.

Checks for new versions via the raprai.com API, downloads the installer,
and applies the update silently (or directs the user to download manually).

Public API:
    check_for_app_update(force=False) → dict | None
    download_update(url, on_progress=None) → Path
    apply_update(installer_path) → None  (kills current process)
    get_update_status() → dict
"""

import os
import subprocess
import sys
import tempfile
import time
import threading
from pathlib import Path
from typing import Optional, Callable

from helm.config import logger
from helm.version import APP_VERSION

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Primary: raprai.com API (fetches from GitHub releases)
_VERSION_API_URL = os.environ.get(
    "RAPR_VERSION_URL",
    "https://raprai.com/api/version",
)

# Fallback: direct GitHub API
_GITHUB_RELEASES_URL = "https://api.github.com/repos/rawalrahul/rapr-releases/releases?per_page=1"

# How often to auto-check (4 hours)
_AUTO_CHECK_INTERVAL = 4 * 60 * 60

# In-memory state
_cached_update: Optional[dict] = None
_last_check_at: float = 0.0
_download_progress: dict = {"status": "idle", "percent": 0, "bytes_downloaded": 0, "total_bytes": 0, "path": ""}


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple:
    """Parse semver string like '2.0.0' into comparable tuple."""
    import re
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v or "")
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


# ---------------------------------------------------------------------------
# Check for updates
# ---------------------------------------------------------------------------

def check_for_app_update(force: bool = False) -> Optional[dict]:
    """
    Check if a new version of RAPR AI is available.

    Returns a dict with update info if available, None otherwise:
        {
            "current_version": "2.0.0",
            "latest_version": "2.1.0",
            "download_url": "https://...",
            "release_notes": "...",
            "release_date": "2026-03-21",
            "file_size": "~200 MB",
        }
    """
    global _cached_update, _last_check_at
    import requests

    now = time.time()

    # Return cached result if fresh
    if not force and _cached_update is not None and (now - _last_check_at) < _AUTO_CHECK_INTERVAL:
        return _cached_update if _cached_update.get("update_available") else None

    _last_check_at = now

    # Try raprai.com API first
    update_info = None
    try:
        resp = requests.get(_VERSION_API_URL, timeout=10, headers={
            "User-Agent": f"RAPR-AI/{APP_VERSION}",
            "Accept": "application/json",
        })
        resp.raise_for_status()
        data = resp.json()

        latest = data.get("latest_version", "")
        if latest and _is_newer(latest, APP_VERSION):
            update_info = {
                "update_available": True,
                "current_version": APP_VERSION,
                "latest_version": latest,
                "download_url": data.get("download_url", ""),
                "release_notes": data.get("release_notes", ""),
                "release_date": data.get("release_date", ""),
                "file_size": data.get("file_size", ""),
            }
            logger.info("Update available: v%s → v%s", APP_VERSION, latest)
        else:
            update_info = {"update_available": False, "current_version": APP_VERSION, "latest_version": latest or APP_VERSION}
            logger.info("App is up to date (v%s)", APP_VERSION)

    except Exception as e:
        logger.warning("Update check via raprai.com failed: %s — trying GitHub fallback", e)

        # Fallback: direct GitHub API
        try:
            resp = requests.get(_GITHUB_RELEASES_URL, timeout=10, headers={
                "User-Agent": f"RAPR-AI/{APP_VERSION}",
                "Accept": "application/vnd.github.v3+json",
            })
            resp.raise_for_status()
            releases = resp.json()
            if releases:
                release = releases[0]
                tag = release.get("tag_name", "").lstrip("v")
                if tag and _is_newer(tag, APP_VERSION):
                    # Find the .exe asset
                    download_url = ""
                    file_size = ""
                    for asset in release.get("assets", []):
                        name = asset.get("name", "")
                        if name.endswith(".exe"):
                            download_url = asset.get("browser_download_url", "")
                            size_bytes = asset.get("size", 0)
                            file_size = f"~{size_bytes // (1024 * 1024)} MB" if size_bytes else ""
                            break

                    update_info = {
                        "update_available": True,
                        "current_version": APP_VERSION,
                        "latest_version": tag,
                        "download_url": download_url,
                        "release_notes": release.get("body", ""),
                        "release_date": (release.get("published_at") or "")[:10],
                        "file_size": file_size,
                    }
                    logger.info("Update available (GitHub fallback): v%s → v%s", APP_VERSION, tag)
                else:
                    update_info = {"update_available": False, "current_version": APP_VERSION, "latest_version": tag or APP_VERSION}
        except Exception as e2:
            logger.warning("Update check via GitHub also failed: %s", e2)
            update_info = None

    _cached_update = update_info
    if update_info and update_info.get("update_available"):
        return update_info
    return None


# ---------------------------------------------------------------------------
# Download update
# ---------------------------------------------------------------------------

def download_update(
    url: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """
    Download the update installer to a temp directory.

    Args:
        url: Direct download URL for the installer .exe
        on_progress: Optional callback(bytes_downloaded, total_bytes)

    Returns: Path to the downloaded installer

    Raises: Exception on download failure
    """
    global _download_progress
    import requests

    _download_progress = {"status": "downloading", "percent": 0, "bytes_downloaded": 0, "total_bytes": 0, "path": ""}

    try:
        resp = requests.get(url, stream=True, timeout=600, headers={
            "User-Agent": f"RAPR-AI/{APP_VERSION}",
        })
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        _download_progress["total_bytes"] = total

        # Save to temp directory
        tmp_dir = Path(tempfile.gettempdir()) / "rapr_update"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Extract filename from URL or use default
        filename = url.rsplit("/", 1)[-1] if "/" in url else "RAPR_AI_Setup.exe"
        if not filename.endswith(".exe"):
            filename = "RAPR_AI_Setup.exe"

        dest = tmp_dir / filename
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):  # 256KB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    _download_progress["bytes_downloaded"] = downloaded
                    if total > 0:
                        _download_progress["percent"] = int((downloaded / total) * 100)
                    if on_progress:
                        on_progress(downloaded, total)

        _download_progress["status"] = "ready"
        _download_progress["path"] = str(dest)
        logger.info("Update downloaded to %s (%d bytes)", dest, downloaded)
        return dest

    except Exception as e:
        _download_progress["status"] = "error"
        logger.error("Update download failed: %s", e)
        raise


def download_update_async(url: str) -> None:
    """Start downloading the update in a background thread."""
    thread = threading.Thread(target=download_update, args=(url,), daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# Apply update
# ---------------------------------------------------------------------------

def apply_update(installer_path: Optional[str] = None) -> dict:
    """
    Launch the downloaded installer in silent mode and exit the current process.

    The Inno Setup installer:
    1. Kills the running web_app.exe (via [Code] section)
    2. Overwrites files in-place (same AppId = upgrade, not fresh install)
    3. Optionally relaunches the app

    Args:
        installer_path: Path to the .exe installer. If None, uses the
                        path from the last download.

    Returns: dict with status (should not actually return — process exits)
    """
    if not installer_path:
        installer_path = _download_progress.get("path", "")

    if not installer_path or not Path(installer_path).exists():
        return {"ok": False, "error": "No installer found. Download the update first."}

    logger.info("Launching update installer: %s", installer_path)

    try:
        # Launch installer with /SILENT flag (no UI, upgrades in-place)
        # /CLOSEAPPLICATIONS tells Inno Setup to close the running app
        # /RESTARTAPPLICATIONS tells it to relaunch after install
        subprocess.Popen(
            [
                str(installer_path),
                "/SILENT",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
                "/NORESTART",  # Don't reboot the PC
            ],
            creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
        )

        logger.info("Update installer launched. App will restart after update.")

        # Give the installer a moment to start, then exit
        # The installer's [Code] section will kill web_app.exe
        return {"ok": True, "message": "Update installer launched. The app will restart shortly."}

    except Exception as e:
        logger.error("Failed to launch update installer: %s", e)
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_update_status() -> dict:
    """Return current update check / download / install status."""
    return {
        "current_version": APP_VERSION,
        "update": _cached_update,
        "download": _download_progress.copy(),
        "last_check_at": _last_check_at,
    }


# ---------------------------------------------------------------------------
# Background auto-check (called from web_app.py startup)
# ---------------------------------------------------------------------------

async def auto_check_loop():
    """Background task that checks for updates periodically."""
    import asyncio

    # Wait a bit after startup before first check
    await asyncio.sleep(30)

    while True:
        try:
            # Run in thread to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, check_for_app_update)
        except Exception as e:
            logger.warning("Auto-update check error: %s", e)

        await asyncio.sleep(_AUTO_CHECK_INTERVAL)
