"""
helm/learning/metrics.py — Aggregates task log data into summary, trend, routing,
playbook, and proposal stats. All functions are safe (never raise).
Cache: module-level dict keyed by (function_name, args), TTL 5 minutes.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE = Path(__file__).parent
_LOG_DIR = _BASE / "task_logs"
_ROUTING_TABLE = _BASE / "routing_table.json"
_PLAYBOOKS_DIR = _BASE / "playbooks"
_PROPOSALS_FILE = _BASE / "skill_proposals" / "proposals.json"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 300.0  # 5 minutes


def _cached(key: str) -> Any | None:
    import time
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _store(key: str, value: Any) -> Any:
    import time
    _cache[key] = (time.monotonic(), value)
    return value


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse ISO 8601 timestamp, return aware datetime or None."""
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _iter_logs(since: datetime):
    """
    Yield parsed task log dicts whose timestamp >= since.
    Walks _LOG_DIR/YYYY-MM/ directories.
    """
    if not _LOG_DIR.exists():
        return
    try:
        month_dirs = sorted(_LOG_DIR.iterdir())
    except Exception:
        return
    for month_dir in month_dirs:
        if not month_dir.is_dir():
            continue
        # Quick skip: if directory name is earlier than since month
        try:
            dir_year, dir_month = month_dir.name.split("-")
            dir_dt = datetime(int(dir_year), int(dir_month), 1, tzinfo=timezone.utc)
            # If even the last day of this month is before since, skip
            if dir_dt + timedelta(days=31) < since:
                continue
        except Exception:
            pass
        try:
            log_files = month_dir.glob("task_*.json")
        except Exception:
            continue
        for log_file in log_files:
            try:
                with log_file.open("r", encoding="utf-8") as fh:
                    record = json.load(fh)
                ts = _parse_ts(record.get("timestamp", ""))
                if ts and ts >= since:
                    yield record
            except Exception:
                continue


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_summary(days: int = 30) -> dict:
    """
    Returns aggregated stats over last N days from task logs.
    Never raises.
    """
    key = f"get_summary:{days}"
    cached = _cached(key)
    if cached is not None:
        return cached

    try:
        since = _cutoff(days)
        total = 0
        success_count = 0
        total_duration = 0.0
        total_cost = 0.0
        tasks_by_type: dict[str, int] = defaultdict(int)
        tasks_by_ai: dict[str, int] = defaultdict(int)
        duration_by_ai: dict[str, float] = defaultdict(float)
        success_by_ai: dict[str, int] = defaultdict(int)
        cost_by_ai: dict[str, float] = defaultdict(float)

        for rec in _iter_logs(since):
            total += 1
            ai = rec.get("ai_used") or "unknown"
            task_type = rec.get("task_type") or "unknown"
            duration = float(rec.get("duration_seconds") or 0.0)
            cost = float(rec.get("estimated_cost_usd") or 0.0)
            success = rec.get("success")

            if success is True:
                success_count += 1
                success_by_ai[ai] += 1

            total_duration += duration
            total_cost += cost
            tasks_by_type[task_type] += 1
            tasks_by_ai[ai] += 1
            duration_by_ai[ai] += duration
            cost_by_ai[ai] += cost

        avg_duration = round(total_duration / total, 2) if total else 0.0
        success_rate = round(success_count / total, 4) if total else 0.0

        avg_duration_by_ai = {
            ai: round(duration_by_ai[ai] / tasks_by_ai[ai], 2)
            for ai in tasks_by_ai
        }
        success_rate_by_ai = {
            ai: round(success_by_ai[ai] / tasks_by_ai[ai], 4)
            for ai in tasks_by_ai
        }
        cost_by_ai_rounded = {
            ai: round(cost_by_ai[ai], 6) for ai in cost_by_ai
        }

        result = {
            "total_tasks": total,
            "success_rate": success_rate,
            "avg_duration_seconds": avg_duration,
            "total_cost_usd": round(total_cost, 6),
            "tasks_by_type": dict(tasks_by_type),
            "tasks_by_ai": dict(tasks_by_ai),
            "avg_duration_by_ai": avg_duration_by_ai,
            "success_rate_by_ai": success_rate_by_ai,
            "cost_by_ai": cost_by_ai_rounded,
            "period_days": days,
            "computed_at": _iso_now(),
        }
        return _store(key, result)

    except Exception:
        return {
            "total_tasks": 0,
            "success_rate": 0.0,
            "avg_duration_seconds": 0.0,
            "total_cost_usd": 0.0,
            "tasks_by_type": {},
            "tasks_by_ai": {},
            "avg_duration_by_ai": {},
            "success_rate_by_ai": {},
            "cost_by_ai": {},
            "period_days": days,
            "computed_at": _iso_now(),
        }


