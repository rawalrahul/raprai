"""
helm/brief.py — Your brief: what needs you, from every AI you use.

Each morning (and, if you like, every few hours after that) RAPR puts together
one short list of what needs you, and sends it to Telegram, WhatsApp, Discord,
Slack, your phone and the app:

  1. What's waiting inside RAPR: approvals, sessions you left unfinished,
     results of your scheduled tasks. Costs nothing; no AI runs for it.
  2. What each AI you picked can see in the apps *it* is connected to. Claude
     Code looks through your claude.ai connectors and its MCP servers, Codex
     through its own, and so on (helm/reach.py lists them). Several AIs means
     several accounts and many more apps than any one AI has. These runs only
     read: helm/outward.py refuses anything that would act.
  3. A one-tap next step on each item. Tapping it starts a session with the AI
     that has the app, with the item as its task. Anything it then wants to send
     or change still asks you first.

Settings: user data/brief.json (Settings → Your brief in the app):
  {"enabled": true, "time": "08:00", "every_hours": 0, "max_items": 5,
   "sources": [{"id": "s1", "ai": "claude", "look_at": "my Gmail and calendar",
                "folder": "", "enabled": true}]}
The latest brief: user data/brief_latest.json. Scheduled task results the brief
reports: user data/schedule_results.json.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

import helm.state as _st
from helm.config import logger

DEFAULTS = {"enabled": True, "time": "08:00", "every_hours": 0, "max_items": 5, "sources": []}
SOURCE_TIMEOUT = 600          # seconds one AI may spend looking
LATE_LIMIT = 3 * 3600         # a missed slot still runs this long after (PC was asleep)
LAST_CHECKIN_HOUR = 21        # no check-ins after this hour
URGENCY = ("high", "normal", "low")
_ICON = {"high": "🔴", "normal": "🟡", "low": "⚪"}

_lock = asyncio.Lock()


# ── Settings and storage ─────────────────────────────────────────────────────

def _path(name: str):
    from helm.paths import user_data_dir
    return user_data_dir() / name


def _read(name: str, default):
    try:
        return json.loads(_path(name).read_text(encoding="utf-8"))
    except Exception:
        return default


def _write(name: str, data) -> None:
    _path(name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_settings() -> dict:
    data = _read("brief.json", {})
    out = {**DEFAULTS, **(data if isinstance(data, dict) else {})}
    out["sources"] = [s for s in out.get("sources") or [] if isinstance(s, dict)]
    return out


def clean_source(src: dict) -> dict:
    """A valid source, or ValueError saying what's wrong."""
    ai = str(src.get("ai", "")).strip()
    look_at = " ".join(str(src.get("look_at", "")).split())[:300]
    if not ai:
        raise ValueError("pick an AI for each source")
    if not look_at:
        raise ValueError(f"say what {ai} should look at")
    return {"id": str(src.get("id") or f"s-{uuid.uuid4().hex[:6]}")[:40], "ai": ai,
            "look_at": look_at, "folder": str(src.get("folder") or "").strip()[:500],
            "enabled": bool(src.get("enabled", True))}


def save_settings(data: dict) -> dict:
    t = str(data.get("time", DEFAULTS["time"])).strip()
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t):
        raise ValueError("time must look like 08:00")
    try:
        every = int(data.get("every_hours", 0) or 0)
        max_items = int(data.get("max_items", DEFAULTS["max_items"]) or DEFAULTS["max_items"])
    except (TypeError, ValueError):
        raise ValueError("every_hours and max_items must be whole numbers")
    clean = {"enabled": bool(data.get("enabled", True)), "time": t,
             "every_hours": max(0, min(every, 12)), "max_items": max(1, min(max_items, 15)),
             "sources": [clean_source(s) for s in data.get("sources") or []]}
    _write("brief.json", clean)
    return clean


def latest() -> Optional[dict]:
    data = _read("brief_latest.json", None)
    return data if isinstance(data, dict) and data.get("items") is not None else None


def _save_latest(brief: dict) -> None:
    _write("brief_latest.json", brief)


# ── Scheduled task results (the brief reports them) ──────────────────────────

