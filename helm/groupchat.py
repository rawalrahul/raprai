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
CONTEXT_MESSAGES = 30          # most recent room messages shown to a member
REPLY_TIMEOUT = 600            # seconds one member may take to answer
PASS_RE = re.compile(r"^\s*\(?\s*pass\s*\)?\s*\.?\s*$", re.IGNORECASE)
_ANSI_ESC_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

groups: dict[str, dict] = {}   # group_id -> group
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
    except Exception as exc:
        logger.warning("groupchat: could not load groups: %s", exc)


def save_groups() -> None:
    try:
        path = _store_path()
        payload = {"groups": [_public(g) for g in groups.values()]}
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


def member_from_session(sess: dict) -> dict:
    return {
        "id": f"m-{uuid4().hex[:6]}",
        "session_id": sess["id"],
        "ai": sess.get("ai"),
        "model": sess.get("model"),
        "name": sess.get("name") or sess.get("ai") or "AI",
        "emoji": sess.get("emoji") or "🤖",
        "color": sess.get("color") or "#6b7280",
        "cwd": sess.get("cwd") or _st.last_cwd,
    }


def make_group(name: str, about: str, sessions: list[dict]) -> dict:
    members = [member_from_session(s) for s in sessions]
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


def make_message(role: str, content: str, member: Optional[dict] = None) -> dict:
    msg = {
        "id": f"gm-{uuid4().hex[:8]}",
        "role": role,                 # user | member | system
        "content": content,
        "timestamp": _now(),
    }
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


def build_prompt(group: dict, member: dict) -> str:
    others = [m for m in group["members"] if m["id"] != member["id"]]
    roster = ", ".join(f'{m["name"]} ({m["ai"]})' for m in others) or "nobody else"
    header = f'[Group chat: "{group["name"]}" - with the user, {roster}]'

    history = [m for m in group["messages"] if m["role"] in ("user", "member")]
    recent = history[-CONTEXT_MESSAGES:]
    lines = []
    if len(history) > len(recent):
        lines.append(f"(… {len(history) - len(recent)} earlier messages not shown)")
    for msg in recent:
        who = "You" if msg.get("author") == member["id"] else _speaker(msg)
        lines.append(f"{who}: {msg['content']}")
    transcript = "\n\n".join(lines) or "(no messages yet)"

    about = f'What this group is for: {group["about"]}\n\n' if group.get("about") else ""
    return (
        f"{header}\n\n"
        f"You are {member['name']}, one of several AI assistants in a group chat "
        f"with the user. {about}"
        f"Conversation so far (oldest first):\n\n{transcript}\n\n"
        f"---\nWrite your next message to the group as {member['name']}.\n"
        "- Answer the user directly, and build on, correct or agree with the other "
        "assistants instead of repeating them.\n"
        "- Address someone with @Name (e.g. @" + (others[0]["name"].split()[0] if others else "User")
        + ") when you want a specific member to respond.\n"
        "- If you have nothing useful to add, reply with exactly: (pass)\n"
        "- Reply with your message only: no name prefix, no preamble."
    )


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
    except Exception:
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
    env = {**os.environ, **extra_env} if extra_env else None
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
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Broadcast helpers
# ---------------------------------------------------------------------------

async def _broadcast(event: dict) -> None:
    from helm.broadcast import broadcast
    await broadcast(event)


async def broadcast_group(group: dict) -> None:
    await _broadcast({"type": "group_updated", "group": _public(group)})


async def _set_status(group: dict, status: str, speaking: Optional[str] = None) -> None:
    group["status"] = status
    group["speaking"] = speaking
    await _broadcast({"type": "group_status", "group_id": group["id"],
                      "status": status, "speaking": speaking})


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
                await _broadcast({"type": "group_message", "group_id": group_id, "message": msg})
            if spoke == 0:
                break
    finally:
        if not cancelled():
            group.pop("_turn", None)
            await _set_status(group, "idle", None)
            save_groups()


async def send_user_message(group: dict, text: str) -> dict:
    """Post the user's message and start a new room turn (ending any running one)."""
    _kill_running(group)
    msg = make_message("user", text)
    append_message(group, msg)
    await _broadcast({"type": "group_message", "group_id": group["id"], "message": msg})
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
