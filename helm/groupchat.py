"""
helm/groupchat.py — Group chats: several AIs and the user in one conversation.

Unlike the AI Council (a moderated debate on a fixed topic), a group chat is an
ordinary chat that happens to have more than one AI in it. You talk, they answer
and can build on each other's replies, and you can @mention who should answer.

How a group answers a message (a "room turn"):
  • Up to MAX_ROUNDS rounds and MAX_REPLIES replies in all.
  • Who answers each round: the members @-mentioned since the user's last
    message (full name, name without spaces, or first word; @all / @everyone),
    or every member if nobody was mentioned. Members speak one at a time and
    each round starts one member later, so nobody always goes first.
  • Each member is told who is in the room, what the room is for, and what was
    said. Replying "(pass)" says nothing. A member with nothing new to react to
    is skipped, and a round where nobody speaks ends the turn.
  • A new user message, or Stop, ends a running turn before its next speaker
    (and kills the reply that is being written).

What a member sees (its prompt) is built fresh for every reply, because each
reply is a new, one-shot run of that AI's CLI:
  • the room header (who is here, what the group is for, the member's role),
  • messages the user pinned (always shown, never scroll out),
  • a running summary of older messages (see below),
  • the most recent messages, newest kept word for word and older ones
    shortened, fitted into a budget sized for that member's AI (a share of
    its context window, capped; tighter when the prompt has to go on the
    command line). Older messages that don't fit are counted, not shown.
When enough messages have piled up, or some no longer fit, the oldest ones are
folded into the group's running summary by one of the members (falling back to
a plain digest if that fails). Long prompts go to Claude over stdin, so they
never hit the OS command-line length limit (about 8K chars through cmd.exe).

Groups are kept in <user data>/group_chats.json so they survive restarts.
Members are snapshots of sessions (AI, model, folder); while that session is
open its current model and folder are used, otherwise the snapshot is.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import threading
import time
from typing import Optional
from uuid import uuid4

import helm.state as _st
from helm.config import logger

MAX_ROUNDS = 3
MAX_REPLIES = 10
MAX_MEMBERS = 8
MAX_STORED_MESSAGES = 500
CONTEXT_MESSAGES = 40          # at most this many recent room messages in a prompt
KEEP_FULL_MESSAGES = 6         # the newest ones are shown in full, older ones shortened
OLD_MESSAGE_CHARS = 2000       # longest an older message may be in a prompt
CONTEXT_SHARE = float(os.environ.get("GROUP_CONTEXT_SHARE", "0.3"))       # of the AI's window
MAX_PROMPT_TOKENS = int(os.environ.get("GROUP_CONTEXT_MAX_TOKENS", "24000"))
MIN_PROMPT_TOKENS = 2000
CHARS_PER_TOKEN = 4
ARGV_MAX_CHARS_WINDOWS = 7000  # cmd.exe caps a whole command line at 8191 chars
ARGV_MAX_CHARS_POSIX = 100_000 # Linux caps one argument at 128 KiB
SUMMARY_KEEP_RECENT = 20       # messages never folded into the summary
SUMMARY_BATCH = 10             # fold once this many more have piled up…
SUMMARY_MIN_FOLD = 4           # …or once at least this many no longer fit a prompt
SUMMARY_MAX_CHARS = 3000
SUMMARY_TIMEOUT = 180
MAX_PINS = 10
PIN_CHARS = 1500
REPLY_TIMEOUT = 600            # seconds one member may take to answer
PASS_RE = re.compile(r"^\s*\(?\s*pass\s*\)?\s*\.?\s*$", re.IGNORECASE)
_ANSI_ESC_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

groups: dict[str, dict] = {}   # group_id -> group
# Channel ("telegram", "whatsapp") -> id of the group that channel is talking to.
# While set, plain messages from that channel go to the group, and the group's
# messages are relayed back to it.
active_groups: dict[str, str] = {}
# Channel -> async fn(group, text) that delivers a relayed group message.
_channel_senders: dict = {}
_loaded = False
_save_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _store_path():
    from helm.paths import user_data_dir
    return user_data_dir() / "group_chats.json"


def _public(group: dict) -> dict:
    """Group as sent to clients and saved to disk (no runtime-only keys)."""
    return {k: v for k, v in group.items() if not k.startswith("_")}


def load_groups() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        path = _store_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for g in data.get("groups", []):
                g["status"] = "idle"
                g["speaking"] = None
                groups[g["id"]] = g
            for ch, gid in (data.get("active") or {}).items():
                if gid in groups:
                    active_groups[ch] = gid
    except Exception as exc:
        logger.warning("groupchat: could not load groups: %s", exc)


def save_groups() -> None:
    try:
        path = _store_path()
        payload = {"groups": [_public(g) for g in groups.values()],
                   "active": dict(active_groups)}
        tmp = path.with_suffix(".tmp")
        with _save_lock:
            tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
            os.replace(tmp, path)
    except Exception as exc:
        logger.warning("groupchat: could not save groups: %s", exc)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def member_from_session(sess: dict, role: str = "", role_prompt: str = "") -> dict:
    return {
        "id": f"m-{uuid4().hex[:6]}",
        "role": role,
        "role_prompt": role_prompt,
        "session_id": sess["id"],
        "ai": sess.get("ai"),
        "model": sess.get("model"),
        "name": sess.get("name") or sess.get("ai") or "AI",
        "emoji": sess.get("emoji") or "🤖",
        "color": sess.get("color") or "#6b7280",
        "cwd": sess.get("cwd") or _st.last_cwd,
    }


def make_group(name: str, about: str, sessions: list[dict],
               roles: Optional[list[tuple[str, str]]] = None) -> dict:
    """roles: optional (role name, role prompt) per session, in the same order."""
    roles = roles or [("", "")] * len(sessions)
    members = [member_from_session(s, r, p) for s, (r, p) in zip(sessions, roles)]
    group = {
        "id": f"g-{uuid4().hex[:8]}",
        "name": (name or "").strip() or ", ".join(m["name"] for m in members),
        "about": (about or "").strip(),
        "members": members,
        "messages": [],
        "created_at": _now(),
        "updated_at": _now(),
        "status": "idle",
        "speaking": None,
    }
    groups[group["id"]] = group
    return group


def make_message(role: str, content: str, member: Optional[dict] = None,
                 source: str = "web") -> dict:
    msg = {
        "id": f"gm-{uuid4().hex[:8]}",
        "role": role,                 # user | member | system
        "content": content,
        "timestamp": _now(),
    }
    if role == "user":
        msg["source"] = source        # web | telegram | whatsapp
    if member:
        msg["author"] = member["id"]
        msg["author_name"] = member["name"]
        msg["author_ai"] = member["ai"]
        msg["author_color"] = member["color"]
        msg["author_emoji"] = member["emoji"]
    return msg


def append_message(group: dict, msg: dict) -> None:
    group["messages"].append(msg)
    if len(group["messages"]) > MAX_STORED_MESSAGES:
        del group["messages"][:-MAX_STORED_MESSAGES]
    group["updated_at"] = msg["timestamp"]


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------

def _aliases(member: dict) -> set[str]:
    full = member["name"].strip().lower()
    out = {full, full.replace(" ", "")}
    first = full.split()[0] if full.split() else ""
    if first:
        out.add(first)
    return {a for a in out if a}


def parse_mentions(text: str, members: list[dict]) -> list[str]:
    """Member ids @-mentioned in text, in roster order. @all/@everyone → all."""
    if not text or "@" not in text:
        return []
    low = text.lower()
    if re.search(r"(?<!\w)@(all|everyone)\b", low):
        return [m["id"] for m in members]
    hit = []
    for m in members:
        for alias in _aliases(m):
            if re.search(r"(?<!\w)@" + re.escape(alias) + r"(?![\w#])", low):
                hit.append(m["id"])
                break
    return hit


def _mentioned_since_user(group: dict) -> list[str]:
    """Members mentioned in the latest user message and every reply after it."""
    msgs = group["messages"]
    start = 0
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i]["role"] == "user":
            start = i
            break
    found: list[str] = []
    for msg in msgs[start:]:
        for mid in parse_mentions(msg["content"], group["members"]):
            if mid not in found:
                found.append(mid)
    return [m["id"] for m in group["members"] if m["id"] in found]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _speaker(msg: dict) -> str:
    if msg["role"] == "user":
        return "User"
    if msg["role"] == "member":
        return msg.get("author_name") or "AI"
    return "System"


def _shorten(text: str, limit: int) -> str:
    """text cut to about limit chars, keeping its start and end."""
    if len(text) <= limit:
        return text
    if limit < 80:
        return text[:max(limit - 1, 0)] + "…"
    note = f"\n[… {len(text) - limit} chars cut …]\n"
    keep = max(limit - len(note), 20)
    head = keep * 2 // 3
    return text[:head] + note + text[len(text) - (keep - head):]


def _chat_messages(group: dict) -> list[dict]:
    return [m for m in group["messages"] if m["role"] in ("user", "member")]


def _unsummarised(group: dict) -> list[dict]:
    """Chat messages newer than the ones folded into the running summary."""
    msgs = _chat_messages(group)
    upto = group.get("summary_upto")
    if not upto or not group.get("summary"):
        return msgs
    for i, m in enumerate(msgs):
        if m["id"] == upto:
            return msgs[i + 1:]
    # The boundary message was trimmed from storage, so everything left is newer.
    return msgs


def prompt_via_stdin(member: dict) -> bool:
    """True when a long prompt reaches this member's CLI over stdin, not argv."""
    if member.get("ai") == "claude":
        return True
    info = _st.integrations.get(member.get("ai") or "") or {}
    return bool(info.get("stdin_prompt"))


