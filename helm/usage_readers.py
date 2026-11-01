"""
helm/usage_readers.py: each AI's real usage, asked of the AI's own service, live.

Each reader returns what the AI's own usage page shows, without spending a token:

  - Claude: GET https://api.anthropic.com/api/oauth/usage with Claude Code's own claude.ai
    sign-in (what Claude Code's interactive /usage reads): the 5-hour and weekly windows,
    and the weekly Opus / Sonnet ones where the plan has them.
  - Codex: `codex app-server` (what the Codex IDE extension talks to): account/read says
    ChatGPT plan or API key, account/rateLimits/read gives the windows. RAPR never touches
    Codex's sign-in; Codex reads its own.
  - Gemini: with a Google sign-in, Gemini CLI's per-model daily quota from Google's Code Assist
    service (retrieveUserQuota, what its /stats shows), with Gemini CLI's own sign-in.

A reader returns a Reading, or None when the AI isn't installed or set up. Sign-ins are only
read, never refreshed: refreshing would replace the AI's own tokens and could sign it out.
An expired sign-in gives a Reading with a note; the AI renews it the next time it runs.
Nothing is sent anywhere but the AI's own service.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

PLAN, API = "plan", "api"
TIMEOUT = 10


@dataclass
class Reading:
    agent: str
    name: str
    mode: Optional[str] = None            # PLAN, API, or None when the AI doesn't say
    plan: str = ""                        # "Max", "Plus", "Google AI Pro"... when known
    windows: list = field(default_factory=list)   # [{key, label, pct, resets_at}]
    note: str = ""                        # why there are no windows, in words for people
    source: str = ""

    def as_dict(self) -> dict:
        return {"agent": self.agent, "name": self.name, "mode": self.mode, "plan": self.plan,
                "windows": self.windows, "note": self.note, "source": self.source, "at": time.time()}


def _iso_to_unix(text) -> Optional[int]:
    if not text or not isinstance(text, str):
        return None
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _get_json(url: str, headers: dict, body: Optional[dict] = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={**headers, "Accept": "application/json",
                                                          **({"Content-Type": "application/json"} if data else {})},
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:     # noqa: S310 (fixed https hosts)
        return json.loads(r.read().decode("utf-8") or "{}")


def _truthy_env(*names: str) -> bool:
    return any(os.environ.get(n, "").strip() not in ("", "0", "false", "False") for n in names)


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
CLAUDE_WINDOWS = (("five_hour", "5h"), ("seven_day", "week"),
                  ("seven_day_opus", "week Opus"), ("seven_day_sonnet", "week Sonnet"))


def claude_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def claude_credentials() -> Optional[dict]:
    """Claude Code's claude.ai sign-in ({accessToken, expiresAt, subscriptionType...}):
    ~/.claude/.credentials.json, or on a Mac the keychain item Claude Code keeps it in."""
    text = None
    try:
        text = (claude_config_dir() / ".credentials.json").read_text(encoding="utf-8")
    except OSError:
        if sys.platform == "darwin" and shutil.which("security"):
            try:
                r = subprocess.run(["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                                   capture_output=True, text=True, timeout=5)
                text = r.stdout if r.returncode == 0 else None
            except (OSError, subprocess.SubprocessError):
                text = None
    if not text:
        return None
    try:
        oauth = json.loads(text).get("claudeAiOauth")
    except (ValueError, AttributeError):
        return None
    return oauth if isinstance(oauth, dict) and oauth.get("accessToken") else None


def claude_windows_from_usage(data: dict) -> list[dict]:
    """The windows in /api/oauth/usage's answer (utilization is already a percentage)."""
    out = []
    for key, label in CLAUDE_WINDOWS:
        w = data.get(key) if isinstance(data, dict) else None
        if isinstance(w, dict) and isinstance(w.get("utilization"), (int, float)):
            out.append({"key": key, "label": label, "pct": round(float(w["utilization"]), 1),
                        "resets_at": _iso_to_unix(w.get("resets_at"))})
    return out


PLAN_NAMES = {"max": "Max", "pro": "Pro", "team": "Team", "enterprise": "Enterprise"}


