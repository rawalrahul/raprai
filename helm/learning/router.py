"""
helm/learning/router.py — AI routing based on learned task-type performance.

Phase 1: shadow mode only — compute recommendations but don't enforce.
Phase 2 (future): enforce routing when confidence > 0.8.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).parent
_SEED_PATH = _HERE / "seed" / "default_routing.json"
_TABLE_PATH = _HERE / "routing_table.json"

_seed: dict = {}
_table: dict = {}
_table_mtime: float = 0.0
_CACHE_TTL = 30.0  # reload routing table every 30s max


def _resolve_table_path(user_id_hash: str = "") -> Path:
    """Return per-user routing table if multi-user + user exists, else global."""
    try:
        from helm.learning.namespace import user_routing_table, is_multi_user
        if is_multi_user() and user_id_hash:
            p = user_routing_table(_HERE, user_id_hash)
            if p.exists():
                return p
    except Exception:
        pass
    return _TABLE_PATH


def _load_seed() -> dict:
    """Load seed defaults once at import time."""
    global _seed
    if not _seed:
        try:
            with open(_SEED_PATH, "r", encoding="utf-8") as f:
                _seed = json.load(f)
        except Exception:
            _seed = {"defaults": {}}
    return _seed


def _load_table(path: Path | None = None) -> dict:
    """Load routing table, cached with mtime check (global table only)."""
    global _table, _table_mtime
    target = path or _TABLE_PATH
    # Use cache only for the global table
    if target == _TABLE_PATH:
        try:
            mtime = target.stat().st_mtime
            if mtime != _table_mtime or not _table:
                with open(target, "r", encoding="utf-8") as f:
                    _table = json.load(f)
                _table_mtime = mtime
        except Exception:
            _table = {"task_types": {}}
        return _table
    # Per-user table: always read fresh (small files, infrequent)
    try:
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"task_types": {}}


def _get_budget_pct(ai: str) -> tuple[float, bool]:
    """
    Return (pct_used, allowed) from the budget system.
    pct_used: 0-100+ (percentage of cap consumed).
    allowed: False if hard-blocked (cap exceeded).
    Returns (0.0, True) if no budget configured or on any error.
    """
    try:
        from helm.web_routes.usage_routes import check_budget
        result = check_budget(ai)
        pct = float(result.get("pct_used") or 0.0)
        allowed = bool(result.get("allowed", True))
        return pct, allowed
    except Exception:
        return 0.0, True


def _apply_budget_filter(ais: list[str]) -> tuple[list[str], list[str]]:
    """
    Split AI list into (eligible, warned).
    eligible: AIs that are allowed and under 90% budget.
    warned: AIs at 80-90% (allowed but should note in reason).
    AIs at 100% (not allowed) are excluded entirely.
    """
    eligible: list[str] = []
    warned: list[str] = []
    for ai in ais:
        pct, allowed = _get_budget_pct(ai)
        if not allowed:
            continue  # hard-blocked
        if pct >= 90.0:
            continue  # route away per spec
        eligible.append(ai)
        if pct >= 80.0:
            warned.append(ai)
    return eligible, warned


def get_recommendation(task_type: str, available_ais: list[str],
                        user_id_hash: str = "") -> dict:
    """
    Return routing recommendation for a task type.

    Returns:
    {
        "recommended_ai": str | None,
        "confidence": float,
        "source": "learned" | "seed" | "none",
        "shadow_mode": bool,
        "reason": str,
        "budget_warn": bool,
    }
    """
    # Kill switch
    try:
        from helm.learning import is_learning_enabled
        if not is_learning_enabled():
            return {"recommended_ai": None, "confidence": 0.0,
                    "source": "none", "shadow_mode": True,
                    "reason": "learning disabled", "budget_warn": False}
    except Exception:
        pass

    # Budget filter — remove blocked/over-90% AIs; keep warned (80-90%) with flag
    eligible, warned = _apply_budget_filter(available_ais)
    # If budget filter removes everything, fall back to full list (avoid dead end)
    candidates = eligible if eligible else available_ais
    budget_warn = False

    seed = _load_seed()
    table = _load_table(_resolve_table_path(user_id_hash))

    # Check live routing table first
    task_data = table.get("task_types", {}).get(task_type)
    if task_data and task_data.get("sample_count", 0) >= 5 and task_data.get("best_ai"):
        best = task_data["best_ai"]
        if best in candidates:
            budget_warn = best in warned
            reason = f"Based on {task_data['sample_count']} past tasks"
            if budget_warn:
                reason += " (budget >80% — consider switching)"
            return {
                "recommended_ai": best,
                "confidence": task_data.get("confidence", 0.0),
                "source": "learned",
                "shadow_mode": True,
                "reason": reason,
                "budget_warn": budget_warn,
            }
        # best_ai was filtered out — try next best from ai_stats
        ai_stats = task_data.get("ai_stats", {})
        scored = []
        for ai_key, s in ai_stats.items():
            if ai_key not in candidates or s.get("sample_count", 0) < 2:
                continue
            rate = s["success_count"] / s["sample_count"]
            avg_dur = s["total_duration"] / s["sample_count"]
            scored.append((ai_key, rate, avg_dur))
        if scored:
            scored.sort(key=lambda x: (-x[1], x[2]))
            alt = scored[0][0]
            budget_warn = alt in warned
            return {
                "recommended_ai": alt,
                "confidence": task_data.get("confidence", 0.0) * 0.8,
                "source": "learned",
                "shadow_mode": True,
                "reason": f"Based on {task_data['sample_count']} past tasks (preferred AI at budget limit)",
                "budget_warn": budget_warn,
            }

    # Fall back to seed defaults
    seed_entry = seed.get("defaults", {}).get(task_type) or seed.get("defaults", {}).get("unknown", {})
    seed_ai = seed_entry.get("recommended_ai")
    if seed_ai and seed_ai in candidates:
        budget_warn = seed_ai in warned
        return {
            "recommended_ai": seed_ai,
            "confidence": seed_entry.get("confidence", 0.4),
            "source": "seed",
            "shadow_mode": True,
            "reason": seed_entry.get("reason", "Seed default"),
            "budget_warn": budget_warn,
        }

    # No recommendation
    first = candidates[0] if candidates else None
    return {
        "recommended_ai": first,
        "confidence": 0.0,
        "source": "none",
        "shadow_mode": True,
        "reason": "No data available",
        "budget_warn": first in warned if first else False,
    }


def update_stats(task_type: str, ai: str, duration_seconds: float,
                  success: bool, cost_usd: float = 0.0,
                  weight: float = 1.0, user_id_hash: str = "") -> None:
    """
    Update routing table with new task outcome.
    weight: multiplier for this data point (3.0 for explicit user corrections).
    Called after task completes. Atomic write to routing_table.json.
    """
    try:
        write_path = _resolve_table_path(user_id_hash)
        table = _load_table(write_path)
        types = table.setdefault("task_types", {})
        entry = types.setdefault(task_type, {
            "sample_count": 0,
            "ai_stats": {},
            "best_ai": None,
            "confidence": 0.0,
            "shadow_mode": True,
        })

        ai_stats = entry.setdefault("ai_stats", {})
        stats = ai_stats.setdefault(ai, {
            "sample_count": 0,
            "total_duration": 0.0,
            "success_count": 0,
            "total_cost": 0.0,
        })

        stats["sample_count"] += weight
        stats["total_duration"] += duration_seconds * weight
        if success:
            stats["success_count"] += weight
        stats["total_cost"] += cost_usd * weight
        entry["sample_count"] = sum(s["sample_count"] for s in ai_stats.values())

        # Recompute best_ai (by success_rate, then duration)
        scored = []
        for ai_key, s in ai_stats.items():
            if s["sample_count"] < 2:
                continue
            rate = s["success_count"] / s["sample_count"]
            avg_dur = s["total_duration"] / s["sample_count"]
            scored.append((ai_key, rate, avg_dur))

        if scored:
            scored.sort(key=lambda x: (-x[1], x[2]))  # best rate, then fastest
            best = scored[0]
            entry["best_ai"] = best[0]
            # Confidence: higher with more samples, higher with clearer winner
            n = entry["sample_count"]
            rate_gap = best[1] - (scored[1][1] if len(scored) > 1 else 0)
            entry["confidence"] = min(0.95, (n / (n + 10)) * (0.5 + rate_gap))

        table["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Atomic write
        write_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(write_path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(table, f, indent=2)
        os.replace(tmp, str(write_path))

        # Invalidate global cache if we wrote the global table
        if write_path == _TABLE_PATH:
            global _table_mtime
            _table_mtime = 0.0

    except Exception as e:
        try:
            err_log = Path(__file__).parent / "telemetry_errors.log"
            with open(err_log, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} router.update_stats error: {e}\n")
        except Exception:
            pass