def prompt_budget_tokens(member: dict) -> int:
    """How big (in estimated tokens) a prompt for this member may get."""
    from helm.context_manager import context_window_for
    try:
        window = context_window_for(member.get("ai") or "", member.get("model") or "")
    except Exception:
        window = 128_000
    budget = max(min(int(window * CONTEXT_SHARE), MAX_PROMPT_TOKENS), MIN_PROMPT_TOKENS)
    if not prompt_via_stdin(member):
        argv_max = ARGV_MAX_CHARS_WINDOWS if os.name == "nt" else ARGV_MAX_CHARS_POSIX
        budget = min(budget, argv_max // CHARS_PER_TOKEN)
    return budget


def _pinned_block(group: dict) -> str:
    pins = group.get("pinned") or []
    if not pins:
        return ""
    lines = [f"- {p.get('who') or 'User'}: {_shorten(p.get('content', ''), PIN_CHARS)}" for p in pins]
    return "Pinned by the user (always keep these in mind):\n" + "\n".join(lines) + "\n\n"


def _summary_block(group: dict) -> str:
    if not group.get("summary"):
        return ""
    return f"Summary of the earlier conversation:\n{group['summary']}\n\n"


def _fit_transcript(group: dict, member: dict, budget_chars: int) -> tuple[list[str], int]:
    """Lines of the most recent messages that fit budget_chars (oldest first),
    and how many unsummarised messages didn't fit."""
    msgs = _unsummarised(group)
    chosen: list[str] = []
    remaining = budget_chars
    for i, msg in enumerate(reversed(msgs)):
        if len(chosen) >= CONTEXT_MESSAGES:
            break
        who = "You" if msg.get("author") == member["id"] else _speaker(msg)
        text = msg["content"] if i < KEEP_FULL_MESSAGES else _shorten(msg["content"], OLD_MESSAGE_CHARS)
        line = f"{who}: {text}"
        if len(line) + 2 > remaining:
            if not chosen:   # always show the newest message, cut down if need be
                chosen.append(_shorten(line, max(remaining - 2, 200)))
            break
        chosen.append(line)
        remaining -= len(line) + 2
    chosen.reverse()
    return chosen, len(msgs) - len(chosen)


def _prompt_parts(group: dict, member: dict) -> tuple[str, str]:
    """(everything above the transcript, everything below it)."""
    others = [m for m in group["members"] if m["id"] != member["id"]]
    roster = ", ".join(f'{m["name"]} ({m["ai"]})' for m in others) or "nobody else"
    header = f'[Group chat: "{group["name"]}" - with the user, {roster}]'
    about = f'What this group is for: {group["about"]}\n\n' if group.get("about") else ""
    role = f'Your role in this group: {member["role_prompt"]}\n\n' if member.get("role_prompt") else ""
    top = (
        f"{header}\n\n"
        f"You are {member['name']}, one of several AI assistants in a group chat "
        f"with the user. {about}{role}"
        f"{_pinned_block(group)}{_summary_block(group)}"
        "Conversation so far (oldest first):\n\n"
    )
    bottom = (
        f"\n\n---\nWrite your next message to the group as {member['name']}.\n"
        "- Answer the user directly, and build on, correct or agree with the other "
        "assistants instead of repeating them.\n"
        "- Address someone with @Name (e.g. @" + (others[0]["name"].split()[0] if others else "User")
        + ") when you want a specific member to respond.\n"
        "- If you have nothing useful to add, reply with exactly: (pass)\n"
        "- Reply with your message only: no name prefix, no preamble."
    )
    return top, bottom


def _build(group: dict, member: dict) -> tuple[str, dict]:
    top, bottom = _prompt_parts(group, member)
    budget_tokens = prompt_budget_tokens(member)
    room = budget_tokens * CHARS_PER_TOKEN - len(top) - len(bottom)
    lines, hidden = _fit_transcript(group, member, max(room, 1000))
    if hidden:
        lines.insert(0, f"(… {hidden} earlier messages not shown)")
    transcript = "\n\n".join(lines) or "(no messages yet)"
    prompt = f"{top}{transcript}{bottom}"
    info = {
        "member": member["id"],
        "tokens": len(prompt) // CHARS_PER_TOKEN,
        "budget": budget_tokens,
        "shown": len(lines) - (1 if hidden else 0),
        "hidden": hidden,
    }
    return prompt, info


def build_prompt(group: dict, member: dict) -> str:
    return _build(group, member)[0]


def context_info(group: dict) -> dict:
    """What the members see, for the context indicator: the tightest member's
    usage, how many messages are summarised, shown, and not shown."""
    total = len(_chat_messages(group))
    unsummarised = len(_unsummarised(group))
    worst = None
    for m in group.get("members") or []:
        try:
            _, info = _build(group, m)
        except Exception:
            continue
        info["pct"] = round(100 * info["tokens"] / max(info["budget"], 1))
        if worst is None or (info["pct"], info["hidden"]) > (worst["pct"], worst["hidden"]):
            worst = info
    worst = worst or {"tokens": 0, "budget": 0, "pct": 0, "shown": 0, "hidden": 0, "member": None}
    return {
        "messages": total,
        "summarised": total - unsummarised if group.get("summary") else 0,
        "has_summary": bool(group.get("summary")),
        "pinned": len(group.get("pinned") or []),
        "shown": worst["shown"],
        "hidden": worst["hidden"],
        "tokens": worst["tokens"],
        "budget": worst["budget"],
        "pct": worst["pct"],
        "tightest": worst["member"],
        "summarising": bool(group.get("_summarising")),
    }


# ---------------------------------------------------------------------------
# Running a member
# ---------------------------------------------------------------------------

def _runtime_session(member: dict) -> dict:
    """The member's live session when it is open, else a stand-in from the snapshot."""
    live = _st.sessions.get(member["session_id"])
    if live and live.get("ai") == member["ai"]:
        return live
    return {"id": member["session_id"], "ai": member["ai"],
            "model": member.get("model"), "cwd": member.get("cwd") or _st.last_cwd}


def _extract_text(raw: str) -> str:
    """Pull the reply out of Claude's JSON envelope, else return raw output."""
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "result" in obj:
            return str(obj["result"])
    except (TypeError, ValueError):
        pass
    return raw


def _run_member_blocking(group: dict, member: dict, prompt: str) -> str:
    from helm.council.runner import _build_cmd_for_session
    from helm.subprocess_utils import hidden_kwargs

    sess = _runtime_session(member)
    cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
    cwd = sess.get("cwd") or _st.last_cwd
    if not os.path.isdir(cwd):
        cwd = os.path.expanduser("~")
    from helm.paths import child_env
    env = child_env(cmd, extra_env)
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if stdin_text else subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
            cwd=cwd, env=env, **hidden_kwargs(),
        )
    except FileNotFoundError:
        return f"(error: '{cmd[0]}' not found in PATH)"
    group["_proc"] = proc
    try:
        stdout, stderr = proc.communicate(input=stdin_text, timeout=REPLY_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return "(timed out)"
    finally:
        group.pop("_proc", None)
    out = _extract_text(_ANSI_ESC_RE.sub("", stdout or "").strip()).strip()
    if not out and proc.returncode not in (0, None):
        err = _ANSI_ESC_RE.sub("", stderr or "").strip()
        return f"(error: {err[-300:] or f'exit code {proc.returncode}'})"
    return out


async def _run_member(group: dict, member: dict, prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _run_member_blocking(group, member, prompt))


def _kill_running(group: dict) -> None:
    proc = group.get("_proc")
    if proc and proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Broadcast helpers
# ---------------------------------------------------------------------------

async def _broadcast(event: dict) -> None:
    from helm.broadcast import broadcast
    await broadcast(event)


def client_view(group: dict) -> dict:
    """Group as sent to the app: stored fields plus the context indicator."""
    out = _public(group)
    try:
        out["context"] = context_info(group)
    except Exception:
        logger.debug("groupchat: context info failed", exc_info=True)
    return out


async def broadcast_group(group: dict) -> None:
    await _broadcast({"type": "group_updated", "group": client_view(group)})


async def _set_status(group: dict, status: str, speaking: Optional[str] = None) -> None:
    group["status"] = status
    group["speaking"] = speaking
    # Name and roster ride along so Kelvin can show the group's crew without a fetch.
    await _broadcast({"type": "group_status", "group_id": group["id"],
                      "status": status, "speaking": speaking, "name": group["name"],
                      "members": [{"id": m["id"], "name": m["name"], "ai": m["ai"],
                                   "emoji": m["emoji"], "color": m["color"]}
                                  for m in group["members"]]})


# ---------------------------------------------------------------------------
# Channels (Telegram, WhatsApp): relay a group's messages to the chat apps
# that are currently talking to it
# ---------------------------------------------------------------------------

def register_channel(name: str, sender) -> None:
    """sender: async fn(group, text) that posts text to that chat app."""
    _channel_senders[name] = sender


def set_active_group(channel: str, group_id: Optional[str]) -> None:
    if group_id:
        active_groups[channel] = group_id
    else:
        active_groups.pop(channel, None)
    save_groups()


def active_group(channel: str) -> Optional[dict]:
    load_groups()
    gid = active_groups.get(channel)
    return groups.get(gid) if gid else None


def format_for_channel(msg: dict) -> str:
    if msg["role"] == "member":
        return f"{msg.get('author_emoji') or '🤖'} {msg.get('author_name') or 'AI'}:\n{msg['content']}"
    if msg["role"] == "user":
        where = {"web": "web", "telegram": "Telegram", "whatsapp": "WhatsApp"}.get(msg.get("source"), "web")
        return f"🧑 You (from {where}):\n{msg['content']}"
    return msg["content"]


_join_hinted: set = set()    # (channel, group id) already told how to join in


def _join_hint(group: dict) -> str:
    try:
        from helm.groupchat_channels import ordered_groups
        n = next(i for i, g in enumerate(ordered_groups(), 1) if g["id"] == group["id"])
        return f"\n\n(Group chat. Send /group {n} to join in from here.)"
    except Exception:
        return "\n\n(Group chat. Send /group to join in from here.)"


async def _relay(group: dict, msg: dict) -> None:
    """Send a group message to every linked chat app except the one it came from.
    Apps that are in the group get it as is; the others get the group's name on
    top (and, the first time, how to join in), and keep talking to their session."""
    from helm.config import chat_apps_sync
    sync = chat_apps_sync()
    for channel, sender in list(_channel_senders.items()):
        if channel == msg.get("source"):
            continue
        if not sync and active_groups.get(channel) != group["id"]:
            continue   # sync off: only the chat apps that are in the group
        text = format_for_channel(msg)
        if active_groups.get(channel) != group["id"]:
            text = f"👥 {group['name']}\n{text}"
            if (channel, group["id"]) not in _join_hinted:
                _join_hinted.add((channel, group["id"]))
                text += _join_hint(group)
        try:
            await sender(group, text)
        except Exception as exc:
            logger.warning("groupchat: relay to %s failed: %s", channel, exc)


# ---------------------------------------------------------------------------
# Running summary: older messages folded into a short recap
# ---------------------------------------------------------------------------

def messages_to_fold(group: dict) -> list[dict]:
    """The oldest unsummarised messages that should go into the summary now:
    all but the newest SUMMARY_KEEP_RECENT once SUMMARY_BATCH more have piled up,
    or (at least SUMMARY_MIN_FOLD of) those that no longer fit some member's prompt."""
    msgs = _unsummarised(group)
    n = len(msgs) - SUMMARY_KEEP_RECENT if len(msgs) >= SUMMARY_KEEP_RECENT + SUMMARY_BATCH else 0
    hidden = 0
    for m in group.get("members") or []:
        try:
            hidden = max(hidden, _build(group, m)[1]["hidden"])
        except Exception:
            continue
    if hidden >= SUMMARY_MIN_FOLD:
        n = max(n, hidden)
    return msgs[:n] if n > 0 else []


def _digest(previous: str, msgs: list[dict]) -> str:
    """Plain recap used when no AI could write the summary."""
    lines = previous.splitlines() if previous else []
    for m in msgs:
        text = " ".join(m["content"].split())
        lines.append(f"- {_speaker(m)}: {_shorten(text, 160)}")
    out = "\n".join(lines)
    while len(out) > SUMMARY_MAX_CHARS and len(lines) > 1:
        lines.pop(0)   # drop the oldest lines first
        out = "\n".join(lines)
    return _shorten(out, SUMMARY_MAX_CHARS)


def summary_prompt(group: dict, msgs: list[dict]) -> str:
    convo = "\n\n".join(f"{_speaker(m)}: {_shorten(m['content'], 1500)}" for m in msgs)
    convo = _shorten(convo, 40_000)
    previous = group.get("summary") or "(none yet)"
    about = f'The group is for: {group["about"]}\n' if group.get("about") else ""
    return (
        f'You keep the running summary of a group chat called "{group["name"]}" between '
        "the user and several AI assistants. The assistants only see this summary, not "
        f"the messages it covers, so keep what they will need.\n{about}\n"
        f"Current summary:\n{previous}\n\n"
        f"Messages to fold in (oldest first):\n\n{convo}\n\n"
        "---\nWrite the updated summary: the current summary plus these messages. "
        "Keep the user's goals, requirements and preferences, decisions made, facts, "
        "names, numbers and file paths that matter, open questions, and who agreed to "
        "do what. Drop small talk. Use short bullet points, at most about 300 words. "
        "Reply with the summary only, no preamble."
    )


def _summariser(group: dict) -> Optional[dict]:
    """The member whose AI writes the summary: Claude if there is one."""
    members = group.get("members") or []
    return next((m for m in members if m.get("ai") == "claude"), members[0] if members else None)


def _summarise_blocking(group: dict, msgs: list[dict]) -> str:
    from helm.council.runner import _build_cmd_for_session, _run_subprocess_blocking, failed
    member = _summariser(group)
    if not member:
        return ""
    prompt = summary_prompt(group, msgs)
    try:
        sess = _runtime_session(member)
        cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
        cwd = sess.get("cwd") or _st.last_cwd
        if not os.path.isdir(cwd):
            cwd = os.path.expanduser("~")
        out = _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env, timeout=SUMMARY_TIMEOUT)
    except Exception as exc:
        logger.warning("groupchat: summary by %s failed: %s", member.get("name"), exc)
        return ""
    out = (out or "").strip()
    if not out or failed(out) or PASS_RE.match(out):
        return ""
    return _shorten(out, SUMMARY_MAX_CHARS)


