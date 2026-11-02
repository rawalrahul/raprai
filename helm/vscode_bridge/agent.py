"""
helm/vscode_bridge/agent.py: GitHub Copilot (through the RAPR Bridge in VS Code) as an agent.

The bridge gives Copilot tools through VS Code's language model API and hands back the tool
calls Copilot asks for; this loop runs them in the folder RAPR gave it and sends the results
back, until Copilot answers. Which tools Copilot gets depends on the job (RAPR_AGENT_MODE):

  read      look only: list, read and search files (second opinions, questions)
  edit      also write and edit files (the real project, with allow_edits: like Claude
            Code there, it may change files but not run commands)
  edit+run  also run commands (a copy of the project: ask_agent, bake-offs, relays, teams)

Every path stays inside the working folder: no `..` out of it, no absolute paths elsewhere,
nothing written into .git.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional

READ, EDIT, RUN = "read", "edit", "edit+run"
MODES = (READ, EDIT, RUN)
MAX_STEPS = 60
RESULT_LIMIT = 20_000         # characters of one tool result sent back to Copilot
READ_LIMIT = 60_000
COMMAND_TIMEOUT = 600
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache", "dist", "build"}


class ToolFailed(Exception):
    """A tool couldn't do what was asked: the message goes back to Copilot."""


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


_PATH = {"type": "string", "description": "Path relative to the project folder."}

