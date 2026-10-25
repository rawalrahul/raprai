"""
helm/reach.py — The apps your AIs can already reach.

Claude Code, Codex and Gemini each keep their own connected apps: MCP servers
you added to them and, for Claude Code, your claude.ai connectors (Gmail,
Calendar, Slack, Drive...). RAPR doesn't need a second copy of those
connections or their sign-ins: it asks the AI that has them. Add up every AI's
apps and RAPR's own MCP servers and you get more reach than any one AI has,
with several accounts of the same kind side by side (a work Gmail in Claude,
a personal one in Codex).

discover() lists them: it runs `claude mcp list`, `codex mcp list --json` and
`gemini mcp list`, and keeps the answer for a few hours (Claude Code checks
each server's health, which takes a while). Nothing leaves this computer.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from typing import Optional

from helm.config import logger

CACHE_SECONDS = 6 * 3600

AGENTS = {
    "claude": {"name": "Claude Code", "args": ["mcp", "list"]},
    "codex": {"name": "Codex", "args": ["mcp", "list", "--json"]},
    "gemini": {"name": "Gemini CLI", "args": ["mcp", "list"]},
}

# "github: npx -y @mcp/server-github - ✓ Connected"
# "claude.ai Gmail: https://gmail.mcp.claude.com/mcp - ✓ Connected"
# "✓ github: npx ... (stdio) - Connected"   (Gemini)
_LINE = re.compile(r"^\W*(?P<name>[^:\n]+?):\s+(?P<target>.+?)\s+-\s+(?P<status>.+)$")


def _status(text: str) -> str:
    low = text.lower()
    if "auth" in low or "login" in low or "log in" in low:
        return "needs sign-in"
    if "fail" in low or "error" in low or "×" in text or "✗" in text:
        return "not connected"
    if "disabled" in low:
        return "off"
    return "connected"


def label(name: str) -> tuple[str, str]:
    """('Gmail', 'claude.ai') for 'claude.ai Gmail'; ('github', '') otherwise."""
    if name.lower().startswith("claude.ai "):
        return name[len("claude.ai "):].strip(), "claude.ai"
    return name.strip(), ""


def parse_list(text: str) -> list[dict]:
    """Apps from `claude mcp list` / `gemini mcp list` output."""
    apps = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("checking", "no mcp", "configured mcp")):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        name, via = label(m.group("name"))
        apps.append({"name": name, "via": via, "status": _status(m.group("status"))})
    return apps


def parse_codex_json(text: str) -> list[dict]:
    """Apps from `codex mcp list --json`."""
    servers, decoder = [], json.JSONDecoder()
    for m in re.finditer(r"\[", text or ""):           # warnings may come before or after
        try:
            found, _ = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(found, list) and all(isinstance(x, dict) for x in found):
            servers = found
            break
    apps = []
    for s in servers if isinstance(servers, list) else []:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        status = "connected" if s.get("enabled", True) else "off"
        if str(s.get("auth_status", "")).lower() in ("not_logged_in", "notloggedin", "logged_out"):
            status = "needs sign-in"
        apps.append({"name": s["name"], "via": "", "status": status})
    return apps


def _run(exe: str, args: list[str], timeout: float = 90) -> str:
    from helm.subprocess_utils import hidden_kwargs
    proc = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, stdin=subprocess.DEVNULL, **hidden_kwargs())
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def rapr_servers() -> list[dict]:
    """RAPR's own MCP servers (Settings → Packages), running or not."""
    try:
        from helm.mcp import get_manager
        mgr = get_manager()
        return [{"name": s.get("id") or s.get("name"), "via": "RAPR",
                 "status": "connected" if s.get("running") else "off"}
                for s in (mgr.list_servers() if mgr else []) if s.get("id") != "chrome"]
    except Exception as exc:
        logger.debug("reach: RAPR servers unavailable: %s", exc)
        return []


def scan_agent(ai: str) -> Optional[dict]:
    """One AI's own apps, or None when that AI isn't installed."""
    spec = AGENTS[ai]
    exe = shutil.which(ai)
    if not exe:
        return None
    entry = {"ai": ai, "name": spec["name"], "apps": [], "error": ""}
    try:
        out = _run(exe, spec["args"])
        entry["apps"] = parse_codex_json(out) if ai == "codex" else parse_list(out)
    except subprocess.TimeoutExpired:
        entry["error"] = f"{spec['name']} took too long to list its apps"
    except Exception as exc:
        entry["error"] = str(exc)[:200]
    return entry


_cache: dict = {}


def _cache_path():
    from helm.paths import user_data_dir
    return user_data_dir() / "reach.json"


def discover(force: bool = False) -> dict:
    """{"agents": [{ai, name, apps, error}], "rapr": [...], "updated": ts}. Blocking; run in a thread."""
    global _cache
    now = time.time()
    if not force:
        if not _cache:
            try:
                _cache = json.loads(_cache_path().read_text(encoding="utf-8"))
            except Exception:
                _cache = {}
        if _cache and now - _cache.get("updated", 0) < CACHE_SECONDS:
            return {**_cache, "rapr": rapr_servers()}

    rapr = rapr_servers()
    rapr_names = {s["name"] for s in rapr}
    agents = []
    for ai in AGENTS:
        entry = scan_agent(ai)
        if entry is None:
            continue
        # RAPR copies its own servers into Codex's and Gemini's settings; count them once.
        for app in entry["apps"]:
            if ai != "claude" and app["name"] in rapr_names:
                app["via"] = "RAPR"
        entry["apps"] = [a for a in entry["apps"] if a["via"] != "RAPR"]
        agents.append(entry)
    _cache = {"agents": agents, "updated": now}
    try:
        _cache_path().write_text(json.dumps(_cache), encoding="utf-8")
    except Exception as exc:
        logger.debug("reach: could not save: %s", exc)
    return {**_cache, "rapr": rapr}


def summary(data: dict) -> dict:
    """Counts for headlines: how many AIs, how many connected apps in all."""
    connected = [a for ag in data.get("agents", []) for a in ag["apps"] if a["status"] == "connected"]
    connected += [s for s in data.get("rapr", []) if s["status"] == "connected"]
    return {"ais": len(data.get("agents", [])), "apps": len(connected)}


def apps_text(entry: dict) -> str:
    """'Gmail, Google Calendar (claude.ai), github' for one AI."""
    names = [a["name"] + (f" ({a['via']})" if a["via"] else "")
             for a in entry.get("apps", []) if a["status"] == "connected"]
    return ", ".join(names)