def get_trends(days: int = 14) -> dict:
    """
    Returns daily stats over last N days for trend charts.
    Never raises.
    """
    key = f"get_trends:{days}"
    cached = _cached(key)
    if cached is not None:
        return cached

    try:
        since = _cutoff(days)
        today = datetime.now(timezone.utc).date()

        # Build date range
        date_list = [
            (today - timedelta(days=i)).isoformat()
            for i in range(days - 1, -1, -1)
        ]

        counts: dict[str, int] = defaultdict(int)
        successes: dict[str, int] = defaultdict(int)
        durations: dict[str, float] = defaultdict(float)

        for rec in _iter_logs(since):
            ts = _parse_ts(rec.get("timestamp", ""))
            if ts is None:
                continue
            date_str = ts.date().isoformat()
            counts[date_str] += 1
            dur = float(rec.get("duration_seconds") or 0.0)
            durations[date_str] += dur
            if rec.get("success") is True:
                successes[date_str] += 1

        task_counts = [counts.get(d, 0) for d in date_list]
        success_rates = [
            round(successes[d] / counts[d], 4) if counts.get(d) else 0.0
            for d in date_list
        ]
        avg_durations = [
            round(durations[d] / counts[d], 2) if counts.get(d) else 0.0
            for d in date_list
        ]

        result = {
            "dates": date_list,
            "task_counts": task_counts,
            "success_rates": success_rates,
            "avg_durations": avg_durations,
            "period_days": days,
        }
        return _store(key, result)

    except Exception:
        return {
            "dates": [],
            "task_counts": [],
            "success_rates": [],
            "avg_durations": [],
            "period_days": days,
        }


def get_routing_summary() -> dict:
    """
    Reads routing_table.json and returns routing recommendation stats.
    Never raises.
    """
    key = "get_routing_summary"
    cached = _cached(key)
    if cached is not None:
        return cached

    try:
        with _ROUTING_TABLE.open("r", encoding="utf-8") as fh:
            table = json.load(fh)

        task_types = table.get("task_types", {})
        recommendations = []
        any_shadow = False

        for task_type, data in task_types.items():
            best_ai = data.get("best_ai")
            if not best_ai:
                continue
            shadow = data.get("shadow_mode", True)
            any_shadow = any_shadow or shadow
            recommendations.append({
                "task_type": task_type,
                "best_ai": best_ai,
                "confidence": round(float(data.get("confidence", 0.0)), 4),
                "sample_count": int(data.get("sample_count", 0)),
            })

        # Sort by confidence descending
        recommendations.sort(key=lambda x: -x["confidence"])

        result = {
            "task_types_tracked": len(task_types),
            "routing_recommendations": recommendations,
            "shadow_mode": any_shadow or True,  # Phase 1 always shadow
        }
        return _store(key, result)

    except Exception:
        return {
            "task_types_tracked": 0,
            "routing_recommendations": [],
            "shadow_mode": True,
        }


def get_playbook_stats() -> dict:
    """
    Scans all playbook meta.json files and returns aggregate stats.
    Never raises.
    """
    key = "get_playbook_stats"
    cached = _cached(key)
    if cached is not None:
        return cached

    try:
        total = 0
        status_counts: dict[str, int] = defaultdict(int)
        by_task_type: dict[str, int] = defaultdict(int)
        all_playbooks = []

        if _PLAYBOOKS_DIR.exists():
            for task_type_dir in _PLAYBOOKS_DIR.iterdir():
                if not task_type_dir.is_dir():
                    continue
                task_type = task_type_dir.name
                for pb_dir in task_type_dir.iterdir():
                    if not pb_dir.is_dir():
                        continue
                    meta_path = pb_dir / "meta.json"
                    if not meta_path.exists():
                        continue
                    try:
                        with meta_path.open("r", encoding="utf-8") as fh:
                            meta = json.load(fh)
                        total += 1
                        status = meta.get("status", "unknown")
                        status_counts[status] += 1
                        by_task_type[task_type] += 1
                        all_playbooks.append({
                            "name": meta.get("name", pb_dir.name),
                            "task_type": task_type,
                            "success_rate": float(meta.get("success_rate", 0.0)),
                            "sample_count": int(meta.get("sample_count", 0)),
                        })
                    except Exception:
                        continue

        # Top playbooks: sort by success_rate desc, then sample_count desc
        all_playbooks.sort(key=lambda x: (-x["success_rate"], -x["sample_count"]))
        top_playbooks = all_playbooks[:10]

        result = {
            "total": total,
            "active": status_counts.get("active", 0),
            "draft": status_counts.get("draft", 0),
            "deprecated": status_counts.get("deprecated", 0),
            "by_task_type": dict(by_task_type),
            "top_playbooks": top_playbooks,
        }
        return _store(key, result)

    except Exception:
        return {
            "total": 0,
            "active": 0,
            "draft": 0,
            "deprecated": 0,
            "by_task_type": {},
            "top_playbooks": [],
        }


def get_proposal_stats() -> dict:
    """
    Reads skill_proposals/proposals.json and returns status counts.
    Never raises.
    """
    key = "get_proposal_stats"
    cached = _cached(key)
    if cached is not None:
        return cached

    empty = {"total": 0, "pending": 0, "approved": 0, "applied": 0, "rejected": 0}

    try:
        if not _PROPOSALS_FILE.exists():
            return _store(key, empty)

        with _PROPOSALS_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        # Accept either a list of proposals or a dict with a "proposals" key
        if isinstance(data, list):
            proposals = data
        elif isinstance(data, dict):
            proposals = data.get("proposals", [])
        else:
            return _store(key, empty)

        counts: dict[str, int] = defaultdict(int)
        for p in proposals:
            status = (p.get("status") or "pending").lower()
            counts[status] += 1

        result = {
            "total": len(proposals),
            "pending": counts.get("pending", 0),
            "approved": counts.get("approved", 0),
            "applied": counts.get("applied", 0),
            "rejected": counts.get("rejected", 0),
        }
        return _store(key, result)

    except Exception:
        return _store(key, empty)