async def update_summary(group: dict) -> bool:
    """Fold the messages that are due into the running summary. True if it changed."""
    if group.get("_summarising"):
        return False
    msgs = messages_to_fold(group)
    if not msgs:
        return False
    group["_summarising"] = True
    cleared = group.get("_cleared", 0)
    try:
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, lambda: _summarise_blocking(group, msgs))
        if not text:
            text = _digest(group.get("summary") or "", msgs)
        if groups.get(group["id"]) is not group or group.get("_cleared", 0) != cleared:
            return False   # deleted or cleared meanwhile
        group["summary"] = text
        group["summary_upto"] = msgs[-1]["id"]
        group["summary_count"] = (group.get("summary_count") or 0) + len(msgs)
        save_groups()
        return True
    finally:
        group.pop("_summarising", None)
        await broadcast_context(group)


def _schedule_summary(group: dict) -> None:
    if messages_to_fold(group):
        asyncio.create_task(update_summary(group))


# ---------------------------------------------------------------------------
# Pins: messages the user wants every member to always see
# ---------------------------------------------------------------------------

def pin_message(group: dict, message_id: str) -> Optional[str]:
    """Pin a message. Returns an error, or None."""
    pins = group.setdefault("pinned", [])
    if any(p["id"] == message_id for p in pins):
        return None
    msg = next((m for m in group["messages"] if m["id"] == message_id), None)
    if not msg or msg["role"] not in ("user", "member"):
        return "Message not found"
    if len(pins) >= MAX_PINS:
        return f"At most {MAX_PINS} pinned messages; unpin one first"
    pins.append({"id": msg["id"], "who": _speaker(msg), "content": msg["content"],
                 "timestamp": msg.get("timestamp")})
    return None


