"""
helm/session_mgr.py — Session lifecycle + usage tracking.

Covers: _make_session, _focused_session, _session_cwd, _session_status_icon,
        usage tracking helpers.
"""

import os
import time
from typing import Optional

import helm.state as _st
from helm.config import logger
from helm.history import (
    get_history_messages,
    path_to_id,
    save_cwd_to_log,
)
from helm.terminal import TerminalSession


# ---------------------------------------------------------------------------
# Session creation & lookup
# ---------------------------------------------------------------------------

def make_session(ai: Optional[str], cwd: Optional[str] = None,
                 model: Optional[str] = None) -> dict:
    """Create, launch, and register a new session. Returns the session dict.
    Automatically resumes history if a log exists for the given CWD.
    """
    _st.session_counter += 1
    sid = f"s{_st.session_counter}"

    if ai == "claude":
        name = f"Claude #{_st.session_counter}"; emoji = "🤖"; color = "#f59e0b"
    elif ai and ai in _st.integrations:
        info  = _st.integrations[ai]
        name  = f"{info['name']} #{_st.session_counter}"; emoji = info["emoji"]; color = info["color"]
    else:
        name  = f"Shell #{_st.session_counter}"; emoji = "🐚"; color = "#6b7280"; ai = None

    # Auto-apply default model if none explicitly chosen
    if not model and ai:
        model = _st.default_models.get(ai) or None

    target_cwd = cwd or _st.last_cwd
    path_id    = path_to_id(target_cwd)
    history    = get_history_messages(path_id)

    t = TerminalSession()
    if ai is None:
        t.launch()

    claude_msgs: list[str] = []
    if ai == "claude":
        claude_msgs = [m["content"] for m in history if m.get("role") == "user"]

    sess: dict = {
        "id": sid, "ai": ai, "cwd": target_cwd, "status": "running",
        "terminal": t, "claude_msgs": claude_msgs, "name": name, "emoji": emoji,
        "color": color, "created": time.time(), "last_used": time.time(),
        "busy": False, "task_start": None,
        "session_started": time.time(), "total_task_seconds": 0.0, "task_count": 0,
        "changes": {"new": [], "modified": [], "deleted": []},
        "proc": None,
        "history": history,
        # Per-session model override — None means use the integration's default
        "model": model or None,
        # Ollama REST-API conversation history (None = not yet initialised)
        "ollama_messages": None,
    }
    _st.sessions[sid] = sess

    # Write the CWD record and auto-name entry immediately so history shows
    # the right folder name even before the first message is sent.
    save_cwd_to_log(target_cwd, session_id=sid)

    # Broadcast loaded history to any connected web clients
    if history:
        import asyncio

        async def _push_history():
            from helm.broadcast import broadcast
            await asyncio.sleep(0.5)
            for msg in history:
                msg_with_sess = {**msg, "session_id": sid,
                                 "session_name": name, "session_emoji": emoji}
                await broadcast(msg_with_sess)

        asyncio.create_task(_push_history())

    return sess


_make_session = make_session  # legacy alias


def focused_session() -> Optional[dict]:
    return _st.sessions.get(_st.focused_id) if _st.focused_id else None


_focused_session = focused_session  # legacy alias


def session_cwd() -> str:
    """CWD of the focused session (or the last explicitly-set CWD if none focused)."""
    s = focused_session()
    return s["cwd"] if s else _st.last_cwd


_session_cwd = session_cwd  # legacy alias


def session_status_icon(sess: dict) -> str:
    if sess["status"] == "stopped":
        return "\U0001F534"
    if sess.get("busy"):
        return "\U0001F7E1"
    return "\U0001F7E2"


_session_status_icon = session_status_icon  # legacy alias


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------

def usage_reset_if_needed() -> None:
    from helm.config import USAGE_PERIOD_SECONDS
    now = time.time()
    if now - _st.usage_period_start >= USAGE_PERIOD_SECONDS:
        _st.usage_period_start = now
        _st.usage_stats        = {}
        _st.usage_exact        = {}


_usage_reset_if_needed = usage_reset_if_needed  # legacy alias


def usage_ai_label(ai_key: str) -> str:
    if ai_key == "claude":
        return "Claude"
    if ai_key == "shell":
        return "Shell"
    info = _st.integrations.get(ai_key)
    return info["name"] if info else ai_key.title()


_usage_ai_label = usage_ai_label  # legacy alias


def _parse_rel_reset_seconds(text: str) -> Optional[int]:
    import re
    if not text:
        return None
    m = re.search(r"(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", text.lower())
    if not m:
        return None
    d  = int(m.group(1) or 0)
    h  = int(m.group(2) or 0)
    mm = int(m.group(3) or 0)
    if d == h == mm == 0:
        return None
    return d * 86400 + h * 3600 + mm * 60


