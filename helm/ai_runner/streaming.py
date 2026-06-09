"""
helm/ai_runner/streaming.py — Optional live-progress streaming for the Claude CLI.

Why this exists
---------------
In normal `--output-format json -p` mode the Claude CLI buffers everything and
prints one JSON object at the very end, so the UI can only show a binary
"thinking…" until the whole run finishes. Claude also supports
`--output-format stream-json --verbose`, which emits the SAME information as a
stream of newline-delimited JSON events (one per assistant text / tool call),
ending with a `result` event that is byte-for-byte the object the json mode
returns.

So this module runs Claude in stream-json mode, reads the events as they
arrive, forwards them to a callback (for a live activity timeline), and returns
the final `result` line unchanged — which the existing
`parse_claude_json_output()` then parses exactly as before. The final answer is
therefore identical to the non-streaming path; only the live feedback is added.

Safety
------
* Disabled by default — enable with RAPR_LIVE_PROGRESS=1.
* Any problem (spawn failure, timeout, no result event, bad schema) raises
  StreamUnavailable so the caller falls back to the normal blocking run.
* The final answer always comes from the `result` event via the unchanged
  parser, so a wrong intermediate-event guess can only affect cosmetic
  timeline labels, never the response text.
"""

import json
import os
import subprocess
import threading
import time
from typing import Callable, Optional

from helm.config import logger

try:
    from helm.subprocess_utils import hidden_kwargs
except Exception:  # pragma: no cover
    def hidden_kwargs():
        return {}


class StreamUnavailable(Exception):
    """Raised when streaming can't run — caller should fall back to a normal run."""


def live_progress_enabled() -> bool:
    """True only when RAPR_LIVE_PROGRESS opts in (default off for safety)."""
    return os.environ.get("RAPR_LIVE_PROGRESS", "0").strip().lower() in ("1", "true", "yes", "on")


def to_stream_cmd(cmd: list) -> list:
    """Return a copy of a build_claude_cmd() list switched to stream-json mode."""
    out: list = []
    i = 0
    replaced = False
    while i < len(cmd):
        if cmd[i] == "--output-format" and i + 1 < len(cmd):
            out.extend(["--output-format", "stream-json", "--verbose"])
            i += 2
            replaced = True
            continue
        out.append(cmd[i])
        i += 1
    if not replaced:
        raise StreamUnavailable("command has no --output-format to convert")
    return out


def _tool_label(name: str, inp: dict) -> str:
    """Build a short, human-readable label for a tool-use step."""
    n = (name or "").lower()
    target = (inp.get("file_path") or inp.get("path") or inp.get("pattern")
              or inp.get("command") or inp.get("query") or "")
    target = str(target).splitlines()[0] if target else ""
    if len(target) > 60:
        target = target[:57] + "…"
    verbs = {
        "read": "Reading", "write": "Writing", "edit": "Editing",
        "bash": "Running", "grep": "Searching", "glob": "Finding",
        "webfetch": "Fetching", "websearch": "Searching", "task": "Delegating",
    }
    for k, v in verbs.items():
        if k in n:
            return (f"{v} {target}").strip()
    return (f"{name} {target}").strip() if target else (name or "Working")


def _safe(emit: Callable[[dict], None], ev: dict) -> None:
    try:
        emit(ev)
    except Exception:
        pass


def run_claude_stream(cmd: list, cwd: str, sess: dict,
                      emit: Callable[[dict], None],
                      timeout: Optional[float] = None) -> str:
    """Run Claude with stream-json, emit activity events, return the result line.

    Intended to run inside ``asyncio.to_thread``. ``emit`` must be a thread-safe
    sink (e.g. one that schedules a websocket broadcast on the main loop).
    Returns the raw JSON string of the final ``result`` event, suitable for
    ``parse_claude_json_output``. Raises StreamUnavailable on any failure.
    """
    scmd = to_stream_cmd(cmd)

    try:
        proc = subprocess.Popen(
            scmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge so a stderr-fill can't deadlock the pipe
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            **hidden_kwargs(),
        )
    except FileNotFoundError:
        raise StreamUnavailable("claude not found in PATH")
    except Exception as exc:
        raise StreamUnavailable(f"spawn failed: {exc}")

    sess["proc"] = proc  # let stop/interrupt kill it, same as run_ai_popen

    killed = {"v": False}

    def _watchdog():
        end = time.time() + timeout
        while time.time() < end:
            if proc.poll() is not None:
                return
            time.sleep(0.5)
        if proc.poll() is None:
            killed["v"] = True
            try:
                proc.kill()
            except Exception:
                pass

    if timeout:
        threading.Thread(target=_watchdog, daemon=True).start()

    result_line: Optional[str] = None
    step_n = 0
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue  # non-JSON (merged stderr / banner) — ignore
            if not isinstance(ev, dict):
                continue
            etype = ev.get("type")
            if etype == "result":
                result_line = line  # same shape as --output-format json
            elif etype == "assistant":
                for block in (ev.get("message", {}).get("content") or []):
                    if not isinstance(block, dict):
                        continue
                    bt = block.get("type")
                    if bt == "tool_use":
                        step_n += 1
                        _safe(emit, {
                            "phase": "step",
                            "n": step_n,
                            "label": _tool_label(block.get("name", "tool"),
                                                 block.get("input") or {}),
                        })
                    elif bt == "text":
                        txt = (block.get("text") or "").strip()
                        if txt:
                            _safe(emit, {"phase": "note", "label": txt[:160]})
    except Exception as exc:
        try:
            proc.kill()
        except Exception:
            pass
        raise StreamUnavailable(f"stream read failed: {exc}")
    finally:
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        sess["proc"] = None

    if killed["v"]:
        raise StreamUnavailable("timed out")
    if not result_line:
        raise StreamUnavailable("no result event in stream")

    _safe(emit, {"phase": "done"})
    return result_line
