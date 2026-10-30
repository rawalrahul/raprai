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

import logging
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

logger = logging.getLogger(__name__)

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DIFF_LIMIT = 60_000        # characters of diff given to a reviewer
REPLY_LIMIT = 40_000       # characters of an AI's reply returned to the client
ATTEMPT_DIFF_LIMIT = 8_000
# bakeoff_status waits at most this long per call, so it answers inside MCP clients'
# tool time limits (Codex gives up after 60 seconds unless tool_timeout_sec is raised).
STATUS_WAIT_DEFAULT = 45
STATUS_WAIT_MAX = 50
AGENT_TIMEOUT = 300        # seconds an AI gets to answer (a bake-off attempt gets BUILD_TIMEOUT)
BUILD_TIMEOUT = 1800

INSTRUCTIONS = (
    "RAPR AI runs other AI coding agents installed on this computer (Claude Code, Codex, "
    "Antigravity, Grok, Ollama…) with the user's own sign-ins. Use second_opinion to have a "
    "different AI review the current changes, ask_agent to put any question or task to another "
    "AI, start_relay to have one AI plan, another build, and another review and get fixes, "
    "start_team to split a plan into parts that different AIs do at the same time and then merge, and "
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
    if not (cmd and _found((cmd[0] or "").strip())):
        return False
    from helm.signin import signed_in
    if not signed_in(key):
        return False
    ready = info.get("ready")
    if callable(ready):
        try:
            return bool(ready())
        except Exception:
            return False
    return True


def agents() -> dict[str, str]:
    """AIs that can be run here: key -> display name."""
    import helm.state as _st
    _load()
    from helm.signin import signed_in
    found = {}
    if _found("claude") and signed_in("claude"):
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


def run_agent(agent: str, prompt: str, cwd: str, model: Optional[str] = None, *, edits: bool = False,
              timeout: int = AGENT_TIMEOUT, on_start=None) -> str:
    """Run one AI's command-line tool in `cwd` and return its reply.

    edits: the AI is meant to change files. Claude Code asks before every edit, and
    with nobody there to answer it would change nothing, so it's allowed file edits
    (not commands). The other AIs' commands already let them edit.
    """
    from helm.council.runner import _build_cmd_for_session, _run_subprocess_blocking
    _load()
    sess = {"id": "mcp", "ai": agent, "cwd": cwd, "model": model}
    try:
        cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    if edits and agent == "claude":
        cmd[1:1] = ["--permission-mode", "acceptEdits"]
    return _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env, on_start=on_start, timeout=timeout)


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


_SKIP = ("node_modules", ".venv", "venv", "__pycache__", ".git")


