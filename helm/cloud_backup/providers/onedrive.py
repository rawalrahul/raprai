"""
helm/cloud_backup/providers/onedrive.py — OneDrive backup provider for RAPR AI.

Implements Microsoft Graph API integration for cloud backup using OAuth 2.0.
Tokens are stored securely in the token vault.
"""

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from helm.config import logger
from helm.token_vault import store_token, load_token, delete_token
from .base import BackupProvider


class OneDriveBackupProvider(BackupProvider):
    """OneDrive backup provider using Microsoft Graph API."""

    name = "onedrive"

    OAUTH_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    OAUTH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    SCOPES = "Files.ReadWrite.All offline_access"

    VAULT_KEY = "BACKUP_ONEDRIVE_TOKEN"

    # No bundled OAuth app: register your own and set the credentials via
    # env vars or the Settings UI (token vault).
    _DEFAULT_CLIENT_ID = ""
    _DEFAULT_CLIENT_SECRET = ""

    def __init__(self):
        # Priority: env var → token vault
        self.client_id = os.getenv("BACKUP_ONEDRIVE_CLIENT_ID", "")
        self.client_secret = os.getenv("BACKUP_ONEDRIVE_CLIENT_SECRET", "")
        if not self.client_id or not self.client_secret:
            try:
                from helm.token_vault import load_token
                self.client_id = self.client_id or load_token("BACKUP_ONEDRIVE_CLIENT_ID")
                self.client_secret = self.client_secret or load_token("BACKUP_ONEDRIVE_CLIENT_SECRET")
            except Exception:
                pass
        # Fall back to (empty) defaults
        self.client_id = self.client_id or self._DEFAULT_CLIENT_ID
        self.client_secret = self.client_secret or self._DEFAULT_CLIENT_SECRET
        self._token_data: Optional[dict] = None

    # ── Token helpers ────────────────────────────────────────────────────

    def _get_token_data(self) -> Optional[dict]:
        if self._token_data is not None:
            return self._token_data
        raw = load_token(self.VAULT_KEY)
        if not raw:
            return None
        try:
            self._token_data = json.loads(raw) if isinstance(raw, str) else raw
            return self._token_data
        except (json.JSONDecodeError, TypeError):
            logger.warning("cloud_backup[onedrive]: invalid token JSON")
            return None

    def _save_token_data(self, data: dict):
        try:
            store_token(self.VAULT_KEY, json.dumps(data))
            self._token_data = data
        except Exception as e:
            logger.error("cloud_backup[onedrive]: failed to save token: %s", e)

    def _get_access_token(self) -> Optional[str]:
        td = self._get_token_data()
        if not td:
            return None
        expires_at = td.get("expires_at", 0)
        if expires_at and time.time() >= (expires_at - 300):
            if not self._refresh_token():
                return None
            td = self._get_token_data()
        return td.get("access_token") if td else None

    def _refresh_token(self) -> bool:
        td = self._get_token_data()
        if not td or not td.get("refresh_token"):
            return False
        try:
            payload = urllib.parse.urlencode({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": td["refresh_token"],
                "grant_type": "refresh_token",
            }).encode()
            req = urllib.request.Request(self.OAUTH_TOKEN_URL, data=payload,
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                new = json.loads(resp.read().decode())
            td["access_token"] = new["access_token"]
            td["expires_at"] = time.time() + new.get("expires_in", 3600)
            if new.get("refresh_token"):
                td["refresh_token"] = new["refresh_token"]
            self._save_token_data(td)
            return True
        except Exception as e:
            logger.error("cloud_backup[onedrive]: token refresh failed: %s", e)
            return False

    def _auth_headers(self) -> dict:
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}"} if token else {}

    # ── Base class interface ─────────────────────────────────────────────

    async def is_connected(self) -> bool:
        td = self._get_token_data()
        if not td or not td.get("access_token"):
            return False
        expires_at = td.get("expires_at", 0)
        if expires_at and time.time() >= expires_at:
            return self._refresh_token()
        return True

    def get_oauth_url(self, redirect_uri: str, state: str) -> Optional[str]:
        if not self.client_id:
            logger.error("cloud_backup[onedrive]: BACKUP_ONEDRIVE_CLIENT_ID not set")
            return None
        params = {
            "client_id": self.client_id,
            "scope": self.SCOPES,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            "state": state,
        }
        return f"{self.OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def handle_oauth_callback(self, code: str, redirect_uri: str) -> dict:
        if not self.client_id or not self.client_secret:
            return {"ok": False, "error": "BACKUP_ONEDRIVE_CLIENT_ID or SECRET not set"}
        try:
            payload = urllib.parse.urlencode({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }).encode()
            req = urllib.request.Request(self.OAUTH_TOKEN_URL, data=payload,
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            token_info = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_at": time.time() + data.get("expires_in", 3600),
            }
            self._save_token_data(token_info)
            logger.info("cloud_backup[onedrive]: OAuth successful, token stored")
            return {"ok": True, "error": None}

        except urllib.error.HTTPError as e:
            err = e.read().decode()
            logger.error("cloud_backup[onedrive]: OAuth exchange failed: %s", err)
            return {"ok": False, "error": err}
        except Exception as e:
            logger.error("cloud_backup[onedrive]: OAuth error: %s", e)
            return {"ok": False, "error": str(e)}

    async def disconnect(self) -> dict:
        try:
            delete_token(self.VAULT_KEY)
            self._token_data = None
            logger.info("cloud_backup[onedrive]: credentials removed")
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def upload(self, file_path: Path, remote_folder: str, filename: str) -> dict:
        if not await self.is_connected():
            return {"ok": False, "remote_id": "", "error": "Not connected to OneDrive"}
        if not file_path.exists():
            return {"ok": False, "remote_id": "", "error": f"File not found: {file_path}"}

        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"ok": False, "remote_id": "", "error": "No valid access token"}

            # Ensure backup folder exists
            folder_name = remote_folder.strip("/") or "RAPR-Backups"
            folder_id = self._ensure_folder(folder_name)
            if not folder_id:
                return {"ok": False, "remote_id": "", "error": "Failed to create backup folder"}

            file_size = file_path.stat().st_size

            if file_size < 4 * 1024 * 1024:
                # Simple upload for small files
                result = self._simple_upload(folder_id, filename, file_path, access_token)
            else:
                # Resumable upload for larger files
                result = self._resumable_upload(folder_id, filename, file_path, access_token)

            return result

        except Exception as e:
            logger.error("cloud_backup[onedrive]: upload error: %s", e)
            return {"ok": False, "remote_id": "", "error": str(e)}

    async def list_backups(self, remote_folder: str) -> list[dict]:
        if not await self.is_connected():
            return []
        try:
            access_token = self._get_access_token()
            if not access_token:
                return []

            folder_name = remote_folder.strip("/") or "RAPR-Backups"
            folder_id = self._find_folder(folder_name)
            if not folder_id:
                return []

            url = f"{self.GRAPH_API_URL}/me/drive/items/{folder_id}/children?$top=200"
            req = urllib.request.Request(url, headers=self._auth_headers())
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            return [
                {
                    "id": item["id"],
                    "name": item.get("name"),
                    "size": item.get("size", 0),
                    "created_at": item.get("createdDateTime"),
                }
                for item in data.get("value", [])
                if "file" in item and item.get("name", "").startswith("raprai_backup_")
            ]
        except Exception as e:
            logger.warning("cloud_backup[onedrive]: list error: %s", e)
            return []

    async def download(self, remote_id: str, dest_path: Path) -> dict:
        if not await self.is_connected():
            return {"ok": False, "path": "", "error": "Not connected"}
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"ok": False, "path": "", "error": "No valid token"}

            url = f"{self.GRAPH_API_URL}/me/drive/items/{remote_id}/content"
            req = urllib.request.Request(url, headers=self._auth_headers())
            with urllib.request.urlopen(req, timeout=300) as resp:
                content = resp.read()

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(content)

            return {"ok": True, "path": str(dest_path), "error": None}
        except Exception as e:
            logger.error("cloud_backup[onedrive]: download error: %s", e)
            return {"ok": False, "path": "", "error": str(e)}

    async def delete(self, remote_id: str) -> dict:
        if not await self.is_connected():
            return {"ok": False, "error": "Not connected"}
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"ok": False, "error": "No valid token"}

            url = f"{self.GRAPH_API_URL}/me/drive/items/{remote_id}"
            req = urllib.request.Request(url, method="DELETE", headers=self._auth_headers())
            with urllib.request.urlopen(req, timeout=10):
                pass

            return {"ok": True, "error": None}
        except Exception as e:
            logger.error("cloud_backup[onedrive]: delete error: %s", e)
            return {"ok": False, "error": str(e)}

    # ── Private helpers ──────────────────────────────────────────────────

    def _find_folder(self, name: str) -> Optional[str]:
        """Find folder by name in OneDrive root."""
        try:
            url = (
                f"{self.GRAPH_API_URL}/me/drive/root/children"
                f"?$filter=name eq '{name}' and folder ne null"
            )
            req = urllib.request.Request(url, headers=self._auth_headers())
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            items = data.get("value", [])
            return items[0]["id"] if items else None
        except Exception as e:
            logger.debug("cloud_backup[onedrive]: find folder failed: %s", e)
            return None

    def _ensure_folder(self, name: str) -> Optional[str]:
        """Get or create backup folder in OneDrive root."""
        fid = self._find_folder(name)
        if fid:
            return fid
        try:
            url = f"{self.GRAPH_API_URL}/me/drive/root/children"
            payload = json.dumps({"name": name, "folder": {}}).encode()
            req = urllib.request.Request(url, data=payload, method="POST",
                                         headers={**self._auth_headers(), "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            return data.get("id")
        except Exception as e:
            logger.error("cloud_backup[onedrive]: create folder failed: %s", e)
            return None

    def _simple_upload(self, folder_id: str, filename: str, file_path: Path, token: str) -> dict:
        """Simple upload for files < 4 MB."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            url = f"{self.GRAPH_API_URL}/me/drive/items/{folder_id}:/{filename}:/content"
            req = urllib.request.Request(url, data=content, method="PUT",
                                         headers={"Authorization": f"Bearer {token}",
                                                  "Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            logger.info("cloud_backup[onedrive]: uploaded %s", filename)
            return {"ok": True, "remote_id": data.get("id", ""), "error": None}
        except Exception as e:
            logger.error("cloud_backup[onedrive]: simple upload failed: %s", e)
            return {"ok": False, "remote_id": "", "error": str(e)}

    def _resumable_upload(self, folder_id: str, filename: str, file_path: Path, token: str) -> dict:
        """Resumable upload session for larger files."""
        try:
            # Create upload session
            url = f"{self.GRAPH_API_URL}/me/drive/items/{folder_id}:/{filename}:/createUploadSession"
            payload = json.dumps({"item": {"name": filename}}).encode()
            req = urllib.request.Request(url, data=payload, method="POST",
                                         headers={"Authorization": f"Bearer {token}",
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                session = json.loads(resp.read().decode())

            upload_url = session.get("uploadUrl")
            if not upload_url:
                return {"ok": False, "remote_id": "", "error": "No upload URL in session"}

            file_size = file_path.stat().st_size
            chunk_size = 5 * 1024 * 1024  # 5 MB

            with open(file_path, "rb") as f:
                pos = 0
                last_data = None
                while pos < file_size:
                    chunk = f.read(chunk_size)
                    end = min(pos + len(chunk), file_size)
                    headers = {
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {pos}-{end - 1}/{file_size}",
                    }
                    req = urllib.request.Request(upload_url, data=chunk, method="PUT", headers=headers)
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        last_data = json.loads(resp.read().decode())
                    pos = end

            file_id = last_data.get("id", "") if last_data else ""
            logger.info("cloud_backup[onedrive]: uploaded %s (resumable)", filename)
            return {"ok": True, "remote_id": file_id, "error": None}

        except Exception as e:
            logger.error("cloud_backup[onedrive]: resumable upload failed: %s", e)
            return {"ok": False, "remote_id": "", "error": str(e)}
