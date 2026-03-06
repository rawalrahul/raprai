"""
helm/cloud_backup/providers/local.py — Local folder backup provider.

Copies backup ZIPs to a user-specified local/network folder.
No OAuth or cloud API needed.
"""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from helm.config import logger
from .base import BackupProvider


class LocalBackupProvider(BackupProvider):
    name = "local"

    async def is_connected(self) -> bool:
        """Local provider is always 'connected' — just needs a valid folder path."""
        return True

    async def upload(self, file_path: Path, remote_folder: str, filename: str) -> dict:
        """Copy backup ZIP to the local folder."""
        if not remote_folder:
            return {"ok": False, "remote_id": "", "error": "No backup folder configured"}

        dest_dir = Path(remote_folder)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"ok": False, "remote_id": "", "error": f"Cannot create folder: {e}"}

        dest = dest_dir / filename
        try:
            shutil.copy2(str(file_path), str(dest))
            logger.info("cloud_backup[local]: copied %s to %s", filename, dest)
            return {"ok": True, "remote_id": str(dest), "error": None}
        except Exception as e:
            return {"ok": False, "remote_id": "", "error": str(e)}

    async def list_backups(self, remote_folder: str) -> list[dict]:
        """List .zip files in the backup folder."""
        if not remote_folder or not os.path.isdir(remote_folder):
            return []

        backups = []
        for f in sorted(Path(remote_folder).glob("raprai_backup_*.zip"), reverse=True):
            try:
                stat = f.stat()
                backups.append({
                    "id": str(f),
                    "name": f.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
            except Exception:
                continue
        return backups

    async def download(self, remote_id: str, dest_path: Path) -> dict:
        """Copy a backup from local folder to dest_path."""
        src = Path(remote_id)
        if not src.exists():
            return {"ok": False, "path": "", "error": f"File not found: {remote_id}"}
        try:
            shutil.copy2(str(src), str(dest_path))
            return {"ok": True, "path": str(dest_path), "error": None}
        except Exception as e:
            return {"ok": False, "path": "", "error": str(e)}

    async def delete(self, remote_id: str) -> dict:
        """Delete a backup file."""
        try:
            p = Path(remote_id)
            if p.exists():
                p.unlink()
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}