def read_claude(fetch: Callable[[str, dict], dict] = _get_json) -> Optional[Reading]:
    r = Reading("claude", "Claude")
    if _truthy_env("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
        r.mode, r.note, r.source = API, "Billed through your cloud account: no 5-hour or weekly limit.", "settings"
        return r
    creds = claude_credentials()
    env_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    if creds is None and env_token:
        creds = {"accessToken": env_token}       # `claude setup-token`: a claude.ai sign-in too
    if creds is None:
        if os.environ.get("ANTHROPIC_API_KEY", "").strip():
            r.mode, r.note, r.source = API, "API key: billed per token, no 5-hour or weekly limit.", "ANTHROPIC_API_KEY"
            return r
        if not shutil.which("claude") and not shutil.which("claude.cmd"):
            return None
        r.note = "Not signed in to claude.ai (run `claude` and /login), so there is no plan usage to show."
        return r
    r.mode, r.source = PLAN, "claude.ai usage"
    r.plan = PLAN_NAMES.get(str(creds.get("subscriptionType") or "").lower(), "")
    expires = creds.get("expiresAt")
    if isinstance(expires, (int, float)) and expires / 1000 < time.time():
        r.note = "Claude Code's sign-in has expired; it renews it the next time it runs."
        return r
    try:
        data = fetch(CLAUDE_USAGE_URL, {"Authorization": f"Bearer {creds['accessToken']}",
                                        "anthropic-beta": "oauth-2025-04-20",
                                        "User-Agent": "rapr-ai (usage ribbon)"})
        r.windows = claude_windows_from_usage(data)
        if not r.windows:
            r.note = "claude.ai reported no usage windows for this account."
    except urllib.error.HTTPError as exc:
        r.note = ("Claude Code's sign-in was refused; it renews it the next time it runs."
                  if exc.code in (401, 403) else f"claude.ai didn't answer ({exc.code}).")
    except (OSError, ValueError) as exc:
        r.note = f"Couldn't reach claude.ai ({type(exc).__name__})."
    return r


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------

CODEX_PLANS = {"plus": "Plus", "pro": "Pro", "prolite": "Pro Lite", "promax": "Pro Max", "team": "Team",
               "business": "Business", "enterprise": "Enterprise", "edu": "Edu", "free": "Free", "go": "Go"}


def codex_executable() -> Optional[str]:
    for name in ("codex", "codex.cmd", "codex.exe"):
        found = shutil.which(name)
        if found:
            return found
    try:
        from helm.editor_clis import find_in_editors
        found = find_in_editors("codex")
        return str(found) if found else None
    except Exception:
        return None


def _label_minutes(minutes, fallback: str) -> str:
    if not minutes:
        return fallback
    if minutes <= 24 * 60:
        return f"{round(minutes / 60)}h"
    days = round(minutes / (24 * 60))
    return "week" if days == 7 else f"{days}d"


def codex_windows_from_snapshot(snap: dict, prefix: str = "") -> list[dict]:
    out = []
    for key, fallback in (("primary", "5h"), ("secondary", "week")):
        w = snap.get(key) if isinstance(snap, dict) else None
        if isinstance(w, dict) and isinstance(w.get("usedPercent"), (int, float)):
            out.append({"key": prefix + key, "label": (prefix and prefix + " ") + _label_minutes(w.get("windowDurationMins"), fallback),
                        "pct": round(float(w["usedPercent"]), 1), "resets_at": w.get("resetsAt")})
    return out


def codex_app_server(exe: str, timeout: float = 20) -> dict:
    """Ask `codex app-server` for the account and its rate limits: {id: response}."""
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"clientInfo": {"name": "rapr-ai", "title": "RAPR AI", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "account/read", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "account/rateLimits/read"},
    ]
    from helm.subprocess_utils import hidden_kwargs
    proc = subprocess.Popen([exe, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                            **hidden_kwargs())
    answers: dict = {}
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    try:
        assert proc.stdin and proc.stdout
        proc.stdin.write("".join(json.dumps(m) + "\n" for m in msgs))
        proc.stdin.flush()
        for line in proc.stdout:
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("id") in (2, 3):
                answers[msg["id"]] = msg
                if len(answers) == 2:
                    break
    finally:
        timer.cancel()
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    return answers


def read_codex(ask: Callable[[str], dict] = codex_app_server) -> Optional[Reading]:
    exe = codex_executable()
    if not exe:
        return None
    r = Reading("codex", "Codex", source="codex app-server")
    try:
        answers = ask(exe)
    except (OSError, subprocess.SubprocessError) as exc:
        r.note = f"Couldn't ask Codex ({type(exc).__name__})."
        return r
    account = ((answers.get(2) or {}).get("result") or {}).get("account")
    if not answers:
        r.note = "Codex didn't answer (it may be too old for usage: update it)."
        return r
    if account is None:
        r.note = "Not signed in to Codex (run `codex login`)."
        return r
    kind = account.get("type")
    if kind != "chatgpt":
        r.mode = API
        r.note = {"apiKey": "API key: billed per token, no 5-hour or weekly limit."}.get(
            kind, "Billed through your cloud account: no 5-hour or weekly limit.")
        return r
    r.mode, r.plan = PLAN, CODEX_PLANS.get(str(account.get("planType") or ""), "")
    limits = (answers.get(3) or {}).get("result") or {}
    if (answers.get(3) or {}).get("error"):
        r.note = "Codex couldn't read its limits: " + str(answers[3]["error"].get("message") or "")[:120]
        return r
    r.windows = codex_windows_from_snapshot(limits.get("rateLimits") or {})
    for limit_id, snap in (limits.get("rateLimitsByLimitId") or {}).items():
        if limit_id in ("codex", None) or not isinstance(snap, dict):
            continue
        r.windows += codex_windows_from_snapshot(snap, prefix=str(snap.get("limitName") or limit_id))
    if not r.windows:
        r.note = "Codex reported no usage windows for this account."
    return r


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

CODE_ASSIST = "https://cloudcode-pa.googleapis.com/v1internal"


def gemini_dir() -> Path:
    return Path.home() / ".gemini"


def gemini_auth_type() -> Optional[str]:
    try:
        s = json.loads((gemini_dir() / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    sec = s.get("security") if isinstance(s, dict) else None
    t = ((sec or {}).get("auth") or {}).get("selectedType") if isinstance(sec, dict) else None
    return t or (s.get("selectedAuthType") if isinstance(s, dict) else None)


def _short_model(model: str) -> str:
    m = model.replace("gemini-", "").replace("-preview", "").replace("-", " ")
    return m.title().strip()


def gemini_windows_from_quota(data: dict) -> list[dict]:
    out = []
    for b in (data.get("buckets") or []) if isinstance(data, dict) else []:
        if not isinstance(b, dict) or b.get("remainingFraction") is None or not b.get("modelId"):
            continue
        if b.get("tokenType") not in (None, "REQUESTS"):
            continue
        used = max(0.0, min(100.0, (1 - float(b["remainingFraction"])) * 100))
        out.append({"key": b["modelId"], "label": _short_model(str(b["modelId"])) + " today",
                    "pct": round(used, 1), "resets_at": _iso_to_unix(b.get("resetTime"))})
    return out


def read_gemini(fetch: Callable[..., dict] = _get_json) -> Optional[Reading]:
    if not (shutil.which("gemini") or shutil.which("gemini.cmd")):
        return None
    r = Reading("gemini", "Gemini", source="Gemini Code Assist quota")
    auth = gemini_auth_type()
    if auth in ("gemini-api-key", "vertex-ai") or (auth is None and _truthy_env("GEMINI_API_KEY", "GOOGLE_API_KEY")):
        r.mode = API
        r.note = "API key: billed per token (or the API's free tier), no plan quota to show."
        return r
    try:
        creds = json.loads((gemini_dir() / "oauth_creds.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        r.note = "Gemini CLI keeps its Google sign-in where RAPR can't read it, or isn't signed in."
        return r
    token, expiry = creds.get("access_token"), creds.get("expiry_date")
    if not token:
        r.note = "Not signed in to Gemini CLI."
        return r
    r.mode = PLAN
    if isinstance(expiry, (int, float)) and expiry / 1000 < time.time():
        r.note = "Gemini CLI's sign-in has expired; it renews it the next time it runs."
        return r
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "rapr-ai (usage ribbon)"}
    meta = {"ideType": "IDE_UNSPECIFIED", "platform": "PLATFORM_UNSPECIFIED", "pluginType": "GEMINI"}
    try:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT_ID") or None
        load = fetch(f"{CODE_ASSIST}:loadCodeAssist", headers,
                     {"cloudaicompanionProject": project, "metadata": {**meta, "duetProject": project}})
        proj = load.get("cloudaicompanionProject")
        project = (proj.get("id") if isinstance(proj, dict) else proj) or project
        tier = load.get("currentTier") or {}
        r.plan = str(tier.get("name") or "") if isinstance(tier, dict) else ""
        if not project:
            r.note = "Gemini CLI has no Code Assist project yet; run `gemini` once."
            return r
        r.windows = gemini_windows_from_quota(fetch(f"{CODE_ASSIST}:retrieveUserQuota", headers, {"project": project}))
        if not r.windows:
            r.note = "Google reported no quota for this account."
    except urllib.error.HTTPError as exc:
        r.note = ("Gemini CLI's sign-in was refused; it renews it the next time it runs."
                  if exc.code in (401, 403) else f"Google didn't answer ({exc.code}).")
    except (OSError, ValueError) as exc:
        r.note = f"Couldn't reach Google ({type(exc).__name__})."
    return r


READERS: dict[str, Callable[[], Optional[Reading]]] = {
    "claude": read_claude, "codex": read_codex, "gemini": read_gemini,
}


def read_all(agents: Optional[list[str]] = None) -> dict[str, Reading]:
    """Every reader at once (each can take a few seconds)."""
    keys = [k for k in (agents or READERS) if k in READERS]
    out: dict[str, Reading] = {}

    def one(key):
        try:
            got = READERS[key]()
        except Exception:
            logger.warning("Couldn't read %s's usage", key, exc_info=True)
            got = Reading(key, key.title(), note="Couldn't read its usage.")
        if got is not None:
            out[key] = got
    threads = [threading.Thread(target=one, args=(k,), daemon=True) for k in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join(TIMEOUT * 3)
    return out
