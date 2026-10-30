"""AI command-line tools that came with an editor extension rather than their own install.

The Claude Code extension for VS Code (and Cursor, Windsurf…) ships its own `claude`,
and the Codex extension its own `codex`, inside the extension's folder. Neither puts
it on PATH, so someone with only the extension had no Claude or Codex in RAPR. When a
tool isn't on PATH, add_to_path() appends the folder of the newest extension copy, so
every `shutil.which` and subprocess call finds it. A real install stays first on PATH.
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


def find_in_editors(name: str, home: Optional[Path] = None) -> Optional[Path]:
    """The `name` executable from the newest editor extension that bundles it, or None."""
    prefix = EXTENSIONS.get(name)
    if not prefix:
        return None
    home = home or Path.home()
    exts = []
    for editor in EDITOR_DIRS:
        root = home / editor / "extensions"
        try:
            exts += [p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix)]
        except OSError:
            continue
    for ext in sorted(exts, key=lambda p: _version(p.name, prefix), reverse=True):
        binary = _binary_in(ext, name)
        if binary:
            return binary
    return None


def _on_path(name: str) -> bool:
    return bool(shutil.which(name) or shutil.which(name + ".cmd") or shutil.which(name + ".exe"))


def add_to_path(home: Optional[Path] = None) -> dict[str, str]:
    """Put editor-bundled tools that aren't installed on their own at the end of PATH.
    Returns what was added: command -> its path."""
    added = {}
    for name in EXTENSIONS:
        if _on_path(name):
            continue
        binary = find_in_editors(name, home)
        if binary:
            os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(binary.parent)
            added[name] = str(binary)
    return added


def has_extension(prefix: str, home: Optional[Path] = None) -> bool:
    """Whether any editor has an extension whose folder starts with `prefix` installed."""
    home = home or Path.home()
    for editor in EDITOR_DIRS:
        try:
            if any(p.name.startswith(prefix) for p in (home / editor / "extensions").iterdir()):
                return True
        except OSError:
            continue
    return False
