"""
helm/cloud_backup/core.py — Backup engine for RAPR AI.

Creates ZIP snapshots of the SQLite database with a manifest,
and handles restore operations.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from helm.config import logger
from helm.db import db_path, DB_NAME


def create_backup() -> dict:
    """
    Create a full database backup.

    1. Checkpoint WAL to ensure all data is in the main DB file.
    2. Copy the database to a temp location.
    3. Create manifest.json with metadata + SHA-256 checksum.
    4. ZIP both files into a timestamped archive.

    Returns: {path: str, size: int, manifest: dict, filename: str}
    """
    src = db_path()
    if not src.exists():
        raise FileNotFoundError(f"Database not found: {src}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"raprai_backup_{ts}.zip"

    work_dir = tempfile.mkdtemp(prefix="raprai_backup_")
    try:
        # 1. WAL checkpoint — flush pending writes into the main db file
        try:
            conn = sqlite3.connect(str(src))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except Exception as e:
            logger.warning("cloud_backup: WAL checkpoint warning: %s", e)

        # 2. Copy the database file
        db_copy = os.path.join(work_dir, DB_NAME)
        shutil.copy2(str(src), db_copy)

        # 3. Compute SHA-256 checksum
        sha = hashlib.sha256()
        with open(db_copy, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        checksum = sha.hexdigest()

        # 4. Collect table row counts
        table_counts = {}
        try:
            conn = sqlite3.connect(db_copy)
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()]
            for t in tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
                    table_counts[t] = count
                except Exception:
                    table_counts[t] = -1
            conn.close()
        except Exception as e:
            logger.warning("cloud_backup: table count error: %s", e)

        # 5. Build manifest
        db_size = os.path.getsize(db_copy)
        manifest = {
            "version": "1.0",
            "app": "RAPR AI",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "db_filename": DB_NAME,
            "db_size_bytes": db_size,
            "sha256": checksum,
            "tables": table_counts,
        }

        manifest_path = os.path.join(work_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 6. Create ZIP archive
        zip_path = os.path.join(work_dir, filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_copy, DB_NAME)
            zf.write(manifest_path, "manifest.json")

        zip_size = os.path.getsize(zip_path)
        logger.info("cloud_backup: created backup %s (%.1f MB)", filename, zip_size / 1e6)

        return {
            "path": zip_path,
            "size": zip_size,
            "manifest": manifest,
            "filename": filename,
        }

    except Exception:
        # Clean up temp dir on failure
        shutil.rmtree(work_dir, ignore_errors=True)
        raise


def verify_backup(zip_path: str) -> dict:
    """
    Verify a backup ZIP file.

    Returns: {ok: bool, manifest: dict, error: str|None}
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if "manifest.json" not in names:
                return {"ok": False, "manifest": {}, "error": "Missing manifest.json"}
            if DB_NAME not in names:
                return {"ok": False, "manifest": {}, "error": f"Missing {DB_NAME}"}

            manifest = json.loads(zf.read("manifest.json"))

            # Verify checksum
            with zf.open(DB_NAME) as db_f:
                sha = hashlib.sha256()
                for chunk in iter(lambda: db_f.read(65536), b""):
                    sha.update(chunk)
                actual = sha.hexdigest()

            expected = manifest.get("sha256", "")
            if actual != expected:
                return {"ok": False, "manifest": manifest,
                        "error": f"Checksum mismatch: expected {expected[:12]}... got {actual[:12]}..."}

            return {"ok": True, "manifest": manifest, "error": None}

    except zipfile.BadZipFile:
        return {"ok": False, "manifest": {}, "error": "Invalid ZIP file"}
    except Exception as e:
        return {"ok": False, "manifest": {}, "error": str(e)}


def restore_from_backup(zip_path: str) -> dict:
    """
    Restore the database from a backup ZIP.

    1. Verify the backup integrity.
    2. Close all DB connections.
    3. Replace the current database.
    4. Verify the restored database.

    Returns: {ok: bool, error: str|None, manifest: dict}
    """
    # Step 1: Verify
    result = verify_backup(zip_path)
    if not result["ok"]:
        return result

    manifest = result["manifest"]
    dest = db_path()

    work_dir = tempfile.mkdtemp(prefix="raprai_restore_")
    try:
        # Step 2: Extract DB from ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extract(DB_NAME, work_dir)

        extracted = os.path.join(work_dir, DB_NAME)

        # Step 3: Verify extracted DB is valid SQLite
        try:
            conn = sqlite3.connect(extracted)
            conn.execute("PRAGMA integrity_check")
            conn.close()
        except sqlite3.Error as e:
            return {"ok": False, "error": f"Restored DB integrity check failed: {e}", "manifest": manifest}

        # Step 4: Close existing connections
        from helm.db import close_all
        close_all()

        # Step 5: Backup current DB (safety net)
        if dest.exists():
            safety = str(dest) + ".pre_restore"
            shutil.copy2(str(dest), safety)
            logger.info("cloud_backup: pre-restore safety copy at %s", safety)

        # Step 6: Replace the database
        # Remove WAL/SHM files too
        for ext in ("", "-wal", "-shm"):
            p = Path(str(dest) + ext)
            if p.exists():
                p.unlink()

        shutil.copy2(extracted, str(dest))

        # Step 7: Re-initialize
        from helm.db import init_db
        init_db()

        logger.info("cloud_backup: restored from backup (created %s)", manifest.get("created_at", "?"))
        return {"ok": True, "error": None, "manifest": manifest}

    except Exception as e:
        logger.error("cloud_backup: restore failed: %s", e)
        return {"ok": False, "error": str(e), "manifest": manifest}
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def cleanup_temp_backups():
    """Remove any leftover temp backup directories."""
    import glob
    for d in glob.glob(os.path.join(tempfile.gettempdir(), "raprai_backup_*")):
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass
