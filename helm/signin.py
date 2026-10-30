"""Is an AI's command-line tool signed in? So RAPR doesn't list one that would only fail.

Each check answers True (signed in), False (clearly not), or None (couldn't tell).
Callers treat None as signed in: a tool is never hidden on a guess. Answers are kept
for a minute, since list_agents and every tool call ask.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

CACHE_SECONDS = 60
_cache: dict[str, tuple[Optional[bool], float]] = {}


def _exe(name: str) -> Optional[str]:
    return shutil.which(name) or shutil.which(name + ".cmd") or shutil.which(name + ".exe")


def _run(exe: str, *args: str) -> tuple[int, str]:
    from helm.subprocess_utils import hidden_kwargs
    r = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=15, stdin=subprocess.DEVNULL, **hidden_kwargs())
    return r.returncode, (r.stdout or "") + "\n" + (r.stderr or "")


def _any_env(*names: str) -> bool:
    return any(os.environ.get(n, "").strip() for n in names)


def claude() -> Optional[bool]:
    # An API key, a long-lived token, or a cloud provider means no sign-in is needed.
    if _any_env("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
                "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
        return True
    exe = _exe("claude")
    if not exe:
        return None
    try:
        _, out = _run(exe, "auth", "status")
    except Exception:
        return None
    # It prints JSON with "loggedIn" (an older Claude Code has no such command: can't tell).
    decoder = json.JSONDecoder()
    for i, ch in enumerate(out):
        if ch == "{":
            try:
                data, _ = decoder.raw_decode(out, i)
            except ValueError:
                continue
            if isinstance(data, dict) and isinstance(data.get("loggedIn"), bool):
                return data["loggedIn"]
    return None


def codex() -> Optional[bool]:
    if _any_env("OPENAI_API_KEY", "CODEX_API_KEY"):
        return True
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    # No file: Codex may keep the sign-in in the system keyring instead, so ask it below.
    path = home / "auth.json"
    if path.is_file():
        try:
            auth = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            auth = {}
        if isinstance(auth, dict) and (auth.get("tokens") or auth.get("OPENAI_API_KEY")):
            return True
    exe = _exe("codex")
    if not exe:
        return None
    try:
        code, out = _run(exe, "login", "status")
    except Exception:
        return None
    text = out.lower()
    if "not logged in" in text:
        return False
    if code == 0 and "logged in" in text:
        return True
    return None


CHECKS: dict[str, Callable[[], Optional[bool]]] = {"claude": claude, "codex": codex}


def status(name: str) -> Optional[bool]:
    check = CHECKS.get(name)
    if not check:
        return None
    hit = _cache.get(name)
    if hit and time.monotonic() - hit[1] < CACHE_SECONDS:
        return hit[0]
    try:
        result = check()
    except Exception:
        result = None
    _cache[name] = (result, time.monotonic())
    return result


def signed_in(name: str) -> bool:
    """False only when the tool clearly says it isn't signed in."""
    return status(name) is not False