def record_result(task: dict, output: str) -> None:
    """Keep what a scheduled task answered, for the brief and the Needs-you list."""
    results = _read("schedule_results.json", [])
    results = results if isinstance(results, list) else []
    text = (output or "").strip()
    results.append({"task_id": task.get("id"), "name": task.get("name") or task.get("prompt", "")[:40],
                    "ai": task.get("ai"), "folder": task.get("cwd") or "", "ts": time.time(),
                    "failed": _looks_failed(text), "result": text[:2000]})
    _write("schedule_results.json", results[-50:])


def schedule_results(since: float = 0.0) -> list[dict]:
    results = _read("schedule_results.json", [])
    return [r for r in (results if isinstance(results, list) else []) if r.get("ts", 0) > since]


def _same_folder(a: str, b: str) -> bool:
    import os
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _looks_failed(text: str) -> bool:
    low = text.lower()[:400]
    return (not text or text.startswith(("(error", "error:", "⚠️")) or "timed out after" in low
            or "not found in path" in low or (low.startswith("(") and "exited " in low))


# ── What's waiting inside RAPR ───────────────────────────────────────────────

def builtin_items(since: float) -> list[dict]:
    """Approvals, unfinished sessions and scheduled results. No AI runs for these."""
    import helm.approval as appr
    items = []
    for req in appr.pending():
        items.append({"kind": "approval", "ref": req["id"], "title": req.get("description", "")[:200],
                      "why": "Waiting for your OK.", "app": "RAPR", "urgency": "high", "action": ""})
    try:
        from helm.heartbeat import scan_pending_tasks
        own = _workspace()
        for p in scan_pending_tasks(max_logs=6, max_age_hours=48):
            if p.get("path") and _same_folder(p["path"], own):
                continue                # the brief's own runs
            folder = p.get("folder") or ""
            items.append({"kind": "session", "ref": p.get("history_id", ""),
                          "title": f"Unfinished in {folder}",
                          "why": " ".join(str(p.get("snippet", "")).split())[:200], "app": "RAPR",
                          "urgency": "normal", "ai": p.get("ai") or "", "folder": p.get("path") or "",
                          "action": "Pick up where we left off. Summarise what's left, then carry on with it."})
    except Exception as exc:
        logger.debug("brief: unfinished sessions unavailable: %s", exc)
    for r in schedule_results(since):
        when = datetime.fromtimestamp(r["ts"]).strftime("%H:%M")
        first = next((ln.strip() for ln in r.get("result", "").splitlines() if ln.strip()), "")
        items.append({"kind": "schedule", "ref": r.get("task_id") or "",
                      "title": f"{r['name']} {'failed' if r.get('failed') else 'ran'} at {when}",
                      "why": first[:200], "app": "Scheduled", "ai": r.get("ai") or "",
                      "folder": r.get("folder") or "", "urgency": "high" if r.get("failed") else "low",
                      "action": ("This scheduled task failed. Find out why and fix it:\n" + r.get("result", "")[:1500])
                      if r.get("failed") else ""})
    return items


# ── Asking each AI to look through its own apps ──────────────────────────────

PROMPT = """You are preparing the user's brief. Look at {look_at}, using the apps and tools you are connected to (MCP servers, connectors, command-line tools such as gh). Only look: don't send, post, change or delete anything.

Find what needs the user's attention or a decision now, most important first, at most {max_items} items. Leave out anything that doesn't need them.

For each item, suggest one next step an AI could take for them (for example: draft a reply, fix the failing test, review the pull request), written as an instruction to that AI. Leave it empty if only the user can do it.

Answer with only this JSON, no other text:
{{"items": [{{"title": "what it is, in a few words", "why": "one sentence: why it needs them now", "app": "where it is (Gmail, GitHub, Slack...)", "urgency": "high|normal|low", "action": "instruction for an AI, or empty", "link": "a URL to it, or empty"}}]}}
If nothing needs them, answer {{"items": []}}. If you can't reach {look_at}, answer {{"items": [], "problem": "what is missing, in one sentence"}}."""


def parse_items(text: str) -> tuple[list[dict], str]:
    """(items, problem) from an AI's answer; tolerant of text around the JSON."""
    decoder = json.JSONDecoder()
    text = text or ""
    for i in sorted((m.start() for m in re.finditer(r"\{", text)), reverse=True):
        try:
            obj, _ = decoder.raw_decode(text, i)
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("items"), list):
            items = [it for it in (_clean_item(x) for x in obj["items"]) if it]
            return items, str(obj.get("problem") or "")[:300]
    return [], "The AI didn't answer in the expected format."


