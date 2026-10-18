"""
helm/audit.py — A record of what RAPR asked, what you decided, and why.

One JSON line per event in user data/audit.jsonl:
  approval_requested, approval_resolved (approved | denied | timeout),
  rule_applied (a rule decided without asking).
Nothing leaves your machine; the file is yours to read, export or delete.

Tamper evidence: each line carries `prev` (the previous line's `h`) and
`h = HMAC-SHA256(key, prev + line)`, with the key in user data/.audit_key.
verify() walks the chain, so editing, inserting, reordering or removing a line
in the middle shows up. Removing lines from the very end can't be detected from
the file alone; compare verify()'s `head` with one you noted earlier.
Lines written before the chain existed are counted as `legacy`, not checked.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import threading
import time
from typing import Optional

from helm.config import logger

_lock = threading.Lock()
_head: dict = {}   # path -> (file size, last h) so record() needn't re-read the file


def _path():
    from helm.paths import user_data_dir
    return user_data_dir() / "audit.jsonl"


def _key() -> bytes:
    kp = _path().with_name(".audit_key")
    try:
        return bytes.fromhex(kp.read_text().strip())
    except FileNotFoundError:
        pass
    key = secrets.token_bytes(32)
    kp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(kp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key.hex())
    return key


def _canonical(entry: dict) -> str:
    return json.dumps({k: v for k, v in entry.items() if k != "h"},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sign(key: bytes, entry: dict) -> str:
    return hmac.new(key, _canonical(entry).encode("utf-8"), hashlib.sha256).hexdigest()


def _last_hash(path) -> str:
    """`h` of the file's last line ("" for a new file or a legacy last line)."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return ""
    cached = _head.get(str(path))
    if cached and cached[0] == size:
        return cached[1]
    with open(path, "rb") as f:
        f.seek(max(0, size - 65536))
        tail = f.read().decode("utf-8", errors="replace").splitlines()
    for raw in reversed(tail):
        if raw.strip():
            try:
                return json.loads(raw).get("h", "")
            except (json.JSONDecodeError, AttributeError):
                return ""
    return ""


def record(event: str, **fields) -> None:
    line = {"ts": round(time.time(), 3), "event": event, **{k: v for k, v in fields.items() if v is not None}}
    try:
        line = json.loads(json.dumps(line, ensure_ascii=False, default=str))  # hash what read() will see
        path = _path()
        with _lock:
            line["prev"] = _last_hash(path)
            line["h"] = _sign(_key(), line)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
            _head[str(path)] = (path.stat().st_size, line["h"])
    except Exception as exc:
        logger.debug("audit write failed: %s", exc)


def verify() -> dict:
    """Check the chain. Returns {ok, entries, legacy, head, problem}; problem is
    {line, reason} for the first break (1-based line number), else None."""
    result = {"ok": True, "entries": 0, "legacy": 0, "head": "", "problem": None}

    def broken(n: int, reason: str) -> dict:
        result.update(ok=False, problem={"line": n, "reason": reason})
        return result

    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return result
    with _lock:
        key = _key()
    prev = None   # None until the first chained line
    for n, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            return broken(n, "not a valid entry")
        if not isinstance(entry, dict):
            return broken(n, "not a valid entry")
        if "h" not in entry:
            if prev is not None:
                return broken(n, "unsigned entry after signing began")
            result["legacy"] += 1
            continue
        if entry.get("prev", "") != (prev or ""):
            return broken(n, "entry before this one is missing or changed")
        if not hmac.compare_digest(str(entry["h"]), _sign(key, entry)):
            return broken(n, "entry was edited")
        prev = entry["h"]
        result["entries"] += 1
    result["head"] = prev or ""
    return result


def read(since: float = 0.0, event: Optional[str] = None, query: str = "", limit: int = 500) -> list[dict]:
    try:
        lines = _path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    q = query.lower()
    out = []
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if entry.get("ts", 0) < since:
            break
        if event and entry.get("event") != event:
            continue
        if q and q not in json.dumps({k: v for k, v in entry.items() if k not in ("h", "prev")},
                                     ensure_ascii=False).lower():
            continue
        out.append(entry)
        if len(out) >= limit:
            break
    return out


def to_csv(entries: list[dict]) -> str:
    cols = ["ts", "event", "id", "action", "description", "status", "source", "rule", "session_id"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for e in entries:
        w.writerow({c: e.get(c, "") for c in cols})
    return buf.getvalue()
