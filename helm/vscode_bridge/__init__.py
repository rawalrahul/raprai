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

# ---------------------------------------------------------------------------
# Finding Copilot: installed as an extension, or built into VS Code; on this computer,
# on VS Code Server (a WSL or remote window), or, from inside WSL, on the Windows side
# ---------------------------------------------------------------------------

COPILOT_NAMES = {"copilot-chat", "copilot"}       # GitHub's publisher name for both
FIND_CACHE_SECONDS = 60      # a scan of the Windows side from WSL takes a moment
_found_cache: tuple = (0.0, None)


def _manifest(folder: Path) -> Optional[dict]:
    try:
        data = json.loads((folder / "package.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def is_copilot(folder: Path) -> bool:
    """Whether an extension folder is GitHub Copilot (Chat), by its manifest, not its name."""
    m = _manifest(folder)
    return bool(m) and str(m.get("publisher", "")).lower() == "github" and str(m.get("name", "")).lower() in COPILOT_NAMES


def _obsolete(root: Path) -> set:
    """Folders VS Code has replaced and will delete (an update leaves the old one behind)."""
    try:
        return set(json.loads((root / ".obsolete").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return set()


def _extension_roots(env=None) -> list[tuple[Path, str]]:
    """Where installed extensions live, each with which side it is, for people."""
    from helm.editor_clis import EDITOR_DIRS, is_wsl, windows_homes
    env = os.environ if env is None else env
    here = "WSL" if is_wsl() else "this computer"
    out = []
    for editor in EDITOR_DIRS:
        side = "VS Code Server (WSL or remote)" if editor == ".vscode-server" else here
        out.append((Path.home() / editor / "extensions", side))
    agent = env.get("VSCODE_AGENT_FOLDER")
    if agent:
        out.insert(0, (Path(agent).expanduser() / "extensions", "VS Code Server (WSL or remote)"))
    for home in windows_homes():
        for editor in (".vscode", ".vscode-insiders"):
            out.append((home / editor / "extensions", "Windows"))
    return out


def _vscode_installs() -> list[tuple[Path, str]]:
    """Where VS Code itself is installed (its built-in extensions are inside)."""
    from helm.editor_clis import is_wsl, windows_homes
    names = ("Microsoft VS Code", "Microsoft VS Code Insiders")
    out: list[tuple[Path, str]] = []
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        for base in (local / "Programs", Path(os.environ.get("ProgramFiles") or "C:/Program Files")):
            out += [(base / n, "this computer") for n in names]
    elif sys.platform == "darwin":
        for apps in (Path("/Applications"), Path.home() / "Applications"):
            out += [(apps / f"{n}.app" / "Contents" / "Resources", "this computer")
                    for n in ("Visual Studio Code", "Visual Studio Code - Insiders")]
    else:
        out += [(Path(p), "WSL" if is_wsl() else "this computer") for p in
                ("/usr/share/code", "/usr/share/code-insiders", "/opt/visual-studio-code", "/snap/code/current/usr/share/code")]
        for home in windows_homes():
            out += [(home / "AppData" / "Local" / "Programs" / n, "Windows") for n in names]
        if is_wsl():
            out += [(Path("/mnt/c/Program Files") / n, "Windows") for n in names]
    return out


def _builtin_roots(env=None) -> list[tuple[Path, str]]:
    """VS Code's built-in extension folders: in its install (also a versioned folder inside,
    as newer Windows builds use), and VS Code Server's own."""
    env = os.environ if env is None else env
    out = []
    for install, side in _vscode_installs():
        out.append((install / "resources" / "app" / "extensions", side))
        out.append((install / "app" / "extensions", side))                        # macOS bundle
        try:
            out += [(p, side) for p in install.glob("*/resources/app/extensions")]
        except OSError:
            pass
    agent = Path(env.get("VSCODE_AGENT_FOLDER") or Path.home() / ".vscode-server").expanduser()
    for layout in ("bin/*/extensions", "cli/servers/*/server/extensions"):
        try:
            out += [(p, "VS Code Server (WSL or remote)") for p in agent.glob(layout)]
        except OSError:
            pass
    return out


def find_copilot(env=None, fresh: bool = False) -> list[dict]:
    """Every GitHub Copilot (Chat) found: [{how: "extension" | "built into VS Code", side, path}]."""
    global _found_cache
    import time
    at, found = _found_cache
    if not fresh and env is None and found is not None and time.monotonic() - at < FIND_CACHE_SECONDS:
        return found
    found, seen = [], set()
    for root, side in _extension_roots(env):
        gone = _obsolete(root)
        try:
            folders = [p for p in root.iterdir() if p.is_dir() and p.name.lower().startswith("github.copilot")
                       and p.name not in gone]
        except OSError:
            continue
        for p in folders:
            if (is_copilot(p) or _manifest(p) is None) and str(p) not in seen:
                seen.add(str(p))
                found.append({"how": "extension", "side": side, "path": str(p)})
    for root, side in _builtin_roots(env):
        try:
            folders = [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            continue
        for p in folders:        # built-in folders have plain names: check every manifest
            if is_copilot(p) and str(p) not in seen:
                seen.add(str(p))
                found.append({"how": "built into VS Code", "side": side, "path": str(p)})
    if env is None:
        _found_cache = (time.monotonic(), found)
    return found


def copilot_in_vscode(fresh: bool = False) -> bool:
    """Copilot is in VS Code: found on disk (either kind, either side), or the bridge can
    already see its models (true however VS Code got it). fresh: look again now."""
    if find_copilot(fresh=fresh):
        return True
    if read_info() is not None and healthy():
        try:
            return bool(models())
        except BridgeError:
            return False
    return False


def where_copilot() -> str:
    """Where Copilot was found, for people: "built into VS Code (Windows), extension (WSL)"."""
    parts = []
    for f in find_copilot():
        text = f"{f['how']} ({f['side']})"
        if text not in parts:
            parts.append(text)
    return ", ".join(parts)


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


NOT_FOUND = ("RAPR couldn't find GitHub Copilot in VS Code, neither built in nor as an extension (it looked on "
             "this computer, in VS Code Server for WSL, and on the Windows side). To check: in VS Code open "
             "Extensions (Ctrl+Shift+X) and type @installed copilot; look under both Local and WSL. If it isn't "
             "there, install GitHub Copilot Chat and sign in to GitHub in VS Code (a free Copilot plan works). If "
             "Copilot does work in your VS Code, connect anyway (connect_vscode_copilot with anyway=true): the "
             "bridge then asks VS Code directly. Or install the Copilot CLI: `npm install -g @github/copilot`, "
             "then `copilot login`.")


def status_text() -> str:
    """Where things stand, and the next step, for people."""
    if not copilot_in_vscode() and not installed():
        return NOT_FOUND
    if not installed():
        return "Copilot is in VS Code, but the RAPR Bridge isn't installed yet: use connect_vscode_copilot."
    if not healthy():
        return "The RAPR Bridge is installed but not running: open VS Code (or reload its window)."
    try:
        found = models()
    except BridgeError as exc:
        return str(exc)
    if not found:
        return ("The RAPR Bridge is running, but VS Code has no Copilot models: install GitHub Copilot Chat in VS Code "
                "(if it isn't built in) and sign in to GitHub there.")
    return ("Copilot (VS Code) is ready through the RAPR Bridge, with "
            + ", ".join(m.get("family") or m.get("id") for m in found[:8]) + ". The first question may ask you, in "
            f"VS Code, to allow RAPR Bridge to use Copilot (or run \"{CONNECT_COMMAND}\" there first).")
