"""
helm/cloud_tasks.py — Hand a task to Claude's or Codex's own cloud from a chat app.

Most AIs in RAPR run as a process on this computer (or your RAPR server). Two of
them can also run a task on their company's servers, against your GitHub repo,
with nothing running here once the task has started:

  Claude  `claude --cloud "<task>"`              a Claude Code cloud session
                                                 (the repo of CLOUD_CLAUDE_FOLDER,
                                                 or of the focused session's folder)
  Codex   `codex cloud exec --env <id> "<task>"` a Codex cloud task
                                                 (CODEX_CLOUD_ENV, from `codex cloud`)

Chat commands (WhatsApp, Discord, Slack):
  /cloud claude <task>     start a Claude cloud session
  /cloud codex <task>      start a Codex cloud task
  /cloud list              the tasks you started from here
  /cloud status <n>        where task n is (Codex); its link (Claude)
  /cloud diff <n>          the changes Codex made
  /cloud reply <n> <text>  send a follow-up to Claude cloud session n

Cloud tasks run on your Claude or ChatGPT plan, with that company's own
connectors and permission rules. RAPR's "asks before acting" does not reach
inside them, so every reply that starts one says so. RAPR keeps a list of the
tasks it started (cloud_tasks.json in its data folder) and, for Codex, tells you
in the same chat when one finishes.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import time
from typing import Optional

logger = logging.getLogger(__name__)

AIS = ("claude", "codex")
NAMES = {"claude": "Claude", "codex": "Codex"}
EMOJI = {"claude": "🟠", "codex": "🟢"}
MAX_PROMPT = 6000            # long prompts get cut: Windows limits the command line
START_TIMEOUT = 180.0        # packaging and uploading a repo can take a while
QUERY_TIMEOUT = 60.0
MAX_REPLY = 3500             # what one chat reply carries of a diff or status
WATCH_EVERY = 60.0           # seconds between Codex status checks
WATCH_FOR = 6 * 3600.0       # stop watching a task after this long

USAGE = (
    "☁️ Cloud tasks: Claude or Codex works on your GitHub repo in its own cloud.\n"
    "/cloud claude <task> — start a Claude Code cloud session\n"
    "/cloud codex <task> — start a Codex cloud task\n"
    "/cloud list — tasks you started\n"
    "/cloud status <n> — how task n is doing\n"
    "/cloud diff <n> — Codex's changes for task n\n"
    "/cloud reply <n> <text> — follow up in Claude cloud session n\n"
    "/cloud setup — what's ready and what's missing"
)

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_URL = re.compile(r"https://\S+")
_CLAUDE_ID = re.compile(r"\b((?:session|cse)_[A-Za-z0-9]+)\b")
_CODEX_ID = re.compile(r"\b(task_[A-Za-z0-9_]+)\b")

# Words in `codex cloud status` output that mean the task stopped working.
_DONE_WORDS = ("ready", "completed", "complete", "succeeded", "success", "merged", "applied")
_FAILED_WORDS = ("failed", "error", "cancelled", "canceled")
_RUNNING_WORDS = ("pending", "running", "in progress", "in_progress", "queued", "working")

_watchers: dict[str, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Settings and commands
# ---------------------------------------------------------------------------

def _exe(name: str) -> Optional[str]:
    """Full path of a command-line tool (claude.exe / codex.cmd on Windows), or None."""
    return shutil.which(name)


def codex_env() -> str:
    return os.environ.get("CODEX_CLOUD_ENV", "").strip()


def codex_branch() -> str:
    return os.environ.get("CODEX_CLOUD_BRANCH", "").strip()


def claude_folder() -> str:
    """The folder whose GitHub repo Claude's cloud session works on."""
    folder = os.environ.get("CLOUD_CLAUDE_FOLDER", "").strip()
    if folder:
        return os.path.expanduser(folder)
    try:
        from helm.session_mgr import session_cwd
        return session_cwd() or os.getcwd()
    except Exception:
        return os.getcwd()


def _clip(prompt: str) -> str:
    prompt = (prompt or "").strip()
    return prompt if len(prompt) <= MAX_PROMPT else prompt[:MAX_PROMPT] + " …(cut)"


def claude_start_cmd(prompt: str) -> list[str]:
    return [_exe("claude") or "claude", "--cloud", _clip(prompt)]


def claude_reply_cmd(session_id: str, text: str) -> list[str]:
    return [_exe("claude") or "claude", "-p", "--cloud", session_id, _clip(text)]