def _parse_cli_usage_from_text(text: str, provider: str) -> Optional[dict]:
    import re
    if not text:
        return None
    low = text.lower()
    kw  = ("usage", "quota", "limit", "remaining", "reset", "resets", "renews")
    if provider == "claude":
        kw = kw + ("cost", "/usage", "/cost")
    elif provider == "gemini":
        kw = kw + ("rate", "requests", "rpm", "rpd")
    if not any(k in low for k in kw):
        return None

    pct_used: Optional[float] = None
    for pm in re.finditer(r"(\d{1,3}(?:\.\d+)?)\s*%", text):
        pct = float(pm.group(1))
        if not (0.0 <= pct <= 100.0):
            continue
        window = low[max(0, pm.start() - 40):pm.end() + 40]
        if any(k in window for k in kw):
            pct_used = pct
            break

    reset_in_sec: Optional[int] = None
    rm = re.search(r"(?:resets?|renews?)\s*(?:in|after|:)?\s*([0-9d hms]+)", low)
    if rm:
        reset_in_sec = _parse_rel_reset_seconds(rm.group(1).strip())

    if pct_used is None and reset_in_sec is None:
        return None
    return {"pct_used": pct_used, "reset_in_sec": reset_in_sec}


def usage_cap_minutes(ai_key: str) -> Optional[int]:
    raw = os.environ.get(f"USAGE_CAP_MIN_{ai_key.upper()}", "").strip()
    if not raw:
        raw = os.environ.get("USAGE_CAP_MIN_DEFAULT", "").strip()
    if not raw:
        if ai_key in ("claude", "codex", "gemini"):
            return 300
        return None
    try:
        val = int(raw)
        return val if val > 0 else None
    except Exception:
        return None


_usage_cap_minutes = usage_cap_minutes  # legacy alias


def record_usage_task(ai_key: Optional[str], elapsed_seconds: float,
                      prompt: str = "", output: str = "",
                      input_tokens: Optional[int] = None,
                      output_tokens: Optional[int] = None) -> None:
    usage_reset_if_needed()
    key = ai_key or "shell"
    st = _st.usage_stats.setdefault(key, {
        "tasks": 0, "seconds": 0.0, "chars_in": 0, "chars_out": 0, "last_used": 0.0,
        "tokens_in": 0, "tokens_out": 0, "tokens_source": "estimate",
    })
    st["tasks"]     += 1
    st["seconds"]   += max(0.0, float(elapsed_seconds))
    st["chars_in"]  += len(prompt or "")
    st["chars_out"] += len(output or "")
    st["last_used"]  = time.time()

    # Store actual token counts when available
    if input_tokens is not None or output_tokens is not None:
        st.setdefault("tokens_in", 0)
        st.setdefault("tokens_out", 0)
        st["tokens_in"]  += input_tokens or 0
        st["tokens_out"] += output_tokens or 0
        st["tokens_source"] = "actual"
    else:
        # Ensure keys exist for backward compat
        st.setdefault("tokens_in", 0)
        st.setdefault("tokens_out", 0)
        if st.get("tokens_source") != "actual":
            st["tokens_source"] = "estimate"

    if key in ("codex", "claude", "gemini"):
        exact = _parse_cli_usage_from_text(output or "", key)
        if exact:
            _st.usage_exact[key] = {
                "pct_used":    exact.get("pct_used"),
                "reset_in_sec": exact.get("reset_in_sec"),
                "source":      f"{key}_cli",
                "updated_at":  time.time(),
            }


_record_usage_task = record_usage_task  # legacy alias


def fmt_reset_eta() -> str:
    from helm.config import USAGE_PERIOD_SECONDS
    rem = max(0, int((_st.usage_period_start + USAGE_PERIOD_SECONDS) - time.time()))
    h, rem2 = divmod(rem, 3600)
    m, _    = divmod(rem2, 60)
    return f"{h}h {m}m"


_fmt_reset_eta = fmt_reset_eta  # legacy alias


