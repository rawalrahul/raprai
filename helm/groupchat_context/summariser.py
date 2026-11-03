"""
Who writes a group's summaries.

Claude when it is installed (a Claude member's own session first, so its
model is used), else the strongest paid AI the user has set up — preferring
one that is in the group — else any member. Offline models are skipped: they
are fine to chat with, but the summaries are what every other member relies on.
GROUP_SUMMARISER=<ai key> overrides the choice.
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

import helm.state as _st
from helm.config import logger
from helm.groupchat_context.budget import is_offline

TIMEOUT = 240


def claude_installed() -> bool:
    return shutil.which("claude") is not None


def _member_session(group: dict, member: dict) -> dict:
    live = _st.sessions.get(member["session_id"])
    if live and live.get("ai") == member["ai"]:
        return live
    return {"id": member["session_id"], "ai": member["ai"],
            "model": member.get("model"), "cwd": member.get("cwd") or _st.last_cwd}


def _stand_in(ai: str) -> dict:
    model = None
    try:
        from helm.model_prefs import get_model_pref
        model = get_model_pref(ai)
    except Exception:
        logger.debug("groupchat: no model preference for %s", ai, exc_info=True)
    return {"id": f"summariser-{ai}", "ai": ai, "model": model, "cwd": _st.last_cwd}


def _allowed(ai: str) -> bool:
    try:
        from helm.smart_routing import allowed_from_budget
        return allowed_from_budget(ai)
    except Exception:
        return True


def _for_ai(group: dict, ai: str) -> dict:
    member = next((m for m in group.get("members") or [] if m.get("ai") == ai), None)
    return _member_session(group, member) if member else _stand_in(ai)


def pick(group: dict) -> Optional[dict]:
    """The session (real or stand-in) whose AI writes this group's summaries."""
    members = group.get("members") or []
    forced = os.environ.get("GROUP_SUMMARISER", "").strip()
    if forced:
        return _for_ai(group, forced)
    if any(m.get("ai") == "claude" for m in members) or claude_installed():
        return _for_ai(group, "claude")
    from helm.smart_routing import CAPABILITY_TIER, available_from_state
    in_group = [m["ai"] for m in members if m.get("ai")]
    candidates = list(dict.fromkeys(in_group + available_from_state()))
    paid = [a for a in candidates if not is_offline({"ai": a}) and _allowed(a)]
    if paid:
        best = sorted(paid, key=lambda a: (-CAPABILITY_TIER.get(a, 2), a not in in_group))[0]
        return _for_ai(group, best)
    return _member_session(group, members[0]) if members else None


def run_blocking(group: dict, prompt: str) -> str:
    """The summariser's answer, or "" if it couldn't run."""
    from helm.council.runner import _build_cmd_for_session, _run_subprocess_blocking, failed
    sess = pick(group)
    if not sess:
        return ""
    try:
        cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
        cwd = sess.get("cwd") or _st.last_cwd
        if not cwd or not os.path.isdir(cwd):
            cwd = os.path.expanduser("~")
        out = _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env, timeout=TIMEOUT)
    except Exception as exc:
        logger.warning("groupchat: summary by %s failed: %s", sess.get("ai"), exc)
        return ""
    out = _plain(out)
    if not out or failed(out):
        return ""
    return out


def _plain(raw: str) -> str:
    """The answer text, out of Claude's JSON envelope when there is one."""
    import json
    raw = (raw or "").strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "result" in obj:
            return str(obj["result"]).strip()
    except (TypeError, ValueError):
        pass
    return raw
