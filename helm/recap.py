"""
helm/recap.py — Your month with RAPR, as a card you can share.

Everything is worked out on your computer from what RAPR already keeps: chat
history, group chats and bake-off results. Nothing is sent anywhere; the card
is drawn in the browser and only leaves your machine if you post it.

Money is an estimate from the text you saw (about 4 characters per token, at
each provider's API list price). AIs also read files and run tools you don't
see, so the real figure is higher; the card says "at least".
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

# AIs that run on your own machine. Their work is priced as if Claude's API had done it,
# which is what "saved" means on the card.
FREE_AIS = {"ollama", "claude_ollama", "codex_ollama", "local_openai"}
CHAT_APPS = {"telegram", "whatsapp", "discord", "slack"}


def _db():
    from helm.db import get_db
    return get_db()


def _groups() -> list[dict]:
    try:
        import helm.groupchat as gc
        gc.load_groups()
        return list(gc.groups.values())
    except Exception:
        return []


def _label(ai: str) -> str:
    try:
        from helm.session_mgr import usage_ai_label
        return usage_ai_label(ai)
    except Exception:
        return ai.title()


def _cost(ai: str, chars_in: int, chars_out: int) -> float:
    from helm.pipeline.cost import calculate_cost
    return calculate_cost(ai, chars_in // 4, chars_out // 4)


def month_bounds(month: Optional[str]) -> tuple[date, date]:
    """'2026-10' -> (2026-10-01, 2026-11-01). None means this month."""
    if month:
        y, m = (int(x) for x in month.split("-", 1))
        start = date(y, m, 1)
    else:
        start = date.today().replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def _streak(days: list[date]) -> int:
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    return best


def _persona(s: dict) -> tuple[str, str]:
    """A title for the month, from whatever stood out most."""
    if s["bakeoffs"] >= 3:
        return "The Judge", f'You made your AIs compete {s["bakeoffs"]} times.'
    if len(s["ais"]) >= 3:
        return "The Conductor", f'You kept {len(s["ais"])} different AIs busy.'
    if s["free_share"] >= 0.5:
        return "Local Hero", "Most of your work ran free, on your own machine."
    if s["chat_app_share"] >= 0.4:
        return "Remote Boss", "You ran your AIs from your phone more than your desk."
    hour = s["top_hour"]
    if hour is not None and (hour >= 22 or hour < 5):
        return "Night Owl", "Your AIs did their best work after dark."
    if hour is not None and 5 <= hour < 9:
        return "Early Bird", "Your AIs were at work before most people's coffee."
    return "The Builder", "Steady work, shipped with your AI crew."


def build(month: Optional[str] = None) -> dict:
    start, end = month_bounds(month)
    lo, hi = start.isoformat(), end.isoformat()
    rows = _db().execute(
        """SELECT role, ai, session_id, history_id, timestamp, length(content) AS n, extra
           FROM messages WHERE type = 'message' AND timestamp >= ? AND timestamp < ?
             AND role IN ('user', 'assistant')""", (lo, hi)).fetchall()

    replies: Counter = Counter()
    chars_out: Counter = Counter()
    chars_in: Counter = Counter()
    per_day: Counter = Counter()
    per_hour: Counter = Counter()
    sources: Counter = Counter()
    projects: set = set()
    session_ai: dict = defaultdict(Counter)
    sent_by_session: Counter = Counter()

    def tick(ts: str):
        try:
            when = datetime.fromisoformat(ts)
        except (TypeError, ValueError):
            return
        per_day[when.date()] += 1
        per_hour[when.hour] += 1

    for r in rows:
        tick(r["timestamp"])
        if r["history_id"]:
            projects.add(r["history_id"])
        if r["role"] == "user":
            src = "web"
            if r["extra"]:
                try:
                    src = json.loads(r["extra"]).get("source") or "web"
                except ValueError:
                    pass
            sources[src] += 1
            sent_by_session[r["session_id"]] += r["n"] or 0
        elif r["ai"] and r["ai"] != "shell":
            replies[r["ai"]] += 1
            chars_out[r["ai"]] += r["n"] or 0
            session_ai[r["session_id"]][r["ai"]] += 1

    # What you typed counts toward the AI that answered in that session.
    for sid, n in sent_by_session.items():
        if session_ai.get(sid):
            chars_in[session_ai[sid].most_common(1)[0][0]] += n

    group_msgs = 0
    groups_active = 0
    lo_ts = datetime(start.year, start.month, 1).timestamp()
    hi_ts = datetime(end.year, end.month, 1).timestamp()
    for g in _groups():
        in_month = [m for m in g.get("messages", []) if lo_ts <= float(m.get("timestamp") or 0) < hi_ts]
        if not in_month:
            continue
        groups_active += 1
        for m in in_month:
            group_msgs += 1
            when = datetime.fromtimestamp(float(m["timestamp"]))
            per_day[when.date()] += 1
            per_hour[when.hour] += 1
            if m.get("role") == "user":
                sources[m.get("source") or "web"] += 1
            elif m.get("role") == "member" and m.get("author_ai"):
                replies[m["author_ai"]] += 1
                chars_out[m["author_ai"]] += len(m.get("content") or "")

    try:
        from helm import bakeoff_history
        bakeoffs = bakeoff_history.between(lo_ts, hi_ts)
    except Exception:
        bakeoffs = []
    wins = Counter(b["winner"] for b in bakeoffs if b.get("winner"))

    total_replies = sum(replies.values())
    sent = sum(sources.values())
    saved = sum(_cost("claude", chars_in[a], chars_out[a]) for a in replies if a in FREE_AIS)
    api_value = sum(_cost(a, chars_in[a], chars_out[a]) for a in replies if a not in FREE_AIS)
    free_replies = sum(n for a, n in replies.items() if a in FREE_AIS)
    busiest = max(per_day.items(), key=lambda kv: kv[1]) if per_day else None

    stats = {
        "month": start.strftime("%Y-%m"),
        "month_label": start.strftime("%B %Y"),
        "empty": not (sent or total_replies or bakeoffs),
        "messages_sent": sent,
        "replies": total_replies,
        "ais": [{"ai": a, "label": _label(a), "replies": n,
                 "share": round(n / total_replies, 3) if total_replies else 0,
                 "free": a in FREE_AIS, "bakeoff_wins": wins.get(a, 0)}
                for a, n in replies.most_common()],
        "mvp": None,
        "active_days": len(per_day),
        "longest_streak": _streak(list(per_day)),
        "busiest_day": {"date": busiest[0].isoformat(), "messages": busiest[1]} if busiest else None,
        "top_hour": per_hour.most_common(1)[0][0] if per_hour else None,
        "projects": len(projects),
        "group_chats": groups_active,
        "group_messages": group_msgs,
        "bakeoffs": len(bakeoffs),
        "bakeoff_wins": dict(wins),
        "from_chat_apps": sum(n for s, n in sources.items() if s in CHAT_APPS),
        "chat_app_share": round(sum(n for s, n in sources.items() if s in CHAT_APPS) / sent, 3) if sent else 0,
        "free_share": round(free_replies / total_replies, 3) if total_replies else 0,
        "saved_usd": round(saved, 2),
        "api_value_usd": round(api_value, 2),
    }
    if stats["ais"]:
        stats["mvp"] = stats["ais"][0]
    stats["persona"], stats["persona_line"] = _persona(stats)
    return stats


def first_month() -> Optional[str]:
    """The earliest month with any chat history, for the month picker."""
    row = _db().execute("SELECT MIN(timestamp) FROM messages WHERE type = 'message'").fetchone()
    return row[0][:7] if row and row[0] else None
