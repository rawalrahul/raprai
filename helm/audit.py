"""
helm/audit.py — A record of what RAPR asked, what you decided, and why.

One JSON line per event in user data/audit.jsonl:
  approval_requested, approval_resolved (approved | denied | timeout),
  rule_applied (a rule decided without asking).
Nothing leaves your machine; the file is yours to read, export or delete.
"""

from __future__ import annotations

import csv
import io
import json
import time
from typing import Optional

from helm.config import logger


def _path():
    from helm.paths import user_data_dir
    return user_data_dir() / "audit.jsonl"


def record(event: str, **fields) -> None:
    line = {"ts": round(time.time(), 3), "event": event, **{k: v for k, v in fields.items() if v is not None}}
    try:
        with open(_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
    except Exception as exc:
        logger.debug("audit write failed: %s", exc)


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
        if q and q not in json.dumps(entry, ensure_ascii=False).lower():
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