def _files(root: str) -> dict[str, bytes]:
    """Every file in a plain copy (not a git one) and its contents."""
    out = {}
    for p in Path(root).rglob("*"):
        if p.is_file() and not p.is_symlink() and not any(part in _SKIP for part in p.relative_to(root).parts):
            out[p.relative_to(root).as_posix()] = p.read_bytes()
    return out


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
                        ignore=shutil.ignore_patterns(*_SKIP))
        self.cwd = self.path
        self.start_files = _files(self.path)

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

    # A relay works in one copy for several steps: these keep a planner or reviewer
    # from leaving changes behind, and bring the result back to the project.

    def snapshot(self):
        """A point to go back to: a git tree, or every file's contents in a plain copy."""
        if self.git:
            _git(self.path, "add", "-A")
            return _git(self.path, "write-tree").strip()
        return _files(self.path)

    def restore(self, point) -> None:
        """Put the copy back the way it was at `point`."""
        if self.git:
            _git(self.path, "read-tree", "-u", "--reset", point)
            _git(self.path, "clean", "-fdq")
            return
        now = _files(self.path)
        for name in now.keys() - point.keys():
            Path(self.path, name).unlink()
        for name, data in point.items():
            if now.get(name) != data:
                Path(self.path, name).parent.mkdir(parents=True, exist_ok=True)
                Path(self.path, name).write_bytes(data)

    def diff(self) -> tuple[str, list[str]]:
        """(diff for people, changed files) since the copy was made."""
        if self.git:
            _git(self.path, "add", "-A")
            names = [n for n in _git(self.path, "diff", "--cached", "--name-only", self.start).splitlines() if n]
            return self._patch().decode("utf-8", "replace"), names
        before, now = self.start_files, _files(self.path)
        names = sorted(n for n in before.keys() | now.keys() if before.get(n) != now.get(n))
        return "\n".join(("deleted: " if n not in now else "changed: ") + n for n in names), names

    def _patch(self) -> bytes:
        # Bytes, so files with Windows line endings still apply (see bakeoff._collect).
        out = subprocess.run(["git", "diff", "--cached", "--binary", self.start], cwd=self.path,
                             capture_output=True, timeout=120)
        if out.returncode != 0:
            raise RuntimeError(out.stderr.decode(errors="replace").strip()[:300])
        return out.stdout

    def apply(self) -> list[str]:
        """Bring the copy's changes into the real project (not staged, not committed)."""
        _, names = self.diff()
        if self.git:
            patch = self._patch()
            if patch.strip():
                r = subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=self.top,
                                   input=patch, capture_output=True, timeout=120)
                if r.returncode != 0:
                    raise RuntimeError("the changes don't apply to the project any more (did it change "
                                       "meanwhile?): " + r.stderr.decode(errors="replace").strip()[:300])
            return names
        for name in names:
            src, dst = Path(self.path, name), Path(self.folder, name)
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            elif dst.exists():
                dst.unlink()
        return names

    def close(self) -> None:
        if getattr(self, "top", None):
            _git(self.top, "worktree", "remove", "--force", self.path, check=False)
        shutil.rmtree(self.root, ignore_errors=True)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… ({len(text) - limit:,} more characters cut)"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

SIGN_IN = {"claude": "claude auth login", "codex": "codex login", "grok": "grok login",
           "amazon_q": "kiro-cli login"}


def signed_out() -> list[str]:
    """Installed tools that say they aren't signed in, so they aren't offered."""
    from helm.signin import status
    have = agents()
    return [name for name in SIGN_IN if name not in have and status(name) is False]


def tool_list_agents(args: dict, ctx: "Server") -> str:
    have = agents()
    out = signed_out()
    note = "".join(f"\n{name} is installed but not signed in: run `{SIGN_IN[name]}` in a terminal."
                   for name in out)
    if not have:
        return ("No AI command-line tools are ready. Install one (for example Codex: "
                "npm i -g @openai/codex) and sign in, then try again." + note)
    return ("AIs available through RAPR on this computer:\n"
            + "\n".join(f"- {k} ({v})" for k, v in have.items()) + ("\n" + note if note else ""))


def tool_latest_brief(args: dict, ctx: "Server") -> str:
    """Your latest brief from the RAPR app: what needs you, across every AI's connected apps."""
    from helm import brief
    latest = brief.latest()
    if not latest:
        return ("No brief yet. Briefs are made by the RAPR app (raprai.com): in it, open Settings → Your "
                "brief, pick which AIs should look through their connected apps, and press 'Send me one "
                "now'. The other tools here work without the app.")
    return brief.text(latest, how_to_act=False) + (
        "\n\nTo act on an item, open RAPR (Needs you) or reply /do <number> on Telegram or WhatsApp.")


def tool_ask_agent(args: dict, ctx: "Server") -> str:
    agent, prompt = args["agent"], args["prompt"].strip()
    if not prompt:
        raise ToolError("prompt is empty")
    _check_agent(agent)
    folder = _folder(args.get("folder"), ctx.cwd)
    if args.get("allow_edits"):
        reply = run_agent(agent, prompt, folder, args.get("model"), edits=True)
        return f"{agent} (working in {folder}, edits allowed):\n\n{_clip(reply, REPLY_LIMIT)}"
    scratch = Scratch(folder)
    try:
        reply = run_agent(agent, prompt, scratch.cwd, args.get("model"), edits=True)
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
        return run_agent(ai, prompt, cwd, edits=True, timeout=BUILD_TIMEOUT)

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
        logger.debug("Couldn't save the bake-off to history", exc_info=True)


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


