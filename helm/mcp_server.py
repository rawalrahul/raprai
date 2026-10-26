"""
helm/mcp_server.py — RAPR AI as an MCP server: ask another AI, get a second
opinion, or run a bake-off, from inside Claude Code, Cursor, Codex or any other
MCP client.

    claude mcp add --scope user rapr -- rapr mcp     # Claude Code
    codex mcp add rapr -- rapr mcp                   # Codex

The client starts `rapr mcp` on your own computer and talks to it over
stdin/stdout (MCP's "stdio" transport). Nothing is hosted and the RAPR app
doesn't need to be open: this process runs the AIs' own command-line tools
with your sign-ins, exactly as a RAPR bake-off does.

The other AI works in a temporary copy of your project unless you allow edits,
so a second opinion can't change your files. Bake-offs use RAPR's usual copies
and only touch your project when you merge one.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DIFF_LIMIT = 60_000        # characters of diff given to a reviewer
REPLY_LIMIT = 40_000       # characters of an AI's reply returned to the client
ATTEMPT_DIFF_LIMIT = 8_000
# bakeoff_status waits at most this long per call, so it answers inside MCP clients'
# tool time limits (Codex gives up after 60 seconds unless tool_timeout_sec is raised).
STATUS_WAIT_DEFAULT = 45
STATUS_WAIT_MAX = 50

INSTRUCTIONS = (
    "RAPR AI runs other AI coding agents installed on this computer (Claude Code, Codex, "
    "Antigravity, Ollama…) with the user's own sign-ins. Use second_opinion to have a different "
    "AI review the current changes, ask_agent to put any question or task to another AI, and "
    "start_bakeoff to give the same task to several AIs in separate copies of the project and "
    "compare them. Call list_agents first to see which AIs are available. Each call can take "
    "a few minutes while the other AI works."
)


class ToolError(Exception):
    """A problem to report back to the AI client as a tool error (not a protocol error)."""


# ---------------------------------------------------------------------------
# Running an AI
# ---------------------------------------------------------------------------

_loaded = False


def _load() -> None:
    global _loaded
    if not _loaded:
        from helm.integrations import load_integrations
        load_integrations()
        _loaded = True


def _found(exe: str) -> bool:
    if os.path.isabs(exe):
        return Path(exe).exists()
    return bool(shutil.which(exe) or shutil.which(exe + ".cmd") or shutil.which(exe + ".exe"))


def _ready(key: str, info: dict) -> bool:
    """Installed and set up: its command exists and any keys it needs are set (as in Settings → AI Integrations)."""
    if key == "nemoclaw":
        try:
            from helm.ai_runner.nemoclaw_bridge import is_available
            return bool(is_available())
        except Exception:
            return False
    if not all(os.environ.get(v, "").strip() for v in info.get("env_vars", [])):
        return False
    try:
        cmd = info["build_command"]("test", model=None)
    except Exception:
        return False
    return bool(cmd) and _found((cmd[0] or "").strip())


def agents() -> dict[str, str]:
    """AIs that can be run here: key -> display name."""
    import helm.state as _st
    _load()
    found = {}
    if _found("claude"):
        found["claude"] = "Claude Code"
    for key, info in _st.integrations.items():
        if key not in found and _ready(key, info):
            found[key] = info.get("name") or key
    return found


def _check_agent(agent: str) -> None:
    have = agents()
    if agent not in have:
        raise ToolError(f"{agent!r} isn't available. Installed: {', '.join(have) or 'none'}. "
                        "Use list_agents to see them.")


def run_agent(agent: str, prompt: str, cwd: str, model: Optional[str] = None) -> str:
    """Run one AI's command-line tool in `cwd` and return its reply."""
    from helm.council.runner import _build_cmd_for_session, _run_subprocess_blocking
    _load()
    sess = {"id": "mcp", "ai": agent, "cwd": cwd, "model": model}
    try:
        cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    return _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env)


# ---------------------------------------------------------------------------
# Projects: folders, diffs and throwaway copies
# ---------------------------------------------------------------------------

