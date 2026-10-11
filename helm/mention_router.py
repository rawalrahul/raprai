"""
helm/mention_router.py — start or add AIs by @mentioning them.

A message that STARTS with @mentions of AIs (from the app, Telegram, WhatsApp…):

  "@codex fix the tests"
    • No AI session open, or you've moved the open session to another folder
      since its last task → a new Codex session in the current folder, and the
      rest of the message goes to it.
    • An AI session (say Claude) is open and still in the folder it was working
      in → it becomes a group chat with Claude and Codex (the last few exchanges
      are copied in, so Codex knows the context), and the message goes to the group.
      Mentioning another AI from that session later adds it to the same group.
    • "@claude …" while Claude is the open session → just a normal message.

  "@claude @codex compare approaches" with nothing open → a new group with both.

Inside a group chat, a leading @mention of an AI that isn't a member adds it
(see add_mentioned_members, used by groupchat.send_user_message).

Only mentions at the very start count, and only names of AIs RAPR knows, so
"ask @codex later" or an email address is just text.
"""

from __future__ import annotations

import os
import re
from typing import Optional

import helm.state as _st
from helm.config import logger

USER_CHANNELS = {"web", "telegram", "whatsapp", "discord", "slack"}
CONTEXT_EXCHANGES = 6            # messages copied from the session into a new group

_LEAD_RE = re.compile(r"^\s*((?:@[\w.\-]+[\s,:]*)+)(.*)$", re.DOTALL)
_TOKEN_RE = re.compile(r"@([\w.\-]+)")


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

# Extra short names. Deliberately no first-word matching ("Open Interpreter" must
# not make "@open the file" start an AI).
_SHORT_NAMES = {"agy": "antigravity", "qwen": "qwen_code", "kiro": "amazon_q"}


def _ai_names() -> dict[str, str]:
    """Lower-case name → AI key, for Claude and every loaded integration.
    Keys win over display names (so @claude is Claude Code, not "Claude Code (Ollama)")."""
    names: dict[str, str] = {"claude": "claude"}
    for key in _st.integrations:
        names.setdefault(key.lower(), key)
        names.setdefault(key.lower().replace("_", ""), key)         # @githubmodels
    for alias, key in _SHORT_NAMES.items():
        if key in _st.integrations:
            names.setdefault(alias, key)
    for key, info in _st.integrations.items():
        full = re.sub(r"[^a-z0-9]", "", (info.get("name") or "").lower())   # @claudecodeollama
        if full:
            names.setdefault(full, key)
    return names


def parse_leading(text: str) -> Optional[tuple[list[str], str]]:
    """(AI keys mentioned at the start, rest of the message), or None when the
    message doesn't start with @mentions that are all known AIs."""
    m = _LEAD_RE.match(text or "")
    if not m:
        return None
    tokens = [t.lower() for t in _TOKEN_RE.findall(m.group(1))]
    names = _ai_names()
    if not tokens or any(t not in names for t in tokens):
        return None
    keys = list(dict.fromkeys(names[t] for t in tokens))
    return keys, m.group(2).strip()


def _label(key: str) -> str:
    if key == "claude":
        return "Claude Code"
    return (_st.integrations.get(key) or {}).get("name", key)


def _ready(key: str) -> bool:
    try:
        from helm.ai_runner.core import is_backend_available
        return is_backend_available(key)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Routing a message
# ---------------------------------------------------------------------------

def _same_folder(sess: dict) -> bool:
    """True unless the session was moved to another folder after its last task."""
    last = sess.get("last_task_cwd")
    return not last or os.path.normcase(last) == os.path.normcase(sess.get("cwd") or "")


def _focused_ai_session() -> Optional[dict]:
    sess = _st.sessions.get(_st.focused_id) if _st.focused_id else None
    if sess and sess.get("ai") and sess.get("status") != "stopped":
        return sess
    return None


async def route(text: str, channel: str) -> Optional[str]:
    """Handle a message that starts with @AI mentions. Returns the reply to show,
    or None when the message isn't one (it then goes on as usual)."""
    if channel not in USER_CHANNELS:
        return None
    parsed = parse_leading(text)
    if not parsed:
        return None
    keys, rest = parsed

    not_ready = [k for k in keys if not _ready(k)]
    if not_ready:
        names = ", ".join(_label(k) for k in not_ready)
        return (f"{names} isn't set up yet. Install it (Settings → AI Integrations lists "
                f"the command), then try again.")

    focused = _focused_ai_session()
    if focused and keys == [focused["ai"]]:
        return None                                   # "@claude …" in the Claude session

    if focused and _same_folder(focused):
        others = [k for k in keys if k != focused["ai"]]
        return await _into_group(focused, others, text, channel)

    from helm.session_mgr import session_cwd
    folder = session_cwd()
    if len(keys) == 1:
        return await _new_session(keys[0], rest, folder, channel)
    return await _new_group(keys, text, folder, channel)


async def _new_session(key: str, rest: str, folder: str, channel: str) -> str:
    from helm.broadcast import push_state
    from helm.session_mgr import make_session
    sess = make_session(key, cwd=folder)
    _st.focused_id = sess["id"]
    await push_state()
    logger.info("mention: started %s in %s", sess["name"], folder)
    if not rest:
        return f"✨ {sess['name']} started in {folder}. Just type your task."
    from helm.ai_runner.core import process_message
    return await process_message(rest, source=channel, session_id=sess["id"])


