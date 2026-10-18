"""
helm/updater.py — Auto-update manager for RAPR AI.

How RAPR finds out about updates depends on how it was installed:

- Source installs (scripts/install-windows.ps1, scripts/install-mac.sh) follow a
  branch of github.com/rawalrahul/raprai (main by default). The installer records
  the commit it installed; we ask GitHub how many commits the branch is ahead of
  it, and list their titles as "what's new". start_source_update() reruns the
  installer in the background, which stops RAPR, updates it and starts it again.
- Docker images and developer checkouts are told about updates but update
  themselves the usual way (Cloud server -> Update, docker compose pull, git pull).

Nothing is sent but an ordinary HTTPS request (with RAPR's version in the
User-Agent). Offline, the check fails quietly. UPDATE_CHECK=0 in .env turns the
automatic check off; "Check now" in Settings still works.

Public API:
    install_info() → dict
    check_for_app_update(force=False) → dict | None
    start_source_update() → dict
    get_update_status() → dict
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from helm.config import logger
from helm.version import APP_VERSION

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# How often to auto-check (hourly; GitHub allows 60 unauthenticated requests an hour)
_AUTO_CHECK_INTERVAL = 60 * 60

# Source installs: the repository and the installers that update them
_REPO = "rawalrahul/raprai"
_SOURCE_KINDS = ("source-windows", "source-mac")
_INSTALL_FILE = ".rapr-install.json"     # written into the app folder by the installers
_QUIET_START = "quiet-start"             # in the data folder: don't open a browser on the next start

# In-memory state
_cached_update: Optional[dict] = None
_last_check_at: float = 0.0


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple:
    """Parse semver string like '2.0.0' into comparable tuple."""
    import re
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v or "")
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


# ---------------------------------------------------------------------------
# Check for updates
# ---------------------------------------------------------------------------

def install_info() -> dict:
    """How this copy was installed: kind, the branch it follows, the commit it runs."""
    import json
    from helm.paths import PROJECT_ROOT
    kind = os.environ.get("RAPR_INSTALL_KIND", "").strip() or "dev"
    info = {"kind": kind, "ref": os.environ.get("RAPR_REF", "").strip() or "main",
            "commit": os.environ.get("RAPR_COMMIT", "").strip()}
    try:
        data = json.loads((PROJECT_ROOT / _INSTALL_FILE).read_text(encoding="utf-8-sig"))   # PS 5.1 writes a BOM
        info["ref"] = data.get("ref") or info["ref"]
        info["commit"] = data.get("commit") or info["commit"]
    except (OSError, ValueError):
        pass
    if not info["commit"] and (PROJECT_ROOT / ".git").exists():
        try:
            out = subprocess.run(["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, timeout=5)
            if out.returncode == 0:
                info["commit"] = out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    info["self_update"] = kind in _SOURCE_KINDS
    return info


def auto_check_enabled() -> bool:
    return os.environ.get("UPDATE_CHECK", "1").strip() != "0"


def _check_source_update(info: dict) -> dict:
    """Compare the installed commit with the tip of the branch on GitHub."""
    import requests
    headers = {"User-Agent": f"RAPR-AI/{APP_VERSION}", "Accept": "application/vnd.github+json"}
    ref, commit = info["ref"], info["commit"]
    base = {"current_version": APP_VERSION, "current_commit": commit, "ref": ref}
    if not commit:
        # We don't know what we run (an old install): report the latest, offer to update.
        resp = requests.get(f"https://api.github.com/repos/{_REPO}/commits/{ref}", headers=headers, timeout=10)
        resp.raise_for_status()
        latest = resp.json()
        return {**base, "update_available": None, "latest_commit": latest.get("sha", ""),
                "latest_date": ((latest.get("commit") or {}).get("committer") or {}).get("date", "")[:10],
                "behind_by": None, "changes": []}
    resp = requests.get(f"https://api.github.com/repos/{_REPO}/compare/{commit}...{ref}", headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    commits = data.get("commits") or []
    behind = int(data.get("ahead_by") or 0)     # how far the branch is ahead of us
    changes = []
    for c in reversed(commits):                 # newest first, skipping merge commits
        if len(c.get("parents") or []) > 1:
            continue
        msg = (c.get("commit") or {}).get("message", "")
        changes.append({"title": msg.splitlines()[0][:140] if msg else "",
                        "date": ((c.get("commit") or {}).get("committer") or {}).get("date", "")[:10]})
        if len(changes) >= 15:
            break
    latest = commits[-1] if commits else {}
    return {**base, "update_available": behind > 0, "behind_by": behind,
            "latest_commit": latest.get("sha", commit),
            "latest_date": ((latest.get("commit") or {}).get("committer") or {}).get("date", "")[:10],
            "changes": changes}


def check_for_app_update(force: bool = False) -> Optional[dict]:
    """Check GitHub for new commits on the branch this copy follows.

    Returns the update info when an update is available (or the installed
    commit is unknown), None otherwise. The result is cached for an hour.
    """
    global _cached_update, _last_check_at

    now = time.time()
    if not force and _cached_update is not None and (now - _last_check_at) < _AUTO_CHECK_INTERVAL:
        return _cached_update if _cached_update.get("update_available") else None
    _last_check_at = now

    try:
        update_info = _check_source_update(install_info())
        logger.info("Update check: %s", "update available" if update_info.get("update_available")
                    else "up to date" if update_info.get("update_available") is False else "installed commit unknown")
    except Exception as e:
        logger.warning("Update check failed (offline?): %s", e)
        update_info = {"update_available": False, "error": "Couldn't reach GitHub to check for updates.",
                       "current_version": APP_VERSION}
    _cached_update = update_info
    return update_info if update_info.get("update_available") else None


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_update_status() -> dict:
    """Return current update check / download / install status."""
    return {
        "current_version": APP_VERSION,
        "install": install_info(),
        "auto_check": auto_check_enabled(),
        "update": _cached_update,
        "last_check_at": _last_check_at,
    }


# ---------------------------------------------------------------------------
# Source installs: update from the web UI
# ---------------------------------------------------------------------------

def update_log_path() -> Path:
    from helm.paths import user_data_dir
    d = user_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d / "update.log"


def take_quiet_start() -> bool:
    """True (once) if RAPR is starting after an update from the web UI, whose
    open tab reloads itself, so no new browser window is needed."""
    from helm.paths import user_data_dir
    marker = user_data_dir() / _QUIET_START
    try:
        fresh = time.time() - marker.stat().st_mtime < 20 * 60
        marker.unlink()
        return fresh
    except OSError:
        return False


def start_source_update() -> dict:
    """Rerun this install's installer in the background. It stops RAPR, updates
    it and starts it again; the open web page reloads itself when RAPR is back."""
    from helm.paths import user_data_dir
    info = install_info()
    kind, ref = info["kind"], info["ref"]
    if kind not in _SOURCE_KINDS:
        return {"ok": False, "error": "This copy of RAPR can't update itself from here."}
    if not all(ch.isalnum() or ch in "-_./" for ch in ref):
        return {"ok": False, "error": f"Unexpected branch name: {ref!r}"}
    log = update_log_path()
    log.write_text("", encoding="utf-8")
    (user_data_dir() / _QUIET_START).write_text(str(time.time()), encoding="utf-8")
    home = str(Path.home())
    try:
        if kind == "source-windows":
            def q(v: str) -> str:              # PowerShell single-quoted string
                return "'" + v.replace("'", "''") + "'"
            script = log.with_name("update-from-ui.ps1")
            script.write_text("\r\n".join([
                "# Written by RAPR when you clicked Update now. Safe to delete.",
                "$ErrorActionPreference = 'Continue'",
                "$env:RAPR_NO_OPEN = '1'; $env:RAPR_YES = '1'; $env:RAPR_REF = " + q(ref),
                f"Start-Transcript -Path {q(str(log))} -Force | Out-Null",
                "try { irm https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-windows.ps1 | iex }",
                "catch { Write-Host \"UPDATE FAILED: $_\" }",
                "Stop-Transcript | Out-Null",
                "$rapr = Join-Path $env:LOCALAPPDATA 'rapr-ai\\bin\\rapr.cmd'",
                "& $rapr status *> $null",
                "if ($LASTEXITCODE -ne 0) { & $rapr start }",
                "",
            ]), encoding="utf-8-sig")         # BOM: Windows PowerShell 5.1 then reads it as UTF-8
            # "start" via cmd: the updater's parent is then a cmd.exe that has already
            # exited, so it isn't part of RAPR's process tree when the installer stops RAPR.
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "", "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-WindowStyle", "Hidden", "-File", str(script)],
                cwd=home, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True,
            )
        else:
            import shlex
            script = log.with_name("update-from-ui.sh")
            script.write_text("\n".join([
                "#!/bin/bash",
                "# Written by RAPR when you clicked Update now. Safe to delete.",
                f"export RAPR_NO_OPEN=1 RAPR_REF={shlex.quote(ref)}",
                "{ curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-mac.sh | bash"
                " || echo 'UPDATE FAILED'; } >" + shlex.quote(str(log)) + " 2>&1",
                'B="$HOME/.rapr-ai/bin"',
                '"$B/rapr-stop"; "$B/rapr-start"',
                "",
            ]), encoding="utf-8")
            subprocess.Popen(["/bin/bash", str(script)], cwd=home, start_new_session=True,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.error("Could not start the update: %s", e)
        return {"ok": False, "error": f"Could not start the update: {e}"}
    logger.info("Update from the web UI started (%s, %s)", kind, ref)
    return {"ok": True}


def read_update_log(lines: int = 60) -> dict:
    """The tail of the last update's output, and whether it reported a failure."""
    try:
        text = update_log_path().read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    tail = "\n".join(l for l in text.splitlines() if l.strip() and not l.startswith("*****"))
    tail = "\n".join(tail.splitlines()[-lines:])
    return {"log": tail, "failed": "UPDATE FAILED" in text or "RAPR install:" in text}


# ---------------------------------------------------------------------------
# Background auto-check (called from web_app.py startup)
# ---------------------------------------------------------------------------

async def auto_check_loop():
    """Background task that checks for updates periodically."""
    import asyncio

    # Wait a bit after startup before first check
    await asyncio.sleep(30)

    while True:
        try:
            if auto_check_enabled():
                # Run in thread to avoid blocking event loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, check_for_app_update)
        except Exception as e:
            logger.warning("Auto-update check error: %s", e)

        await asyncio.sleep(_AUTO_CHECK_INTERVAL)