def usage_summary_text() -> str:
    usage_reset_if_needed()
    if not _st.usage_stats:
        return "Usage (current period)\nNo usage recorded yet."

    rows = sorted(_st.usage_stats.items(),
                  key=lambda kv: kv[1].get("seconds", 0.0), reverse=True)
    lines = ["Usage (current period)", f"Reset in: {fmt_reset_eta()}"]

    best_choice   = None
    best_remaining = -1.0

    for key, st in rows:
        mins_used  = st["seconds"] / 60.0
        tasks      = int(st["tasks"])
        # Prefer actual token counts over char-based estimates
        actual_tok_in  = int(st.get("tokens_in", 0))
        actual_tok_out = int(st.get("tokens_out", 0))
        tok_source     = st.get("tokens_source", "estimate")
        if tok_source == "actual" and (actual_tok_in + actual_tok_out) > 0:
            est_tokens = actual_tok_in + actual_tok_out
        else:
            est_tokens = int((st.get("chars_in", 0) + st.get("chars_out", 0)) / 4)
        exact      = _st.usage_exact.get(key) or {}
        exact_pct  = exact.get("pct_used")
        exact_reset = exact.get("reset_in_sec")
        cap        = usage_cap_minutes(key)
        label      = usage_ai_label(key)
        if exact_pct is not None:
            rs = fmt_reset_eta() if exact_reset is None else \
                f"{max(0, int(exact_reset)) // 3600}h {(max(0, int(exact_reset)) % 3600) // 60}m"
            lines.append(
                f"- {label}: {float(exact_pct):.1f}% used (CLI) | resets in {rs}"
                f" | {tasks} task(s) | ~{est_tokens} tok"
            )
        elif cap:
            used_pct = min(100.0, (mins_used / cap) * 100.0)
            rem      = max(0.0, cap - mins_used)
            lines.append(
                f"- {label}: {mins_used:.1f}m / {cap}m ({used_pct:.1f}%)"
                f" | left {rem:.1f}m | {tasks} task(s) | ~{est_tokens} tok"
            )
            if rem > best_remaining:
                best_remaining = rem
                best_choice    = label
        else:
            lines.append(f"- {label}: {mins_used:.1f}m | {tasks} task(s) | ~{est_tokens} tok")

    if best_choice:
        lines.append(f"\nSuggested next AI: {best_choice} (most remaining quota)")
    else:
        lines.append("\nTip: set USAGE_CAP_MIN_<AI> in .env (e.g. USAGE_CAP_MIN_CLAUDE=300).")
    lines.append("Note: CLI-derived values are preferred when detected; otherwise estimates are shown.")
    return "\n".join(lines)


_usage_summary_text = usage_summary_text  # legacy alias


def usage_for_ai(ai_key: Optional[str]) -> dict:
    usage_reset_if_needed()
    from helm.config import USAGE_PERIOD_SECONDS
    key      = ai_key or "shell"
    st       = _st.usage_stats.get(key, {})
    used_min = float(st.get("seconds", 0.0)) / 60.0
    exact    = _st.usage_exact.get(key) or {}
    cap      = usage_cap_minutes(key)
    pct      = min(100.0, (used_min / cap) * 100.0) if cap else None
    reset_in = max(0, int((_st.usage_period_start + USAGE_PERIOD_SECONDS) - time.time()))
    if exact.get("pct_used") is not None:
        pct = float(exact["pct_used"])
    if exact.get("reset_in_sec") is not None:
        reset_in = max(0, int(exact["reset_in_sec"]))
    # Token data
    tokens_in  = int(st.get("tokens_in", 0))
    tokens_out = int(st.get("tokens_out", 0))
    tok_source = st.get("tokens_source", "estimate")
    if tok_source == "actual" and (tokens_in + tokens_out) > 0:
        total_tokens = tokens_in + tokens_out
    else:
        total_tokens = int((st.get("chars_in", 0) + st.get("chars_out", 0)) / 4)
        tok_source = "estimate"
    return {
        "used_min":  used_min,
        "cap_min":   cap,
        "pct":       pct,
        "reset_in_sec": reset_in,
        "has_cap":   cap is not None,
        "source":    exact.get("source") or "estimate",
        "tokens_in":  tokens_in,
        "tokens_out": tokens_out,
        "total_tokens": total_tokens,
        "tokens_source": tok_source,
    }


_usage_for_ai = usage_for_ai  # legacy alias


def sessions_state_payload() -> list[dict]:
    """Serialisable list of all sessions (no terminal objects)."""
    from helm.context_manager import context_info_for_session
    return [
        {"id": s["id"], "name": s["name"], "ai": s["ai"], "cwd": s["cwd"],
         "history_id": path_to_id(s["cwd"]),
         "status": s["status"], "emoji": s["emoji"], "color": s["color"],
         "busy": s.get("busy", False), "task_start": s.get("task_start"),
         "usage": usage_for_ai(s.get("ai")),
         "model": s.get("model"),
         "context": context_info_for_session(s)}
        for s in _st.sessions.values()
    ]


_sessions_state_payload = sessions_state_payload  # legacy alias
