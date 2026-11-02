"""AI command-line tools that came with an editor extension rather than their own install.

The Claude Code extension for VS Code (and Cursor, Windsurf…) ships its own `claude`,
and the Codex extension its own `codex`, inside the extension's folder. Neither puts
it on PATH, so someone with only the extension had no Claude or Codex in RAPR. When a
tool isn't on PATH, add_to_path() appends the folder of the newest extension copy, so
every `shutil.which` and subprocess call finds it. A real install stays first on PATH,
except when RAPR runs under VS Code (`rapr mcp` started by the Claude Code extension, say):
then the copy that came with the editor's own extensions goes first, so RAPR uses the same
tools as the editor. In a VS Code window connected to WSL (or SSH, a container), that is the
copy VS Code Server installed in ~/.vscode-server, where the extensions run.
"""
import os
import platform
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

# command -> start of the extension's folder name (publisher.name-version[-platform])
EXTENSIONS = {
    "claude": "anthropic.claude-code-",
    "codex": "openai.chatgpt-",
}

# Where VS Code and its relatives keep extensions, under the home folder.
EDITOR_DIRS = (".vscode", ".vscode-insiders", ".vscode-server", ".cursor", ".windsurf", ".vscode-oss")


def _version(folder: str, prefix: str) -> tuple:
    m = re.match(r"(\d+(?:\.\d+)*)", folder[len(prefix):])
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def _arch_score(path: Path) -> int:
    """Prefer this machine's build when an extension carries several (e.g. bin/macos-aarch64)."""
    text = str(path).lower()
    arm = platform.machine().lower() in ("arm64", "aarch64")
    if any(t in text for t in ("aarch64", "arm64")):
        return 1 if arm else -1
    if any(t in text for t in ("x86_64", "x64", "amd64")):
        return -1 if arm else 1
    return 0


def _binary_in(ext: Path, name: str) -> Optional[Path]:
    exe = name + ".exe" if sys.platform == "win32" else name
    found = []
    for root, dirs, files in os.walk(ext):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        if exe in files:
            p = Path(root) / exe
            if sys.platform == "win32" or os.access(p, os.X_OK):
                found.append(p)
    return max(found, key=_arch_score) if found else None


# Variables VS Code sets for what it starts: its extension host, its terminals, and so the
# Claude Code extension's `claude` and the MCP servers that starts.
VSCODE_ENV = ("VSCODE_PID", "VSCODE_IPC_HOOK", "VSCODE_IPC_HOOK_CLI", "VSCODE_AGENT_FOLDER", "VSCODE_CWD")


def under_vscode(env=None) -> bool:
    """Whether RAPR was started from VS Code (or Cursor, Windsurf: they set the same)."""
    env = os.environ if env is None else env
    if env.get("TERM_PROGRAM") == "vscode" or str(env.get("CLAUDE_CODE_ENTRYPOINT", "")).endswith("vscode"):
        return True
    return any(env.get(k) for k in VSCODE_ENV)


def _editor_order(home: Path, env=None) -> list[Path]:
    """Extension folders, the running editor's first: in a remote window (WSL, SSH, a
    container) VS Code Server's (VSCODE_AGENT_FOLDER, e.g. ~/.vscode-server)."""
    env = os.environ if env is None else env
    roots = [home / editor / "extensions" for editor in EDITOR_DIRS]
    agent = env.get("VSCODE_AGENT_FOLDER")
    if agent:
        mine = Path(agent).expanduser() / "extensions"
        roots = [mine] + [r for r in roots if r != mine]
    return roots


def is_wsl() -> bool:
    if sys.platform != "linux":
        return False
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def _windows_extension_roots() -> list[Path]:
    """From inside WSL, the Windows side's VS Code extension folders (/mnt/c/Users/*/.vscode...)."""
    if not is_wsl():
        return []
    roots = []
    try:
        for user in Path("/mnt/c/Users").iterdir():
            for editor in (".vscode", ".vscode-insiders", ".cursor", ".windsurf"):
                if (user / editor / "extensions").is_dir():
                    roots.append(user / editor / "extensions")
    except OSError:
        pass
    return roots


def find_in_editors(name: str, home: Optional[Path] = None, env=None) -> Optional[Path]:
    """The `name` executable from the editor extension that bundles it: the running editor's
    first (under VS Code), then the newest, or None."""
    prefix = EXTENSIONS.get(name)
    if not prefix:
        return None
    home = home or Path.home()
    exts = []
    for rank, root in enumerate(_editor_order(home, env)):
        try:
            exts += [(rank, p) for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix)]
        except OSError:
            continue
    exts.sort(key=lambda rp: _version(rp[1].name, prefix), reverse=True)
    if (os.environ if env is None else env).get("VSCODE_AGENT_FOLDER"):
        exts.sort(key=lambda rp: rp[0])          # stable sort: the running editor's folder first, newest within it
    for _, ext in exts:
        binary = _binary_in(ext, name)
        if binary:
            return binary
    return None


def _on_path(name: str) -> bool:
    return bool(shutil.which(name) or shutil.which(name + ".cmd") or shutil.which(name + ".exe"))


def add_to_path(home: Optional[Path] = None, prefer: Optional[bool] = None) -> dict[str, str]:
    """Put editor-bundled tools on PATH. Returns what was added: command -> its path.

    prefer (default: whether RAPR runs under VS Code): put the editor's copy first, ahead of
    any install of its own. Otherwise only tools that aren't installed go on, at the end."""
    if prefer is None:
        prefer = under_vscode()
    added = {}
    for name in EXTENSIONS:
        if _on_path(name) and not prefer:
            continue
        binary = find_in_editors(name, home)
        if not binary:
            continue
        path = os.environ.get("PATH", "")
        folder = str(binary.parent)
        if prefer:
            rest = [p for p in path.split(os.pathsep) if p and p != folder]
            os.environ["PATH"] = os.pathsep.join([folder] + rest)
        else:
            os.environ["PATH"] = path + os.pathsep + folder
        added[name] = str(binary)
    return added


def has_extension(prefix: str, home: Optional[Path] = None) -> bool:
    """Whether any editor has an extension whose folder starts with `prefix` installed: here,
    in VS Code Server's folder (a WSL or remote window), or, from inside WSL, on Windows."""
    home = home or Path.home()
    roots = [home / editor / "extensions" for editor in EDITOR_DIRS]
    if home == Path.home():
        roots += _windows_extension_roots()
    for root in roots:
        try:
            if any(p.name.startswith(prefix) for p in root.iterdir()):
                return True
        except OSError:
            continue
    return False
