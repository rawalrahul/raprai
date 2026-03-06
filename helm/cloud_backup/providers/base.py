"""
helm/cloud_backup/providers/base.py — Abstract base class for backup providers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BackupProvider(ABC):
    """Abstract base for cloud backup providers."""

    name: str = "unknown"

    @abstractmethod
    async def is_connected(self) -> bool:
        """Return True if valid credentials exist for this provider."""

    @abstractmethod
    async def upload(self, file_path: Path, remote_folder: str, filename: str) -> dict:
        """
        Upload a backup file to cloud storage.

        Returns: {ok: bool, remote_id: str, error: str|None}
        """

    @abstractmethod
    async def list_backups(self, remote_folder: str) -> list[dict]:
        """
        List existing backups in the remote folder.

        Returns: [{id, name, size, created_at}]
        """

    @abstractmethod
    async def download(self, remote_id: str, dest_path: Path) -> dict:
        """
        Download a backup file.

        Returns: {ok: bool, path: str, error: str|None}
        """

    @abstractmethod
    async def delete(self, remote_id: str) -> dict:
        """
        Delete a backup from cloud storage.

        Returns: {ok: bool, error: str|None}
        """

    def get_oauth_url(self, redirect_uri: str, state: str) -> Optional[str]:
        """Return OAuth authorization URL, or None if not needed (e.g., local)."""
        return None

    async def handle_oauth_callback(self, code: str, redirect_uri: str) -> dict:
        """
        Exchange auth code for tokens.

        Returns: {ok: bool, error: str|None}
        """
        return {"ok": False, "error": "OAuth not supported by this provider"}

    async def disconnect(self) -> dict:
        """Remove stored credentials."""
        return {"ok": True}
