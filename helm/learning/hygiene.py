"""
helm/learning/hygiene.py — Weekly learning-store maintenance.

Tasks:
  - Mark stale playbooks (no success in 30+ days or recent rate < 0.5)
  - Compact task logs older than 90 days (raw JSON → monthly aggregate)
  - Clean orphan lock files older than 60 seconds
  - Regenerate LEARNING_INDEX.md

Entry points:
  run_hygiene()        — sync, safe to call from any context
  hygiene_runner()     — async loop, call once at startup via asyncio.create_task
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_PLAYBOOKS_DIR = _HERE / "playbooks"
_LOG_DIR = _HERE / "task_logs"
_LOCKS_DIR = _HERE / ".locks"
_ERROR_LOG = _HERE / "telemetry_errors.log"

_HYGIENE_INTERVAL_SECONDS = 7 * 24 * 3600  # 1 week
_LOG_RETENTION_DAYS = 90
_STALE_PLAYBOOK_DAYS = 30
_ORPHAN_LOCK_SECONDS = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_error(msg: str) -> None:
    try:
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} hygiene: {msg}\n")
    except Exception:
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Step 1: Stale playbook detection
# ---------------------------------------------------------------------------


def _check_stale_playbooks() -> int:
    """
    Walk all playbook meta.json files.
    Mark status='deprecated' if:
      - last_success is > 30 days ago (or None with sample_count > 0)
      - OR recent success_rate < 0.5 for active playbooks with 5+ samples
    Returns count of playbooks deprecated this run.
    """
    deprecated = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_PLAYBOOK_DAYS)

    try:
        if not _PLAYBOOKS_DIR.exists():
            return 0

        for task_type_dir in _PLAYBOOKS_DIR.iterdir():
            if not task_type_dir.is_dir():
                continue
            for pb_dir in task_type_dir.iterdir():
                if not pb_dir.is_dir():
                    continue
                meta_path = pb_dir / "meta.json"
                if not meta_path.exists():
                    continue
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    continue

                if meta.get("status") not in ("active", "draft"):
                    continue

                sample_count = int(meta.get("sample_count", 0))
                if sample_count == 0:
                    continue

                should_deprecate = False

                # Check last_success staleness
                last_success = meta.get("last_success")
                if last_success:
                    ls_dt = _parse_iso(last_success)
                    if ls_dt and ls_dt < cutoff:
                        should_deprecate = True
                elif sample_count >= 3:
                    # Has samples but never succeeded — deprecate
                    should_deprecate = True

                # Check rolling success_rate
                if not should_deprecate:
                    rate = float(meta.get("success_rate", 1.0))
                    if sample_count >= 5 and rate < 0.5:
                        should_deprecate = True

                if should_deprecate:
                    meta["status"] = "deprecated"
                    meta["deprecated_at"] = _now_iso()
                    try:
                        tmp = meta_path.with_suffix(".tmp")
                        tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                        if meta_path.exists():
                            meta_path.unlink()
                        tmp.rename(meta_path)
                        deprecated += 1
                    except Exception as exc:
                        _log_error(f"deprecate playbook {pb_dir.name}: {exc}")

    except Exception as exc:
        _log_error(f"_check_stale_playbooks: {exc}")

    return deprecated


# ---------------------------------------------------------------------------
# Step 2: Log compaction (90d raw → monthly aggregate)
# ---------------------------------------------------------------------------


def _compact_old_logs() -> int:
    """
    For each month directory older than LOG_RETENTION_DAYS:
      - Aggregate all task_*.json into a monthly_summary.json
      - Delete the raw task files
    Returns count of files compacted.
    """
    compacted = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=_LOG_RETENTION_DAYS)

    try:
        if not _LOG_DIR.exists():
            return 0

        for month_dir in _LOG_DIR.iterdir():
            if not month_dir.is_dir():
                continue
            try:
                year_str, month_str = month_dir.name.split("-")
                dir_month_end = datetime(
                    int(year_str), int(month_str), 28, tzinfo=timezone.utc
                )
            except Exception:
                continue

            if dir_month_end >= cutoff:
                continue  # still within retention window

            summary_path = month_dir / "monthly_summary.json"
            if summary_path.exists():
                # Already compacted — just clean any remaining raw files
                for f in month_dir.glob("task_*.json"):
                    try:
                        f.unlink()
                        compacted += 1
                    except Exception:
                        pass
                continue

            # Build aggregate from raw files
            totals: dict = {
                "month": month_dir.name,
                "total_tasks": 0,
                "success_count": 0,
                "total_duration": 0.0,
                "total_cost": 0.0,
                "by_ai": defaultdict(lambda: {"count": 0, "success": 0, "duration": 0.0}),
                "by_type": defaultdict(int),
            }

            raw_files = list(month_dir.glob("task_*.json"))
            for f in raw_files:
                try:
                    rec = json.loads(f.read_text(encoding="utf-8"))
                    totals["total_tasks"] += 1
                    ai = rec.get("ai_used", "unknown")
                    task_type = rec.get("task_type", "unknown")
                    dur = float(rec.get("duration_seconds") or 0.0)
                    cost = float(rec.get("estimated_cost_usd") or 0.0)
                    success = rec.get("success") is True

                    if success:
                        totals["success_count"] += 1
                        totals["by_ai"][ai]["success"] += 1
                    totals["total_duration"] += dur
                    totals["total_cost"] += cost
                    totals["by_ai"][ai]["count"] += 1
                    totals["by_ai"][ai]["duration"] += dur
                    totals["by_type"][task_type] += 1
                except Exception:
                    continue

            # Serialize and write summary (convert defaultdicts)
            totals["by_ai"] = dict(totals["by_ai"])
            totals["by_type"] = dict(totals["by_type"])
            totals["compacted_at"] = _now_iso()

            try:
                tmp = summary_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(totals, indent=2), encoding="utf-8")
                if summary_path.exists():
                    summary_path.unlink()
                tmp.rename(summary_path)

                for f in raw_files:
                    try:
                        f.unlink()
                        compacted += 1
                    except Exception:
                        pass
            except Exception as exc:
                _log_error(f"compact write {month_dir.name}: {exc}")

    except Exception as exc:
        _log_error(f"_compact_old_logs: {exc}")

    return compacted


# ---------------------------------------------------------------------------
# Step 3: Orphan lock cleanup
# ---------------------------------------------------------------------------


def _clean_orphan_locks() -> int:
    """
    Remove .lock files older than ORPHAN_LOCK_SECONDS.
    Returns count removed.
    """
    removed = 0
    try:
        if not _LOCKS_DIR.exists():
            return 0
        now = time.time()
        for lock_file in _LOCKS_DIR.glob("*.lock"):
            try:
                age = now - lock_file.stat().st_mtime
                if age > _ORPHAN_LOCK_SECONDS:
                    lock_file.unlink()
                    removed += 1
                    _log_error(f"cleaned orphan lock: {lock_file.name} (age={age:.0f}s)")
            except Exception:
                pass
    except Exception as exc:
        _log_error(f"_clean_orphan_locks: {exc}")
    return removed


# ---------------------------------------------------------------------------
# Step 4: Disk-space guard
# ---------------------------------------------------------------------------


def _check_disk_space() -> None:
    """Log a warning if the learning directory is consuming too much space."""
    try:
        total_bytes = sum(
            f.stat().st_size
            for f in _HERE.rglob("*")
            if f.is_file()
        )
        total_mb = total_bytes / (1024 * 1024)
        if total_mb > 500:
            _log_error(
                f"disk usage WARNING: helm/learning/ = {total_mb:.1f} MB — "
                "consider running compaction or reducing retention days"
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public: run_hygiene
# ---------------------------------------------------------------------------


def run_hygiene() -> dict:
    """
    Run all hygiene steps synchronously.
    Returns a summary dict. Never raises.
    Skips silently when the ENABLED sentinel is absent (kill switch).
    """
    try:
        from helm.learning import is_learning_enabled
        if not is_learning_enabled():
            return {"ran_at": _now_iso(), "skipped": "learning disabled (ENABLED sentinel missing)"}

        deprecated = _check_stale_playbooks()
        compacted = _compact_old_logs()
        locks_removed = _clean_orphan_locks()
        _check_disk_space()

        try:
            from helm.learning.index_updater import update_learning_index
            update_learning_index()
            index_updated = True
        except Exception as exc:
            _log_error(f"index refresh failed: {exc}")
            index_updated = False

        # Daily routing snapshot (skip if already snapshotted today)
        snapshot_created = False
        try:
            routing_table = _HERE / "routing_table.json"
            if routing_table.exists():
                history_dir = _HERE / "routing_history"
                history_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
                snap_path = history_dir / f"{stamp}.json"
                if not snap_path.exists():
                    import shutil
                    shutil.copy2(routing_table, snap_path)
                    snapshot_created = True
        except Exception as exc:
            _log_error(f"routing snapshot failed: {exc}")

        result = {
            "ran_at": _now_iso(),
            "playbooks_deprecated": deprecated,
            "log_files_compacted": compacted,
            "locks_removed": locks_removed,
            "index_updated": index_updated,
            "routing_snapshot": snapshot_created,
        }
        return result

    except Exception as exc:
        _log_error(f"run_hygiene top-level: {exc}")
        return {"ran_at": _now_iso(), "error": str(exc)}


# ---------------------------------------------------------------------------
# Async runner (started once at app startup)
# ---------------------------------------------------------------------------


async def hygiene_runner() -> None:
    """
    Weekly background loop. Call once via asyncio.create_task().
    First run after 1 hour (let app warm up), then every 7 days.
    """
    await asyncio.sleep(3600)  # 1-hour warm-up delay
    while True:
        try:
            result = await asyncio.to_thread(run_hygiene)
            from helm.config import logger
            logger.info(
                "Learning hygiene complete: deprecated=%d compacted=%d locks=%d index=%s",
                result.get("playbooks_deprecated", 0),
                result.get("log_files_compacted", 0),
                result.get("locks_removed", 0),
                result.get("index_updated", False),
            )
        except Exception as exc:
            _log_error(f"hygiene_runner iteration: {exc}")

        await asyncio.sleep(_HYGIENE_INTERVAL_SECONDS)