# ---------------------------------------------------------------------------
# Relays: one AI plans, another builds, another reviews, fixes, reviews again
# ---------------------------------------------------------------------------

ROLE_NAMES = {"plan": "Plan", "build": "Build", "review": "Review", "fix": "Fix"}


def tool_start_relay(args: dict, ctx: "Server") -> str:
    from helm import relay
    executor = args["executor"]
    reviewer = args.get("reviewer") or args.get("planner") or ""
    if not reviewer:
        raise ToolError("Pick a reviewer (or a planner, who then reviews too).")
    plan = (args.get("plan") or "").strip()
    planner = None if plan else (args.get("planner") or None)
    for a in dict.fromkeys(x for x in (planner, executor, reviewer, args.get("fixer")) if x):
        _check_agent(a)
    folder = _folder(args.get("folder"), ctx.cwd)
    try:
        r = relay.create(folder, args["task"], executor, reviewer, planner=planner, plan=plan,
                         fixer=args.get("fixer"), fix_rounds=int(args.get("fix_rounds", 1)),
                         test_command=args.get("test_command"))
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    scratch = Scratch(folder)

    def runner(agent, prompt, cwd, *, edits, timeout, on_start):
        return run_agent(agent, prompt, cwd, edits=edits, timeout=timeout, on_start=on_start)

    def go():
        relay.run(r, runner, scratch)
        if r.status in ("failed", "discarded"):
            scratch.close()

    ctx.relays[r.id] = r
    threading.Thread(target=go, daemon=True, name=f"relay-{r.id}").start()
    who = ([f"{planner} plans"] if planner else []) + [f"{executor} builds", f"{reviewer} reviews"]
    if r.fix_rounds:
        who.append(f"{r.fixer} fixes what it finds")
    return (f"Started relay {r.id} in a copy of {folder}: {', '.join(who)}. This usually takes "
            f"10 minutes or more. Call relay_status with id {r.id!r} to follow it.")


def _relay_report(r, include_diff: bool) -> str:
    roles = ([f"planner {r.planner}"] if r.planner else ["plan given"] if r.plan else []) + [
        f"executor {r.executor}", f"reviewer {r.reviewer}"]
    if r.fix_rounds:
        roles.append(f"fixer {r.fixer}")
    lines = [f"Relay {r.id}: {r.status}" + (f" ({r.stage})" if r.busy else ""),
             f"Task: {r.task}", "Roles: " + ", ".join(roles)]
    if r.plan and not r.planner:
        lines.append("\n## The plan you gave\n" + _clip(r.plan, 3000))
    for st in r.steps:
        head = f"\n## {ROLE_NAMES.get(st.role, st.role)}: {st.agent}"
        if not st.seconds and r.busy and st is r.steps[-1]:
            lines.append(head + ": working…")
            continue
        lines.append(head + f" ({st.seconds:.0f}s)" + (f", failed: {st.error}" if st.error else ""))
        if st.output.strip():
            lines.append(_clip(st.output.strip(), 6000 if st.role in ("plan", "review") else 2000))
    if r.tests_passed is not None:
        lines.append(f"\nTests (`{r.test_command}`): {'passed' if r.tests_passed else 'FAILED'}")
        if not r.tests_passed and r.test_output:
            lines.append(_clip(r.test_output, 2000))
    if r.error:
        lines.append(f"\nStopped: {r.error}")
    if r.files and r.status != "discarded":
        lines.append(f"\nFiles changed ({len(r.files)}): " + ", ".join(r.files[:30])
                     + (" …" if len(r.files) > 30 else ""))
        if include_diff and r.diff.strip():
            lines.append("Diff:\n" + _clip(r.diff, REPLY_LIMIT))
    if r.busy:
        lines.append("\nStill running. Call relay_status again to keep waiting.")
    elif r.status == "done":
        said = {True: "The reviewer approved the change.",
                False: "The reviewer still wants changes after the last fix round.",
                None: "The reviewer gave no clear verdict; read the review."}[r.approved]
        lines.append(f"\n{said} Next: merge_relay to apply it to the project (not staged or "
                     "committed), or discard_relay to throw it away.")
    return "\n".join(lines)


