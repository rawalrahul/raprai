"""
helm/mcp_usage.py: what the RAPR MCP server's AIs have done, kept in one small JSON file.

Every AI that `rapr mcp` runs (ask_agent, second_opinion, relays, teams, bake-offs) adds a
line here: which AI, how long it took, roughly how many tokens went in and out, and whether
it answered. The file is read by

  - the RAPR band in Claude Code (integrations/claude-code-plugin), the ribbon above the prompt,
  - the `usage` MCP tool, for clients without a band (Codex, Cursor, Antigravity...),
  - the RAPR app's usage ribbon (/api/usage), so work done from an editor shows there too.

It lives at a fixed place in the home folder, not the RAPR data folder, so the band finds
it whether or not the app is installed: ~/.config/rapr/mcp-usage.json, or RAPR_MCP_USAGE_FILE.
Counters for "today" start over at local midnight; "total" never does.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VERSION = 1
_lock = threading.Lock()


def usage_file() -> Path:
    override = os.environ.get("RAPR_MCP_USAGE_FILE", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".config" / "rapr" / "mcp-usage.json"


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _empty_bucket() -> dict:
    return {"calls": 0, "failed": 0, "seconds": 0.0, "tokens": 0, "agents": {}}


def _empty() -> dict:
    return {"version": VERSION, "day": _today(), "updated": 0.0,
            "today": _empty_bucket(), "total": _empty_bucket(), "last": None}


def load() -> dict:
    """The usage file, with today's counters reset if the day has changed. Never raises."""
    try:
        data = json.loads(usage_file().read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != VERSION:
            return _empty()
    except (OSError, ValueError):
        return _empty()
    for key in ("today", "total"):
        if not isinstance(data.get(key), dict):
            data[key] = _empty_bucket()
    if data.get("day") != _today():
        data["day"] = _today()
        data["today"] = _empty_bucket()
    return data


def _add(bucket: dict, agent: str, name: str, seconds: float, tokens: int, ok: bool) -> None:
    bucket["calls"] = bucket.get("calls", 0) + 1
    bucket["failed"] = bucket.get("failed", 0) + (0 if ok else 1)
    bucket["seconds"] = round(bucket.get("seconds", 0.0) + seconds, 1)
    bucket["tokens"] = bucket.get("tokens", 0) + tokens
    a = bucket.setdefault("agents", {}).setdefault(agent, {"name": name, "calls": 0, "failed": 0,
                                                          "seconds": 0.0, "tokens": 0})
    a["name"] = name
    a["calls"] += 1
    a["failed"] += 0 if ok else 1
    a["seconds"] = round(a["seconds"] + seconds, 1)
    a["tokens"] += tokens


def record(agent: str, seconds: float, prompt: str = "", reply: str = "", ok: bool = True,
           name: Optional[str] = None) -> None:
    """Add one AI run. Tokens are estimated as characters / 4 (the CLIs don't all report them).
    A failure to write is logged, never raised: usage must not break a tool call."""
    tokens = (len(prompt or "") + len(reply or "")) // 4
    seconds = max(0.0, float(seconds))
    name = name or agent
    with _lock:
        try:
            data = load()
            _add(data["today"], agent, name, seconds, tokens, ok)
            _add(data["total"], agent, name, seconds, tokens, ok)
            now = time.time()
            data["updated"] = now
            data["last"] = {"agent": agent, "name": name, "seconds": round(seconds, 1),
                            "tokens": tokens, "ok": ok, "at": now}
            path = usage_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            os.replace(tmp, path)     # the band never reads half a file
        except OSError:
            logger.warning("Couldn't save MCP usage", exc_info=True)


# ---------------------------------------------------------------------------
# Words for people
# ---------------------------------------------------------------------------

def fmt_seconds(s: float) -> str:
    s = int(round(s))
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _bucket_line(b: dict) -> str:
    calls = b.get("calls", 0)
    line = (f"{calls} call{'s' if calls != 1 else ''}, {fmt_seconds(b.get('seconds', 0))} of AI time, "
            f"~{fmt_tokens(b.get('tokens', 0))} tokens")
    if b.get("failed"):
        line += f", {b['failed']} failed"
    return line


def summary(data: Optional[dict] = None) -> str:
    """The ribbon as text: what the `usage` tool answers."""
    data = data or load()
    today, total = data["today"], data["total"]
    if not total.get("calls"):
        return "RAPR usage: no AI has been run through RAPR yet."
    lines = [f"RAPR usage today: {_bucket_line(today)}"]
    agents = sorted(today.get("agents", {}).items(), key=lambda kv: -kv[1].get("seconds", 0))
    for _key, a in agents:
        lines.append(f"- {a.get('name') or _key}: {_bucket_line(a)}")
    lines.append(f"All time: {_bucket_line(total)}")
    last = data.get("last")
    if last:
        ago = fmt_seconds(max(0, time.time() - last.get("at", 0)))
        lines.append(f"Last: {last.get('name')} took {fmt_seconds(last.get('seconds', 0))}"
                     f"{'' if last.get('ok') else ' and failed'}, {ago} ago")
    lines.append("Tokens are estimated from text length (4 characters a token).")
    return "\n".join(lines)
