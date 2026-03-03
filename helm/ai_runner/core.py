"""
helm/ai_runner/core.py — Core subprocess runner and message processor.

Covers: run_ai_popen, kill_session_proc, and process_message (the main dispatcher).
"""

import asyncio
import os
import re
import subprocess
import sys
import time
from typing import Optional

import helm.state as _st
from helm.broadcast import push_message, push_state, push_thinking
from helm.config import CLAUDE_TIMEOUT, INTEGRATION_TIMEOUT, logger
from helm.history import save_cwd_to_log
from helm.session_mgr import focused_session, record_usage_task
from helm.skills import inject_skill_prefix, detect_skill, auto_create_skill_template

from .claude import build_claude_cmd
from .helpers import tg_progress_notify


_ANSI_ESC_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


# ---------------------------------------------------------------------------
# Pre-install document-generation packages (runs once at import time)
# ---------------------------------------------------------------------------
def _ensure_doc_packages():
    """Silently install Python packages needed by document-generation skills."""
    _pkgs = ["python-pptx", "python-docx", "openpyxl", "reportlab", "pypdf"]
    for pkg in _pkgs:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=60,
            )
        except Exception:
            logger.warning("Could not pre-install %s — skills may install it on demand", pkg)

try:
    _ensure_doc_packages()
except Exception:
    pass