def _get_relay(args: dict, ctx: "Server"):
    r = ctx.relays.get(args.get("id", ""))
    if not r:
        raise ToolError(f"No relay {args.get('id')!r} in this session. Relays: {', '.join(ctx.relays) or 'none'}.")
    return r


def tool_relay_status(args: dict, ctx: "Server") -> str:
    r = _get_relay(args, ctx)
    wait = max(0, min(int(args.get("wait_seconds", STATUS_WAIT_DEFAULT)), STATUS_WAIT_MAX))
    end = time.monotonic() + wait
    while r.busy and time.monotonic() < end:
        time.sleep(1)
    return _relay_report(r, include_diff=args.get("include_diff", True))


def tool_merge_relay(args: dict, ctx: "Server") -> str:
    r = _get_relay(args, ctx)
    if r.status != "done":
        raise ToolError(f"Relay {r.id} is {r.status}; only a finished relay can be merged.")
    try:
        names = r.workspace.apply()
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc
    r.workspace.close()
    r.status = "merged"
    return (f"Applied relay {r.id} to {r.folder}: {len(names)} file(s) changed. The changes are not "
            "staged or committed; the copy was removed.")


def tool_discard_relay(args: dict, ctx: "Server") -> str:
    from helm import relay
    r = _get_relay(args, ctx)
    if r.status in ("merged", "discarded"):
        return f"Relay {r.id} is already {r.status}."
    _discard_relay(r, relay)
    return f"Discarded relay {r.id}; the copy is removed and your project is unchanged."


def _discard_relay(r, relay) -> None:
    if relay.stop(r) != "running" and r.workspace is not None:
        r.workspace.close()   # otherwise the relay's thread removes it as it stops


# ---------------------------------------------------------------------------
# Teams: one plan split into parts, each AI on its own part at the same time
# ---------------------------------------------------------------------------

TEAM_PROMPT = """You are one of several AI coding agents working on the same plan at the same time, each in a separate copy of the project. Your changes will be merged with theirs afterwards.
{plan}
Your part ({n} of {total}):
{task}
{others}
Do only your part. Don't make changes that belong to the other parts, and avoid reformatting or moving code you don't need to touch, so the parts merge cleanly. When you're done, say briefly what you changed.
"""


class TeamPart:
    def __init__(self, n: int, agent: str, task: str):
        self.n, self.agent, self.task = n, agent, task
        self.status = "waiting"     # waiting, working, done, failed, merged, conflict, discarded
        self.reply = self.error = self.diff = ""
        self.files: list[str] = []
        self.seconds = 0.0
        self.scratch: Optional[Scratch] = None


class Team:
    def __init__(self, folder: str, plan: str, parts: list[TeamPart]):
        import uuid
        self.id = "team-" + uuid.uuid4().hex[:6]
        self.folder, self.plan, self.parts = folder, plan, parts
        self.closed = False

    @property
    def busy(self) -> bool:
        return any(p.status in ("waiting", "working") for p in self.parts)


def _team_prompt(t: Team, part: TeamPart) -> str:
    others = [f"- part {o.n} ({o.agent}): {o.task}" for o in t.parts if o is not part]
    return TEAM_PROMPT.format(
        plan=f"\nThe overall plan:\n{t.plan}\n" if t.plan else "",
        n=part.n, total=len(t.parts), task=part.task,
        others=("\nThe other parts, done by others (and maybe the user) at the same time:\n"
                + "\n".join(others) + "\n") if others else "")