TOOLS = {
    "list_files": ({
        "description": "List the files and folders in a folder of the project (recursively up to `depth`).",
        "inputSchema": _schema({"path": {**_PATH, "default": "."},
                                "depth": {"type": "integer", "default": 2, "minimum": 1, "maximum": 6}}, []),
    }, READ),
    "read_file": ({
        "description": "Read a text file of the project, optionally only lines start_line to end_line (1-based).",
        "inputSchema": _schema({"path": _PATH, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
                               ["path"]),
    }, READ),
    "search_files": ({
        "description": "Search the project's text files for a regular expression; returns path:line: text.",
        "inputSchema": _schema({"pattern": {"type": "string"}, "path": {**_PATH, "default": "."}}, ["pattern"]),
    }, READ),
    "write_file": ({
        "description": "Create or overwrite a file of the project with this content.",
        "inputSchema": _schema({"path": _PATH, "content": {"type": "string"}}, ["path", "content"]),
    }, EDIT),
    "edit_file": ({
        "description": "Replace one exact piece of text in a file (old_text must appear exactly once) with new_text.",
        "inputSchema": _schema({"path": _PATH, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
                               ["path", "old_text", "new_text"]),
    }, EDIT),
    "run_command": ({
        "description": "Run a shell command in the project folder (tests, builds, git status...) and get its output.",
        "inputSchema": _schema({"command": {"type": "string"},
                                "timeout_seconds": {"type": "integer", "default": 300, "maximum": COMMAND_TIMEOUT}},
                               ["command"]),
    }, RUN),
}

_RANK = {READ: 0, EDIT: 1, RUN: 2}


def tools_for(mode: str) -> list[dict]:
    return [{"name": name, **spec} for name, (spec, needs) in TOOLS.items() if _RANK[needs] <= _RANK[mode]]


def instructions(mode: str, cwd: str) -> str:
    can = {READ: "You can look at the project (list, read, search files) but not change it.",
           EDIT: "You can look at the project and change files (write_file, edit_file), but not run commands.",
           RUN: "You can look at the project, change files (write_file, edit_file) and run commands (run_command)."}[mode]
    return (f"You are GitHub Copilot, working as a coding agent in the project folder {cwd}. {can} "
            "Use the tools to do the task yourself: read what you need, make the changes, and check them "
            "(run the tests when you can). Paths are relative to the project folder. When you're done, reply "
            "with a short summary of what you did and anything left open, without calling more tools.\n\nTask:\n")


# ---------------------------------------------------------------------------
# The tools
# ---------------------------------------------------------------------------

def _inside(cwd: Path, rel, write: bool = False) -> Path:
    if not isinstance(rel, str) or not rel.strip():
        raise ToolFailed("path is required")
    p = (cwd / rel).resolve()
    root = cwd.resolve()
    if p != root and root not in p.parents:
        raise ToolFailed(f"{rel} is outside the project folder")
    if write and (".git" in p.relative_to(root).parts):
        raise ToolFailed("RAPR doesn't let the agent write inside .git")
    return p


def _clip(text: str, limit: int = RESULT_LIMIT) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n…({len(text) - limit:,} more characters)"


def _list(cwd: Path, args: dict) -> str:
    base = _inside(cwd, args.get("path") or ".")
    depth = max(1, min(int(args.get("depth") or 2), 6))
    if not base.is_dir():
        raise ToolFailed(f"{args.get('path')} isn't a folder")
    lines = []
    for root, dirs, files in os.walk(base):
        level = len(Path(root).relative_to(base).parts)
        shown = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        dirs[:] = shown if level < depth - 1 else []          # listed, but not entered, at the last level
        rel = Path(root).relative_to(cwd.resolve())
        for d in shown:
            lines.append(f"{(rel / d).as_posix()}/")
        for f in sorted(files):
            lines.append((rel / f).as_posix())
        if len(lines) > 800:
            lines.append("…(more)")
            break
    return "\n".join(lines) or "(empty)"


def _read(cwd: Path, args: dict) -> str:
    p = _inside(cwd, args.get("path"))
    if not p.is_file():
        raise ToolFailed(f"{args.get('path')} isn't a file")
    text = p.read_text(encoding="utf-8", errors="replace")
    start, end = args.get("start_line"), args.get("end_line")
    if start or end:
        lines = text.splitlines()
        a = max(1, int(start or 1))
        b = min(len(lines), int(end or len(lines)))
        text = "\n".join(f"{i}: {lines[i - 1]}" for i in range(a, b + 1))
    return _clip(text, READ_LIMIT)


def _search(cwd: Path, args: dict) -> str:
    try:
        rx = re.compile(args.get("pattern") or "")
    except re.error as exc:
        raise ToolFailed(f"bad pattern: {exc}") from exc
    base = _inside(cwd, args.get("path") or ".")
    hits = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            p = Path(root) / f
            try:
                if p.stat().st_size > 2_000_000:
                    continue
                with open(p, encoding="utf-8") as fh:
                    for n, line in enumerate(fh, 1):
                        if rx.search(line):
                            hits.append(f"{p.relative_to(cwd.resolve()).as_posix()}:{n}: {line.rstrip()[:300]}")
                            if len(hits) >= 200:
                                return "\n".join(hits) + "\n…(more matches)"
            except (OSError, UnicodeDecodeError):
                continue
    return "\n".join(hits) or "(no matches)"


def _write(cwd: Path, args: dict) -> str:
    p = _inside(cwd, args.get("path"), write=True)
    content = args.get("content")
    if not isinstance(content, str):
        raise ToolFailed("content is required")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {args['path']} ({len(content):,} characters)"


def _edit(cwd: Path, args: dict) -> str:
    p = _inside(cwd, args.get("path"), write=True)
    if not p.is_file():
        raise ToolFailed(f"{args.get('path')} isn't a file")
    old, new = args.get("old_text"), args.get("new_text")
    if not isinstance(old, str) or not old or not isinstance(new, str):
        raise ToolFailed("old_text and new_text are required")
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        raise ToolFailed(f"old_text appears {n} times in {args['path']}; it must appear exactly once "
                         "(include more of the surrounding lines)")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"edited {args['path']}"


def _run(cwd: Path, args: dict) -> str:
    command = args.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ToolFailed("command is required")
    timeout = max(1, min(int(args.get("timeout_seconds") or 300), COMMAND_TIMEOUT))
    from helm.subprocess_utils import hidden_kwargs
    try:
        r = subprocess.run(command, shell=True, cwd=str(cwd), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           stdin=subprocess.DEVNULL, **hidden_kwargs())
    except subprocess.TimeoutExpired:
        return f"(timed out after {timeout}s)"
    out = ((r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")).strip()
    if not out:
        return f"exit code {r.returncode} (no output)"
    return f"exit code {r.returncode}\n" + _clip(out[-RESULT_LIMIT * 2:])


_RUNNERS: dict[str, Callable[[Path, dict], str]] = {
    "list_files": _list, "read_file": _read, "search_files": _search,
    "write_file": _write, "edit_file": _edit, "run_command": _run,
}


def run_tool(name: str, args, cwd: Path, mode: str) -> str:
    """Run one tool call; any failure comes back as text Copilot can act on."""
    spec = TOOLS.get(name)
    if spec is None:
        return f"error: there's no tool called {name}"
    if _RANK[spec[1]] > _RANK[mode]:
        return f"error: {name} isn't allowed for this task"
    try:
        return _clip(_RUNNERS[name](cwd, args if isinstance(args, dict) else {}))
    except ToolFailed as exc:
        return f"error: {exc}"
    except (OSError, ValueError, TypeError) as exc:
        return f"error: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def run(prompt: str, cwd: str, mode: str = READ, model: Optional[str] = None,
        chat: Optional[Callable[..., dict]] = None, max_steps: int = MAX_STEPS,
        log: Callable[[str], None] = lambda line: None) -> str:
    """Give Copilot the task and its tools, run the tool calls it asks for, and return its
    final answer."""
    if mode not in MODES:
        mode = READ
    if chat is None:
        from helm import vscode_bridge
        chat = vscode_bridge.chat
    folder = Path(cwd)
    tools = tools_for(mode)
    messages: list[dict] = [{"role": "user", "content": instructions(mode, cwd) + prompt}]
    last_text = ""
    started = time.monotonic()
    for step in range(1, max_steps + 1):
        answer = chat(messages, tools, model)
        text, calls = answer.get("text") or "", answer.get("toolCalls") or []
        if text.strip():
            last_text = text
        if not calls:
            return text if text.strip() else last_text
        messages.append({"role": "assistant", "content": text, "toolCalls": calls})
        results = []
        for c in calls:
            out = run_tool(str(c.get("name")), c.get("input"), folder, mode)
            log(f"step {step}: {c.get('name')} -> {out.splitlines()[0][:120] if out else ''}")
            results.append({"callId": c.get("callId"), "content": out})
        messages.append({"role": "user", "toolResults": results})
    minutes = int((time.monotonic() - started) // 60)
    return (last_text + f"\n\n(RAPR stopped Copilot after {max_steps} steps, {minutes} min; the work so far is in "
            "the folder.)").strip()