def codex_start_cmd(prompt: str, env: str, branch: str = "") -> list[str]:
    cmd = [_exe("codex") or "codex", "cloud", "exec", "--env", env]
    if branch:
        cmd += ["--branch", branch]
    return cmd + [_clip(prompt)]


def codex_cmd(sub: str, task_id: str) -> list[str]:
    return [_exe("codex") or "codex", "cloud", sub, task_id]


# ---------------------------------------------------------------------------
# Reading what the tools print
# ---------------------------------------------------------------------------

def clean(text: str) -> str:
    return _ANSI.sub("", text or "").replace("\r", "").strip()


def parse_started(ai: str, output: str) -> dict:
    """The task's id and link from what `claude --cloud` / `codex cloud exec` printed."""
    out = clean(output)
    urls = [u.rstrip(").,'\"") for u in _URL.findall(out)]
    found = {"id": "", "url": "", "title": ""}
    if ai == "claude":
        m = _CLAUDE_ID.search(out)
        found["url"] = next((u for u in urls if "claude.ai/code" in u), urls[0] if urls else "")
        if m:
            found["id"] = m.group(1)
        elif found["url"]:          # https://claude.ai/code/session_… carries the id
            tail = found["url"].rstrip("/").rsplit("/", 1)[-1]
            found["id"] = tail if _CLAUDE_ID.fullmatch(tail) else ""
        t = re.search(r"Created cloud session:\s*(.+)", out)
        found["title"] = t.group(1).strip() if t else ""
    else:
        m = _CODEX_ID.search(out)
        found["id"] = m.group(1) if m else ""
        found["url"] = next((u for u in urls if "codex" in u), urls[0] if urls else "")
    return found


def status_word(output: str) -> str:
    """'done', 'failed' or 'running' from `codex cloud status` output ('' if unclear)."""
    low = clean(output).lower()
    # Look at the status line first when there is one ("Status: ready").
    m = re.search(r"status\s*[:=]\s*([a-z_ ]+)", low)
    scope = m.group(1) if m else low
    for words, word in ((_FAILED_WORDS, "failed"), (_RUNNING_WORDS, "running"), (_DONE_WORDS, "done")):
        if any(re.search(rf"\b{re.escape(w)}\b", scope) for w in words):
            return word
    return ""


# ---------------------------------------------------------------------------
# Running the tools
# ---------------------------------------------------------------------------