def run_ai_popen(cmd: list[str], cwd: str, name: str, sess: dict,
                 timeout_override: float | None = None,
                 stdin_text: str | None = None) -> str:
    """Run an AI CLI subprocess, storing the Popen handle in sess['proc'] so it
    can be killed externally by stop_session / interrupt handlers.

    timeout_override: explicit seconds; None → use CLAUDE_TIMEOUT (0 = unlimited).
    stdin_text: if provided, the prompt is piped via stdin instead of appearing
    on the command line — this avoids Windows cmd.exe 8 KB arg-length limits.
    Integration AIs (Gemini, Codex, …) pass INTEGRATION_TIMEOUT to prevent an
    infinite hang when an invalid --model causes the CLI to enter an interactive
    picker with no terminal attached.
    """
    if timeout_override is not None:
        _timeout: float | None = timeout_override if timeout_override > 0 else None
    else:
        _timeout = CLAUDE_TIMEOUT if CLAUDE_TIMEOUT > 0 else None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if stdin_text else None,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
        )
        sess["proc"] = proc  # store so stop/interrupt can kill it
        try:
            stdout, stderr = proc.communicate(input=stdin_text, timeout=_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            sess["proc"] = None
            t = int(_timeout) if _timeout else 0
            return (f"**{name}** timed out after {t}s.\n"
                    f"The model may be invalid or the CLI is waiting for interactive "
                    f"input. Reset with `/model default` or pick a known model.")
        finally:
            sess["proc"] = None  # clear after natural completion

        stdout = _ANSI_ESC_RE.sub('', stdout).strip()
        stderr = _ANSI_ESC_RE.sub('', stderr).strip()

        if proc.returncode != 0:
            parts = [p for p in [stdout, stderr] if p]
            raw = "\n".join(parts) if parts else f"({name} exited {proc.returncode})"
            if ("oauth token has expired" in raw.lower()
                    or ("401" in raw and "expired" in raw.lower())):
                return (
                    "⚠️ **Claude Code authentication has expired.**\n\n"
                    "Open a terminal and run:\n```\nclaude\n```\nThen log in again. "
                    "Once done, your next message here will work normally."
                )
            return raw
        return stdout or "(no output)"

    except FileNotFoundError:
        return f"Error: '{cmd[0]}' not found in PATH."
    except Exception as e:
        return f"(error: {e})"


_run_ai_popen = run_ai_popen  # legacy alias


def kill_session_proc(sess: dict) -> None:
    """Kill the running AI subprocess for a session (if any). Safe to call always."""
    proc = sess.get("proc")
    if proc is not None:
        try:
            proc.kill()
        except Exception:
            pass
        sess["proc"] = None


_kill_session_proc = kill_session_proc  # legacy alias


async def process_message(text: str, source: str = "web",
                          session_id: Optional[str] = None) -> str:
    """
    Route `text` to the given session (or focused session if session_id is None).
    Returns the response string. Broadcasts to all WS clients.
    """
    from helm.file_tracker import snapshot_dir, handle_diff

    sid  = session_id or _st.focused_id
    sess = _st.sessions.get(sid) if sid else None

    if not sess or sess["status"] == "stopped":
        msg = "No active session. Create or resume a session first."
        await push_message("system", msg, source=source)
        return msg

    # ── /model slash command — handled before routing to any AI ──────────────
    stripped = text.strip()
    if stripped.lower().startswith("/model"):
        from helm.web_routes import (
            _fetch_claude_models, _fetch_ollama_models,
            _fetch_gemini_models, _fetch_openai_models,
        )
        parts_cmd = stripped.split(None, 1)
        arg = parts_cmd[1].strip() if len(parts_cmd) == 2 else ""
        arg_lower = arg.lower()

        # ── /model  or  /model list  → show status ──────────────────────────
        if not arg or arg_lower in ("list", "ls", "show", "?"):
            ai_key        = sess.get("ai") or "shell"
            current_model = sess.get("model") or None

            # Fetch available models live for this AI
            try:
                if ai_key == "claude":
                    available = await asyncio.to_thread(_fetch_claude_models)
                elif ai_key == "ollama":
                    available = await asyncio.to_thread(_fetch_ollama_models)
                elif ai_key == "gemini":
                    available = await asyncio.to_thread(_fetch_gemini_models)
                elif ai_key in ("codex", "openai"):
                    available = await asyncio.to_thread(_fetch_openai_models)
                else:
                    available = []
            except Exception:
                available = []

            if current_model:
                current_line = f"**Current model:** `{current_model}`"
            elif available:
                current_line = f"**Current model:** (default — `{available[0]}`)"
            else:
                current_line = f"**Current model:** (AI's built-in default)"

            models_line = ""
            if available:
                models_line = "\n\n**Available models:**\n" + "\n".join(
                    f"  • `{m}`" + (" ✅" if m == current_model else "")
                    for m in available
                )
            else:
                models_line = (
                    "\n\n_Could not fetch model list — AI service may be offline,_"
                    "_or no API key is configured. The AI will use its own built-in default._"
                )

            msg = (
                f"{current_line}\n"
                f"**AI:** {ai_key}\n"
                f"{models_line}\n\n"
                f"To switch: `/model <name>`\n"
                f"To reset to default: `/model default`"
            )
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        # ── /model default  → reset to AI's built-in default ────────────────
        if arg_lower == "default":
            sess["model"] = None
            await push_state()
            msg = "✅ Model reset to default (AI will use its own built-in latest)."
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        # ── /model <name>  → switch to named model ───────────────────────────
        sess["model"] = arg
        await push_state()

        # For Ollama: warn if the requested model isn't installed locally.
        if sess.get("ai") == "ollama":
            try:
                _list_result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True, text=True, timeout=5,
                )
                _local = []
                for _line in _list_result.stdout.strip().splitlines()[1:]:
                    _parts = _line.split()
                    if _parts:
                        _local.append(_parts[0].strip())
                if _local and arg not in _local:
                    _names = ", ".join(f"`{m}`" for m in _local)
                    await push_message(
                        "system",
                        f"⚠️ **`{arg}`** is not installed locally.\n"
                        f"Locally available: {_names}\n"
                        f"Ollama will attempt to pull `{arg}` from the registry "
                        f"on your next message. Use `/model default` to revert.",
                        source=source, session_id=sid,
                    )
            except Exception:
                pass  # if ollama list fails, don't block the switch

        msg = f"✅ Model switched to `{arg}`."
        await push_message("system", msg, source=source, session_id=sid)
        return msg
    # ── end /model ────────────────────────────────────────────────────────────

    task_started_at = time.time()
    sess["last_used"] = task_started_at
    sess["busy"]       = True
    sess["task_start"] = task_started_at
    await push_state()  # immediately reflect busy status on web UI and Telegram

    ai       = sess["ai"]
    cwd      = sess["cwd"]
    terminal = sess["terminal"]

    await push_message("user", text, ai=None, source=source, session_id=sid)

    output = ""  # safe default — overwritten in every branch below
    try:
        if ai == "claude":
            await push_thinking(True, "claude", session_id=sid)
            has_history = len(sess["claude_msgs"]) > 0
            # Skill injection — enrich prompt with best-practice templates
            enriched_text = inject_skill_prefix(text, ai="claude")
            cmd = build_claude_cmd(enriched_text, has_history, model=sess.get("model"))
            sess["claude_msgs"].append(text)  # store original (unenriched) for history
            before = await asyncio.to_thread(snapshot_dir, cwd)
            output = await asyncio.to_thread(run_ai_popen, cmd, cwd, "claude", sess)
            after  = await asyncio.to_thread(snapshot_dir, cwd)
            await push_thinking(False, session_id=sid)
            await push_message("assistant", output, ai="claude", source=source, session_id=sid)
            await handle_diff(before, after, source, cwd, session_id=sid)
            # Auto-create a skill if no existing skill matched
            if not detect_skill(text):
                asyncio.create_task(
                    asyncio.to_thread(auto_create_skill_template, text, "claude", output)
                )

        elif ai == "ollama":
            # Ollama uses the REST API + tool calling agent loop
            from .ollama import _run_ollama_agent  # lazy to avoid circular import
            await push_thinking(True, ai, session_id=sid)
            output = await _run_ollama_agent(sess, text, source, sid)
            await push_thinking(False, session_id=sid)
            await push_message("assistant", output, ai=ai, source=source, session_id=sid)

        elif ai in _st.integrations:
            await push_thinking(True, ai, session_id=sid)
            skill_matched = detect_skill(text)
            enriched_text = inject_skill_prefix(text, ai=ai)
            integration = _st.integrations[ai]
            use_stdin   = integration.get("stdin_prompt", False)
            cmd    = integration["build_command"](enriched_text,
                                                  model=sess.get("model"))
            before = await asyncio.to_thread(snapshot_dir, cwd)
            output = await asyncio.to_thread(
                run_ai_popen, cmd, cwd, ai, sess, INTEGRATION_TIMEOUT,
                stdin_text=enriched_text if use_stdin else None,
            )
            after  = await asyncio.to_thread(snapshot_dir, cwd)
            await push_thinking(False, session_id=sid)
            await push_message("assistant", output, ai=ai, source=source, session_id=sid)
            await handle_diff(before, after, source, cwd, session_id=sid)

            # Auto-create a skill if no existing skill matched this task.
            if not skill_matched:
                asyncio.create_task(
                    asyncio.to_thread(auto_create_skill_template, text, ai, output)
                )

        else:
            # Shell mode
            if not terminal.is_alive():
                output = "Terminal stopped. Stop and restart this session."
                await push_message("system", output, source=source, session_id=sid)
            else:
                before = await asyncio.to_thread(snapshot_dir, cwd)
                terminal.write(text)
                output = await asyncio.to_thread(terminal.drain)
                after  = await asyncio.to_thread(snapshot_dir, cwd)
                output = output or "(no output)"
                await push_message("assistant", output, ai="shell", source=source, session_id=sid)
                await handle_diff(before, after, source, cwd, session_id=sid)

    finally:
        started = sess.get("task_start") if sess else None
        elapsed = time.time() - (started if started is not None else task_started_at)
        if sess:
            sess["total_task_seconds"] = float(sess.get("total_task_seconds") or 0.0) + max(0.0, elapsed)
            sess["task_count"] = int(sess.get("task_count") or 0) + 1
        record_usage_task(ai, elapsed, prompt=text, output=output)
        sess["busy"]       = False
        sess["task_start"] = None
        await push_state()  # flip session back to idle
        await tg_progress_notify(sess, output, elapsed, source)

    return output


_process_message = process_message  # legacy alias
