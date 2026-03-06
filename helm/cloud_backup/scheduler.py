"""
helm/cloud_backup/scheduler.py — Async background scheduler for automatic backups.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from helm.config import logger


def calculate_next_backup(frequency: str, hour: int = 2, weekday: int = 0) -> Optional[datetime]:
    """
    Calculate the next backup time based on frequency.

    Args:
        frequency: 'daily', 'weekly', or 'manual'
        hour: Hour of day (0-23) for scheduled backup
        weekday: Day of week (0=Monday, 6=Sunday) for weekly

    Returns: datetime in UTC, or None for manual
    """
    if frequency == "manual":
        return None

    now = datetime.now(timezone.utc)
    # Target time today
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)

    if frequency == "daily":
        if target <= now:
            target += timedelta(days=1)
        return target

    elif frequency == "weekly":
        # Find next occurrence of the target weekday
        days_ahead = weekday - target.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target += timedelta(days=days_ahead)
        if target <= now:
            target += timedelta(weeks=1)
        return target

    return None


class BackupScheduler:
    """Manages periodic backup execution."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._check_interval = 300  # 5 minutes

    async def start(self):
        """Start the scheduler loop."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("cloud_backup: scheduler started (checking every %ds)", self._check_interval)

    async def stop(self):
        """Gracefully stop the scheduler."""
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None
        logger.info("cloud_backup: scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop."""
        # Initial delay to let the app finish starting up
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=30)
            return  # Stop was called during startup delay
        except asyncio.TimeoutError:
            pass  # Expected — continue to check loop

        while not self._stop_event.is_set():
            try:
                await self._check_and_run()
            except Exception as e:
                logger.error("cloud_backup: scheduler error: %s", e)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._check_interval)
                break  # Stop was called
            except asyncio.TimeoutError:
                pass  # Expected — check again

    async def _check_and_run(self):
        """Check if any provider is due for backup and run if so."""
        from helm.db import get_db

        db = get_db()
        now = datetime.now(timezone.utc)

        rows = db.execute("""
            SELECT provider, frequency, scheduled_hour, scheduled_weekday,
                   next_backup_at, remote_folder
            FROM cloud_backup_config
            WHERE enabled = 1 AND frequency != 'manual'
        """).fetchall()

        for row in rows:
            provider_name = row["provider"]
            next_at_str = row["next_backup_at"]

            if not next_at_str:
                # No next time set — calculate and store it
                next_at = calculate_next_backup(
                    row["frequency"], row["scheduled_hour"], row["scheduled_weekday"]
                )
                if next_at:
                    db.execute(
                        "UPDATE cloud_backup_config SET next_backup_at = ? WHERE provider = ?",
                        (next_at.isoformat(), provider_name)
                    )
                    db.commit()
                continue

            # Parse next backup time
            try:
                next_at = datetime.fromisoformat(next_at_str)
                if next_at.tzinfo is None:
                    next_at = next_at.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            if now >= next_at:
                logger.info("cloud_backup: scheduled backup due for %s", provider_name)
                await self._run_backup(provider_name, row)

    async def _run_backup(self, provider_name: str, config):
        """Execute a backup for a single provider."""
        from helm.db import get_db
        from helm.cloud_backup.core import create_backup

        db = get_db()

        # Create job record
        db.execute(
            "INSERT INTO cloud_backup_jobs (provider, job_type, status, started_at) "
            "VALUES (?, 'auto', 'running', datetime('now'))",
            (provider_name,)
        )
        db.commit()
        job_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        try:
            # Create backup
            backup = create_backup()

            # Get provider
            from helm.web_routes.backup_routes import _get_provider
            provider = _get_provider(provider_name)
            if not provider:
                raise RuntimeError(f"Unknown provider: {provider_name}")

            folder = config["remote_folder"] or "/RAPR-Backups"

            # Upload
            result = await provider.upload(
                Path(backup["path"]), folder, backup["filename"]
            )

            if result.get("ok"):
                db.execute(
                    "UPDATE cloud_backup_jobs SET status='completed', completed_at=datetime('now'), "
                    "backup_size=?, remote_id=? WHERE id=?",
                    (backup["size"], result.get("remote_id", ""), job_id)
                )
                db.execute(
                    "UPDATE cloud_backup_config SET last_backup_at=datetime('now') WHERE provider=?",
                    (provider_name,)
                )
                logger.info("cloud_backup: scheduled backup completed for %s", provider_name)
            else:
                error = result.get("error", "Upload failed")
                db.execute(
                    "UPDATE cloud_backup_jobs SET status='failed', completed_at=datetime('now'), "
                    "error_message=? WHERE id=?",
                    (error, job_id)
                )
                logger.error("cloud_backup: scheduled backup failed for %s: %s", provider_name, error)

            # Update next backup time
            next_at = calculate_next_backup(
                config["frequency"], config["scheduled_hour"], config["scheduled_weekday"]
            )
            if next_at:
                db.execute(
                    "UPDATE cloud_backup_config SET next_backup_at = ? WHERE provider = ?",
                    (next_at.isoformat(), provider_name)
                )

            db.commit()

            # Cleanup temp files
            import shutil
            shutil.rmtree(str(Path(backup["path"]).parent), ignore_errors=True)

        except Exception as e:
            logger.error("cloud_backup: scheduled backup error for %s: %s", provider_name, e)
            db.execute(
                "UPDATE cloud_backup_jobs SET status='failed', completed_at=datetime('now'), "
                "error_message=? WHERE id=?",
                (str(e), job_id)
            )
            db.commit()


# Module-level instance
_scheduler: Optional[BackupScheduler] = None


async def start_scheduler():
    """Start the global backup scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackupScheduler()
    await _scheduler.start()


async def stop_scheduler():
    """Stop the global backup scheduler."""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None
