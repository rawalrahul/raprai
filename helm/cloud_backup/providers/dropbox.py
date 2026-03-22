"""
helm/cloud_backup/providers/dropbox.py — Dropbox backup provider for RAPR AI.

Implements cloud backup to Dropbox using OAuth 2.0 and Dropbox HTTP API v2.
Tokens are stored securely in the token vault with automatic refresh handling.
"""

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from helm.config import logger
from helm.token_vault import store_token, load_token, delete_token
from .base import BackupProvider


class DropboxBackupProvider(BackupProvider):
    """Cloud backup provider for Dropbox."""

    name = "dropbox"

    # OAuth endpoints
    OAUTH_AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    OAUTH_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"

    # API endpoints
    API_BASE_URL = "https://api.dropboxapi.com"
    CONTENT_BASE_URL = "https://content.dropboxapi.com"

    # Token vault key for Dropbox
    VAULT_KEY = "BACKUP_DROPBOX_TOKEN"

    # Bundled OAuth app credentials (registered by RAPR AI developer).
    # Users can override via env vars or the Settings UI (token vault).
    _DEFAULT_APP_KEY = "REDACTED"
    _DEFAULT_APP_SECRET = "REDACTED"

    def __init__(self):
        """Initialize the Dropbox provider."""
        # Priority: env var → token vault → bundled default
        self.app_key = os.environ.get("BACKUP_DROPBOX_APP_KEY", "")
        self.app_secret = os.environ.get("BACKUP_DROPBOX_APP_SECRET", "")
        if not self.app_key or not self.app_secret:
            try:
                from helm.token_vault import load_token
                self.app_key = self.app_key or load_token("BACKUP_DROPBOX_APP_KEY")
                self.app_secret = self.app_secret or load_token("BACKUP_DROPBOX_APP_SECRET")
            except Exception:
                pass
        # Fall back to bundled defaults
        self.app_key = self.app_key or self._DEFAULT_APP_KEY
        self.app_secret = self.app_secret or self._DEFAULT_APP_SECRET
        self._token_data: Optional[dict] = None

    def _get_token_data(self) -> Optional[dict]:
        """Load and parse the stored token data."""
        if self._token_data is not None:
            return self._token_data

        token_json = load_token(self.VAULT_KEY)
        if not token_json:
            return None

        try:
            self._token_data = json.loads(token_json)
            return self._token_data
        except json.JSONDecodeError:
            logger.warning("cloud_backup[dropbox]: invalid token JSON in vault")
            return None

    def _save_token_data(self, token_data: dict) -> None:
        """Save token data to the vault."""
        try:
            token_json = json.dumps(token_data)
            store_token(self.VAULT_KEY, token_json)
            self._token_data = token_data
        except Exception as e:
            logger.error("cloud_backup[dropbox]: failed to save token: %s", e)

    async def is_connected(self) -> bool:
        """Check if a valid Dropbox token exists."""
        token_data = self._get_token_data()
        if not token_data:
            return False

        access_token = token_data.get("access_token", "")
        if not access_token:
            return False

        # If token is expired, try to refresh it
        expires_at = token_data.get("expires_at", 0)
        if expires_at and time.time() >= expires_at:
            try:
                await self._refresh_token()
            except Exception as e:
                logger.warning("cloud_backup[dropbox]: token refresh failed: %s", e)
                return False

        return True

    async def upload(self, file_path: Path, remote_folder: str, filename: str) -> dict:
        """
        Upload a backup file to Dropbox.

        Args:
            file_path: Local path to the backup ZIP file
            remote_folder: Dropbox folder path (e.g., "/raprai_backups")
            filename: Name to save the file as

        Returns:
            {ok: bool, remote_id: str, error: str|None}
        """
        if not await self.is_connected():
            return {"ok": False, "remote_id": "", "error": "Not connected to Dropbox"}

        if not file_path.exists():
            return {"ok": False, "remote_id": "", "error": f"File not found: {file_path}"}

        try:
            token_data = self._get_token_data()
            access_token = token_data.get("access_token", "")

            # Construct the remote path
            remote_path = f"{remote_folder}/{filename}".rstrip("/")

            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Prepare the request
            url = f"{self.CONTENT_BASE_URL}/2/files/upload"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/octet-stream",
                "Dropbox-API-Arg": json.dumps({
                    "path": remote_path,
                    "mode": "add",
                    "autorename": False,
                    "mute": False
                })
            }

            request = urllib.request.Request(url, data=file_content, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=300) as response:
                resp_data = json.loads(response.read().decode("utf-8"))

            logger.info("cloud_backup[dropbox]: uploaded %s to %s", filename, remote_path)
            return {
                "ok": True,
                "remote_id": resp_data.get("id", remote_path),
                "error": None
            }

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("error_summary", error_msg)
            except Exception:
                pass
            logger.error("cloud_backup[dropbox]: upload failed: %s", error_msg)
            return {"ok": False, "remote_id": "", "error": error_msg}

        except Exception as e:
            logger.error("cloud_backup[dropbox]: upload error: %s", e)
            return {"ok": False, "remote_id": "", "error": str(e)}

    async def list_backups(self, remote_folder: str) -> list[dict]:
        """
        List backup files in a Dropbox folder.

        Args:
            remote_folder: Dropbox folder path (e.g., "/raprai_backups")

        Returns:
            [{id, name, size, created_at}]
        """
        if not await self.is_connected():
            return []

        try:
            token_data = self._get_token_data()
            access_token = token_data.get("access_token", "")

            url = f"{self.API_BASE_URL}/2/files/list_folder"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            payload = json.dumps({
                "path": remote_folder,
                "recursive": False,
                "include_media_info": False,
                "include_deleted": False,
                "include_has_explicit_shared_members": False
            })

            request = urllib.request.Request(url, data=payload.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                resp_data = json.loads(response.read().decode("utf-8"))

            backups = []
            for entry in resp_data.get("entries", []):
                if entry[".tag"] != "file":
                    continue

                # Only list backup files
                if not entry["name"].startswith("raprai_backup_") or not entry["name"].endswith(".zip"):
                    continue

                backups.append({
                    "id": entry["id"],
                    "name": entry["name"],
                    "size": entry["size"],
                    "created_at": entry["server_modified"]
                })

            # Sort by creation time, newest first
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            logger.info("cloud_backup[dropbox]: listed %d backups", len(backups))
            return backups

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("error_summary", error_msg)
            except Exception:
                pass
            logger.warning("cloud_backup[dropbox]: list failed: %s", error_msg)
            return []

        except Exception as e:
            logger.warning("cloud_backup[dropbox]: list error: %s", e)
            return []

    async def download(self, remote_id: str, dest_path: Path) -> dict:
        """
        Download a backup file from Dropbox.

        Args:
            remote_id: Dropbox file ID
            dest_path: Local destination path

        Returns:
            {ok: bool, path: str, error: str|None}
        """
        if not await self.is_connected():
            return {"ok": False, "path": "", "error": "Not connected to Dropbox"}

        try:
            token_data = self._get_token_data()
            access_token = token_data.get("access_token", "")

            url = f"{self.CONTENT_BASE_URL}/2/files/download"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Dropbox-API-Arg": json.dumps({"path": remote_id})
            }

            request = urllib.request.Request(url, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=300) as response:
                file_content = response.read()

            # Write to destination
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(file_content)

            logger.info("cloud_backup[dropbox]: downloaded %s to %s", remote_id, dest_path)
            return {"ok": True, "path": str(dest_path), "error": None}

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("error_summary", error_msg)
            except Exception:
                pass
            logger.error("cloud_backup[dropbox]: download failed: %s", error_msg)
            return {"ok": False, "path": "", "error": error_msg}

        except Exception as e:
            logger.error("cloud_backup[dropbox]: download error: %s", e)
            return {"ok": False, "path": "", "error": str(e)}

    async def delete(self, remote_id: str) -> dict:
        """
        Delete a backup file from Dropbox.

        Args:
            remote_id: Dropbox file ID

        Returns:
            {ok: bool, error: str|None}
        """
        if not await self.is_connected():
            return {"ok": False, "error": "Not connected to Dropbox"}

        try:
            token_data = self._get_token_data()
            access_token = token_data.get("access_token", "")

            url = f"{self.API_BASE_URL}/2/files/delete_v2"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            payload = json.dumps({"path": remote_id})

            request = urllib.request.Request(url, data=payload.encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()

            logger.info("cloud_backup[dropbox]: deleted %s", remote_id)
            return {"ok": True, "error": None}

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("error_summary", error_msg)
            except Exception:
                pass
            logger.error("cloud_backup[dropbox]: delete failed: %s", error_msg)
            return {"ok": False, "error": error_msg}

        except Exception as e:
            logger.error("cloud_backup[dropbox]: delete error: %s", e)
            return {"ok": False, "error": str(e)}

    def get_oauth_url(self, redirect_uri: str, state: str) -> Optional[str]:
        """
        Build the OAuth authorization URL.

        Args:
            redirect_uri: OAuth callback URI
            state: CSRF protection state parameter

        Returns:
            Full authorization URL
        """
        if not self.app_key:
            logger.error("cloud_backup[dropbox]: BACKUP_DROPBOX_APP_KEY not set")
            return None

        params = {
            "client_id": self.app_key,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "token_access_type": "offline"
        }

        url = f"{self.OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return url

    async def handle_oauth_callback(self, code: str, redirect_uri: str) -> dict:
        """
        Exchange OAuth code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: OAuth callback URI (must match registered URI)

        Returns:
            {ok: bool, error: str|None}
        """
        if not self.app_key or not self.app_secret:
            return {
                "ok": False,
                "error": "BACKUP_DROPBOX_APP_KEY or BACKUP_DROPBOX_APP_SECRET not set"
            }

        try:
            payload = {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "client_id": self.app_key,
                "client_secret": self.app_secret
            }

            url = self.OAUTH_TOKEN_URL
            data = urllib.parse.urlencode(payload).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            request = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                resp_data = json.loads(response.read().decode("utf-8"))

            # Parse token response
            access_token = resp_data.get("access_token", "")
            refresh_token = resp_data.get("refresh_token", "")
            expires_in = resp_data.get("expires_in", 3600)

            if not access_token:
                logger.error("cloud_backup[dropbox]: no access_token in response")
                return {"ok": False, "error": "No access token in response"}

            # Calculate expiration time
            expires_at = time.time() + expires_in

            # Store token data
            token_data = {
                "access_token": access_token,
                "refresh_token": refresh_token if refresh_token else None,
                "expires_at": expires_at
            }
            self._save_token_data(token_data)

            logger.info("cloud_backup[dropbox]: OAuth successful, token stored")
            return {"ok": True, "error": None}

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("error_description", error_msg)
            except Exception:
                pass
            logger.error("cloud_backup[dropbox]: OAuth exchange failed: %s", error_msg)
            return {"ok": False, "error": error_msg}

        except Exception as e:
            logger.error("cloud_backup[dropbox]: OAuth error: %s", e)
            return {"ok": False, "error": str(e)}

    async def _refresh_token(self) -> None:
        """
        Refresh the access token using the refresh token.

        Raises:
            Exception: If refresh fails or refresh token is not available
        """
        token_data = self._get_token_data()
        if not token_data:
            raise ValueError("No token data found")

        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise ValueError("No refresh token available")

        if not self.app_key or not self.app_secret:
            raise ValueError("App key/secret not configured")

        try:
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.app_key,
                "client_secret": self.app_secret
            }

            url = self.OAUTH_TOKEN_URL
            data = urllib.parse.urlencode(payload).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            request = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=30) as response:
                resp_data = json.loads(response.read().decode("utf-8"))

            access_token = resp_data.get("access_token", "")
            new_refresh_token = resp_data.get("refresh_token")
            expires_in = resp_data.get("expires_in", 3600)

            if not access_token:
                raise ValueError("No access token in refresh response")

            expires_at = time.time() + expires_in
            token_data["access_token"] = access_token
            if new_refresh_token:
                token_data["refresh_token"] = new_refresh_token
            token_data["expires_at"] = expires_at

            self._save_token_data(token_data)
            logger.info("cloud_backup[dropbox]: token refreshed successfully")

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                body = json.loads(e.read().decode("utf-8"))
                error_msg = body.get("error_description", error_msg)
            except Exception:
                pass
            logger.error("cloud_backup[dropbox]: token refresh failed: %s", error_msg)
            raise

        except Exception as e:
            logger.error("cloud_backup[dropbox]: token refresh error: %s", e)
            raise

    async def disconnect(self) -> dict:
        """
        Remove stored Dropbox credentials.

        Returns:
            {ok: bool, error: str|None}
        """
        try:
            delete_token(self.VAULT_KEY)
            self._token_data = None
            logger.info("cloud_backup[dropbox]: credentials removed")
            return {"ok": True, "error": None}
        except Exception as e:
            logger.error("cloud_backup[dropbox]: disconnect failed: %s", e)
            return {"ok": False, "error": str(e)}