async def run(cmd: list[str], cwd: Optional[str] = None, timeout: float = QUERY_TIMEOUT) -> tuple[int, str]:
    """Run a command with no terminal and no input. Returns (exit code, output)."""
    from helm.subprocess_utils import hidden_kwargs
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd or None,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            **hidden_kwargs())
    except FileNotFoundError:
        return 127, f"{os.path.basename(cmd[0])} isn't installed (or isn't on PATH)."
    except Exception as exc:
        return 1, str(exc)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return 124, f"No answer after {int(timeout)} seconds."
    return proc.returncode or 0, clean(out.decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# The list of tasks RAPR started
# ---------------------------------------------------------------------------

def _path():
    from helm.paths import user_data_dir
    return user_data_dir() / "cloud_tasks.json"


def tasks() -> list[dict]:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    path = _path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(items[-200:], ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _add(task: dict) -> dict:
    items = tasks()
    task["n"] = (max((t.get("n", 0) for t in items), default=0) + 1)
    items.append(task)
    _save(items)
    return task


def _update(n: int, **fields) -> None:
    items = tasks()
    for t in items:
        if t.get("n") == n:
            t.update(fields)
    _save(items)


def find(ref: str) -> Optional[dict]:
    ref = (ref or "").strip().lstrip("#")
    for t in reversed(tasks()):
        if str(t.get("n")) == ref or (ref and t.get("id") == ref):
            return t
    return None


# ---------------------------------------------------------------------------
# What's ready
# ---------------------------------------------------------------------------

def setup_problems(ai: str) -> list[str]:
    """What stops a cloud task from starting, in plain words (empty when ready)."""
    problems = []
    if ai == "claude":
        if not _exe("claude"):
            problems.append("Claude Code isn't installed here (npm install -g @anthropic-ai/claude-code).")
        folder = claude_folder()
        if not os.path.isdir(os.path.join(folder, ".git")):
            problems.append(f"{folder} isn't a git repository. Set CLOUD_CLAUDE_FOLDER to a "
                            "folder cloned from GitHub, or /use a session in one.")
    elif ai == "codex":
        if not _exe("codex"):
            problems.append("Codex isn't installed here (npm install -g @openai/codex).")
        if not codex_env():
            problems.append("CODEX_CLOUD_ENV isn't set. Make a Codex cloud environment for your "
                            "repo at chatgpt.com/codex, run `codex cloud` to see its id, then set "
                            "CODEX_CLOUD_ENV in RAPR's settings (.env).")
    return problems


def setup_text() -> str:
    lines = ["☁️ Cloud tasks setup"]
    for ai in AIS:
        problems = setup_problems(ai)
        where = (f"repo in {claude_folder()}" if ai == "claude"
                 else f"environment {codex_env() or '(not set)'}"
                 + (f", branch {codex_branch()}" if codex_branch() else ""))
        lines.append(f"\n{EMOJI[ai]} {NAMES[ai]}: {'ready' if not problems else 'not ready'} ({where})")
        lines += [f"  • {p}" for p in problems]
    lines.append("\nBoth need a one-time sign-in on this machine: `claude` (then /login) and `codex login`.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Starting, checking and following up
# ---------------------------------------------------------------------------

_NOT_GATED = ("It runs on your {plan} plan with {who}'s own connectors and rules: "
              "RAPR can't ask you before it acts in there.")


async def start(ai: str, prompt: str, channel: str = "chat") -> str:
    ai = ai.lower()
    if ai not in AIS:
        return f"Cloud tasks are for Claude and Codex only. {USAGE}"
    prompt = (prompt or "").strip()
    if not prompt:
        return f"What should {NAMES[ai]} do? /cloud {ai} <task>"
    problems = setup_problems(ai)
    if problems:
        return f"Can't start a {NAMES[ai]} cloud task yet:\n" + "\n".join(f"• {p}" for p in problems)

    if ai == "claude":
        folder = claude_folder()
        code, out = await run(claude_start_cmd(prompt), cwd=folder, timeout=START_TIMEOUT)
        where = os.path.basename(folder.rstrip("/\\")) or folder
    else:
        folder = None
        code, out = await run(codex_start_cmd(prompt, codex_env(), codex_branch()), timeout=START_TIMEOUT)
        where = f"environment {codex_env()}"
    found = parse_started(ai, out)
    if code != 0 or not (found["id"] or found["url"]):
        _audit("cloud_task_failed", ai=ai, channel=channel, code=code)
        return f"❌ {NAMES[ai]} didn't start a cloud task (exit {code}):\n{out[-1500:] or '(no output)'}"

    task = _add({"ai": ai, "id": found["id"], "url": found["url"], "title": found["title"],
                 "prompt": prompt[:500], "folder": folder, "channel": channel,
                 "created": time.time(), "state": "running"})
    _audit("cloud_task_started", ai=ai, channel=channel, task=task["id"] or task["url"])
    if ai == "codex" and task["id"]:
        watch(task)
    lines = [f"☁️ {EMOJI[ai]} {NAMES[ai]} cloud task #{task['n']} started on {where}."]
    if task["url"]:
        lines.append(task["url"])
    if ai == "codex":
        lines.append(f"I'll tell you here when it finishes. /cloud diff {task['n']} shows the changes.")
    else:
        lines.append(f"Follow up with /cloud reply {task['n']} <text>, or open the link.")
    lines.append(_NOT_GATED.format(plan="Claude" if ai == "claude" else "ChatGPT",
                                   who="Anthropic" if ai == "claude" else "OpenAI"))
    return "\n".join(lines)


async def status(ref: str) -> str:
    task = find(ref)
    if not task:
        return f"No cloud task {ref}. See /cloud list."
    head = f"{EMOJI[task['ai']]} #{task['n']} {NAMES[task['ai']]}: {task.get('prompt', '')[:80]}"
    if task["ai"] == "claude":
        return f"{head}\nOpen it to see how it's going: {task.get('url') or task.get('id')}"
    code, out = await run(codex_cmd("status", task["id"]))
    word = status_word(out) if code == 0 else ""
    if word and word != task.get("state"):
        _update(task["n"], state=word)
    return f"{head}\n{out[:MAX_REPLY] or '(no output)'}"


async def diff(ref: str) -> str:
    task = find(ref)
    if not task:
        return f"No cloud task {ref}. See /cloud list."
    if task["ai"] != "codex":
        return f"Claude's changes are on its branch; open the session: {task.get('url') or task.get('id')}"
    code, out = await run(codex_cmd("diff", task["id"]))
    if code != 0:
        return f"Couldn't get the diff for #{task['n']}:\n{out[:1500]}"
    if len(out) > MAX_REPLY:
        out = out[:MAX_REPLY] + f"\n…(cut; {len(out)} characters in all. See {task.get('url') or 'the task'})"
    return out or "No changes yet."


async def reply(ref: str, text: str) -> str:
    task = find(ref)
    if not task:
        return f"No cloud task {ref}. See /cloud list."
    if task["ai"] != "claude":
        return "Codex cloud tasks don't take follow-ups from here; start another with /cloud codex <task>."
    if not text.strip():
        return f"What should Claude do next? /cloud reply {task['n']} <text>"
    code, out = await run(claude_reply_cmd(task.get("id") or task.get("url"), text),
                          cwd=task.get("folder"), timeout=START_TIMEOUT)
    if code != 0:
        return f"❌ Couldn't reach Claude cloud session #{task['n']}:\n{out[-1500:]}"
    return f"➡️ Sent to Claude cloud session #{task['n']}. {task.get('url', '')}".rstrip()


def list_text() -> str:
    items = tasks()[-10:]
    if not items:
        return "No cloud tasks yet. Start one with /cloud claude <task> or /cloud codex <task>."
    icon = {"running": "⏳", "done": "✅", "failed": "❌"}
    lines = ["☁️ Cloud tasks:"]
    for t in reversed(items):
        state = icon.get(t.get("state", ""), "•") if t["ai"] == "codex" else "🔗"
        lines.append(f"{state} #{t['n']} {EMOJI[t['ai']]} {NAMES[t['ai']]}: {t.get('prompt', '')[:70]}")
    return "\n".join(lines)


async def handle(channel: str, args: str) -> str:
    """Reply to `/cloud <args>`."""
    parts = (args or "").strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    if sub in ("", "help"):
        return USAGE
    if sub in AIS:
        return await start(sub, rest, channel)
    if sub in ("list", "ls"):
        return list_text()
    if sub == "setup":
        return setup_text()
    if sub == "status":
        return await status(rest)
    if sub == "diff":
        return await diff(rest)
    if sub == "reply":
        ref, _, text = rest.partition(" ")
        return await reply(ref, text)
    return f"Cloud tasks are for Claude and Codex only.\n\n{USAGE}"


# ---------------------------------------------------------------------------
# Telling you when a Codex task finishes
# ---------------------------------------------------------------------------

async def _send(channel: str, text: str) -> None:
    try:
        if channel == "whatsapp":
            import helm.whatsapp_bridge as wa
            await wa.send_text(text)
            return
        import helm.groupchat as gc
        send = gc._channel_senders.get(channel)
        if send:
            await send({}, text)
            return
        from helm.audit import send_to_chat_apps
        await send_to_chat_apps(text)
    except Exception as exc:
        logger.warning("cloud task note to %s failed: %s", channel, exc)


async def _watch(task: dict) -> None:
    started = time.time()
    try:
        while time.time() - started < WATCH_FOR:
            await asyncio.sleep(WATCH_EVERY)
            code, out = await run(codex_cmd("status", task["id"]))
            word = status_word(out) if code == 0 else ""
            if word in ("done", "failed"):
                _update(task["n"], state=word)
                mark = "✅ finished" if word == "done" else "❌ stopped"
                await _send(task.get("channel", "chat"),
                            f"☁️ Codex cloud task #{task['n']} {mark}: {task.get('prompt', '')[:80]}\n"
                            + (f"{task['url']}\n" if task.get("url") else "")
                            + (f"/cloud diff {task['n']} shows the changes." if word == "done" else out[:800]))
                return
    finally:
        _watchers.pop(task["id"], None)


def watch(task: dict) -> None:
    if task["id"] in _watchers:
        return
    try:
        _watchers[task["id"]] = asyncio.get_running_loop().create_task(_watch(task))
    except RuntimeError:
        pass          # no event loop (a script): nothing to watch with


def resume_watching() -> None:
    """After RAPR restarts, carry on watching Codex tasks that were still running."""
    for t in tasks():
        if t.get("ai") == "codex" and t.get("state") == "running" and t.get("id") \
                and time.time() - t.get("created", 0) < WATCH_FOR:
            watch(t)


def _audit(event: str, **fields) -> None:
    try:
        from helm import audit
        audit.record(event, **fields)
    except Exception as exc:
        logger.debug("cloud task audit skipped: %s", exc)
