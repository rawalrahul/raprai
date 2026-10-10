"""
helm/bakeoff.py — Same task, several AIs, pick the best result.

Each contestant works in its own copy of your project (a git worktree when the
folder is a git repo, otherwise a plain copy), so they can't step on each other.
When they're done you see each attempt side by side: files changed, the diff,
whether your test command passed, how long it took, and what the AI said. You
then merge the one you like into your project, or discard them all.

The AI itself is supplied by the caller (`runner`), so this module can be
tested with fake AIs and used with the real ones.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Optional

# runner(ai, prompt, cwd) -> the AI's final text
Runner = Callable[[str, str, str], Awaitable[str]]


@dataclass
class Attempt:
    ai: str
    path: str
    branch: Optional[str] = None
    seconds: float = 0.0
    output: str = ""
    diff: str = ""
    files_changed: int = 0
    tests_passed: Optional[bool] = None
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {"ai": self.ai, "files_changed": self.files_changed, "seconds": round(self.seconds, 1),
                "tests_passed": self.tests_passed, "error": self.error,
                "output": self.output[:4000], "diff": self.diff[:20000]}


@dataclass
class BakeOff:
    id: str
    repo: str
    task: str
    attempts: list[Attempt] = field(default_factory=list)
    is_git: bool = False
    test_command: Optional[str] = None
    status: str = "created"   # created | running | done | merged | discarded

    def as_dict(self) -> dict:
        return {"id": self.id, "repo": self.repo, "task": self.task, "status": self.status,
                "is_git": self.is_git, "test_command": self.test_command,
                "attempts": [a.as_dict() for a in self.attempts]}


def _git(cwd: str, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()[:300]}")
    return out.stdout


def is_git_repo(path: str) -> bool:
    try:
        return _git(path, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except Exception:
        return False


def create(repo: str, task: str, ais: list[str], test_command: Optional[str] = None,
           root: Optional[str] = None) -> BakeOff:
    """Make one copy of the project per AI. `root` is where copies go (default: a temp folder)."""
    src = Path(repo).resolve()
    if not src.is_dir():
        raise ValueError(f"{repo} is not a folder")
    if not 2 <= len(ais) <= 4:
        raise ValueError("pick 2 to 4 AIs")
    bid = uuid.uuid4().hex[:8]
    base = Path(root or (Path.home() / ".rapr-bakeoff")) / bid
    base.mkdir(parents=True, exist_ok=True)
    git = is_git_repo(str(src))
    bo = BakeOff(id=bid, repo=str(src), task=task, is_git=git, test_command=test_command)
    for i, ai in enumerate(ais, 1):
        dest = base / f"{i}-{ai}"
        if git:
            branch = f"bakeoff/{bid}-{i}-{ai}"
            _git(str(src), "worktree", "add", "-q", "-b", branch, str(dest), "HEAD")
            bo.attempts.append(Attempt(ai=ai, path=str(dest), branch=branch))
        else:
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
            bo.attempts.append(Attempt(ai=ai, path=str(dest)))
    return bo


def _snapshot(path: str, git: bool) -> dict[str, bytes]:
    """File contents for a plain copy (used when not a git repo)."""
    out = {}
    for p in Path(path).rglob("*"):
        if p.is_file():
            out[str(p.relative_to(path))] = p.read_bytes()
    return out


async def run(bo: BakeOff, runner: Runner, prompt_prefix: str = "") -> BakeOff:
    """Run every contestant in parallel, then collect each attempt's changes and test result."""
    bo.status = "running"
    before = {} if bo.is_git else {a.ai: _snapshot(a.path, False) for a in bo.attempts}

    async def one(a: Attempt):
        t0 = time.time()
        prompt = (prompt_prefix + "\n\n" if prompt_prefix else "") + bo.task
        try:
            a.output = (await runner(a.ai, prompt, a.path)) or ""
        except Exception as exc:
            a.error = str(exc)
        a.seconds = time.time() - t0
        _collect(bo, a, before)

    await asyncio.gather(*(one(a) for a in bo.attempts))
    bo.status = "done"
    return bo


def _collect(bo: BakeOff, a: Attempt, before: dict) -> None:
    if bo.is_git:
        _git(a.path, "add", "-A")
        a.diff = _git(a.path, "diff", "--cached", "HEAD")
        names = _git(a.path, "diff", "--cached", "--name-only", "HEAD").split()
        a.files_changed = len(names)
    else:
        now = _snapshot(a.path, False)
        old = before.get(a.ai, {})
        changed = [k for k in set(now) | set(old) if now.get(k) != old.get(k)]
        a.files_changed = len(changed)
        a.diff = "\n".join(f"changed: {k}" for k in sorted(changed))
    if bo.test_command and not a.error:
        r = subprocess.run(bo.test_command, shell=True, cwd=a.path, capture_output=True, text=True, timeout=900)
        a.tests_passed = r.returncode == 0


def merge(bo: BakeOff, index: int) -> int:
    """Apply attempt `index`'s changes to the project and clean up all copies. Returns files changed."""
    if bo.status != "done":
        raise ValueError("wait for the attempts to finish before merging")
    a = bo.attempts[index]
    if bo.is_git:
        patch = a.diff
        if patch.strip():
            r = subprocess.run(["git", "apply", "--index", "-"], cwd=bo.repo, input=patch,
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise RuntimeError(f"could not apply {a.ai}'s changes: {r.stderr.strip()[:300]}")
    else:
        for line in a.diff.splitlines():
            rel = line.removeprefix("changed: ")
            src, dst = Path(a.path) / rel, Path(bo.repo) / rel
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    cleanup(bo)
    bo.status = "merged"
    return a.files_changed


def cleanup(bo: BakeOff) -> None:
    """Remove the copies (and their branches in a git repo)."""
    for a in bo.attempts:
        if bo.is_git:
            try:
                _git(bo.repo, "worktree", "remove", "--force", a.path)
            except Exception:
                pass
            if a.branch:
                try:
                    _git(bo.repo, "branch", "-D", a.branch)
                except Exception:
                    pass
        shutil.rmtree(a.path, ignore_errors=True)
    shutil.rmtree(Path(bo.attempts[0].path).parent, ignore_errors=True) if bo.attempts else None


def discard(bo: BakeOff) -> None:
    cleanup(bo)
    bo.status = "discarded"
