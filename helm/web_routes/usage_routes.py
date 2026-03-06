"""
helm/web_routes/usage_routes.py — Token Usage Dashboard & Budget Guardrails API.

Endpoints:
  GET  /api/usage      — full usage stats for all AIs (dashboard data)
  GET  /api/budget      — current budget config & remaining allowances
  POST /api/budget      — update budget caps
"""

import os
import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger, USAGE_PERIOD_SECONDS
from helm.session_mgr import (
    usage_reset_if_needed, usage_ai_label, usage_cap_minutes,
    usage_for_ai, fmt_reset_eta,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Budget helpers
# ---------------------------------------------------------------------------

_BUDGET_AI_KEYS = ["claude", "gemini", "codex", "ollama"]


def _budget_config() -> dict:
    """Read budget configuration from environment."""
    cfg = {}
    for ai in _BUDGET_AI_KEYS:
        key_daily = f"BUDGET_DAILY_{ai.upper()}"
        key_warn = f"BUDGET_WARN_{ai.upper()}"
        daily_cap = os.environ.get(key_daily, "").strip()
        warn_pct = os.environ.get(key_warn, "80").strip()
        cfg[ai] = {
            "daily_cap_min": float(daily_cap) if daily_cap else None,
            "warn_pct": float(warn_pct) if warn_pct else 80.0,
        }
    # Global budget enabled flag
    cfg["enabled"] = os.environ.get("BUDGET_ENABLED", "1").strip().lower() in ("1", "true", "yes")
    return cfg


def check_budget(ai_key: str) -> dict:
    """Check if an AI is within budget. Returns status dict.

    Returns:
        {
            "allowed": True/False,
            "reason": str or None,
            "used_min": float,
            "cap_min": float or None,
            "pct_used": float or None,
            "warn": bool,
        }
    """
    cfg = _budget_config()
    if not cfg.get("enabled", True):
        return {"allowed": True, "reason": None, "used_min": 0, "cap_min": None, "pct_used": None, "warn": False}

    ai_cfg = cfg.get(ai_key, {})
    daily_cap = ai_cfg.get("daily_cap_min")
    warn_pct = ai_cfg.get("warn_pct", 80.0)

    if daily_cap is None:
        # No cap set — always allowed
        usage_reset_if_needed()
        st = _st.usage_stats.get(ai_key, {})
        used_min = float(st.get("seconds", 0.0)) / 60.0
        return {"allowed": True, "reason": None, "used_min": used_min, "cap_min": None, "pct_used": None, "warn": False}

    usage_reset_if_needed()
    st = _st.usage_stats.get(ai_key, {})
    used_min = float(st.get("seconds", 0.0)) / 60.0
    pct_used = min(100.0, (used_min / daily_cap) * 100.0) if daily_cap > 0 else 0.0

    if used_min >= daily_cap:
        return {
            "allowed": False,
            "reason": f"{usage_ai_label(ai_key)} has reached its daily budget cap ({used_min:.1f}m / {daily_cap:.0f}m). Resets in {fmt_reset_eta()}.",
            "used_min": used_min,
            "cap_min": daily_cap,
            "pct_used": pct_used,
            "warn": True,
        }

    warn = pct_used >= warn_pct
    return {
        "allowed": True,
        "reason": f"⚠️ {usage_ai_label(ai_key)} usage at {pct_used:.1f}% of daily cap" if warn else None,
        "used_min": used_min,
        "cap_min": daily_cap,
        "pct_used": pct_used,
        "warn": warn,
    }


# ---------------------------------------------------------------------------
# Usage Dashboard endpoint
# ---------------------------------------------------------------------------

@router.get("/api/usage")
async def get_usage():
    """Full usage stats for all AIs — powers the dashboard."""
    usage_reset_if_needed()

    # Gather all known AI keys
    ai_keys = set(_st.usage_stats.keys())
    ai_keys.update(_BUDGET_AI_KEYS)
    ai_keys.discard("shell")  # exclude shell from dashboard

    period_remaining = max(0, int((_st.usage_period_start + USAGE_PERIOD_SECONDS) - time.time()))
    reset_eta = fmt_reset_eta()

    ais = {}
    for key in sorted(ai_keys):
        st = _st.usage_stats.get(key, {})
        exact = _st.usage_exact.get(key, {})
        budget = check_budget(key)

        used_min = float(st.get("seconds", 0.0)) / 60.0
        tasks = int(st.get("tasks", 0))
        chars_in = int(st.get("chars_in", 0))
        chars_out = int(st.get("chars_out", 0))
        last_used = float(st.get("last_used", 0.0))

        # Token data — prefer actual counts from AI backends
        tokens_in  = int(st.get("tokens_in", 0))
        tokens_out = int(st.get("tokens_out", 0))
        tok_source = st.get("tokens_source", "estimate")
        if tok_source == "actual" and (tokens_in + tokens_out) > 0:
            total_tokens = tokens_in + tokens_out
        else:
            total_tokens = int((chars_in + chars_out) / 4)
            tokens_in = 0
            tokens_out = 0
            tok_source = "estimate"

        # Usage cap from environment
        cap_min = usage_cap_minutes(key)

        # Percentage from CLI or estimate
        pct_used = None
        if exact.get("pct_used") is not None:
            pct_used = float(exact["pct_used"])
        elif cap_min:
            pct_used = min(100.0, (used_min / cap_min) * 100.0)

        ais[key] = {
            "label": usage_ai_label(key),
            "tasks": tasks,
            "used_min": round(used_min, 2),
            "cap_min": cap_min,
            "pct_used": round(pct_used, 1) if pct_used is not None else None,
            "chars_in": chars_in,
            "chars_out": chars_out,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": total_tokens,
            "tokens_source": tok_source,
            "est_tokens": total_tokens,  # backward compat for dashboard
            "last_used": last_used,
            "source": exact.get("source", "estimate"),
            "budget": budget,
        }

    # Per-session breakdown
    session_usage = []
    for sid, sess in _st.sessions.items():
        ai = sess.get("ai") or "shell"
        if ai == "shell":
            continue
        session_usage.append({
            "id": sid,
            "name": sess.get("name", sid),
            "ai": ai,
            "task_count": int(sess.get("task_count", 0)),
            "total_seconds": float(sess.get("total_task_seconds", 0.0)),
            "total_min": round(float(sess.get("total_task_seconds", 0.0)) / 60.0, 2),
        })

    return JSONResponse({
        "ais": ais,
        "sessions": session_usage,
        "period_remaining_sec": period_remaining,
        "reset_eta": reset_eta,
        "budget_enabled": _budget_config().get("enabled", True),
    })


# ---------------------------------------------------------------------------
# Budget config endpoint
# ---------------------------------------------------------------------------

@router.get("/api/budget")
async def get_budget():
    """Current budget configuration."""
    cfg = _budget_config()
    return JSONResponse(cfg)


@router.post("/api/budget")
async def save_budget(request: Request):
    """Save budget caps. Body: { claude: { daily_cap_min: 300, warn_pct: 80 }, ... }"""
    from .app import update_env, reload_env

    body = await request.json()
    saved = []

    # Global enable/disable
    if "enabled" in body:
        val = "1" if body["enabled"] else "0"
        update_env("BUDGET_ENABLED", val)
        os.environ["BUDGET_ENABLED"] = val
        saved.append("BUDGET_ENABLED")

    for ai_key in _BUDGET_AI_KEYS:
        if ai_key not in body:
            continue
        ai_data = body[ai_key]
        if "daily_cap_min" in ai_data:
            env_key = f"BUDGET_DAILY_{ai_key.upper()}"
            val = str(ai_data["daily_cap_min"]) if ai_data["daily_cap_min"] else ""
            update_env(env_key, val)
            os.environ[env_key] = val
            saved.append(env_key)
        if "warn_pct" in ai_data:
            env_key = f"BUDGET_WARN_{ai_key.upper()}"
            val = str(ai_data["warn_pct"])
            update_env(env_key, val)
            os.environ[env_key] = val
            saved.append(env_key)

    reload_env()
    return JSONResponse({"saved": saved})