def _run_part(t: Team, part: TeamPart) -> None:
    start = time.monotonic()
    part.status = "working"
    try:
        part.reply = run_agent(part.agent, _team_prompt(t, part), part.scratch.cwd, edits=True,
                               timeout=BUILD_TIMEOUT)
        part.diff, part.files = part.scratch.diff()
        part.status = "done"
    except Exception as exc:
        part.error = str(exc) or type(exc).__name__
        part.status = "failed"
    part.seconds = time.monotonic() - start
    if t.closed:   # discarded while it worked
        part.scratch.close()
        part.status = "discarded"


def tool_start_team(args: dict, ctx: "Server") -> str:
    raw = args.get("parts") or []
    if not 1 <= len(raw) <= 6:
        raise ToolError("Give 1 to 6 parts, each with an agent and its task.")
    parts = []
    for i, item in enumerate(raw, 1):
        agent, task = (item.get("agent") or "").strip(), (item.get("task") or "").strip()
        if not agent or not task:
            raise ToolError(f"Part {i} needs both an agent and a task.")
        _check_agent(agent)
        parts.append(TeamPart(i, agent, task))
    folder = _folder(args.get("folder"), ctx.cwd)
    t = Team(folder, (args.get("plan") or "").strip(), parts)
    try:
        for part in parts:
            part.scratch = Scratch(folder)
    except Exception as exc:
        for part in parts:
            if part.scratch is not None:
                part.scratch.close()
        raise ToolError(f"Couldn't copy the project: {exc}") from exc
    ctx.teams[t.id] = t
    for part in parts:
        threading.Thread(target=_run_part, args=(t, part), daemon=True,
                         name=f"{t.id}-{part.n}").start()
    who = ", ".join(f"part {p.n} to {p.agent}" for p in parts)
    return (f"Started team {t.id} in separate copies of {folder}: {who}. They work at the same time; "
            "you can work on your own part in the project meanwhile. Call team_status with id "
            f"{t.id!r} to follow them, then merge_team to bring their parts into the project.")


def _overlaps(t: Team) -> dict[str, list[int]]:
    seen: dict[str, list[int]] = {}
    for p in t.parts:
        if p.status in ("done", "merged", "conflict"):
            for name in p.files:
                seen.setdefault(name, []).append(p.n)
    return {name: ns for name, ns in seen.items() if len(ns) > 1}


def _team_report(t: Team, include_diffs: bool) -> str:
    lines = [f"Team {t.id}" + (": working" if t.busy else ""), f"Project: {t.folder}"]
    for p in t.parts:
        head = f"\n## Part {p.n}: {p.agent}, {p.status}"
        if p.seconds:
            head += f" ({p.seconds:.0f}s)"
        lines.append(head + f"\nTask: {_clip(p.task, 500)}")
        if p.error:
            lines.append(f"Error: {_clip(p.error, 1000)}")
        if p.reply.strip():
            lines.append(_clip(p.reply.strip(), 2000))
        if p.files:
            lines.append(f"Files changed ({len(p.files)}): " + ", ".join(p.files[:30])
                         + (" …" if len(p.files) > 30 else ""))
            if include_diffs and p.diff.strip() and p.status == "done":
                lines.append("Diff:\n" + _clip(p.diff, ATTEMPT_DIFF_LIMIT))
    overlaps = _overlaps(t)
    if overlaps:
        lines.append("\nFiles changed by more than one part (check these merge cleanly): "
                     + "; ".join(f"{name} (parts {', '.join(map(str, ns))})" for name, ns in overlaps.items()))
    if t.busy:
        lines.append("\nStill running. Call team_status again to keep waiting; merge_team can already "
                     "bring in the parts that are done.")
    elif any(p.status == "done" for p in t.parts):
        lines.append("\nNext: merge_team to apply the finished parts to the project (not staged or "
                     "committed), or discard_team to throw them away.")
    return "\n".join(lines)