def _start_member_sessions(keys: list[str], folder: str) -> list[dict]:
    """A session per AI in this folder: reuse an idle open one, else start one."""
    from helm.session_mgr import make_session
    out = []
    for key in keys:
        sess = next((s for s in _st.sessions.values()
                     if s.get("ai") == key and s.get("status") != "stopped" and not s.get("busy")
                     and os.path.normcase(s.get("cwd") or "") == os.path.normcase(folder)), None)
        if sess is None:
            sess = make_session(key, cwd=folder)
            sess["_started_for_group"] = True
        out.append(sess)
    return out


def _copy_context(group: dict, sess: dict, member: dict) -> None:
    """Copy the session's last exchanges into the group so new members know the context."""
    import helm.groupchat as gc
    msgs = [m for m in _st.chat_history
            if m.get("session_id") == sess["id"] and m.get("role") in ("user", "assistant")
            and (m.get("content") or "").strip()]
    for m in msgs[-CONTEXT_EXCHANGES:]:
        if m["role"] == "user":
            gm = gc.make_message("user", m["content"], source=m.get("source") or "web")
        else:
            gm = gc.make_message("member", m["content"], member=member)
        group["messages"].append(gm)


async def _open(group: dict, channel: str) -> None:
    """Show the group where the user is: chat apps switch into it, the app opens it."""
    import helm.groupchat as gc
    if channel == "web":
        await gc._broadcast({"type": "group_open", "group_id": group["id"]})
    else:
        gc.set_active_group(channel, group["id"])


async def _into_group(focused: dict, keys: list[str], text: str, channel: str) -> str:
    import helm.groupchat as gc
    from helm.broadcast import push_message, push_state
    gc.load_groups()
    group = gc.groups.get(focused.get("mention_group_id") or "")
    if group and not any(m["session_id"] == focused["id"] for m in group["members"]):
        group = None
    folder = focused.get("cwd") or _st.last_cwd
    if group is None:
        sessions = [focused] + _start_member_sessions(keys, folder)
        if len(sessions) > gc.MAX_MEMBERS:
            return f"A group can have at most {gc.MAX_MEMBERS} members."
        group = gc.make_group("", "", sessions)
        group["started_session_ids"] = [s["id"] for s in sessions if s.pop("_started_for_group", False)]
        _copy_context(group, focused, group["members"][0])
        focused["mention_group_id"] = group["id"]
        action = "Started"
    else:
        added = await add_members(group, keys)
        if added is None:
            return f"A group can have at most {gc.MAX_MEMBERS} members."
        action = "Added to"
    gc.save_groups()
    await push_state()
    await gc.broadcast_group(group)
    await _open(group, channel)
    names = ", ".join(m["name"] for m in group["members"])
    note = f"💬 {action} the group chat \"{group['name']}\" ({names}) in {folder}."
    await push_message("system", note + " Replies continue there.", source=channel,
                       session_id=focused["id"])
    await gc.send_user_message(group, text, source=channel)
    return note + (" Replies will follow here." if channel != "web" else "")


async def _new_group(keys: list[str], text: str, folder: str, channel: str) -> str:
    import helm.groupchat as gc
    from helm.broadcast import push_state
    gc.load_groups()
    sessions = _start_member_sessions(keys, folder)
    if len(sessions) > gc.MAX_MEMBERS:
        return f"A group can have at most {gc.MAX_MEMBERS} members."
    group = gc.make_group("", "", sessions)
    group["started_session_ids"] = [s["id"] for s in sessions if s.pop("_started_for_group", False)]
    gc.save_groups()
    await push_state()
    await gc.broadcast_group(group)
    await _open(group, channel)
    await gc.send_user_message(group, text, source=channel)
    names = ", ".join(m["name"] for m in group["members"])
    return f"💬 Started the group chat \"{group['name']}\" ({names}) in {folder}." + (
        " Replies will follow here." if channel != "web" else "")


# ---------------------------------------------------------------------------
# Inside a group
# ---------------------------------------------------------------------------

async def add_members(group: dict, keys: list[str]) -> Optional[list[dict]]:
    """Add a member for each AI key not already in the group. None if too many."""
    import helm.groupchat as gc
    have = {m.get("ai") for m in group["members"]}
    keys = [k for k in keys if k not in have and _ready(k)]
    if not keys:
        return []
    if len(group["members"]) + len(keys) > gc.MAX_MEMBERS:
        return None
    folder = (group["members"][0].get("cwd") if group["members"] else None) or _st.last_cwd
    sessions = _start_member_sessions(keys, folder)
    started = group.setdefault("started_session_ids", [])
    added = []
    for s in sessions:
        if s.pop("_started_for_group", False):
            started.append(s["id"])
        m = gc.member_from_session(s)
        group["members"].append(m)
        added.append(m)
    return added


async def add_mentioned_members(group: dict, text: str) -> list[dict]:
    """A group message starting with @AI mentions adds the AIs that aren't members yet."""
    import helm.groupchat as gc
    m = _LEAD_RE.match(text or "")
    if not m:
        return []
    names = _ai_names()
    member_names = set().union(*(gc._aliases(x) for x in group["members"])) if group["members"] else set()
    keys = []
    for tok in (t.lower() for t in _TOKEN_RE.findall(m.group(1))):
        if tok in member_names or tok == "all":
            continue
        if tok in names:
            keys.append(names[tok])
    if not keys:
        return []
    added = await add_members(group, list(dict.fromkeys(keys))) or []
    if added:
        from helm.broadcast import push_state
        gc.save_groups()
        await push_state()
        await gc.broadcast_group(group)
        logger.info("mention: added %s to group %s", [a["name"] for a in added], group["id"])
    return added