def unpin_message(group: dict, message_id: str) -> None:
    group["pinned"] = [p for p in group.get("pinned") or [] if p["id"] != message_id]


def clear_messages(group: dict) -> None:
    """Empty the chat, with its summary and pins."""
    group["messages"] = []
    group["pinned"] = []
    group["_cleared"] = group.get("_cleared", 0) + 1
    for k in ("summary", "summary_upto", "summary_count"):
        group.pop(k, None)


async def broadcast_context(group: dict) -> None:
    try:
        info = context_info(group)
    except Exception:
        logger.debug("groupchat: context info failed", exc_info=True)
        return
    await _broadcast({"type": "group_context", "group_id": group["id"], "context": info})


# ---------------------------------------------------------------------------
# Room turn
# ---------------------------------------------------------------------------

def _spoke_last_index(group: dict, member_id: str) -> int:
    for i in range(len(group["messages"]) - 1, -1, -1):
        if group["messages"][i].get("author") == member_id:
            return i
    return -1


def _has_news(group: dict, member_id: str) -> bool:
    """True when someone else said something since this member last spoke."""
    last = _spoke_last_index(group, member_id)
    return any(m["role"] in ("user", "member") and m.get("author") != member_id
               for m in group["messages"][last + 1:])


async def run_room_turn(group_id: str, token: str) -> None:
    group = groups.get(group_id)
    if not group:
        return

    def cancelled() -> bool:
        return group.get("_turn") != token

    replies = 0
    started = time.time()
    last_reply = ""
    try:
        for rnd in range(MAX_ROUNDS):
            mentioned = _mentioned_since_user(group)
            ids = mentioned or [m["id"] for m in group["members"]]
            order = [m for m in group["members"] if m["id"] in ids]
            if order:
                shift = rnd % len(order)
                order = order[shift:] + order[:shift]

            spoke = 0
            for member in order:
                if cancelled() or replies >= MAX_REPLIES:
                    return
                if not _has_news(group, member["id"]):
                    continue
                await _set_status(group, "running", member["id"])
                try:
                    reply = await _run_member(group, member, build_prompt(group, member))
                except Exception as exc:
                    logger.warning("groupchat: %s failed: %s", member["name"], exc)
                    reply = f"(error: {exc})"
                if cancelled():
                    return
                if not reply or PASS_RE.match(reply):
                    continue
                msg = make_message("member", reply, member)
                append_message(group, msg)
                replies += 1
                spoke += 1
                last_reply = reply
                await _broadcast({"type": "group_message", "group_id": group_id, "message": msg})
                await _relay(group, msg)
            if spoke == 0:
                break
    finally:
        if not cancelled():
            group.pop("_turn", None)
            await _set_status(group, "idle", None)
            save_groups()
            await broadcast_context(group)
            _schedule_summary(group)
            if replies:
                # Same rule as single sessions: a sticker only for long turns.
                try:
                    from helm.kelvin_stickers import done_sticker_for_task
                    done_sticker_for_task(time.time() - started, last_reply, source="group")
                except Exception:
                    logger.debug("Couldn't show the done sticker", exc_info=True)


async def send_user_message(group: dict, text: str, source: str = "web") -> dict:
    """Post the user's message and start a new room turn (ending any running one)."""
    try:   # "@codex …" adds Codex to the group if it isn't a member yet
        from helm.mention_router import add_mentioned_members
        await add_mentioned_members(group, text)
    except Exception as exc:
        logger.warning("groupchat: adding mentioned AIs failed: %s", exc)
    _kill_running(group)
    msg = make_message("user", text, source=source)
    append_message(group, msg)
    if source != "web":
        # Sent from a chat app: show this group in the RAPR app too.
        await _broadcast({"type": "group_open", "group_id": group["id"]})
    await _broadcast({"type": "group_message", "group_id": group["id"], "message": msg})
    await _relay(group, msg)
    await broadcast_context(group)
    token = uuid4().hex
    group["_turn"] = token
    save_groups()
    asyncio.create_task(run_room_turn(group["id"], token))
    return msg


async def stop_group(group: dict) -> None:
    group.pop("_turn", None)
    _kill_running(group)
    await _set_status(group, "idle", None)
    save_groups()
