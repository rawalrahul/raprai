"""helm/council/runner.py — Low-level AI runner for council: no session history save."""

import asyncio
import re
import subprocess
from typing import AsyncGenerator

import helm.state as _st
from helm.config import logger
from helm.subprocess_utils import hidden_kwargs

_ANSI_ESC_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _build_cmd_for_session(sess: dict, prompt: str) -> tuple[list, str | None]:
    """Build (cmd, stdin_text) for the session's AI with the given prompt."""
    ai = sess.get("ai")
    cwd = sess.get("cwd", ".")
    model = sess.get("model")

    if ai == "claude":
        from helm.ai_runner.claude import build_claude_cmd
        cmd = build_claude_cmd(prompt, cwd=cwd, model=model)
        return cmd, None

    if ai and ai in _st.integrations:
        info = _st.integrations[ai]
        build_fn = info.get("build_command")
        if build_fn:
            if info.get("stdin_prompt", False):
                base_cmd = build_fn("", model=model)
                return base_cmd, prompt
            cmd = build_fn(prompt, model=model)
            return cmd, None

    raise ValueError(f"Cannot build command for AI: {ai!r}")


def _run_subprocess_blocking(cmd: list, cwd: str, stdin_text: str | None) -> str:
    """Blocking subprocess run. Returns stdout as string."""
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
        return stdout or "(no output)"
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
        cmd, stdin_text = _build_cmd_for_session(sess, prompt)
    except Exception as exc:
        logger.warning("council runner: cannot build cmd for %s: %s", session_id, exc)
        return ""
    cwd = sess.get("cwd", ".")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: _run_subprocess_blocking(cmd, cwd, stdin_text)
    )


async def stream_council_response(
    session_id: str,
    topic: str,
    transcript: str,
    moderator_prompt: str,
    participant_name: str,
) -> AsyncGenerator[str, None]:
    """Async generator yielding response chunks from participant AI. No history save."""
    sess = _st.sessions.get(session_id)
    if not sess:
        return

    full_prompt = (
        f"You are {participant_name} in an AI council debate.\n\n"
        f"Topic: {topic}\n"
        f"Your role: Provide {participant_name}'s perspective.\n\n"
        f"Council conversation so far:\n{transcript}\n\n"
        f"The moderator asks you: {moderator_prompt}\n\n"
        f"Respond as {participant_name}. Be direct. Engage with what others have said."
    )

    try:
        cmd, stdin_text = _build_cmd_for_session(sess, full_prompt)
    except Exception as exc:
        logger.warning("council runner: cannot build cmd for %s: %s", session_id, exc)
        yield f"(error: {exc})"
        return

    cwd = sess.get("cwd", ".")

    try:
        stdin_flag = asyncio.subprocess.PIPE if stdin_text else None
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=stdin_flag,
            cwd=cwd,
        )

        if stdin_text:
            proc.stdin.write(stdin_text.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

        buffer = ""
        while True:
            try:
                raw = await asyncio.wait_for(proc.stdout.read(256), timeout=300)
            except asyncio.TimeoutError:
                break
            if not raw:
                break
            text = _ANSI_ESC_RE.sub('', raw.decode("utf-8", errors="replace"))
            buffer += text
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    yield line + "\n"

        if buffer.strip():
            yield buffer

        await proc.wait()
    except Exception as exc:
        logger.warning("council stream error: %s", exc)
        yield f"(error: {exc})"