def _clean_item(raw) -> Optional[dict]:
    if not isinstance(raw, dict) or not str(raw.get("title", "")).strip():
        return None
    link = str(raw.get("link") or "").strip()
    urgency = str(raw.get("urgency", "normal")).lower()
    return {"title": " ".join(str(raw["title"]).split())[:200],
            "why": " ".join(str(raw.get("why", "")).split())[:300],
            "app": " ".join(str(raw.get("app", "")).split())[:40],
            "urgency": urgency if urgency in URGENCY else "normal",
            "action": str(raw.get("action") or "").strip()[:1000],
            "link": link[:500] if link.startswith(("https://", "http://")) else ""}


def _workspace() -> str:
    from helm.paths import user_data_dir
    folder = user_data_dir() / "brief"
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder)


async def run_source(src: dict, max_items: int) -> dict:
    """Ask one AI to look through its apps. Returns {source, items, problem}."""
    from helm.ai_runner import process_message
    from helm.broadcast import push_state
    from helm.session_mgr import make_session

    folder = src.get("folder") or _workspace()
    sess = make_session(src["ai"], cwd=folder, fresh=True)
    sess["read_only"] = True            # helm/outward.py refuses anything that would act
    sess["claude_msgs"] = []            # a fresh look each time, not --continue
    sess["name"] = f"Brief · {sess['name']}"
    out, problem = "", ""
    try:
        out = await asyncio.wait_for(
            process_message(PROMPT.format(look_at=src["look_at"], max_items=max_items),
                            source="brief", session_id=sess["id"]),
            timeout=SOURCE_TIMEOUT)
    except asyncio.TimeoutError:
        problem = f"took longer than {SOURCE_TIMEOUT // 60} minutes"
    except Exception as exc:
        problem = str(exc)[:200]
    finally:
        try:
            from helm.ai_runner import kill_session_proc
            kill_session_proc(sess)
            sess["terminal"].stop()
        except Exception:
            pass
        _st.deleted_session_cwds[sess["id"]] = folder
        _st.sessions.pop(sess["id"], None)
        await push_state()
    items, parse_problem = parse_items(out) if out else ([], "")
    for it in items:
        it.update(kind="ai", ai=src["ai"], folder=src.get("folder") or "", ref=src.get("id", ""))
    return {"source": src, "items": items, "problem": problem or (parse_problem if not items else "")}


# ── Putting the brief together ───────────────────────────────────────────────

def _order(item: dict) -> tuple:
    kind_rank = {"approval": 0, "ai": 1, "schedule": 2, "session": 3}.get(item["kind"], 4)
    return (URGENCY.index(item.get("urgency", "normal")), kind_rank)


async def build(trigger: str = "manual") -> dict:
    """Collect everything, number the items, keep it as the latest brief."""
    settings = load_settings()
    prev = latest() or {}
    since = prev.get("created", time.time() - 86400)
    items = builtin_items(since)
    sources = [s for s in settings["sources"] if s.get("enabled", True)]
    checked = []
    if sources:
        results = await asyncio.gather(*(run_source(s, settings["max_items"]) for s in sources))
        for r in results:
            items += r["items"]
            checked.append({"ai": r["source"]["ai"], "look_at": r["source"]["look_at"],
                            "found": len(r["items"]), "problem": r["problem"]})
    items.sort(key=_order)
    for n, it in enumerate(items, 1):
        it["n"] = n
        it["status"] = "open"
    brief = {"id": f"b{int(time.time())}", "created": time.time(), "trigger": trigger,
             "items": items, "checked": checked}
    if trigger == "check-in":
        seen = {(i.get("kind"), i.get("title")) for i in prev.get("items", [])}
        brief["new"] = sum(1 for i in items if (i.get("kind"), i.get("title")) not in seen)
    _save_latest(brief)
    return brief


async def run(trigger: str = "manual", deliver: bool = True) -> Optional[dict]:
    """Build the brief and send it out. None when one is already being put together."""
    if _lock.locked():
        return None
    async with _lock:
        brief = await build(trigger)
        await _broadcast(brief)
        if deliver and (brief["items"] or brief["checked"]) and not (trigger == "check-in" and not brief.get("new")):
            await send(brief)
        return brief


def item(brief: Optional[dict], n) -> Optional[dict]:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    return next((i for i in (brief or {}).get("items", []) if i.get("n") == n), None)


