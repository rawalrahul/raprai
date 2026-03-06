"""
helm/web_routes/backup_routes.py — Cloud backup API endpoints.
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse

from helm.config import logger
from helm.db import get_db

router = APIRouter()

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS = ("onedrive", "gdrive", "dropbox", "local")


def _get_provider(name: str):
    """Lazy-load and return a provider instance."""
    if name == "onedrive":
        from helm.cloud_backup.providers.onedrive import OneDriveBackupProvider
        return OneDriveBackupProvider()
    elif name == "gdrive":
        from helm.cloud_backup.providers.gdrive import GDriveBackupProvider
        return GDriveBackupProvider()
    elif name == "dropbox":
        from helm.cloud_backup.providers.dropbox import DropboxBackupProvider
        return DropboxBackupProvider()
    elif name == "local":
        from helm.cloud_backup.providers.local import LocalBackupProvider
        return LocalBackupProvider()
    return None


# ---------------------------------------------------------------------------
# Config endpoints
# ---------------------------------------------------------------------------

@router.get("/backups/config")
async def get_backup_config():
    """Return backup config for all providers + connection status."""
    db = get_db()
    result = {}

    for p in PROVIDERS:
        row = db.execute(
            "SELECT * FROM cloud_backup_config WHERE provider = ?", (p,)
        ).fetchone()

        if row:
            config = dict(row)
        else:
            config = {
                "provider": p, "enabled": 0, "frequency": "daily",
                "scheduled_hour": 2, "scheduled_weekday": 0,
                "remote_folder": "", "last_backup_at": None, "next_backup_at": None,
            }

        # Check connection status
        provider = _get_provider(p)
        try:
            config["connected"] = await provider.is_connected() if provider else False
        except Exception:
            config["connected"] = False

        result[p] = config

    return JSONResponse(result)


@router.post("/backups/config/{provider}")
async def save_backup_config(provider: str, request: Request):
    """Save/update backup config for a provider."""
    if provider not in PROVIDERS:
        return JSONResponse({"error": f"Unknown provider: {provider}"}, status_code=400)

    body = await request.json()
    db = get_db()

    # Upsert the config
    db.execute("""
        INSERT INTO cloud_backup_config (provider, enabled, frequency, scheduled_hour,
                                          scheduled_weekday, remote_folder, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(provider) DO UPDATE SET
            enabled = excluded.enabled,
            frequency = excluded.frequency,
            scheduled_hour = excluded.scheduled_hour,
            scheduled_weekday = excluded.scheduled_weekday,
            remote_folder = excluded.remote_folder,
            updated_at = datetime('now')
    """, (
        provider,
        1 if body.get("enabled") else 0,
        body.get("frequency", "daily"),
        body.get("scheduled_hour", 2),
        body.get("scheduled_weekday", 0),
        body.get("remote_folder", ""),
    ))
    db.commit()

    # Recalculate next backup time
    _update_next_backup(db, provider)

    return JSONResponse({"ok": True})


def _update_next_backup(db, provider: str):
    """Recalculate and store next_backup_at for a provider."""
    from helm.cloud_backup.scheduler import calculate_next_backup
    row = db.execute(
        "SELECT frequency, scheduled_hour, scheduled_weekday FROM cloud_backup_config WHERE provider = ?",
        (provider,)
    ).fetchone()
    if row:
        next_at = calculate_next_backup(row["frequency"], row["scheduled_hour"], row["scheduled_weekday"])
        if next_at:
            db.execute(
                "UPDATE cloud_backup_config SET next_backup_at = ? WHERE provider = ?",
                (next_at.isoformat(), provider)
            )
            db.commit()


# ---------------------------------------------------------------------------
# Backup execution
# ---------------------------------------------------------------------------

@router.post("/backups/now")
async def backup_now(request: Request):
    """Trigger a manual backup to all enabled providers."""
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    target_provider = body.get("provider")  # Optional: backup to specific provider only

    db = get_db()
    if target_provider:
        providers = [target_provider] if target_provider in PROVIDERS else []
    else:
        # All enabled providers
        rows = db.execute(
            "SELECT provider FROM cloud_backup_config WHERE enabled = 1"
        ).fetchall()
        providers = [r["provider"] for r in rows]

    if not providers:
        return JSONResponse({"ok": False, "error": "No enabled backup providers. Configure one in Settings."})

    # Create backup snapshot
    from helm.cloud_backup.core import create_backup
    try:
        backup = create_backup()
    except Exception as e:
        logger.error("cloud_backup: backup creation failed: %s", e)
        return JSONResponse({"ok": False, "error": f"Backup creation failed: {e}"})

    # Upload to each provider (async)
    results = []
    for p_name in providers:
        provider = _get_provider(p_name)
        if not provider:
            continue

        # Create job record
        db.execute(
            "INSERT INTO cloud_backup_jobs (provider, job_type, status, started_at) VALUES (?, 'manual', 'running', datetime('now'))",
            (p_name,)
        )
        db.commit()
        job_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Get remote folder config
        cfg = db.execute(
            "SELECT remote_folder FROM cloud_backup_config WHERE provider = ?", (p_name,)
        ).fetchone()
        folder = (cfg["remote_folder"] if cfg else "") or "/RAPR-Backups"

        try:
            result = await provider.upload(
                Path(backup["path"]), folder, backup["filename"]
            )
            if result.get("ok"):
                db.execute(
                    "UPDATE cloud_backup_jobs SET status='completed', completed_at=datetime('now'), backup_size=?, remote_id=? WHERE id=?",
                    (backup["size"], result.get("remote_id", ""), job_id)
                )
                db.execute(
                    "UPDATE cloud_backup_config SET last_backup_at=datetime('now') WHERE provider=?",
                    (p_name,)
                )
                _update_next_backup(db, p_name)
            else:
                db.execute(
                    "UPDATE cloud_backup_jobs SET status='failed', completed_at=datetime('now'), error_message=? WHERE id=?",
                    (result.get("error", "Unknown error"), job_id)
                )
            db.commit()
            results.append({"provider": p_name, "ok": result.get("ok", False), "error": result.get("error")})
        except Exception as e:
            db.execute(
                "UPDATE cloud_backup_jobs SET status='failed', completed_at=datetime('now'), error_message=? WHERE id=?",
                (str(e), job_id)
            )
            db.commit()
            results.append({"provider": p_name, "ok": False, "error": str(e)})

    # Cleanup temp backup file
    try:
        backup_dir = str(Path(backup["path"]).parent)
        import shutil
        shutil.rmtree(backup_dir, ignore_errors=True)
    except Exception:
        pass

    return JSONResponse({"ok": True, "results": results})


# ---------------------------------------------------------------------------
# Job history
# ---------------------------------------------------------------------------

@router.get("/backups/jobs")
async def list_backup_jobs(limit: int = 20):
    """Return recent backup jobs."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM cloud_backup_jobs ORDER BY started_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return JSONResponse({"jobs": [dict(r) for r in rows]})


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

@router.post("/backups/restore/{job_id}")
async def restore_backup(job_id: int):
    """Download and restore from a previous backup."""
    db = get_db()
    job = db.execute(
        "SELECT * FROM cloud_backup_jobs WHERE id = ? AND status = 'completed'", (job_id,)
    ).fetchone()

    if not job:
        return JSONResponse({"ok": False, "error": "Backup job not found or not completed"}, status_code=404)

    provider = _get_provider(job["provider"])
    if not provider:
        return JSONResponse({"ok": False, "error": f"Unknown provider: {job['provider']}"})

    remote_id = job["remote_id"]
    if not remote_id:
        return JSONResponse({"ok": False, "error": "No remote file ID stored for this backup"})

    import tempfile
    dest = Path(tempfile.mkdtemp(prefix="raprai_restore_")) / "backup.zip"

    try:
        dl = await provider.download(remote_id, dest)
        if not dl.get("ok"):
            return JSONResponse({"ok": False, "error": f"Download failed: {dl.get('error')}"})

        from helm.cloud_backup.core import restore_from_backup
        result = restore_from_backup(str(dest))
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
    finally:
        import shutil
        shutil.rmtree(str(dest.parent), ignore_errors=True)


# ---------------------------------------------------------------------------
# OAuth flow
# ---------------------------------------------------------------------------

@router.get("/backups/providers/{provider}/connect")
async def backup_oauth_connect(provider: str, request: Request):
    """Serve an OAuth connection page (opens in popup)."""
    if provider not in PROVIDERS or provider == "local":
        return JSONResponse({"error": "OAuth not available for this provider"}, status_code=400)

    p = _get_provider(provider)
    if not p:
        return JSONResponse({"error": "Provider not found"}, status_code=404)

    # Build callback URL
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/backups/providers/{provider}/callback"

    import secrets
    state = secrets.token_urlsafe(32)

    url = p.get_oauth_url(redirect_uri, state)
    if not url:
        return JSONResponse({"error": "OAuth not supported by this provider"})

    # Store state for verification
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO cloud_backup_config (provider, updated_at) VALUES (?, datetime('now')) "
        "ON CONFLICT(provider) DO UPDATE SET updated_at = datetime('now')",
        (provider,)
    )
    db.commit()

    # Return HTML page that redirects to OAuth
    html = f"""<!DOCTYPE html><html><head><title>Connect {provider}</title>
<style>body{{font-family:system-ui;background:#1a1a2e;color:#e0e0e0;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}
.box{{text-align:center;padding:40px}}a{{color:#a78bfa;font-size:16px}}</style>
</head><body><div class="box">
<h2>Connect {provider.title()} for Backup</h2>
<p>You will be redirected to sign in.</p>
<p><a href="{url}">Click here if not redirected</a></p>
<script>window.location.href="{url}";</script>
</div></body></html>"""
    return HTMLResponse(html)


