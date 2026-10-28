"""
helm/relay.py — Plan with one AI, build with another, review with a third, fix, review again.

A relay hands one task down a line of AIs, each in the role you picked:

    planner   reads the project and writes a plan (optional: you can pass your own plan)
    executor  carries out the plan
    reviewer  reviews the change and gives a verdict
    fixer     fixes what the reviewer found (the executor, unless you pick another AI)

then the reviewer looks again, up to `fix_rounds` times. Everything happens in one
throwaway copy of the project (the caller's `workspace`), so your files only change
when you merge the result. Planners and reviewers are told not to edit; anything
they change anyway is undone before the next step.

The AIs and the copy are supplied by the caller, so this module can be tested with
fake AIs (see tests/test_relay.py) and is used with real ones by helm/mcp_server.py.
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

# runner(agent, prompt, cwd, edits, timeout, on_start) -> the AI's reply.
# edits: whether the AI may change files; on_start(proc) lets a relay stop it.
Runner = Callable[..., str]

PLAN_TIMEOUT = 900       # seconds an AI gets to plan or review
BUILD_TIMEOUT = 1800     # seconds an AI gets to carry out the plan or fix
TEST_TIMEOUT = 900
DIFF_LIMIT = 60_000      # characters of the change shown to a reviewer
TEXT_LIMIT = 20_000      # characters of a plan or review handed to the next AI

PLAN_PROMPT = """You are the planner. Another AI ({executor}) will carry out your plan in this project, so it must be specific enough to follow without asking you anything.

Read the code you need. Do not modify any files.

Reply with the plan: which files to change and what to change in each, edge cases to handle, and how to check the result (tests to add or run). Keep it as short as the task allows.

The task:

{task}
"""

BUILD_PROMPT = """Carry out this task in this project. Make the changes directly in the files. Run the project's tests if there's a quick way to. Do not commit.

When you're done, summarise what you changed and anything you didn't do.

The task:

{task}
{plan}"""

REVIEW_PROMPT = """You are the reviewer. Another AI ({executor}) changed this project to do the task below; the changes are already in the files here, so read the surrounding code where you need context. Do not modify any files.

Look for real problems: bugs, wrong logic, missed edge cases, parts of the task or plan that weren't done, security issues, broken callers, missing tests for risky paths. Skip style nits unless they hide a bug.

Reply with your findings, most serious first. For each: the file and line, what goes wrong and when, and the fix.

End your reply with exactly one of these lines:
VERDICT: APPROVED
VERDICT: CHANGES NEEDED

The task:

{task}
{plan}{tests}
The changes:

{diff}
"""

FIX_PROMPT = """A reviewer ({reviewer}) checked the changes in this project for the task below and found problems. Fix the ones that are real, directly in the files. If you disagree with a finding, leave the code as it is and say why. Do not commit.

When you're done, summarise what you fixed and what you left as it is.

The task:

{task}

The review:

{review}
"""

_VERDICT = re.compile(r"VERDICT:\s*\**\s*(APPROVED|CHANGES NEEDED)", re.IGNORECASE)


def verdict(review: str) -> Optional[bool]:
    """True if the reviewer approved, False if it asked for changes, None if it gave no verdict."""
    found = _VERDICT.findall(review or "")
    return None if not found else found[-1].upper() == "APPROVED"


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… ({len(text) - limit:,} more characters cut)"


@dataclass
class Step:
    role: str           # plan | build | review | fix
    agent: str
    seconds: float = 0.0
    output: str = ""
    error: Optional[str] = None


@dataclass
class Relay:
    id: str
    folder: str
    task: str
    executor: str
    reviewer: str
    fixer: str
    planner: Optional[str] = None
    plan: str = ""                      # the planner's plan, or the one passed in
    fix_rounds: int = 1
    test_command: Optional[str] = None
    status: str = "running"             # running | done | failed | merged | discarded
    stage: str = "starting"
    steps: list[Step] = field(default_factory=list)
    approved: Optional[bool] = None     # the last review's verdict
    tests_passed: Optional[bool] = None
    test_output: str = ""
    diff: str = ""                      # the change so far, for people and reviewers
    files: list[str] = field(default_factory=list)
    error: Optional[str] = None
    workspace: object = field(default=None, repr=False)
    proc: object = field(default=None, repr=False)     # the AI running now, so discard can stop it
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def busy(self) -> bool:
        return self.status == "running"


def create(folder: str, task: str, executor: str, reviewer: str, *, planner: Optional[str] = None,
           plan: str = "", fixer: Optional[str] = None, fix_rounds: int = 1,
           test_command: Optional[str] = None) -> Relay:
    if not task.strip():
        raise ValueError("task is empty")
    if not 0 <= fix_rounds <= 3:
        raise ValueError("fix_rounds must be 0 to 3")
    return Relay(id=uuid.uuid4().hex[:8], folder=folder, task=task.strip(), planner=planner,
                 plan=(plan or "").strip(), executor=executor, reviewer=reviewer,
                 fixer=fixer or executor, fix_rounds=fix_rounds, test_command=test_command or None)


class Stopped(Exception):
    """The relay was discarded while it ran."""


def run(r: Relay, runner: Runner, workspace) -> Relay:
    """Run the relay to the end in `workspace`: a copy of the project with .cwd, .snapshot(),
    .restore(point) and .diff() -> (text, files). Blocking; call it from a thread."""
    r.workspace = workspace
    try:
        _run(r, runner, workspace)
        with r.lock:
            if r.status == "running":
                r.status, r.stage = "done", "finished"
    except Stopped:
        pass
    except Exception as exc:   # report it instead of leaving the relay "running" forever
        with r.lock:
            if r.status == "running":
                r.status, r.stage, r.error = "failed", "stopped by an error", str(exc)
    return r


def _ask(r: Relay, runner: Runner, role: str, agent: str, prompt: str) -> Step:
    """Run one AI for one step. Planners and reviewers can't leave changes behind."""
    with r.lock:
        if r.status != "running":
            raise Stopped
    edits = role in ("build", "fix")
    ws = r.workspace
    point = None if edits else ws.snapshot()
    step = Step(role=role, agent=agent)
    r.steps.append(step)

    def started(proc):
        r.proc = proc

    t0 = time.time()
    try:
        step.output = runner(agent, prompt, ws.cwd, edits=edits,
                             timeout=BUILD_TIMEOUT if edits else PLAN_TIMEOUT, on_start=started) or ""
    except Exception as exc:
        step.error = str(exc)
    finally:
        r.proc = None
        step.seconds = time.time() - t0
    with r.lock:
        if r.status != "running":
            raise Stopped
    if point is not None:
        ws.restore(point)
    return step


