"""
helm/claude_models.py — Claude's models, read live.

Two sources, both from the user's own setup, so new models show up without a
RAPR update:

  live_models()   what Claude Code's own /model menu offers this account: each
                  name ("opus") with the exact model behind it ("claude-opus-5-5")
                  and Claude's description ("Opus 5.5 · Best for everyday…").
                  Read by asking the installed CLI to start up (its "initialize"
                  control request, the one the Agent SDK uses) and stopping it
                  before any prompt: no usage, about a second. It runs in an
                  empty temporary folder without saving a session, so it can't
                  become the conversation a chat's --continue picks up.

  all_versions()  every model id Anthropic's Models API lists (older versions
                  like claude-opus-4-5 included), when an API key is set.

configured_model() is the model the user set for Claude Code itself
(ANTHROPIC_MODEL, or "model" in its settings files), which is what "Default"
means for them.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

from helm.subprocess_utils import hidden_kwargs

_INIT = json.dumps({"type": "control_request", "request_id": "rapr-models",
                    "request": {"subtype": "initialize"}}) + "\n"


def _claude_exe() -> Optional[str]:
    return shutil.which("claude") or shutil.which("claude.cmd")


def parse_initialize(output: str) -> list[dict]:
    """The models from Claude Code's initialize reply (one JSON object per line)."""
    for line in (output or "").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") != "control_response":
            continue
        resp = (ev.get("response") or {}).get("response") or {}
        models = []
        for m in resp.get("models") or []:
            if isinstance(m, dict) and m.get("value"):
                levels = m.get("supportedEffortLevels") if m.get("supportsEffort") else []
                models.append({
                    "value": str(m["value"]),
                    "resolved": m.get("resolvedModel") or None,
                    "name": m.get("displayName") or str(m["value"]),
                    "description": m.get("description") or "",
                    "efforts": [str(x) for x in levels or [] if isinstance(x, str)],
                })
        return models
    return []


def help_effort_levels() -> list[str]:
    """The effort levels `claude --help` lists ("--effort <level> … (low, medium, high,
    xhigh, max)"), for when the live list can't be read."""
    import re
    exe = _claude_exe()
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "--help"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=15, **hidden_kwargs())
    except Exception:
        return []
    m = re.search(r"--effort <level>[^(]*\(([^)]*)\)", " ".join((r.stdout or "").split()))
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def live_models(timeout: int = 30) -> list[dict]:
    """[{value, resolved, name, description}] from the installed Claude Code; [] if unavailable."""
    exe = _claude_exe()
    if not exe:
        return []
    base = [exe, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    with tempfile.TemporaryDirectory(prefix="rapr-claude-models-") as tmp:
        for extra in (["--no-session-persistence"], []):   # older CLIs may not know the flag
            try:
                r = subprocess.run(base + extra, input=_INIT, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", cwd=tmp, timeout=timeout,
                                   **hidden_kwargs())
            except Exception:
                return []
            models = parse_initialize(r.stdout)
            if models:
                return models
            if "no-session-persistence" not in (r.stderr or "") + (r.stdout or ""):
                break
    return []


def all_versions(timeout: int = 15) -> list[dict]:
    """[{id, name}] from Anthropic's Models API, newest first; [] without an API key."""
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key or key == "vault-managed":
        return []
    base = (os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com").rstrip("/")
    req = urllib.request.Request(f"{base}/v1/models?limit=1000",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return [{"id": m["id"], "name": m.get("display_name") or m["id"]}
            for m in data.get("data") or [] if isinstance(m, dict) and m.get("id")]


def configured_model(cwd: Optional[str] = None) -> Optional[str]:
    """The model the user set for Claude Code itself, in Claude Code's own order:
    ANTHROPIC_MODEL, then "model" in the project's .claude/settings.local.json and
    .claude/settings.json, then ~/.claude/settings.json."""
    env = (os.environ.get("ANTHROPIC_MODEL") or "").strip()
    if env:
        return env
    files = []
    if cwd:
        files += [Path(cwd, ".claude", "settings.local.json"), Path(cwd, ".claude", "settings.json")]
    files.append(Path.home() / ".claude" / "settings.json")
    for f in files:
        try:
            model = json.loads(f.read_text(encoding="utf-8")).get("model")
        except Exception:
            continue
        if isinstance(model, str) and model.strip():
            return model.strip()
    return None


def replaced(chosen: Optional[str], answered: Optional[str]) -> bool:
    """True when an exact version was picked but a different model answered. Claude Code
    quietly answers a retired version (claude-opus-4-1) with a current one. An exact id
    may come back with a date suffix (claude-opus-4-5 -> claude-opus-4-5-20251101).
    Names like "opus" or "sonnet[1m]" are Claude's to resolve, so they never count."""
    if not chosen or not answered or not chosen.lower().startswith("claude-"):
        return False
    chosen, answered = chosen.lower(), answered.lower()
    return not (answered == chosen or answered.startswith(chosen + "-"))
