"""
helm/vscode_bridge: GitHub Copilot through the person's VS Code sign-in, by way of the
RAPR Bridge extension (vscode-bridge/ in the repository; its package ships here as
rapr-bridge.vsix).

VS Code's Copilot keeps its GitHub sign-in in VS Code's own encrypted storage, and its
Copilot Chat extension ships the Copilot engine but no `copilot` command, so RAPR can't run
it the way it runs Claude Code or Codex. The bridge, a small extension, uses VS Code's
language model API (vscode.lm) with the person's permission and answers RAPR on this
computer: 127.0.0.1, a random port, and a random key, both in
~/.config/rapr/vscode-bridge.json (RAPR_CONFIG_DIR overrides the folder).

It answers questions (reviews, plans, second opinions); it doesn't edit files.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

EXTENSION_ID = "raprai.rapr-bridge"
COPILOT_CHAT = "github.copilot-chat-"
CONNECT_COMMAND = "RAPR: Connect Copilot"


class BridgeError(Exception):
    """The bridge isn't there, or answered with an error: the message says what to do."""


def config_dir() -> Path:
    return Path(os.environ.get("RAPR_CONFIG_DIR") or Path.home() / ".config" / "rapr")


def bridge_file() -> Path:
    return config_dir() / "vscode-bridge.json"


def vsix_path() -> Path:
    return Path(__file__).with_name("rapr-bridge.vsix")


def bundled_version() -> str:
    """The version of the bridge RAPR carries (from the .vsix's manifest)."""
    import zipfile
    try:
        with zipfile.ZipFile(vsix_path()) as z:
            return json.loads(z.read("extension/package.json")).get("version", "")
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return ""


def read_info() -> Optional[dict]:
    try:
        info = json.loads(bridge_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(info, dict) and isinstance(info.get("port"), int) and isinstance(info.get("key"), str):
        return info
    return None


def request(path: str, body: Optional[dict] = None, timeout: float = 5.0) -> dict:
    """Ask the bridge. Raises BridgeError with words for people when it can't answer."""
    info = read_info()
    if info is None:
        raise BridgeError("The RAPR Bridge isn't running: open VS Code (with the RAPR Bridge extension installed).")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{info['port']}{path}", data=data, method="POST" if data is not None else "GET",
        headers={"Authorization": f"Bearer {info['key']}", "Content-Type": "application/json"})
    # Straight to this machine, never through a proxy someone set for the web.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8") or "{}").get("message")
        except ValueError:
            msg = None
        raise BridgeError(msg or f"The RAPR Bridge answered {exc.code}.") from exc
    except (OSError, ValueError) as exc:
        raise BridgeError("The RAPR Bridge isn't answering: is VS Code open? "
                          f"({type(exc).__name__})") from exc


def healthy(timeout: float = 2.0) -> bool:
    try:
        return bool(request("/health", timeout=timeout).get("ok"))
    except BridgeError:
        return False


def models(timeout: float = 10.0) -> list[dict]:
    return request("/models", timeout=timeout).get("models") or []


def ask(prompt: str, model: Optional[str] = None, timeout: float = 900.0) -> str:
    body = {"prompt": prompt}
    if model:
        body["model"] = model
    return request("/chat", body, timeout=timeout).get("text") or ""


# ---------------------------------------------------------------------------
# VS Code: is Copilot there, is the bridge installed, install it
# ---------------------------------------------------------------------------

def copilot_in_vscode() -> bool:
    from helm.editor_clis import has_extension
    return has_extension(COPILOT_CHAT)


def installed() -> bool:
    from helm.editor_clis import has_extension
    return has_extension(EXTENSION_ID + "-")


def _server_cli(env=None) -> Optional[str]:
    """In a VS Code window connected to WSL (or SSH, a container), the extensions, Claude Code
    and so `rapr mcp` run on VS Code Server, and the bridge belongs there too: install it with
    the server's own CLI. Its remote `code` while VS Code is attached (VSCODE_IPC_HOOK_CLI),
    else its `code-server`. Newest server first (VS Code updates leave older ones behind)."""
    env = os.environ if env is None else env
    if sys.platform == "win32":
        return None
    agent = Path(env.get("VSCODE_AGENT_FOLDER") or Path.home() / ".vscode-server").expanduser()
    if not agent.is_dir():
        return None
    layouts = ("bin/*/bin/{}", "cli/servers/*/server/bin/{}")
    names = (["remote-cli/code"] if env.get("VSCODE_IPC_HOOK_CLI") else []) + ["code-server"]
    for name in names:
        found = [p for layout in layouts for p in agent.glob(layout.format(name)) if os.access(p, os.X_OK)]
        if found:
            return str(max(found, key=lambda p: p.stat().st_mtime))
    return None


def code_cli(env=None) -> Optional[str]:
    """The command that installs an extension where RAPR runs: VS Code Server's (WSL, SSH,
    containers), else VS Code's `code`, on PATH or where its installers put it."""
    server = _server_cli(env)
    if server:
        return server
    from helm.editor_clis import is_wsl
    for name in ("code", "code.cmd", "code-insiders", "code-insiders.cmd"):
        found = shutil.which(name)
        # In WSL, the `code` on PATH is Windows' launcher: it would install on the Windows side.
        if found and not (is_wsl() and found.startswith("/mnt/")):
            return found
    home = Path.home()
    candidates = []
    if sys.platform == "darwin":
        candidates += [Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
                       home / "Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"]
    elif sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        candidates += [local / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd",
                       Path(os.environ.get("ProgramFiles") or "C:/Program Files") / "Microsoft VS Code" / "bin" / "code.cmd"]
    else:
        candidates += [Path("/usr/bin/code"), Path("/usr/share/code/bin/code"), Path("/snap/bin/code")]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def install(timeout: float = 120.0) -> str:
    """Install (or update) the bridge in VS Code. Returns what happened, for people."""
    cli = code_cli()
    if not cli:
        raise BridgeError("Couldn't find VS Code's `code` command. In VS Code, run \"Extensions: Install from "
                          f"VSIX...\" and choose {vsix_path()}.")
    if not vsix_path().exists():
        raise BridgeError("RAPR's copy of the bridge is missing; reinstall RAPR.")
    r = subprocess.run([cli, "--install-extension", str(vsix_path()), "--force"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise BridgeError("VS Code couldn't install the RAPR Bridge: "
                          + ((r.stderr or r.stdout).strip()[-400:] or f"exit code {r.returncode}"))
    return (r.stdout or "").strip()


def status_text() -> str:
    """Where things stand, and the next step, for people."""
    if not copilot_in_vscode():
        return ("GitHub Copilot isn't installed in VS Code here. Install GitHub Copilot Chat in VS Code and sign in, "
                "or install the Copilot CLI (`npm install -g @github/copilot`, then `copilot login`).")
    if not installed():
        return "Copilot is in VS Code, but the RAPR Bridge isn't installed yet: use connect_vscode_copilot."
    if not healthy():
        return "The RAPR Bridge is installed but not running: open VS Code (or reload its window)."
    try:
        found = models()
    except BridgeError as exc:
        return str(exc)
    if not found:
        return "The RAPR Bridge is running, but VS Code has no Copilot models: sign in to GitHub Copilot in VS Code."
    return ("Copilot (VS Code) is ready through the RAPR Bridge, with "
            + ", ".join(m.get("family") or m.get("id") for m in found[:8]) + ". The first question may ask you, in "
            f"VS Code, to allow RAPR Bridge to use Copilot (or run \"{CONNECT_COMMAND}\" there first).")
