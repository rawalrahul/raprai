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


# Per-CLI failure tracking. One CLI's stream failure must never disable live
# progress for the others, and a single transient failure (interrupted run,
# crashed CLI) shouldn't permanently disable it either — only repeated
# consecutive failures do, since those suggest a real schema/flag mismatch.
_FAILURE_LIMIT = 2
_stream_failures: dict[str, int] = {}
_stream_disabled: dict[str, bool] = {}


def mark_unavailable(reason: str = "", key: str = "claude") -> None:
    """Record a stream failure for one CLI. After _FAILURE_LIMIT consecutive
    failures, disable streaming for that CLI (only) for the rest of the process,
    so we don't keep paying a failed-stream + fallback double run per message."""
    n = _stream_failures.get(key, 0) + 1
    _stream_failures[key] = n
    if n >= _FAILURE_LIMIT and not _stream_disabled.get(key):
        _stream_disabled[key] = True
        logger.info("live progress auto-disabled for %s this session (%s)", key, reason)
    else:
        logger.info("live progress failure %d/%d for %s (%s)",
                    n, _FAILURE_LIMIT, key, reason)


def mark_ok(key: str = "claude") -> None:
    """Reset the consecutive-failure counter after a successful stream."""
    _stream_failures[key] = 0


def live_progress_enabled(key: str = "claude") -> bool:
    """True when RAPR_LIVE_PROGRESS is on (default ON) and streaming hasn't been
    auto-disabled for this CLI after repeated failures. RAPR_LIVE_PROGRESS=0 forces off."""
    if _stream_disabled.get(key):
        return False
    return os.environ.get("RAPR_LIVE_PROGRESS", "1").strip().lower() in ("1", "true", "yes", "on")


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
    sess.pop("_user_killed", None)  # clear stale stop flag from a previous run

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
    _lines = 0
    _t0 = time.time()
    try:
        for line in proc.stdout:
            _lines += 1
            if _lines == 1:
                logger.info("run_claude_stream: first line at +%.2fs", time.time() - _t0)
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

    logger.info("run_claude_stream: read %d lines, %d steps, result=%s, killed=%s, elapsed=%.1fs",
                _lines, step_n, bool(result_line), killed["v"], time.time() - _t0)
    if killed["v"]:
        raise StreamUnavailable("timed out")
    if not result_line:
        raise StreamUnavailable("no result event in stream")

    _safe(emit, {"phase": "done"})
    mark_ok("claude")
    return result_line


# ---------------------------------------------------------------------------
# Generic JSONL streaming for CLIs that take the prompt via stdin (Codex, Gemini)
# ---------------------------------------------------------------------------

def _stream_cli(scmd, cwd, sess, stdin_text, extra_env, timeout, on_event, tag="cli"):
    """Run `scmd`, feed `stdin_text`, read stdout JSONL, call on_event(dict) per line.
    Raises StreamUnavailable on spawn/read failure or timeout."""
    import os as _os
    env = {**_os.environ, **extra_env} if extra_env else None
    try:
        proc = subprocess.Popen(
            scmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE if stdin_text else None,
            text=True, encoding="utf-8", errors="replace",
            cwd=cwd, env=env, **hidden_kwargs(),
        )
    except FileNotFoundError:
        raise StreamUnavailable(f"{scmd[0]} not found in PATH")
    except Exception as exc:
        raise StreamUnavailable(f"spawn failed: {exc}")

    sess["proc"] = proc
    sess.pop("_user_killed", None)  # clear stale stop flag from a previous run
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

    _lines = 0
    _json_lines = 0
    _t0 = time.time()
    try:
        if stdin_text and proc.stdin:
            try:
                proc.stdin.write(stdin_text)
                proc.stdin.close()
            except Exception:
                pass
        for line in proc.stdout:
            _lines += 1
            if _lines == 1:
                logger.info("%s stream: first line at +%.2fs", tag, time.time() - _t0)
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if isinstance(ev, dict):
                _json_lines += 1
                try:
                    on_event(ev)
                except Exception:
                    pass
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

    logger.info("%s stream: read %d lines (%d json), killed=%s, elapsed=%.1fs",
                tag, _lines, _json_lines, killed["v"], time.time() - _t0)
    if killed["v"]:
        raise StreamUnavailable("timed out")


def _shorten(s, n=60):
    s = str(s).splitlines()[0] if s else ""
    return s[:n - 1] + "…" if len(s) > n else s


# ---- Codex (codex exec --json) ----

def _codex_stream_cmd(cmd: list) -> list:
    out = list(cmd)
    if "--json" in out:
        return out
    try:
        out.insert(out.index("exec") + 1, "--json")
    except ValueError:
        out.insert(1, "--json")
    return out


