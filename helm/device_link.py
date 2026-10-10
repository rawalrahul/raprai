"""
helm/device_link.py — Device linking & credential sync with raprai.com.

Optional: RAPR works without it. Linking connects the app to the user's
raprai.com account (Settings → raprai.com account) so connections set up on
raprai.com sync into the app; linked apps also send usage counts (which features
are used, no chat content). Handles: activation code entry, credential sync,
usage telemetry, and unlinking.

Public API:
    get_device_token() → str | None
    set_device_token(token) → None
    activate_with_code(code) → dict
    unlink_device() → None
    sync_connections() → dict
    send_telemetry(events) → bool
    get_link_status() → dict
"""

import os
import time
import threading
from typing import Optional

from helm.config import logger
from helm.version import APP_VERSION

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_RAPRAI_BASE = os.environ.get("RAPRAI_URL", "https://raprai.com")

# Sync interval: check for new connections every 30 minutes
_SYNC_INTERVAL = 30 * 60

# Telemetry flush interval: send every 2 hours
_TELEMETRY_INTERVAL = 2 * 60 * 60

# In-memory state
_device_token: Optional[str] = None
_last_sync_at: float = 0.0
_cached_connections: dict = {}  # provider → credentials
_telemetry_buffer: list = []    # queued telemetry events


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def get_device_token() -> Optional[str]:
    """Return the stored device token, or None if not linked."""
    global _device_token
    if _device_token:
        return _device_token

    # Try loading from vault
    try:
        from helm.token_vault import get_token
        token = get_token("RAPR_DEVICE_TOKEN")
        if token and token != "vault-managed":
            _device_token = token
            return token
    except Exception:
        pass

    # Try loading from .env
    token = os.environ.get("RAPR_DEVICE_TOKEN", "")
    if token and token != "vault-managed":
        _device_token = token
        return token

    return None