def _get_team(args: dict, ctx: "Server") -> Team:
    t = ctx.teams.get(args.get("id", ""))
    if not t:
        raise ToolError(f"No team {args.get('id')!r} in this session. Teams: {', '.join(ctx.teams) or 'none'}.")
    return t


def tool_team_status(args: dict, ctx: "Server") -> str:
    t = _get_team(args, ctx)
    wait = max(0, min(int(args.get("wait_seconds", STATUS_WAIT_DEFAULT)), STATUS_WAIT_MAX))
    end = time.monotonic() + wait
    while t.busy and time.monotonic() < end:
        time.sleep(1)
    return _team_report(t, include_diffs=args.get("include_diffs", True))


def _changed_since_copy(s: Scratch, names: list[str]) -> list[str]:
    """Files this part changed that also changed in the project since its copy was made (plain folders:
    a part replaces whole files there, so it would undo the other change)."""
    out = []
    for name in names:
        now = Path(s.folder, name)
        before = s.start_files.get(name)
        current = now.read_bytes() if now.is_file() else None
        if current != before:
            out.append(name)
    return out


def tool_merge_team(args: dict, ctx: "Server") -> str:
    t = _get_team(args, ctx)
    wanted = args.get("parts") or [p.n for p in t.parts]
    by_n = {p.n: p for p in t.parts}
    unknown = [n for n in wanted if n not in by_n]
    if unknown:
        raise ToolError(f"No part {', '.join(map(str, unknown))}; this team has parts 1 to {len(t.parts)}.")
    merged, problems = [], []
    for n in wanted:
        p = by_n[n]
        if p.status != "done":
            if p.status != "merged":
                problems.append(f"part {n} ({p.agent}) is {p.status}, not merged")
            continue
        if not p.files:
            p.status = "merged"
            p.scratch.close()
            merged.append(f"part {n} ({p.agent}): no changes")
            continue
        clash = [] if p.scratch.git else _changed_since_copy(p.scratch, p.files)
        if clash:
            p.status = "conflict"
            problems.append(f"part {n} ({p.agent}) not merged: {', '.join(clash[:10])} also changed in the "
                            "project since the copy was made")
            continue
        try:
            names = p.scratch.apply()
        except RuntimeError as exc:
            p.status = "conflict"
            problems.append(f"part {n} ({p.agent}) not merged, it clashes with changes already in the "
                            f"project: {exc}")
            continue
        p.status = "merged"
        p.scratch.close()
        merged.append(f"part {n} ({p.agent}): {len(names)} file(s)")
    out = [f"Team {t.id} into {t.folder}. The changes are not staged or committed."]
    if merged:
        out.append("Merged: " + "; ".join(merged) + ".")
    if problems:
        out.append("Not merged: " + "; ".join(problems) + ".")
    if any(p.status == "conflict" for p in t.parts):
        out.append("A part that clashes keeps its copy: read its diff with team_status, then make that "
                   "change by hand or with ask_agent, or discard_team.")
    return "\n".join(out)


def tool_discard_team(args: dict, ctx: "Server") -> str:
    t = _get_team(args, ctx)
    _close_team(t)
    return f"Discarded team {t.id}: the parts not yet merged are thrown away; merged ones stay in the project."


def _close_team(t: Team) -> None:
    t.closed = True
    for p in t.parts:
        if p.status in ("waiting", "working", "merged", "discarded"):
            continue   # a part still working removes its own copy when it stops
        if p.scratch is not None:
            p.scratch.close()
        p.status = "discarded"


