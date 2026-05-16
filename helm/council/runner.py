"""helm/council/runner.py — Low-level AI runner for council: no session history save."""

import asyncio
import os
import re
import subprocess
from typing import AsyncGenerator

import helm.state as _st
from helm.config import logger
from helm.subprocess_utils import hidden_kwargs

_ANSI_ESC_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
import json as _json


def _extract_text(raw: str) -> str:
    """Extract plain text from Claude CLI JSON envelope if present, else return raw."""
    try:
        obj = _json.loads(raw)
        if isinstance(obj, dict) and "result" in obj:
            return str(obj["result"])
    except Exception:
        pass
    return raw


def _build_cmd_for_session(sess: dict, prompt: str) -> tuple[list, str | None, dict]:
    """Build (cmd, stdin_text, extra_env) for the session's AI with the given prompt."""
    ai = sess.get("ai")
    model = sess.get("model")

    if ai == "claude":
        from helm.ai_runner.claude import build_claude_cmd
        cmd = build_claude_cmd(prompt, has_history=False, model=model)
        return cmd, None, {}

    if ai and ai in _st.integrations:
        info = _st.integrations[ai]
        build_fn = info.get("build_command")
        extra_env = info.get("process_env") or {}
        if build_fn:
            if info.get("stdin_prompt", False):
                base_cmd = build_fn("", model=model)
                return base_cmd, prompt, extra_env
            cmd = build_fn(prompt, model=model)
            return cmd, None, extra_env

    raise ValueError(f"Cannot build command for AI: {ai!r}")


def _run_subprocess_blocking(cmd: list, cwd: str, stdin_text: str | None,
                             extra_env: dict | None = None) -> str:
    """Blocking subprocess run. Returns stdout as string."""
    env = None
    if extra_env:
        env = {**os.environ, **extra_env}
    dummy = {"proc": None}
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
            env=env,
            **hidden_kwargs(),
        )
        dummy["proc"] = proc
        try:
            stdout, _ = proc.communicate(input=stdin_text, timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return "(timed out)"
        finally:
            dummy["proc"] = None

        stdout = _ANSI_ESC_RE.sub('', stdout).strip()
        return _extract_text(stdout) or "(no output)"
    except FileNotFoundError:
        return f"(error: '{cmd[0]}' not found in PATH)"
    except Exception as exc:
        return f"(error: {exc})"


async def run_moderator(session_id: str, prompt: str) -> str:
    """Run moderator AI, return full response string. No history save."""
    sess = _st.sessions.get(session_id)
    if not sess:
        return ""
    try:
        cmd, stdin_text, extra_env = _build_cmd_for_session(sess, prompt)
    except Exception as exc:
        logger.warning("council runner: cannot build cmd for %s: %s", session_id, exc)
        return ""
    cwd = sess.get("cwd", ".")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env)
    )


async def stream_council_response(
    session_id: str,
    topic: str,
    transcript: str,
    moderator_prompt: str,
    participant_name: str,
    context_summary: str = "",
) -> AsyncGenerator[str, None]:
    """Async generator yielding response chunks from participant AI. No history save."""
    sess = _st.sessions.get(session_id)
    if not sess:
        return

    summary_block = (
        f"Debate summary (prior rounds):\n{context_summary}\n\n"
        if context_summary else ""
    )
    full_prompt = (
        f"You are {participant_name} in an AI council debate.\n\n"
        f"Topic: {topic}\n\n"
        f"{summary_block}"
        f"Most recent exchanges:\n{transcript}\n\n"
        f"The moderator asks you: {moderator_prompt}\n\n"
        f"Respond as {participant_name}. Be direct. Engage with what others have said."
    )

    try:
        cmd, stdin_text, extra_env = _build_cmd_for_session(sess, full_prompt)
    except Exception as exc:
        logger.warning("council runner: cannot build cmd for %s: %s", session_id, exc)
        yield f"(error: {exc})"
        return

    cwd = sess.get("cwd", ".")

    # Use the same blocking executor path as run_moderator — asyncio.create_subprocess_exec
    # has inconsistent stdout buffering on Windows for some CLIs (e.g. Gemini gives blank output).
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: _run_subprocess_blocking(cmd, cwd, stdin_text, extra_env)
        )
        if result:
            yield result
    except Exception as exc:
        logger.warning("council stream error: %s", exc)
        yield f"(error: {exc})"