def set_device_token(token: str) -> None:
    """Store the device token securely."""
    global _device_token
    _device_token = token
    os.environ["RAPR_DEVICE_TOKEN"] = token

    # Store in encrypted vault
    try:
        from helm.token_vault import store_token
        store_token("RAPR_DEVICE_TOKEN", token)
        logger.info("Device token stored in vault")
    except Exception as e:
        logger.warning("Could not store device token in vault: %s", e)

        # Fallback: store in .env
        try:
            from helm.paths import user_data_dir
            env_path = user_data_dir() / ".env"
            lines = []
            found = False
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("RAPR_DEVICE_TOKEN="):
                        lines.append(f"RAPR_DEVICE_TOKEN={token}")
                        found = True
                    else:
                        lines.append(line)
            if not found:
                lines.append(f"RAPR_DEVICE_TOKEN={token}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as e2:
            logger.error("Failed to store device token: %s", e2)


def unlink_device() -> None:
    """Forget the device token: stop syncing and stop sending usage counts."""
    global _device_token, _cached_connections
    _device_token = None
    _cached_connections = {}
    _telemetry_buffer.clear()
    os.environ.pop("RAPR_DEVICE_TOKEN", None)
    try:
        from helm.token_vault import delete_token
        delete_token("RAPR_DEVICE_TOKEN")
    except Exception as e:
        logger.warning("Could not remove device token from vault: %s", e)
    try:
        from helm.paths import user_data_dir
        env_path = user_data_dir() / ".env"
        if env_path.exists():
            lines = [l for l in env_path.read_text(encoding="utf-8").splitlines()
                     if not l.strip().startswith("RAPR_DEVICE_TOKEN=")]
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        logger.warning("Could not remove device token from .env: %s", e)
    logger.info("Device unlinked from raprai.com")


# ---------------------------------------------------------------------------
# Machine fingerprint (survives reinstalls)
# ---------------------------------------------------------------------------

def _get_machine_id() -> str:
    """Return a stable, hashed machine fingerprint that survives app reinstalls.

    On Windows: uses the SMBIOS product UUID (from ``wmic csproduct get uuid``).
    Fallback: SHA-256 of MAC address + hostname + platform info.
    The raw identifiers are hashed so we never transmit actual hardware IDs.
    """
    import hashlib
    import platform
    import subprocess
    import uuid as _uuid

    raw = ""

    # Windows: SMBIOS product UUID (most stable identifier)
    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                "wmic csproduct get uuid",
                shell=True, timeout=5, text=True,
            ).strip()
            # Output is like "UUID\nXXXXX-XXXX-..."
            lines = [ln.strip() for ln in out.splitlines() if ln.strip() and ln.strip().upper() != "UUID"]
            if lines and lines[0] not in ("", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"):
                raw = lines[0]
        except Exception:
            pass

    # Fallback: MAC + hostname + platform
    if not raw:
        mac = str(_uuid.getnode())
        host = platform.node()
        raw = f"{mac}|{host}|{platform.system()}|{platform.machine()}"

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------

def activate_with_code(code: str) -> dict:
    """
    Activate the app using a human-readable activation code.

    The code (e.g. RAPR-4X7K-M2NP) is exchanged with raprai.com for
    a device token which is then stored locally.

    Returns: {"ok": True, "token": "rapr_dev_..."} or {"ok": False, "error": "..."}
    """
    import requests

    code = code.strip().upper()
    if not code:
        return {"ok": False, "error": "Activation code is required"}

    try:
        machine_id = _get_machine_id()
        resp = requests.get(
            f"{_RAPRAI_BASE}/api/device-token",
            params={"code": code, "machine_id": machine_id},
            timeout=15,
            headers={"User-Agent": f"RAPR-AI/{APP_VERSION}"},
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success") and data.get("token"):
            set_device_token(data["token"])
            devices_used = data.get("devices_used", "?")
            devices_max = data.get("devices_max", "?")
            logger.info("App activated with code %s (%s/%s devices)", code[:9] + "...", devices_used, devices_max)

            # Immediately sync connections
            threading.Thread(target=sync_connections, daemon=True).start()

            return {
                "ok": True,
                "token": data["token"],
                "devices_used": devices_used,
                "devices_max": devices_max,
            }
        else:
            error_msg = data.get("error", "Invalid activation code")
            if data.get("limit_reached"):
                error_msg = (
                    f"This code has reached its activation limit "
                    f"({data.get('max', 2)} devices). "
                    f"Deactivate an existing device at raprai.com/dashboard/connections "
                    f"or generate a new code at raprai.com/activate."
                )
            return {"ok": False, "error": error_msg}

    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return {"ok": False, "error": "Invalid activation code. Check and try again."}
        if e.response is not None and e.response.status_code == 403:
            try:
                err_data = e.response.json()
                if err_data.get("limit_reached"):
                    return {"ok": False, "error": err_data.get("error", "Activation limit reached.")}
            except Exception:
                pass
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error("Activation failed: %s", e)
        return {"ok": False, "error": f"Connection error: {e}"}


# ---------------------------------------------------------------------------
# Credential sync
# ---------------------------------------------------------------------------

def sync_connections(force: bool = False) -> dict:
    """
    Fetch credentials from raprai.com and cache them locally.

    Returns: {"ok": True, "connections": {"supabase": {...}, ...}}
    """
    global _last_sync_at, _cached_connections
    import requests

    token = get_device_token()
    if not token:
        return {"ok": False, "error": "App not linked. Restart the app to enter your activation code."}

    now = time.time()
    if not force and _cached_connections and (now - _last_sync_at) < _SYNC_INTERVAL:
        return {"ok": True, "connections": _cached_connections, "cached": True}

    try:
        resp = requests.get(
            f"{_RAPRAI_BASE}/api/connections",
            timeout=15,
            headers={
                "User-Agent": f"RAPR-AI/{APP_VERSION}",
                "Authorization": f"Bearer {token}",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success"):
            connections = {}
            for conn in data.get("connections", []):
                provider = conn.get("provider")
                creds = conn.get("credentials", {})
                if provider and creds:
                    connections[provider] = creds

                    # Inject credentials into environment
                    for key, value in creds.items():
                        if value:
                            os.environ[key] = value

            _cached_connections = connections
            _last_sync_at = now
            logger.info("Synced %d connection(s) from raprai.com", len(connections))
            return {"ok": True, "connections": connections}
        else:
            return {"ok": False, "error": data.get("error", "Sync failed")}

    except Exception as e:
        logger.warning("Connection sync failed: %s", e)
        # Return cached connections if available
        if _cached_connections:
            return {"ok": True, "connections": _cached_connections, "cached": True, "sync_error": str(e)}
        return {"ok": False, "error": str(e)}


def get_synced_connections() -> dict:
    """Return cached connections without making a network call."""
    return _cached_connections.copy()


# ---------------------------------------------------------------------------
# Usage telemetry
# ---------------------------------------------------------------------------

def track_usage(feature: str, action: str = "used", metadata: Optional[dict] = None) -> None:
    """
    Queue a telemetry event to be sent to raprai.com.

    Safe to call even if the app is not linked (events are buffered,
    and silently dropped if the buffer gets too large or no token exists).

    Call this from anywhere in the app:
        track_usage("playwright-cli", "used")
        track_usage("chat", "messages_sent", {"count": 42})
    """
    # Cap buffer at 500 events to prevent memory growth for unlinked/offline users
    if len(_telemetry_buffer) >= 500:
        _telemetry_buffer.pop(0)  # drop oldest

    _telemetry_buffer.append({
        "feature": feature,
        "action": action,
        "metadata": metadata or {},
    })


def flush_telemetry() -> bool:
    """Send queued telemetry events to raprai.com."""
    global _telemetry_buffer
    import requests

    token = get_device_token()
    if not token or not _telemetry_buffer:
        return False

    events = _telemetry_buffer.copy()
    _telemetry_buffer.clear()

    try:
        resp = requests.post(
            f"{_RAPRAI_BASE}/api/telemetry",
            json={"events": events, "app_version": APP_VERSION},
            timeout=15,
            headers={
                "User-Agent": f"RAPR-AI/{APP_VERSION}",
                "Authorization": f"Bearer {token}",
            },
        )
        resp.raise_for_status()
        logger.info("Sent %d telemetry event(s)", len(events))
        return True

    except Exception as e:
        logger.warning("Telemetry flush failed: %s — re-queuing %d events", e, len(events))
        _telemetry_buffer.extend(events)  # Re-queue for next attempt
        return False


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_link_status() -> dict:
    """Return the current device linking status."""
    token = get_device_token()
    return {
        "linked": bool(token),
        "token_preview": f"{token[:12]}...{token[-4:]}" if token and len(token) > 16 else None,
        "connections": list(_cached_connections.keys()),
        "connection_count": len(_cached_connections),
        "last_sync_at": _last_sync_at,
        "pending_telemetry": len(_telemetry_buffer),
    }


# ---------------------------------------------------------------------------
# Background sync loop (called from web_app.py startup)
# ---------------------------------------------------------------------------

async def device_sync_loop():
    """Background task that periodically syncs connections and flushes telemetry."""
    import asyncio

    # Wait for app to fully start
    await asyncio.sleep(15)

    while True:
        try:
            token = get_device_token()
            if token:
                # Sync connections
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, sync_connections)

                # Flush telemetry
                await loop.run_in_executor(None, flush_telemetry)
        except Exception as e:
            logger.warning("Device sync loop error: %s", e)

        await asyncio.sleep(_SYNC_INTERVAL)