def set_status(n, status: str, session_id: str = "") -> Optional[dict]:
    brief = latest()
    it = item(brief, n)
    if not it:
        return None
    it["status"] = status
    if session_id:
        it["session_id"] = session_id
    _save_latest(brief)
    return it


def task_prompt(it: dict) -> str:
    """What the AI is asked to do when you tap an item."""
    where = f" ({it['app']})" if it.get("app") else ""
    link = f"\nLink: {it['link']}" if it.get("link") else ""
    return (f"{it.get('action') or 'Help me with this.'}\n\n"
            f"From my brief: {it['title']}{where}. {it.get('why', '')}{link}")


async def start_item(n, source: str = "web") -> tuple[Optional[dict], str]:
    """Hand item n to its AI in a new session. Returns (session, message)."""
    from helm.ai_runner import process_message
    from helm.broadcast import push_state
    from helm.session_mgr import make_session

    brief = latest()
    it = item(brief, n)
    if not it:
        return None, f"There's no item {n} in your latest brief."
    if it["kind"] == "approval":
        return None, f"Item {n} is an approval: /approve {it['ref']} or /deny {it['ref']}."
    if not it.get("action"):
        return None, f"Item {n} is for you to do; there's no step to hand to an AI."
    ai = it.get("ai") or "claude"
    if ai != "claude" and not ai.startswith("acp:") and ai not in _st.integrations:
        ai = "claude"
    sess = make_session(ai, cwd=it.get("folder") or None)
    _st.focused_id = sess["id"]
    set_status(n, "started", sess["id"])
    await push_state()
    await _broadcast(latest())
    prompt = task_prompt(it)
    if source == "web":
        asyncio.create_task(process_message(prompt, source=source, session_id=sess["id"]))
    return sess, prompt


# ── Sending it out ───────────────────────────────────────────────────────────

def _checked_line(brief: dict) -> str:
    parts = []
    for c in brief.get("checked", []):
        name = "Claude" if c["ai"] == "claude" else (_st.integrations.get(c["ai"], {}).get("name") or c["ai"])
        note = f" ⚠️ {c['problem']}" if c.get("problem") else ""
        parts.append(f"{name}: {c['look_at']}{note}")
    return "Checked: " + "; ".join(parts + ["RAPR"]) if parts else ""


def text(brief: dict, how_to_act: bool = True) -> str:
    """The brief as plain text, for any chat app."""
    when = datetime.fromtimestamp(brief["created"]).strftime("%a %d %b, %H:%M")
    head = "☀️ Your brief" if datetime.fromtimestamp(brief["created"]).hour < 12 else "🐧 Check-in"
    lines = [f"{head} · {when}"]
    checked = _checked_line(brief)
    if checked:
        lines.append(checked)
    open_items = [i for i in brief["items"] if i.get("status", "open") == "open"]
    if not open_items:
        lines.append("\nNothing needs you right now. 🎉")
        return "\n".join(lines)
    lines.append("")
    for it in open_items:
        app = f" ({it['app']})" if it.get("app") and it["app"] != "RAPR" else ""
        lines.append(f"{it['n']}. {_ICON.get(it.get('urgency'), '🟡')} {it['title']}{app}")
        if it.get("why"):
            lines.append(f"   {it['why']}")
        if it.get("link"):
            lines.append(f"   {it['link']}")
    if how_to_act:
        lines.append("\nReply /do <number> to hand an item to its AI, /skip <number> to drop it, "
                     "/approve <id> for approvals.")
    return "\n".join(lines)


