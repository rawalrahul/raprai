"""
Every chat message of a group, kept on disk for good.

The room keeps only its newest messages in group_chats.json. Summaries can
cover far older ones, and expanding a summary (or searching) needs their exact
words, so each user/AI message is also appended to
<user data>/group_archive/<group id>.jsonl when it is posted.

Plain files, so the MCP server (a separate process) can read them too.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Iterable, Optional

from helm.config import logger
from helm.groupchat_context.text import is_chat

_lock = threading.Lock()
_cache: dict[str, tuple[tuple, dict[str, dict]]] = {}   # path -> ((mtime, size), id -> msg)


def _dir() -> Path:
    from helm import groupchat as gc   # follows the room store (tests move it)
    return Path(gc._store_path()).parent / "group_archive"


def path(group_id: str) -> Path:
    safe = "".join(c for c in group_id if c.isalnum() or c in "-_") or "group"
    return _dir() / f"{safe}.jsonl"


def append(group_id: str, msg: dict) -> None:
    if not is_chat(msg):
        return
    p = path(group_id)
    try:
        with _lock:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")
    except OSError as exc:
        logger.warning("groupchat: could not archive a message: %s", exc)


def backfill(group: dict) -> None:
    """Archive a group's current messages if it has no archive yet (groups made
    before the archive existed), so its later summaries can still be opened."""
    p = path(group["id"])
    msgs = [m for m in group.get("messages") or [] if is_chat(m)]
    if p.exists() or not msgs:
        return
    try:
        with _lock:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                for m in msgs:
                    f.write(json.dumps(m, ensure_ascii=False, default=str) + "\n")
    except OSError as exc:
        logger.warning("groupchat: could not archive a group's messages: %s", exc)


def load(group_id: str) -> dict[str, dict]:
    """id -> message for every archived message of the group (cached until the file changes)."""
    p = path(group_id)
    try:
        st = p.stat()
    except OSError:
        return {}
    mtime = (st.st_mtime_ns, st.st_size)
    key = str(p)
    hit = _cache.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    out: dict[str, dict] = {}
    try:
        with open(p, encoding="utf-8") as f:
            for raw in f:
                try:
                    m = json.loads(raw)
                except ValueError:
                    continue          # a half-written last line after a crash
                if isinstance(m, dict) and m.get("id"):
                    out[m["id"]] = m
    except OSError:
        return {}
    _cache[key] = (mtime, out)
    return out


def lookup(group: dict, ids: Iterable[str]) -> list[Optional[dict]]:
    """Messages by id, from the room first and the archive for older ones."""
    live = {m["id"]: m for m in group.get("messages") or []}
    ids = list(ids)
    missing = [i for i in ids if i not in live]
    old = load(group["id"]) if missing else {}
    return [live.get(i) or old.get(i) for i in ids]


def all_messages(group: dict) -> list[dict]:
    """Every chat message of the group, oldest first (archive plus room)."""
    seen: dict[str, dict] = dict(load(group["id"]))
    for m in group.get("messages") or []:
        if is_chat(m):
            seen[m["id"]] = m
    return sorted(seen.values(), key=lambda m: m.get("timestamp") or 0)


def delete(group_id: str) -> None:
    p = path(group_id)
    with _lock:
        _cache.pop(str(p), None)
        try:
            os.remove(p)
        except OSError:
            pass
