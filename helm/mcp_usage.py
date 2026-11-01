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

It also keeps each AI's plan limits exactly as the AI itself reports them ("limits"), so the
ribbon shows the same numbers as the AI's own usage page. They are read live from each AI's
own service (helm/usage_readers.py, kept under "live"); between readings, runs update them:

  - Claude: the `rate_limit_event` every `claude -p --output-format stream-json` run prints
    (the 5-hour and weekly windows of your plan, as on claude.ai's usage page).
  - Codex: the `token_count` events Codex writes to its session files in ~/.codex/sessions
    (the 5-hour and weekly windows, as Codex's /status shows them).

Plan windows exist only on a subscription (Claude Pro/Max, ChatGPT Plus/Pro...). An AI used
with an API key is billed per token and has no 5-hour or weekly limit, so RAPR keeps each AI's
billing ("billing": plan or api) and never shows plan windows for an API account, nor an API
price as money spent on a plan (Claude's total_cost_usd is a list price, not a bill, there):

  - Claude: the `apiKeySource` of its stream-json init line ("none" is a claude.ai sign-in),
    and Bedrock / Vertex / Foundry settings, which are API billing.
  - Codex: ~/.codex/auth.json says whether it signed in with ChatGPT or an API key (only the
    kind of sign-in is read, never the key).

Token counts are exact where the AI reports them (Claude's result, Codex's session file)
and estimated from text length otherwise; "estimated" counts how many tokens were guessed.
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
    return {"calls": 0, "failed": 0, "seconds": 0.0, "tokens": 0, "estimated": 0, "cost_usd": 0.0,
            "agents": {}}


def _empty() -> dict:
    return {"version": VERSION, "day": _today(), "updated": 0.0,
            "today": _empty_bucket(), "total": _empty_bucket(), "last": None, "limits": {},
            "billing": {}, "live": {}}


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
    for key in ("limits", "billing", "live"):
        if not isinstance(data.get(key), dict):
            data[key] = {}
    if data.get("day") != _today():
        data["day"] = _today()
        data["today"] = _empty_bucket()
    return data


def _add(bucket: dict, agent: str, name: str, seconds: float, tokens: int, estimated: bool,
         cost: Optional[float], ok: bool) -> None:
    a = bucket.setdefault("agents", {}).setdefault(agent, {"name": name})
    a["name"] = name
    for b in (bucket, a):
        b["calls"] = b.get("calls", 0) + 1
        b["failed"] = b.get("failed", 0) + (0 if ok else 1)
        b["seconds"] = round(b.get("seconds", 0.0) + seconds, 1)
        b["tokens"] = b.get("tokens", 0) + tokens
        b["estimated"] = b.get("estimated", 0) + (tokens if estimated else 0)
        b["cost_usd"] = round(b.get("cost_usd", 0.0) + (cost or 0.0), 6)


def _write(data: dict) -> None:
    data["updated"] = time.time()
    path = usage_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)     # the band never reads half a file


def record(agent: str, seconds: float, prompt: str = "", reply: str = "", ok: bool = True,
           name: Optional[str] = None, tokens: Optional[int] = None,
           cost_usd: Optional[float] = None) -> None:
    """Add one AI run. `tokens` is the AI's own count when it gave one; without it they are
    estimated as characters / 4. A failure to write is logged, never raised: usage must not
    break a tool call."""
    estimated = tokens is None
    if tokens is None:
        tokens = (len(prompt or "") + len(reply or "")) // 4
    seconds = max(0.0, float(seconds))
    name = name or agent
    with _lock:
        try:
            data = load()
            # Money only where it is spent: on an API key. A plan's run has a list price
            # (Claude reports one) that nobody is billed.
            spent = cost_usd if billing(agent, data) == API else None
            _add(data["today"], agent, name, seconds, tokens, estimated, spent, ok)
            _add(data["total"], agent, name, seconds, tokens, estimated, spent, ok)
            data["last"] = {"agent": agent, "name": name, "seconds": round(seconds, 1),
                            "tokens": tokens, "estimated": estimated, "ok": ok, "at": time.time()}
            _write(data)
        except OSError:
            logger.warning("Couldn't save MCP usage", exc_info=True)


# ---------------------------------------------------------------------------
# Plan limits, as each AI reports them
# ---------------------------------------------------------------------------

WINDOW_LABELS = {"five_hour": "5h", "seven_day": "week", "seven_day_opus": "week Opus",
                 "seven_day_sonnet": "week Sonnet", "primary": "5h", "secondary": "week"}


def _label(key: str, minutes: Optional[float] = None) -> str:
    if minutes:
        if minutes <= 24 * 60:
            return f"{round(minutes / 60)}h"
        if round(minutes / (24 * 60)) == 7:
            return "week"
        return f"{round(minutes / (24 * 60))}d"
    return WINDOW_LABELS.get(key, key.replace("_", " "))


PLAN, API = "plan", "api"


def set_billing(agent: str, name: str, mode: str, source: str) -> None:
    """How the AI is paid for: PLAN (a subscription, with 5-hour and weekly windows) or API
    (per token, no windows). Switching to API drops the plan windows kept for it."""
    with _lock:
        try:
            data = load()
            old = (data["billing"].get(agent) or {}).get("mode")
            if old == mode and (mode == PLAN or agent not in data["limits"]):
                return
            data["billing"][agent] = {"name": name, "mode": mode, "source": source, "at": time.time()}
            if mode == API:
                data["limits"].pop(agent, None)
            _write(data)
        except OSError:
            logger.warning("Couldn't save %s's billing", agent, exc_info=True)


def billing(agent: str, data: Optional[dict] = None) -> Optional[str]:
    """PLAN, API, or None when the AI hasn't said."""
    data = data or load()
    return (data.get("billing", {}).get(agent) or {}).get("mode")


def set_limits(agent: str, name: str, windows: list[dict], source: str) -> None:
    """Keep an AI's plan windows: [{key, label, pct, resets_at}] (pct 0-100, resets_at unix).
    Only a subscription has them, so this also marks the AI as on a plan."""
    windows = [w for w in windows if isinstance(w.get("pct"), (int, float))]
    if not windows:
        return
    with _lock:
        try:
            data = load()
            data["limits"][agent] = {"name": name, "windows": windows, "source": source, "at": time.time()}
            data["billing"][agent] = {"name": name, "mode": PLAN, "source": source, "at": time.time()}
            _write(data)
        except OSError:
            logger.warning("Couldn't save %s's plan limits", agent, exc_info=True)


def limits(data: Optional[dict] = None) -> dict:
    """Every AI's plan windows; a window whose reset time has passed reads 0% (it started over).
    An AI on an API key has none, whatever was kept from before."""
    data = data or load()
    now = time.time()
    out = {}
    for agent, lim in (data.get("limits") or {}).items():
        if billing(agent, data) == API:
            continue
        wins = []
        for w in lim.get("windows") or []:
            w = dict(w)
            if w.get("resets_at") and w["resets_at"] < now:
                w["pct"], w["reset"] = 0.0, True
            wins.append(w)
        out[agent] = {**lim, "windows": wins}
    return out


def claude_windows(event: dict) -> list[dict]:
    """The windows in one `rate_limit_event` line of Claude's stream-json output."""
    info = event.get("rate_limit_info") if isinstance(event, dict) else None
    if not isinstance(info, dict):
        return []
    found = {}
    unified = info.get("unifiedWindows")
    if isinstance(unified, dict):
        for key, w in unified.items():
            if isinstance(w, dict) and isinstance(w.get("utilization"), (int, float)):
                found[key] = w
    kind = info.get("rateLimitType")
    if kind and kind not in found and isinstance(info.get("utilization"), (int, float)):
        found[kind] = info
    return [{"key": k, "label": _label(k), "pct": round(float(w["utilization"]) * 100, 1),
             "resets_at": w.get("resetsAt")} for k, w in found.items()]


CLAUDE_API_ENV = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY")


def claude_mode(init: dict, env: Optional[dict] = None) -> Optional[str]:
    """PLAN or API from Claude's stream-json init line: `apiKeySource` is "none" when it is
    signed in to claude.ai, else names the key (ANTHROPIC_API_KEY, apiKeyHelper...)."""
    env = os.environ if env is None else env
    if any(str(env.get(k, "")).strip() not in ("", "0", "false") for k in CLAUDE_API_ENV):
        return API
    src = init.get("apiKeySource") if isinstance(init, dict) else None
    if not isinstance(src, str):
        return None
    return PLAN if src == "none" else API


def note_claude_init(event: dict) -> None:
    mode = claude_mode(event)
    if mode:
        set_billing("claude", "Claude", mode, "claude init apiKeySource")


def note_claude_event(event: dict) -> None:
    """Keep Claude's plan windows from a stream-json `rate_limit_event`."""
    wins = claude_windows(event)
    if wins:
        set_limits("claude", "Claude", wins, "claude rate_limit_event")


def codex_windows(rate_limits: dict, seen_at: Optional[float] = None) -> list[dict]:
    """Codex's `rate_limits` ({primary, secondary}: used_percent, window_minutes, resets_at
    or resets_in_seconds) as windows."""
    out = []
    for key in ("primary", "secondary"):
        w = rate_limits.get(key) if isinstance(rate_limits, dict) else None
        if not isinstance(w, dict) or not isinstance(w.get("used_percent"), (int, float)):
            continue
        resets = w.get("resets_at")
        if resets is None and isinstance(w.get("resets_in_seconds"), (int, float)):
            resets = (seen_at or time.time()) + w["resets_in_seconds"]
        out.append({"key": key, "label": _label(key, w.get("window_minutes")),
                    "pct": round(float(w["used_percent"]), 1),
                    "resets_at": int(resets) if resets else None})
    return out


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def _newest_rollouts(limit: int = 3) -> list[Path]:
    """Codex's newest session files: sessions/YYYY/MM/DD/rollout-*.jsonl, newest day first."""
    root = codex_home() / "sessions"
    files: list[Path] = []
    try:
        for y in sorted((p for p in root.iterdir() if p.is_dir()), reverse=True):
            for m in sorted((p for p in y.iterdir() if p.is_dir()), reverse=True):
                for d in sorted((p for p in m.iterdir() if p.is_dir()), reverse=True):
                    files += sorted(d.glob("rollout-*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
                    if len(files) >= limit:
                        return files[:limit]
    except OSError:
        pass
    return files[:limit]


def _tail_lines(path: Path, size: int = 256_000) -> list[str]:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        f.seek(max(0, end - size))
        return f.read().decode("utf-8", "replace").splitlines()


def codex_session_reading(path: Path) -> tuple[Optional[dict], Optional[int]]:
    """The last rate_limits and total tokens in one Codex session file."""
    rate, tokens = None, None
    for line in reversed(_tail_lines(path)):
        if '"token_count"' not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        p = ev.get("payload") if isinstance(ev.get("payload"), dict) else ev.get("msg") or ev
        if not isinstance(p, dict) or p.get("type") != "token_count":
            continue
        if rate is None and isinstance(p.get("rate_limits"), dict):
            rate = p["rate_limits"]
        info = p.get("info")
        if tokens is None and isinstance(info, dict):
            total = (info.get("total_token_usage") or {}).get("total_tokens")
            if isinstance(total, int):
                tokens = total
        if rate is not None and tokens is not None:
            break
    return rate, tokens


def codex_mode() -> Optional[str]:
    """PLAN when Codex is signed in with ChatGPT, API with an API key, from ~/.codex/auth.json.
    Only which kind of sign-in it holds is looked at."""
    try:
        auth = json.loads((codex_home() / "auth.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(auth, dict):
        return None
    mode = str(auth.get("auth_mode") or "").lower()
    if mode in ("chatgpt", "chatgptauthtokens"):
        return PLAN
    if mode in ("apikey", "api_key", "api"):
        return API
    if auth.get("tokens"):
        return PLAN
    if auth.get("OPENAI_API_KEY"):
        return API
    return None


# ---------------------------------------------------------------------------
# Live readings (helm/usage_readers.py): each AI's own service, asked directly
# ---------------------------------------------------------------------------

def store_readings(readings: dict) -> None:
    """Keep what the readers found: per AI its billing, its plan windows (an API key drops
    any kept from before) and a note for the ribbon when there are none."""
    if not readings:
        return
    with _lock:
        try:
            data = load()
            live = data.setdefault("live", {})
            for agent, r in readings.items():
                d = r.as_dict() if hasattr(r, "as_dict") else dict(r)
                live[agent] = d
                if d.get("mode"):
                    data["billing"][agent] = {"name": d["name"], "mode": d["mode"], "source": d.get("source", ""),
                                              "at": d["at"]}
                if d.get("mode") == API:
                    data["limits"].pop(agent, None)
                elif d.get("windows"):
                    data["limits"][agent] = {"name": d["name"], "windows": d["windows"], "plan": d.get("plan", ""),
                                             "source": d.get("source", ""), "at": d["at"]}
                elif d.get("mode") is None:
                    # Not signed in (or not set up): old windows describe nobody now.
                    data["limits"].pop(agent, None)
                    data["billing"].pop(agent, None)
            _write(data)
        except OSError:
            logger.warning("Couldn't save the usage readings", exc_info=True)


_live = {"at": 0.0, "thread": None}
_live_lock = threading.Lock()


def refresh_live(max_age: float = 120.0, wait: float = 0.0, agents: Optional[list] = None) -> None:
    """Ask each AI's own service for its usage, at most every `max_age` seconds, in the
    background (each answer can take a few seconds). `wait`: how long to wait for it.
    RAPR_USAGE_READERS=0 turns this off (tests: never touch real accounts)."""
    if os.environ.get("RAPR_USAGE_READERS", "").strip() == "0":
        return
    with _live_lock:
        t = _live["thread"]
        if t is None or not t.is_alive():
            if time.monotonic() - _live["at"] < max_age and _live["at"]:
                return
            _live["at"] = time.monotonic()

            def go():
                from helm import usage_readers
                store_readings(usage_readers.read_all(agents))
            t = threading.Thread(target=go, name="usage-readers", daemon=True)
            _live["thread"] = t
            t.start()
    if wait:
        t.join(wait)


def refresh_codex_limits(every: float = 30.0) -> None:
    """Codex's usage, live from `codex app-server` (kept for older callers)."""
    refresh_live(max_age=every, agents=["codex"])


def readings(data: Optional[dict] = None) -> dict:
    """The last live reading of each AI: {agent: {name, mode, plan, windows, note, source, at}}."""
    data = data or load()
    return data.get("live") or {}


def codex_run_tokens(since: float) -> Optional[int]:
    """Tokens of the Codex run that started at `since` (unix time), from its session file."""
    for f in _newest_rollouts(1):
        try:
            if f.stat().st_mtime >= since:
                rate, tokens = codex_session_reading(f)
                if rate and billing("codex") == PLAN:
                    # seconds old, from the run just done: as fresh as the live reading
                    set_limits("codex", "Codex", codex_windows(rate, f.stat().st_mtime), "codex session file")
                return tokens
        except OSError:
            pass
    return None


def claude_stream_result(raw: str) -> tuple[Optional[str], Optional[int], Optional[float]]:
    """From Claude's stream-json output: keep its plan windows, and return the result line
    (the same JSON `--output-format json` prints), its exact token count and its cost."""
    result, tokens, cost = None, None, None
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            note_claude_init(ev)
        elif ev.get("type") == "rate_limit_event":
            note_claude_event(ev)
        elif ev.get("type") == "result":
            result = line
            u = ev.get("usage") or {}
            tokens = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens",
                                                       "cache_creation_input_tokens",
                                                       "cache_read_input_tokens")) or None
            if isinstance(ev.get("total_cost_usd"), (int, float)):
                cost = float(ev["total_cost_usd"])
    return result, tokens, cost


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
    approx = "~" if b.get("estimated") else ""
    line = (f"{calls} call{'s' if calls != 1 else ''}, {fmt_seconds(b.get('seconds', 0))} of AI time, "
            f"{approx}{fmt_tokens(b.get('tokens', 0))} tokens")
    if b.get("cost_usd"):
        line += f", ${b['cost_usd']:.2f} spent on API keys"
    if b.get("failed"):
        line += f", {b['failed']} failed"
    return line


def fmt_reset(at: Optional[float]) -> str:
    if not at:
        return ""
    left = max(0, at - time.time())
    if left >= 86400:
        return f"resets in {int(left // 86400)}d {int(left % 86400 // 3600)}h"
    return "resets in " + fmt_seconds(left)


def limits_lines(data: Optional[dict] = None) -> list[str]:
    lines = []
    for _agent, lim in limits(data).items():
        parts = [f"{w['label']} {w['pct']:.0f}%" + (f" ({fmt_reset(w.get('resets_at'))})" if w.get("resets_at") else "")
                 for w in lim["windows"]]
        ago = fmt_seconds(max(0, time.time() - lim.get("at", 0)))
        plan = f" ({lim['plan']})" if lim.get("plan") else ""
        lines.append(f"- {lim.get('name') or _agent}{plan}: " + ", ".join(parts) + f" (as of {ago} ago)")
    return lines


def summary(data: Optional[dict] = None) -> str:
    """The ribbon as text: what the `usage` tool answers."""
    refresh_live(max_age=60, wait=15)
    data = data or load()
    today, total = data["today"], data["total"]
    lines = []
    plan = limits_lines(data)
    if plan:
        lines += ["Plan usage (subscriptions), as each AI reports it:"] + plan
    notes = [f"- {r.get('name') or k}: {r['note']}" for k, r in readings(data).items()
             if r.get("note") and r.get("mode") != API and k not in limits(data)]
    if notes:
        lines += ["No plan usage to show for:"] + notes
    api = [(k, b) for k, b in (data.get("billing") or {}).items() if b.get("mode") == API]
    if api:
        lines.append("On an API key (billed per token, no 5-hour or weekly limits):")
        for k, b in api:
            a = today.get("agents", {}).get(k) or {}
            lines.append(f"- {b.get('name') or k}: ${a.get('cost_usd', 0):.2f} today through RAPR"
                         + (f", {fmt_tokens(a.get('tokens', 0))} tokens" if a.get("tokens") else ""))
    if not total.get("calls"):
        lines.append("RAPR usage: no AI has been run through RAPR yet.")
        return "\n".join(lines)
    lines.append(f"RAPR usage today: {_bucket_line(today)}")
    agents = sorted(today.get("agents", {}).items(), key=lambda kv: -kv[1].get("seconds", 0))
    for _key, a in agents:
        lines.append(f"- {a.get('name') or _key}: {_bucket_line(a)}")
    lines.append(f"All time: {_bucket_line(total)}")
    last = data.get("last")
    if last:
        ago = fmt_seconds(max(0, time.time() - last.get("at", 0)))
        lines.append(f"Last: {last.get('name')} took {fmt_seconds(last.get('seconds', 0))}"
                     f"{'' if last.get('ok') else ' and failed'}, {ago} ago")
    if today.get("estimated") or total.get("estimated"):
        lines.append("~ : some tokens are estimated from text length, for AIs that don't report them.")
    return "\n".join(lines)