_ROLE = "Which AI, e.g. claude, codex, antigravity, grok. See list_agents."

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
    "start_relay": ({
        "description": "Hand a task down a line of AIs, each in a role the user picks: the planner writes a "
                       "plan, the executor carries it out, the reviewer reviews it and gives a verdict, the "
                       "fixer fixes what it found, and the reviewer checks again (up to fix_rounds times). "
                       "Any AI from list_agents can take any role, and one AI can take several, e.g. plan "
                       "with claude, build with codex, review with claude. Instead of a planner you can pass "
                       "a plan you wrote. It all happens in a copy of the project, so nothing changes until "
                       "merge_relay. Returns an id right away; call relay_status to follow it.",
        "inputSchema": {"type": "object", "required": ["task", "executor"], "properties": {
            "task": {"type": "string", "description": "The task, as you'd give it to one AI."},
            "planner": {"type": "string", "description": "AI that writes the plan. " + _ROLE},
            "plan": {"type": "string", "description": "Optional: a plan to follow instead of asking a planner."},
            "executor": {"type": "string", "description": "AI that carries out the plan. " + _ROLE},
            "reviewer": {"type": "string", "description": "AI that reviews the result. Defaults to the planner. " + _ROLE},
            "fixer": {"type": "string", "description": "AI that fixes what the reviewer found. Defaults to the executor."},
            "fix_rounds": {"type": "integer", "minimum": 0, "maximum": 3, "default": 1,
                           "description": "How many times to fix and review again if the reviewer wants changes."},
            "test_command": {"type": "string", "description": "Optional command run after each build or fix, e.g. pytest -q. "
                                                              "The reviewer sees the result."},
            "folder": _FOLDER,
        }},
        "annotations": {"openWorldHint": True},
    }, tool_start_relay),
    "relay_status": ({
        "description": "Wait for a relay (up to wait_seconds) and report where it is: the plan, what each AI "
                       "said, the reviewer's findings and verdict, test results and the change so far. If "
                       "it's still running, call again.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {
            "id": {"type": "string"},
            "wait_seconds": {"type": "integer", "minimum": 0, "maximum": STATUS_WAIT_MAX, "default": STATUS_WAIT_DEFAULT},
            "include_diff": {"type": "boolean", "default": True},
        }},
        "annotations": {"readOnlyHint": True},
    }, tool_relay_status),
    "merge_relay": ({
        "description": "Apply a finished relay's change to the project (not staged or committed) and remove the copy.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
        "annotations": {"destructiveHint": True},
    }, tool_merge_relay),
    "discard_relay": ({
        "description": "Stop a relay if it's running and throw away its copy. The project is left unchanged.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
    }, tool_discard_relay),
    "start_team": ({
        "description": "Split a plan into parts and give each part to a different AI (or the same AI more "
                       "than once). They work at the same time, each in its own copy of the project, while "
                       "the user can do their own part in the project itself. Each AI is told the whole plan "
                       "and what the others are doing. Returns an id right away; call team_status to follow "
                       "it and merge_team to combine the parts.",
        "inputSchema": {"type": "object", "required": ["parts"], "properties": {
            "parts": {"type": "array", "minItems": 1, "maxItems": 6, "items": {
                "type": "object", "required": ["agent", "task"], "properties": {
                    "agent": _AGENT,
                    "task": {"type": "string", "description": "This part of the plan, as you'd give it to that AI."},
                }}, "description": "1 to 6 parts. Leave out the part the user does themselves."},
            "plan": {"type": "string", "description": "Optional: the whole plan, so each AI sees how its part fits."},
            "folder": _FOLDER,
        }},
        "annotations": {"openWorldHint": True},
    }, tool_start_team),
    "team_status": ({
        "description": "Wait for a team (up to wait_seconds) and report each part: its AI, status, time, what "
                       "it said, the files it changed and its diff, plus files changed by more than one part. "
                       "If it's still running, call again.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {
            "id": {"type": "string"},
            "wait_seconds": {"type": "integer", "minimum": 0, "maximum": STATUS_WAIT_MAX, "default": STATUS_WAIT_DEFAULT},
            "include_diffs": {"type": "boolean", "default": True},
        }},
        "annotations": {"readOnlyHint": True},
    }, tool_team_status),
    "merge_team": ({
        "description": "Apply the finished parts of a team to the project, one after another, on top of what "
                       "is there now (including the user's own work). A part that clashes with changes "
                       "already in the project is skipped and reported, and keeps its copy. Not staged or "
                       "committed.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {
            "id": {"type": "string"},
            "parts": {"type": "array", "items": {"type": "integer"},
                      "description": "Optional: which part numbers to merge, in order. Defaults to all finished parts."},
        }},
        "annotations": {"destructiveHint": True},
    }, tool_merge_team),
    "discard_team": ({
        "description": "Throw away a team's parts that aren't merged yet. Parts already merged stay in the project.",
        "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
    }, tool_discard_team),
}


