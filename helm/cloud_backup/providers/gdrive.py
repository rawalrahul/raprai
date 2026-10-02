"""
helm/cloud_backup/providers/gdrive.py — Google Drive backup provider for RAPR AI.

Implements OAuth 2.0 authentication and file operations using Google Drive API v3.
Tokens are stored securely in the token vault.
"""

import json
import os
import time
import uuid
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from helm.config import logger
from helm.token_vault import store_token, load_token, delete_token
from .base import BackupProvider


class GDriveBackupProvider(BackupProvider):
    """Google Drive backup provider using OAuth 2.0 and Drive API v3."""

    name = "gdrive"

    # OAuth 2.0 endpoints
    OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    OAUTH_SCOPE = "https://www.googleapis.com/auth/drive.file"

    # Google Drive API endpoints
    API_BASE_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

    VAULT_KEY = "BACKUP_GDRIVE_TOKEN"

    # No bundled OAuth app: register your own and set the credentials via
    # env vars or the Settings UI (token vault).
    _DEFAULT_CLIENT_ID = ""
    _DEFAULT_CLIENT_SECRET = ""

    def __init__(self):
        # Priority: env var → token vault
        self.client_id = os.getenv("BACKUP_GDRIVE_CLIENT_ID", "")
        self.client_secret = os.getenv("BACKUP_GDRIVE_CLIENT_SECRET", "")
        if not self.client_id or not self.client_secret:
            try:
                from helm.token_vault import load_token
                self.client_id = self.client_id or load_token("BACKUP_GDRIVE_CLIENT_ID")
                self.client_secret = self.client_secret or load_token("BACKUP_GDRIVE_CLIENT_SECRET")
            except Exception:
                pass
        # Fall back to (empty) defaults
        self.client_id = self.client_id or self._DEFAULT_CLIENT_ID
        self.client_secret = self.client_secret or self._DEFAULT_CLIENT_SECRET
        self._token_data: Optional[dict] = None
        self._folder_id: Optional[str] = None

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
            logger.warning("cloud_backup[gdrive]: invalid token JSON")
            return None

    def _save_token_data(self, data: dict):
        try:
            store_token(self.VAULT_KEY, json.dumps(data))
            self._token_data = data
        except Exception as e:
            logger.error("cloud_backup[gdrive]: failed to save token: %s", e)

    def _get_access_token(self) -> Optional[str]:
        """Return a valid access token, refreshing if needed."""
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
            expires_in = new.get("expires_in", 3600)
            td["access_token"] = new["access_token"]
            td["expires_at"] = time.time() + expires_in
            if new.get("refresh_token"):
                td["refresh_token"] = new["refresh_token"]
            self._save_token_data(td)
            return True
        except Exception as e:
            logger.error("cloud_backup[gdrive]: token refresh failed: %s", e)
            return False

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
            logger.error("cloud_backup[gdrive]: BACKUP_GDRIVE_CLIENT_ID not set")
            return None
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.OAUTH_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def handle_oauth_callback(self, code: str, redirect_uri: str) -> dict:
        if not self.client_id or not self.client_secret:
            return {"ok": False, "error": "BACKUP_GDRIVE_CLIENT_ID or SECRET not set"}
        try:
            payload = urllib.parse.urlencode({
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }).encode()
            req = urllib.request.Request(self.OAUTH_TOKEN_URL, data=payload,
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            expires_in = data.get("expires_in", 3600)
            token_info = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_at": time.time() + expires_in,
            }
            self._save_token_data(token_info)
            logger.info("cloud_backup[gdrive]: OAuth successful, token stored")
            return {"ok": True, "error": None}
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            logger.error("cloud_backup[gdrive]: OAuth exchange failed: %s", err)
            return {"ok": False, "error": err}
        except Exception as e:
            logger.error("cloud_backup[gdrive]: OAuth error: %s", e)
            return {"ok": False, "error": str(e)}

    async def disconnect(self) -> dict:
        try:
            delete_token(self.VAULT_KEY)
            self._token_data = None
            self._folder_id = None
            logger.info("cloud_backup[gdrive]: credentials removed")
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def upload(self, file_path: Path, remote_folder: str, filename: str) -> dict:
        if not await self.is_connected():
            return {"ok": False, "remote_id": "", "error": "Not connected to Google Drive"}
        if not file_path.exists():
            return {"ok": False, "remote_id": "", "error": f"File not found: {file_path}"}
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"ok": False, "remote_id": "", "error": "No valid access token"}

            folder_id = self._get_or_create_folder(remote_folder)
            if not folder_id:
                return {"ok": False, "remote_id": "", "error": "Failed to get/create backup folder"}

            with open(file_path, "rb") as f:
                content = f.read()

            metadata = json.dumps({
                "name": filename,
                "parents": [folder_id],
                "mimeType": "application/zip",
            })

            boundary = f"==============={uuid.uuid4().hex}=="
            body = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{metadata}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: application/zip\r\n"
                f"Content-Transfer-Encoding: binary\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

            req = urllib.request.Request(
                f"{self.UPLOAD_URL}?uploadType=multipart",
                data=body, method="POST"
            )
            req.add_header("Authorization", f"Bearer {access_token}")
            req.add_header("Content-Type", f"multipart/related; boundary={boundary}")

            with urllib.request.urlopen(req, timeout=300) as resp:
                resp_data = json.loads(resp.read().decode())

            file_id = resp_data.get("id", "")
            logger.info("cloud_backup[gdrive]: uploaded %s", filename)
            return {"ok": True, "remote_id": file_id, "error": None}

        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}: {e.reason}"
            try:
                err = json.loads(e.read().decode()).get("error", {}).get("message", err)
            except Exception:
                pass
            logger.error("cloud_backup[gdrive]: upload failed: %s", err)
            return {"ok": False, "remote_id": "", "error": err}
        except Exception as e:
            logger.error("cloud_backup[gdrive]: upload error: %s", e)
            return {"ok": False, "remote_id": "", "error": str(e)}

    async def list_backups(self, remote_folder: str) -> list[dict]:
        if not await self.is_connected():
            return []
        try:
            access_token = self._get_access_token()
            if not access_token:
                return []
            folder_id = self._get_or_create_folder(remote_folder)
            if not folder_id:
                return []

            query = f"'{folder_id}' in parents and trashed = false"
            params = {
                "q": query,
                "fields": "files(id, name, size, createdTime, modifiedTime)",
                "pageSize": 100,
                "orderBy": "modifiedTime desc",
            }
            url = f"{self.API_BASE_URL}/files?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {access_token}")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            return [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "size": int(f.get("size", 0)),
                    "created_at": f.get("createdTime"),
                }
                for f in data.get("files", [])
                if f.get("name", "").startswith("raprai_backup_")
            ]
        except Exception as e:
            logger.warning("cloud_backup[gdrive]: list error: %s", e)
            return []

    async def download(self, remote_id: str, dest_path: Path) -> dict:
        if not await self.is_connected():
            return {"ok": False, "path": "", "error": "Not connected"}
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"ok": False, "path": "", "error": "No valid token"}

            url = f"{self.API_BASE_URL}/files/{remote_id}?alt=media"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {access_token}")

            with urllib.request.urlopen(req, timeout=300) as resp:
                content = resp.read()

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(content)

            return {"ok": True, "path": str(dest_path), "error": None}
        except Exception as e:
            logger.error("cloud_backup[gdrive]: download error: %s", e)
            return {"ok": False, "path": "", "error": str(e)}

    async def delete(self, remote_id: str) -> dict:
        if not await self.is_connected():
            return {"ok": False, "error": "Not connected"}
        try:
            access_token = self._get_access_token()
            if not access_token:
                return {"ok": False, "error": "No valid token"}

            url = f"{self.API_BASE_URL}/files/{remote_id}"
            req = urllib.request.Request(url, method="DELETE")
            req.add_header("Authorization", f"Bearer {access_token}")

            with urllib.request.urlopen(req, timeout=10):
                pass

            return {"ok": True, "error": None}
        except Exception as e:
            logger.error("cloud_backup[gdrive]: delete error: %s", e)
            return {"ok": False, "error": str(e)}

    # ── Private helpers ──────────────────────────────────────────────────

    def _get_or_create_folder(self, folder_name: str = "RAPR_Backups") -> Optional[str]:
        """Get or create backup folder in Drive. Returns folder ID."""
        if self._folder_id:
            return self._folder_id

        access_token = self._get_access_token()
        if not access_token:
            return None

        # Strip leading slash for Drive folder name
        clean_name = folder_name.strip("/") or "RAPR-Backups"

        try:
            # Search for existing folder
            query = f"name = '{clean_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            params = {"q": query, "fields": "files(id)", "pageSize": 1}
            url = f"{self.API_BASE_URL}/files?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {access_token}")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            files = data.get("files", [])
            if files:
                self._folder_id = files[0]["id"]
                return self._folder_id

            # Create folder
            meta = json.dumps({
                "name": clean_name,
                "mimeType": "application/vnd.google-apps.folder",
            }).encode()
            req = urllib.request.Request(f"{self.API_BASE_URL}/files", data=meta)
            req.add_header("Authorization", f"Bearer {access_token}")
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                folder_data = json.loads(resp.read().decode())

            self._folder_id = folder_data.get("id")
            return self._folder_id

        except Exception as e:
            logger.error("cloud_backup[gdrive]: folder op failed: %s", e)
            return None