@router.get("/backups/providers/{provider}/callback")
async def backup_oauth_callback(provider: str, request: Request):
    """Handle OAuth callback from provider."""
    code = request.query_params.get("code")
    if not code:
        error = request.query_params.get("error", "No authorization code received")
        return HTMLResponse(f"<h2>Error</h2><p>{error}</p>")

    p = _get_provider(provider)
    if not p:
        return HTMLResponse("<h2>Error</h2><p>Unknown provider</p>")

    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/backups/providers/{provider}/callback"

    try:
        result = await p.handle_oauth_callback(code, redirect_uri)
        if result.get("ok"):
            html = f"""<!DOCTYPE html><html><head><title>Connected!</title>
<style>body{{font-family:system-ui;background:#1a1a2e;color:#e0e0e0;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}
.box{{text-align:center;padding:40px}}h2{{color:#22c55e}}</style>
</head><body><div class="box">
<h2>Connected to {provider.title()}!</h2>
<p>You can close this window.</p>
<script>
if(window.opener){{window.opener.postMessage({{type:'backup-oauth-done',provider:'{provider}'}},'*')}}
setTimeout(()=>window.close(),2000);
</script>
</div></body></html>"""
            return HTMLResponse(html)
        else:
            return HTMLResponse(f"<h2>Error</h2><p>{result.get('error', 'Unknown error')}</p>")
    except Exception as e:
        return HTMLResponse(f"<h2>Error</h2><p>{e}</p>")


@router.post("/backups/providers/{provider}/disconnect")
async def backup_disconnect(provider: str):
    """Disconnect a cloud provider (remove tokens)."""
    p = _get_provider(provider)
    if not p:
        return JSONResponse({"error": "Unknown provider"}, status_code=404)
    result = await p.disconnect()
    return JSONResponse(result)