def _codex_label(item: dict) -> str:
    it = item.get("type")
    if it == "command_execution":
        return "Running " + _shorten(item.get("command"))
    if it == "file_change":
        return "Editing " + _shorten(item.get("path") or item.get("file") or "files")
    if it == "mcp_tool_call":
        return "Tool " + _shorten(item.get("tool") or item.get("name") or "")
    if it == "web_search":
        return "Searching " + _shorten(item.get("query") or "")
    return _shorten(it or "Working")


def run_codex_stream(cmd, cwd, sess, emit, stdin_text=None, extra_env=None, timeout=None) -> str:
    """Run Codex with --json, emit step events, return the final agent-message text."""
    scmd = _codex_stream_cmd(cmd)
    texts = []
    step = [0]

    def _step(label):
        step[0] += 1
        _safe(emit, {"phase": "step", "n": step[0], "label": label})

    def on_event(ev):
        t = ev.get("type")
        # ── Newer schema: {"type":"item.started"/"item.completed","item":{...}} ──
        if t in ("item.started", "item.completed"):
            item = ev.get("item") or {}
            it = item.get("type") or item.get("item_type")
            if it == "agent_message":
                if t == "item.completed" and item.get("text"):
                    texts.append(item["text"])
            elif t == "item.started" and it in ("command_execution", "file_change",
                                                "mcp_tool_call", "web_search"):
                _step(_codex_label(item))
            return
        # ── Older protocol schema: {"id":...,"msg":{"type":...}} ──
        m = ev.get("msg")
        if isinstance(m, dict):
            mt = m.get("type") or ""
            if mt == "agent_message" and m.get("message"):
                texts.append(str(m["message"]))
            elif mt == "task_complete":
                last = m.get("last_agent_message")
                if isinstance(last, str) and last.strip():
                    texts.append(last)
            elif mt == "exec_command_begin":
                c = m.get("command")
                c = " ".join(c) if isinstance(c, list) else (c or "")
                _step("Running " + _shorten(c))
            elif mt in ("patch_apply_begin", "apply_patch_approval_request"):
                _step("Editing files")
            elif mt == "web_search_begin":
                _step("Searching " + _shorten(m.get("query") or ""))
            elif mt == "mcp_tool_call_begin":
                _step("Tool " + _shorten(m.get("tool") or ""))

    _stream_cli(scmd, cwd, sess, stdin_text, extra_env, timeout, on_event, tag="codex")
    final = texts[-1].strip() if texts else ""
    if not final:
        raise StreamUnavailable("no agent_message in codex stream")
    _safe(emit, {"phase": "done"})
    mark_ok("codex")
    return final


# ---- Gemini (--output-format stream-json) ----

def _gemini_stream_cmd(cmd: list) -> list:
    out = list(cmd)
    if "--output-format" in out:
        i = out.index("--output-format")
        if i + 1 < len(out):
            out[i + 1] = "stream-json"
        return out
    out += ["--output-format", "stream-json"]
    return out


def run_gemini_stream(cmd, cwd, sess, emit, stdin_text=None, extra_env=None, timeout=None) -> str:
    """Run Gemini with stream-json, emit step events, return the final response text.

    Prefers the `result` event's `response`; falls back to concatenated assistant
    `message` chunks. If neither yields text, raises StreamUnavailable so the
    caller re-runs normally — the reply is never guessed wrong.
    """
    scmd = _gemini_stream_cmd(cmd)
    result_text = [""]
    msg_parts = []
    step = [0]

    def on_event(ev):
        t = ev.get("type")
        if t == "tool_use":
            step[0] += 1
            name = ev.get("name") or (ev.get("tool") or {}).get("name") or "tool"
            args = ev.get("args") or ev.get("input") or {}
            tgt = ""
            if isinstance(args, dict):
                tgt = args.get("path") or args.get("file_path") or args.get("query") or ""
            _safe(emit, {"phase": "step", "n": step[0],
                         "label": (_shorten(name) + " " + _shorten(tgt)).strip()})
        elif t == "message":
            role = ev.get("role") or (ev.get("message") or {}).get("role")
            content = ev.get("content") or ev.get("text")
            if content is None:
                m = ev.get("message") or {}
                content = m.get("content") or m.get("text")
            if role in ("assistant", "model") and isinstance(content, str):
                msg_parts.append(content)
        elif t == "result":
            r = ev.get("response")
            if isinstance(r, str) and r.strip():
                result_text[0] = r

    _stream_cli(scmd, cwd, sess, stdin_text, extra_env, timeout, on_event, tag="gemini")
    text = result_text[0].strip() or "".join(msg_parts).strip()
    if not text:
        raise StreamUnavailable("no response in gemini stream")
    _safe(emit, {"phase": "done"})
    mark_ok("gemini")
    return text