def _git(cwd: str, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return r.stdout


def is_git(folder: str) -> bool:
    try:
        return _git(folder, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except Exception:
        return False


def _folder(value: Optional[str], default: str) -> str:
    p = Path(value or default).expanduser().resolve()
    if not p.is_dir():
        raise ToolError(f"{p} is not a folder")
    return str(p)


def current_changes(folder: str, base: Optional[str] = None) -> tuple[str, str]:
    """(what, diff): the changes to review. Uncommitted work by default, else the last commit."""
    if not is_git(folder):
        raise ToolError(f"{folder} isn't a git repository, so there's no diff to review. "
                        "Use ask_agent and describe what to look at instead.")
    if base:
        return f"changes since {base}", _git(folder, "diff", base)
    diff = _git(folder, "diff", "HEAD")
    untracked = [f for f in _git(folder, "ls-files", "--others", "--exclude-standard").splitlines() if f]
    for name in untracked[:50]:
        path = Path(folder, name)
        try:
            if path.stat().st_size <= 200_000:
                body = path.read_text(encoding="utf-8")
                diff += f"\n--- /dev/null\n+++ b/{name}\n" + "".join(f"+{l}\n" for l in body.splitlines())
        except (OSError, UnicodeDecodeError):
            diff += f"\n(new file, not shown: {name})\n"
    if diff.strip():
        return "uncommitted changes", diff
    if _git(folder, "rev-parse", "--verify", "HEAD~1", check=False).strip():
        return "the last commit", _git(folder, "show", "--format=%s%n%n%b", "HEAD")
    raise ToolError("There are no changes to review (no uncommitted changes and only one commit).")


class Scratch:
    """A throwaway copy of a project, including uncommitted changes. The other AI works here."""

    def __init__(self, folder: str):
        self.folder = folder
        self.root = tempfile.mkdtemp(prefix="rapr-mcp-")
        self.path = str(Path(self.root, Path(folder).name or "project"))
        self.git = False
        if is_git(folder):
            try:
                self._from_git(folder)
                self.git = True
                return
            except Exception:   # e.g. a repository with no commits yet: fall back to a plain copy
                self.close()
                self.root = tempfile.mkdtemp(prefix="rapr-mcp-")
                self.path = str(Path(self.root, Path(folder).name or "project"))
        shutil.copytree(folder, self.path, symlinks=True,
                        ignore=shutil.ignore_patterns("node_modules", ".venv", "venv", "__pycache__", ".git"))
        self.cwd = self.path

    def _from_git(self, folder: str) -> None:
        top = _git(folder, "rev-parse", "--show-toplevel").strip()
        self.top = top
        _git(top, "worktree", "add", "--detach", "-q", self.path, "HEAD")
        patch = _git(top, "diff", "HEAD", "--binary")
        if patch.strip():
            subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=self.path, input=patch,
                           capture_output=True, text=True, timeout=120)
        for name in _git(top, "ls-files", "--others", "--exclude-standard").splitlines():
            src, dst = Path(top, name), Path(self.path, name)
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        # Remember the starting point without committing (no hooks, no signing).
        _git(self.path, "add", "-A")
        self.start = _git(self.path, "write-tree").strip()
        # Run in the same subfolder the client is in.
        self.cwd = str(Path(self.path, Path(folder).resolve().relative_to(Path(top).resolve())))

    def changes(self) -> str:
        """What the AI changed in the copy (git projects only)."""
        if not self.git:
            return ""
        _git(self.path, "add", "-A")
        return _git(self.path, "diff", "--cached", self.start)

    def close(self) -> None:
        if getattr(self, "top", None):
            _git(self.top, "worktree", "remove", "--force", self.path, check=False)
        shutil.rmtree(self.root, ignore_errors=True)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… ({len(text) - limit:,} more characters cut)"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def tool_list_agents(args: dict, ctx: "Server") -> str:
    have = agents()
    if not have:
        return ("No AI command-line tools were found. Install one (for example Codex: "
                "npm i -g @openai/codex) and sign in, then try again.")
    return "AIs available through RAPR on this computer:\n" + "\n".join(f"- {k} ({v})" for k, v in have.items())


def tool_latest_brief(args: dict, ctx: "Server") -> str:
    """Your latest brief from the RAPR app: what needs you, across every AI's connected apps."""
    from helm import brief
    latest = brief.latest()
    if not latest:
        return ("No brief yet. In the RAPR app, open Settings → Your brief, pick which AIs should look "
                "through their connected apps, and press 'Send me one now'.")
    return brief.text(latest, how_to_act=False) + (
        "\n\nTo act on an item, open RAPR (Needs you) or reply /do <number> on Telegram or WhatsApp.")


def tool_ask_agent(args: dict, ctx: "Server") -> str:
    agent, prompt = args["agent"], args["prompt"].strip()
    if not prompt:
        raise ToolError("prompt is empty")
    _check_agent(agent)
    folder = _folder(args.get("folder"), ctx.cwd)
    if args.get("allow_edits"):
        reply = run_agent(agent, prompt, folder, args.get("model"))
        return f"{agent} (working in {folder}, edits allowed):\n\n{_clip(reply, REPLY_LIMIT)}"
    scratch = Scratch(folder)
    try:
        reply = run_agent(agent, prompt, scratch.cwd, args.get("model"))
        changes = scratch.changes()
    finally:
        scratch.close()
    out = f"{agent} replied:\n\n{_clip(reply, REPLY_LIMIT)}"
    if changes.strip():
        out += ("\n\nIt also made changes in a temporary copy of the project (not applied to your files):\n\n"
                + _clip(changes, REPLY_LIMIT))
    return out


REVIEW_PROMPT = """You are reviewing a code change written by another AI coding agent. You are the second opinion.

Look for real problems: bugs, wrong logic, missed edge cases, security issues, broken callers, missing tests for risky paths. Read the surrounding code in this project where you need context. Do not modify any files.

Reply with your findings, most serious first. For each: the file and line, what goes wrong and when, and the fix. Skip style nits unless they hide a bug. If you find nothing worth changing, say "Looks good" and what you checked.
{focus}
The change ({what}):

{diff}
"""


def tool_second_opinion(args: dict, ctx: "Server") -> str:
    agent = args["agent"]
    _check_agent(agent)
    folder = _folder(args.get("folder"), ctx.cwd)
    what, diff = current_changes(folder, args.get("base"))
    focus = f"\nThe author asks you to focus on: {args['focus'].strip()}\n" if (args.get("focus") or "").strip() else ""
    prompt = REVIEW_PROMPT.format(focus=focus, what=what, diff=_clip(diff, DIFF_LIMIT))
    scratch = Scratch(folder)
    try:
        reply = run_agent(agent, prompt, scratch.cwd, args.get("model"))
    finally:
        scratch.close()
    return f"Second opinion from {agent} on {what}:\n\n{_clip(reply, REPLY_LIMIT)}"


def _bakeoff_report(b, include_diffs: bool) -> str:
    lines = [f"Bake-off {b.id}: {b.status}", f"Task: {b.task}"]
    if b.test_command:
        lines.append(f"Test command: {b.test_command}")
    for a in b.attempts:
        if b.status in ("created", "running") and not a.seconds:
            lines.append(f"\n## {a.ai}: still working…")
            continue
        bits = ["failed: " + a.error if a.error else f"{a.seconds:.0f}s",
                f"{a.files_changed} file(s) changed, +{a.lines_added} −{a.lines_removed}"]
        if a.tests_passed is not None:
            bits.append("tests passed" if a.tests_passed else "tests FAILED")
        lines.append(f"\n## {a.ai}{' (merged)' if b.winner is not None and b.attempts[b.winner] is a else ''}: "
                     + ", ".join(bits))
        if a.output:
            lines.append("What it said:\n" + _clip(a.output.strip(), 1500))
        if include_diffs and a.diff.strip():
            lines.append("Diff:\n" + _clip(a.diff, ATTEMPT_DIFF_LIMIT))
    if b.status in ("created", "running"):
        lines.append("\nStill running. Call bakeoff_status again to keep waiting.")
    if b.status == "done":
        lines.append("\nNext: merge_bakeoff with the agent you prefer (it applies that attempt to the project), "
                     "or discard_bakeoff. The result is also kept in RAPR, where it counts in the monthly recap.")
    return "\n".join(lines)


def tool_start_bakeoff(args: dict, ctx: "Server") -> str:
    import helm.bakeoff as bakeoff
    ais = list(dict.fromkeys(args.get("agents") or []))
    for a in ais:
        _check_agent(a)
    folder = _folder(args.get("folder"), ctx.cwd)
    try:
        b = bakeoff.create(folder, args["task"], ais, test_command=(args.get("test_command") or None))
    except (ValueError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc

    async def runner(ai: str, prompt: str, cwd: str) -> str:
        return run_agent(ai, prompt, cwd)

    def go():
        import asyncio
        try:
            asyncio.run(bakeoff.run(b, runner))
        except Exception as exc:   # a crash shows up in the report instead of hanging
            for a in b.attempts:
                a.error = a.error or f"bake-off stopped: {exc}"
            b.status = "done" if b.status == "running" else b.status
        _save(b)

    ctx.bakeoffs[b.id] = b
    threading.Thread(target=go, daemon=True, name=f"bakeoff-{b.id}").start()
    return (f"Started bake-off {b.id}: {', '.join(ais)} are each working in their own copy of {folder}. "
            f"This usually takes a few minutes. Call bakeoff_status with id {b.id!r} to wait for the results.")


def _save(b) -> None:
    try:
        import helm.bakeoff as bakeoff
        from helm import bakeoff_history
        from helm.db import init_db
        init_db()
        bakeoff_history.save(bakeoff.result(b))
    except Exception:
        pass   # history is a nice-to-have; the bake-off itself worked


def _get_bakeoff(args: dict, ctx: "Server"):
    b = ctx.bakeoffs.get(args.get("id", ""))
    if not b:
        raise ToolError(f"No bake-off {args.get('id')!r} in this session. Running ones: "
                        f"{', '.join(ctx.bakeoffs) or 'none'}.")
    return b


def tool_bakeoff_status(args: dict, ctx: "Server") -> str:
    b = _get_bakeoff(args, ctx)
    wait = max(0, min(int(args.get("wait_seconds", STATUS_WAIT_DEFAULT)), STATUS_WAIT_MAX))
    end = time.monotonic() + wait
    while b.status in ("created", "running") and time.monotonic() < end:
        time.sleep(1)
    return _bakeoff_report(b, include_diffs=args.get("include_diffs", True))


def tool_merge_bakeoff(args: dict, ctx: "Server") -> str:
    import helm.bakeoff as bakeoff
    b = _get_bakeoff(args, ctx)
    names = [a.ai for a in b.attempts]
    if args.get("agent") not in names:
        raise ToolError(f"pick one of: {', '.join(names)}")
    try:
        n = bakeoff.merge(b, names.index(args["agent"]))
    except (ValueError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc
    _save(b)
    return (f"Merged {args['agent']}'s attempt into {b.repo} ({n} file(s)); the other copies were removed. "
            "The changes are staged, not committed.")


def tool_discard_bakeoff(args: dict, ctx: "Server") -> str:
    import helm.bakeoff as bakeoff
    b = _get_bakeoff(args, ctx)
    finished = b.status == "done"
    bakeoff.discard(b)
    if finished:
        _save(b)
    return f"Discarded bake-off {b.id}; all copies removed and your project is unchanged."


_FOLDER = {"type": "string", "description": "Project folder. Defaults to the folder the MCP client started in."}
_AGENT = {"type": "string", "description": "Which AI, e.g. codex, claude, antigravity, ollama. See list_agents."}

TOOLS: dict[str, tuple[dict, Callable[[dict, "Server"], str]]] = {
    "list_agents": ({
        "description": "List the AI coding agents RAPR can run on this computer.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    }, tool_list_agents),
    "latest_brief": ({
        "description": "What needs the user right now, from their latest RAPR brief: approvals waiting, "
                       "unfinished sessions, scheduled-task results, and what each of their AIs found in the "
                       "apps it is connected to (email, calendar, chat, GitHub...). Read-only.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True},
    }, tool_latest_brief),
    "second_opinion": ({
        "description": "Have a different AI review the current code changes (uncommitted work, or the last "
                       "commit if there is none) and report bugs and risks. It works in a temporary copy, so "
                       "your files are never changed. Takes a few minutes.",
        "inputSchema": {"type": "object", "required": ["agent"], "properties": {
            "agent": _AGENT,
            "focus": {"type": "string", "description": "Optional: what the reviewer should look at hardest."},
            "base": {"type": "string", "description": "Optional git ref to diff against instead, e.g. main."},
            "folder": _FOLDER,
            "model": {"type": "string", "description": "Optional model for that AI."},
        }},
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    }, tool_second_opinion),
    "ask_agent": ({
        "description": "Send a question or task to another AI and return its reply. By default it works in a "
                       "temporary copy of the project and any changes it makes are returned as a diff, not "
                       "applied. Set allow_edits to let it change the real project.",
        "inputSchema": {"type": "object", "required": ["agent", "prompt"], "properties": {
            "agent": _AGENT,
            "prompt": {"type": "string", "description": "What to ask or ask it to do."},
            "allow_edits": {"type": "boolean", "default": False,
                            "description": "Let the AI edit files in the real project folder."},
            "folder": _FOLDER,
            "model": {"type": "string", "description": "Optional model for that AI."},
        }},
        "annotations": {"openWorldHint": True},
    }, tool_ask_agent),
    "start_bakeoff": ({
        "description": "Give the same task to 2-4 AIs, each in its own copy of the project, to compare their "
                       "solutions. Returns an id right away; call bakeoff_status to get the results.",
        "inputSchema": {"type": "object", "required": ["task", "agents"], "properties": {
            "task": {"type": "string", "description": "The task, as you'd give it to one AI."},
            "agents": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4,
                       "description": "2 to 4 AIs from list_agents."},
            "test_command": {"type": "string", "description": "Optional command run in each copy afterwards, e.g. pytest -q."},
            "folder": _FOLDER,
        }},
        "annotations": {"openWorldHint": True},
    }, tool_start_bakeoff),
    "bakeoff_status": ({
        "description": "Wait for a bake-off (up to wait_seconds) and report each AI's time, files and lines "
                       "changed, test result, what it said and its diff. If it's still running, call again.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {
            "id": {"type": "string"},
            "wait_seconds": {"type": "integer", "minimum": 0, "maximum": STATUS_WAIT_MAX, "default": STATUS_WAIT_DEFAULT},
            "include_diffs": {"type": "boolean", "default": True},
        }},
        "annotations": {"readOnlyHint": True},
    }, tool_bakeoff_status),
    "merge_bakeoff": ({
        "description": "Apply one AI's bake-off attempt to the project (staged, not committed) and remove the copies.",
        "inputSchema": {"type": "object", "required": ["id", "agent"], "properties": {
            "id": {"type": "string"}, "agent": {"type": "string", "description": "The AI whose attempt to keep."},
        }},
        "annotations": {"destructiveHint": True},
    }, tool_merge_bakeoff),
    "discard_bakeoff": ({
        "description": "Throw away every attempt of a bake-off. The project is left unchanged.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
    }, tool_discard_bakeoff),
}


# ---------------------------------------------------------------------------
# The MCP protocol (JSON-RPC 2.0, one message per line on stdin/stdout)
# ---------------------------------------------------------------------------

class Server:
    def __init__(self, out, cwd: Optional[str] = None):
        self.out = out
        self.cwd = cwd or os.getcwd()
        self.bakeoffs: dict = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mcp-tool")

    def send(self, msg: dict) -> None:
        line = json.dumps(msg, ensure_ascii=False)
        with self._lock:
            self.out.write(line + "\n")
            self.out.flush()

    def _reply(self, mid, result=None, error=None) -> None:
        msg = {"jsonrpc": "2.0", "id": mid}
        if error is not None:
            msg["error"] = error
        else:
            msg["result"] = result
        self.send(msg)

    def call_tool(self, name: str, args: dict) -> dict:
        if name not in TOOLS:
            return {"content": [{"type": "text", "text": f"Unknown tool {name!r}"}], "isError": True}
        spec, fn = TOOLS[name]
        missing = [k for k in spec["inputSchema"].get("required", []) if k not in args]
        if missing:
            return {"content": [{"type": "text", "text": f"Missing: {', '.join(missing)}"}], "isError": True}
        try:
            return {"content": [{"type": "text", "text": fn(args, self)}]}
        except ToolError as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        except Exception as exc:
            return {"content": [{"type": "text", "text": f"{name} failed: {exc}"}], "isError": True}

    def handle(self, msg: dict) -> None:
        method, mid = msg.get("method"), msg.get("id")
        if method is None:          # a response to something we never send
            return
        params = msg.get("params") or {}
        if method == "initialize":
            from helm.version import APP_VERSION
            asked = params.get("protocolVersion")
            self._reply(mid, {
                "protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "rapr-ai", "title": "RAPR AI", "version": APP_VERSION},
                "instructions": INSTRUCTIONS,
            })
        elif method == "ping":
            self._reply(mid, {})
        elif method == "tools/list":
            self._reply(mid, {"tools": [{"name": n, **spec} for n, (spec, _) in TOOLS.items()]})
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            # Tools take minutes; run them off the reading thread so pings still get answers.
            self._pool.submit(lambda: self._reply(mid, self.call_tool(name, args)))
        elif mid is not None:
            self._reply(mid, error={"code": -32601, "message": f"Method not found: {method}"})
        # other notifications (initialized, cancelled…) need no answer

    def serve(self, inp) -> None:
        for line in inp:
            line = line.strip().lstrip("\ufeff")   # Windows PowerShell can put a byte-order mark in front
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                self.send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
                continue
            for m in msg if isinstance(msg, list) else [msg]:
                if isinstance(m, dict):
                    self.handle(m)
        self._pool.shutdown(wait=False, cancel_futures=True)


def main() -> None:
    # stdout carries the protocol; anything else printed (logs, warnings) goes to stderr.
    proto = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", buffering=1, closefd=False)
    sys.stdout = sys.stderr
    inp = open(sys.stdin.fileno(), "r", encoding="utf-8", closefd=False)
    import logging
    logging.getLogger("helm").setLevel(logging.WARNING)
    Server(proto).serve(inp)