def telegram_keyboard(brief: dict):
    """One row of buttons per item you can act on."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows = []
    for it in brief["items"]:
        if it.get("status", "open") != "open":
            continue
        if it["kind"] == "approval":
            rows.append([InlineKeyboardButton(f"✅ {it['n']}: Approve", callback_data=f"brief:ok:{it['ref']}"),
                         InlineKeyboardButton("❌ Deny", callback_data=f"brief:no:{it['ref']}")])
        elif it.get("action"):
            who = "Claude" if it.get("ai") in ("", "claude", None) else \
                (_st.integrations.get(it["ai"], {}).get("name") or it["ai"])
            rows.append([InlineKeyboardButton(f"▶ {it['n']}: Hand to {who}", callback_data=f"brief:do:{it['n']}"),
                         InlineKeyboardButton("✕", callback_data=f"brief:skip:{it['n']}")])
    return InlineKeyboardMarkup(rows[:12]) if rows else None


async def send(brief: dict) -> list[str]:
    """Send the brief to every linked chat app and your phone. Returns where it went."""
    sent = []
    if _st.telegram_app and _st.telegram_chat_id:
        try:
            await _st.telegram_app.bot.send_message(chat_id=_st.telegram_chat_id,
                                                    text=text(brief, how_to_act=False)[:4000],
                                                    reply_markup=telegram_keyboard(brief))
            sent.append("Telegram")
        except Exception as exc:
            logger.warning("brief: Telegram failed: %s", exc)
    plain = text(brief)
    try:
        import helm.whatsapp_bridge as wa
        if wa.state.get("status") == "connected":
            await wa.send_text(plain)
            sent.append("WhatsApp")
    except Exception as exc:
        logger.debug("brief: WhatsApp skipped: %s", exc)
    try:
        import helm.groupchat as gc
        for name in ("discord", "slack"):   # they can only post to a chat you've used since start
            sender = gc._channel_senders.get(name)
            if sender and getattr(getattr(sender, "__self__", None), "last_chat", None):
                await sender({}, plain)
                sent.append(name.capitalize())
    except Exception as exc:
        logger.debug("brief: Discord/Slack skipped: %s", exc)
    try:
        from helm import push
        open_items = [i for i in brief["items"] if i.get("status", "open") == "open"]
        if open_items:
            title = f"Your brief: {len(open_items)} thing{'s' if len(open_items) != 1 else ''} need you"
            await asyncio.to_thread(push.send, title, open_items[0]["title"], "brief", "/#needs")
            sent.append("phone")
    except Exception as exc:
        logger.debug("brief: push skipped: %s", exc)
    return sent


async def _broadcast(brief: Optional[dict]) -> None:
    from helm.broadcast import broadcast
    await broadcast({"type": "brief", "brief": brief})


# ── When it runs ─────────────────────────────────────────────────────────────

def slots(day: datetime, settings: dict) -> list[datetime]:
    """Today's run times: the brief, then a check-in every N hours until evening."""
    hh, mm = (int(x) for x in settings["time"].split(":"))
    first = day.replace(hour=hh, minute=mm, second=0, microsecond=0)
    out = [first]
    every = settings.get("every_hours") or 0
    if every:
        t = first + timedelta(hours=every)
        while t.date() == first.date() and t.hour < LAST_CHECKIN_HOUR:
            out.append(t)
            t += timedelta(hours=every)
    return out


def due_slot(now: datetime, settings: dict, last_slot: str) -> Optional[datetime]:
    """The slot to run now, if any: the latest one that has passed and hasn't run."""
    if not settings.get("enabled"):
        return None
    passed = [s for s in slots(now, settings) if s <= now]
    if not passed:
        return None
    slot = passed[-1]
    if slot.strftime("%Y-%m-%d %H:%M") == last_slot or (now - slot).total_seconds() > LATE_LIMIT:
        return None
    return slot


async def brief_loop(poll_seconds: float = 30.0) -> None:
    """Background loop: run the brief and check-ins at their times."""
    state = _read("brief_state.json", {})
    last = state.get("last_slot", "") if isinstance(state, dict) else ""
    await asyncio.sleep(20)
    while True:
        try:
            settings = load_settings()
            now = datetime.now()
            slot = due_slot(now, settings, last)
            if slot:
                last = slot.strftime("%Y-%m-%d %H:%M")
                _write("brief_state.json", {"last_slot": last})
                first = slot == slots(now, settings)[0]
                await run("schedule" if first else "check-in")
        except Exception as exc:
            logger.warning("brief: run failed: %s", exc)
        await asyncio.sleep(poll_seconds)


def suggestions(reach: dict) -> list[dict]:
    """Sources worth adding, from the apps each AI already has."""
    from helm.reach import apps_text
    out = []
    for entry in reach.get("agents", []):
        apps = apps_text(entry)
        if apps:
            out.append({"ai": entry["ai"], "look_at": f"my apps you're connected to: {apps}"})
    import shutil
    if shutil.which("gh"):
        ai = next((a["ai"] for a in reach.get("agents", []) if a["ai"] in ("claude", "codex")), "claude")
        out.append({"ai": ai, "look_at": "GitHub, with the gh command: pull requests waiting for my "
                                         "review, failing checks on my pull requests, issues assigned to me"})
    return out