# ---------------------------------------------------------------------------
# The MCP protocol (JSON-RPC 2.0, one message per line on stdin/stdout)
# ---------------------------------------------------------------------------

class Server:
    def __init__(self, out, cwd: Optional[str] = None):
        self.out = out
        self.cwd = cwd or os.getcwd()
        self.bakeoffs: dict = {}
        self.relays: dict = {}
        self.teams: dict = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mcp-tool")

    def send(self, msg: dict) -> None:
        # An AI's reply can hold half an emoji (a lone surrogate), which UTF-8 can't encode.
        line = json.dumps(msg, ensure_ascii=False).encode("utf-8", "replace").decode("utf-8")
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

    def _answer(self, mid, name: str, args: dict) -> None:
        """Run a tool and send its result. Whatever goes wrong, the client gets an answer:
        an error the thread pool swallowed would leave it waiting forever."""
        try:
            self._reply(mid, self.call_tool(name, args))
        except Exception as exc:
            logger.exception("MCP: couldn't answer %s", name)
            self._reply(mid, {"content": [{"type": "text", "text": f"{name} failed: {exc}"}], "isError": True})

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
            self._pool.submit(self._answer, mid, name, args)
        elif mid is not None:
            self._reply(mid, error={"code": -32601, "message": f"Method not found: {method}"})
        # other notifications (initialized, cancelled…) need no answer

    def serve(self, inp) -> None:
        try:
            self._serve(inp)
        finally:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self.close_relays()

    def _serve(self, inp) -> None:
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

    def close_relays(self) -> None:
        """The client went away: nobody can merge these any more, so stop them and remove their copies."""
        from helm import relay
        for r in self.relays.values():
            if r.status not in ("merged", "discarded"):
                try:
                    relay.stop(r)
                    if r.workspace is not None:
                        r.workspace.close()   # now: a running relay's thread won't outlive the process
                except Exception:
                    logger.debug("Couldn't clean up relay %s", r.id, exc_info=True)
        for t in self.teams.values():
            try:
                _close_team(t)
            except Exception:
                logger.debug("Couldn't clean up team %s", t.id, exc_info=True)


def default_data_dir() -> Path:
    """Where the RAPR app keeps its data (scripts/install-*.{sh,ps1}), so a standalone MCP
    server shares bake-off history, your brief and keys with an app installed later."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RAPR AI"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "RAPR AI"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "RAPR AI"


def standalone() -> None:
    """`rapr-mcp`: the MCP server installed on its own (pyproject.toml), without the app."""
    os.environ.setdefault("RAPR_DATA_DIR", str(default_data_dir()))
    main()


def main() -> None:
    # stdout carries the protocol; anything else printed (logs, warnings) goes to stderr.
    proto = open(sys.stdout.fileno(), "w", encoding="utf-8", newline="\n", buffering=1, closefd=False)
    sys.stdout = sys.stderr
    inp = open(sys.stdin.fileno(), "r", encoding="utf-8", closefd=False)
    import logging
    import signal
    logging.getLogger("helm").setLevel(logging.WARNING)
    # A client that stops the server (rather than closing stdin) still gets the relays' copies removed.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    Server(proto).serve(inp)
