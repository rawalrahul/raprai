"""
helm/learning/cross_ai.py — Cross-AI approach comparison and insight generation.

When the same task fingerprint is completed by multiple AIs, compare:
  - Duration (which was faster?)
  - Tool call sequence (what did the faster AI do differently?)
  - Retry count (which struggled less?)

Generates context hints injected into slower AI's future prompts.

Entry point:
  record_task(record)   — call after each task completes
  get_hints(ai, task_type, fingerprint) → str   — called by injector
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_INSIGHTS_DIR = _HERE / "cross_ai_insights"
_ACTIVE_DIR = _INSIGHTS_DIR / "active"
_PROPOSED_DIR = _INSIGHTS_DIR / "proposed"
_ERROR_LOG = _HERE / "telemetry_errors.log"

# In-memory buffer: fingerprint -> list of recent task records
# Kept to last 10 records per fingerprint to detect cross-AI patterns
_buffer: dict[str, list[dict]] = defaultdict(list)
_BUFFER_MAX = 10

# Cache for active hints: (ai, fingerprint) -> (hint_text, expires_at)
_hint_cache: dict[tuple, tuple[str, float]] = {}
_HINT_CACHE_TTL = 300.0  # 5 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_error(msg: str) -> None:
    try:
        with _ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} cross_ai: {msg}\n")
    except Exception:
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if path.exists():
        path.unlink()
    tmp.rename(path)


# ---------------------------------------------------------------------------
# Core: record + analyze
# ---------------------------------------------------------------------------


def record_task(record: dict) -> None:
    """
    Buffer a completed task record.
    If same fingerprint has records from 2+ different AIs: run comparison.
    Non-blocking. Never raises.
    """
    try:
        fingerprint = record.get("task_fingerprint")
        task_type = record.get("task_type", "unknown")
        ai = record.get("ai_used", "unknown")
        if not fingerprint or task_type in ("chat", "unknown"):
            return

        key = f"{task_type}:{fingerprint}"
        buf = _buffer[key]
        buf.append({
            "ai": ai,
            "duration": float(record.get("duration_seconds") or 0.0),
            "success": bool(record.get("success")),
            "retry_count": int(record.get("retry_count") or 0),
            "tool_count": len(record.get("tool_call_sequence") or []),
            "task_type": task_type,
            "fingerprint": fingerprint,
            "ts": time.time(),
        })
        # Keep last N per key
        if len(buf) > _BUFFER_MAX:
            buf[:] = buf[-_BUFFER_MAX:]

        # Check if we have 2+ successful records from different AIs
        ais_seen = {r["ai"] for r in buf if r["success"]}
        if len(ais_seen) >= 2:
            _analyze(key, buf, task_type, fingerprint)

    except Exception as exc:
        _log_error(f"record_task: {exc}")


def _analyze(key: str, buf: list[dict], task_type: str, fingerprint: str) -> None:
    """
    Compare successful records across AIs.
    If significant duration gap found: generate insight hint for slower AI.
    """
    try:
        # Group by AI, take most recent successful record per AI
        by_ai: dict[str, dict] = {}
        for r in buf:
            if r["success"]:
                ai = r["ai"]
                if ai not in by_ai or r["ts"] > by_ai[ai]["ts"]:
                    by_ai[ai] = r

        if len(by_ai) < 2:
            return

        # Find fastest and slowest successful AI
        ranked = sorted(by_ai.values(), key=lambda x: x["duration"])
        fastest = ranked[0]
        slowest = ranked[-1]

        gap_ratio = slowest["duration"] / max(fastest["duration"], 1.0)
        if gap_ratio < 1.5:
            return  # less than 50% gap — not worth noting

        faster_ai = fastest["ai"]
        slower_ai = slowest["ai"]
        gap_seconds = round(slowest["duration"] - fastest["duration"], 1)

        # Check if we already have a recent active insight for this combo
        insight_path = _ACTIVE_DIR / f"{task_type}_{faster_ai}_vs_{slower_ai}_{fingerprint[:8]}.json"
        if insight_path.exists():
            try:
                existing = json.loads(insight_path.read_text(encoding="utf-8"))
                # Refresh if older than 7 days
                age = time.time() - existing.get("created_at_ts", 0)
                if age < 7 * 24 * 3600:
                    return
            except Exception:
                pass

        # Generate insight
        hint = (
            f"For '{task_type}' tasks, {faster_ai} completes ~{gap_seconds}s faster than {slower_ai} "
            f"(based on {len(buf)} observations). "
            f"Approach hint: go direct, minimize intermediate verification steps, "
            f"prefer keyboard shortcuts over click sequences when possible."
        )

        insight = {
            "task_type": task_type,
            "fingerprint": fingerprint,
            "faster_ai": faster_ai,
            "slower_ai": slower_ai,
            "gap_seconds": gap_seconds,
            "gap_ratio": round(gap_ratio, 2),
            "hint": hint,
            "sample_count": len(buf),
            "created_at": _now_iso(),
            "created_at_ts": time.time(),
            "status": "active",
        }

        _atomic_write(insight_path, insight)

        # Invalidate hint cache for slower AI
        keys_to_drop = [k for k in _hint_cache if k[0] == slower_ai]
        for k in keys_to_drop:
            del _hint_cache[k]

    except Exception as exc:
        _log_error(f"_analyze: {exc}")


# ---------------------------------------------------------------------------
# Public: get_hints
# ---------------------------------------------------------------------------


def get_hints(ai: str, task_type: str, fingerprint: Optional[str] = None) -> str:
    """
    Return insight hint string to inject into AI's context, or empty string.
    Reads from active insights directory. Cached for 5 minutes.
    Never raises.
    """
    try:
        cache_key = (ai, task_type, fingerprint or "")
        entry = _hint_cache.get(cache_key)
        if entry:
            text, expires = entry
            if time.monotonic() < expires:
                return text

        if not _ACTIVE_DIR.exists():
            return ""

        hints: list[str] = []
        for insight_file in _ACTIVE_DIR.glob(f"{task_type}_*_vs_{ai}_*.json"):
            try:
                data = json.loads(insight_file.read_text(encoding="utf-8"))
                if data.get("status") != "active":
                    continue
                if fingerprint and data.get("fingerprint") != fingerprint:
                    continue
                hints.append(data["hint"])
            except Exception:
                continue

        result = "\n".join(hints) if hints else ""
        _hint_cache[cache_key] = (result, time.monotonic() + _HINT_CACHE_TTL)
        return result

    except Exception as exc:
        _log_error(f"get_hints: {exc}")
        return ""


# ---------------------------------------------------------------------------
# List insights (for dashboard)
# ---------------------------------------------------------------------------


def list_insights(limit: int = 20) -> list[dict]:
    """Return list of active insights sorted by gap_ratio desc. Never raises."""
    try:
        if not _ACTIVE_DIR.exists():
            return []
        results = []
        for f in _ACTIVE_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("status") == "active":
                    results.append({
                        "task_type": data.get("task_type"),
                        "faster_ai": data.get("faster_ai"),
                        "slower_ai": data.get("slower_ai"),
                        "gap_seconds": data.get("gap_seconds"),
                        "gap_ratio": data.get("gap_ratio"),
                        "hint": data.get("hint", "")[:200],
                        "sample_count": data.get("sample_count"),
                        "created_at": data.get("created_at"),
                    })
            except Exception:
                continue
        results.sort(key=lambda x: x.get("gap_ratio") or 0, reverse=True)
        return results[:limit]
    except Exception as exc:
        _log_error(f"list_insights: {exc}")
        return []