def _test(r: Relay) -> None:
    if not r.test_command:
        return
    r.stage = "running the tests"
    point = r.workspace.snapshot()
    try:
        out = subprocess.run(r.test_command, shell=True, cwd=r.workspace.cwd, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=TEST_TIMEOUT)
        r.tests_passed = out.returncode == 0
        r.test_output = _clip((out.stdout + out.stderr).strip()[-4000:], 4000)
    except subprocess.TimeoutExpired:
        r.tests_passed, r.test_output = False, f"(the tests took longer than {TEST_TIMEOUT}s)"
    finally:
        # Leave out what the run made (__pycache__, coverage files…): the merge should be
        # exactly the change that was reviewed.
        r.workspace.restore(point)


def _run(r: Relay, runner: Runner, ws) -> None:
    if r.planner and not r.plan:
        r.stage = f"{r.planner} is planning"
        step = _ask(r, runner, "plan", r.planner,
                    PLAN_PROMPT.format(executor=r.executor, task=r.task))
        if step.error or not step.output.strip():
            raise RuntimeError(f"{r.planner} didn't produce a plan: {step.error or 'empty reply'}")
        r.plan = step.output.strip()
    plan = f"\nThe plan to follow:\n\n{_clip(r.plan, TEXT_LIMIT)}\n" if r.plan else ""

    r.stage = f"{r.executor} is carrying out the {'plan' if r.plan else 'task'}"
    step = _ask(r, runner, "build", r.executor, BUILD_PROMPT.format(task=r.task, plan=plan))
    r.diff, r.files = ws.diff()
    if not r.files:
        detail = step.error or _clip(step.output.strip(), 500) or "no reply"
        raise RuntimeError(f"{r.executor} didn't change any files ({detail})")
    _test(r)

    for rnd in range(r.fix_rounds + 1):
        r.stage = f"{r.reviewer} is reviewing" + (f" (round {rnd + 1})" if rnd else "")
        tests = ""
        if r.tests_passed is not None:
            tests = (f"\n`{r.test_command}` {'passed' if r.tests_passed else 'FAILED'}:\n\n"
                     f"{r.test_output}\n")
        step = _ask(r, runner, "review", r.reviewer, REVIEW_PROMPT.format(
            executor=r.executor if rnd == 0 else f"{r.executor}, then {r.fixer}",
            task=r.task, plan=plan, tests=tests, diff=_clip(r.diff, DIFF_LIMIT)))
        if step.error:
            raise RuntimeError(f"{r.reviewer} couldn't review: {step.error}")
        r.approved = verdict(step.output)
        if r.approved is not False or rnd == r.fix_rounds:
            return
        r.stage = f"{r.fixer} is fixing what {r.reviewer} found" + (f" (round {rnd + 1})" if rnd else "")
        _ask(r, runner, "fix", r.fixer,
             FIX_PROMPT.format(reviewer=r.reviewer, task=r.task, review=_clip(step.output, TEXT_LIMIT)))
        r.diff, r.files = ws.diff()
        _test(r)


def stop(r: Relay) -> str:
    """Discard a relay and stop the AI that's working, if any. Returns the status it had: if
    that was "running", the relay's own thread removes the copy as it stops; otherwise the
    caller does."""
    with r.lock:
        was = r.status
        r.status, r.stage = "discarded", "discarded"
    proc = r.proc
    if proc is not None:
        try:
            proc.kill()
        except OSError:   # it may have just finished
            pass
    return was
