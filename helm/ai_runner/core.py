"""
helm/ai_runner/core.py — Core subprocess runner and message processor.

Covers: run_ai_popen, kill_session_proc, and process_message (the main dispatcher).
Includes Error Recovery & Resilience: auto-retry (3 attempts) and fallback AI switching.
"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Optional

from helm.subprocess_utils import hidden_kwargs

import helm.state as _st
from helm.broadcast import broadcast, push_agent_error, push_message, push_state, push_thinking
from helm.config import CLAUDE_TIMEOUT, INTEGRATION_TIMEOUT, logger
from helm.session_mgr import record_usage_task
from helm.skills import inject_skill_prefix
from helm.skill_creation import generate_skill
from helm.plugins import inject_plugin_context
from helm.context_manager import update_token_count, check_and_compact

from .helpers import tg_progress_notify
from .prompt import _SAFETY_PREAMBLE, base_prompt  # noqa: F401  (tests import the preamble from here)
from helm.learning.hooks import task_started, task_finished
from . import slash_commands


# ---------------------------------------------------------------------------
# Error Recovery & Resilience — constants and helpers
# ---------------------------------------------------------------------------

def _max_retries() -> int:
    """Max retry attempts before switching AI (default 3, min 1, max 10)."""
    return max(1, min(10, int(os.environ.get("AI_MAX_RETRIES", "3"))))

def _auto_switch_enabled() -> bool:
    """Whether to auto-switch AI on failure (default True)."""
    return os.environ.get("AI_AUTO_SWITCH", "1").strip().lower() in ("1", "true", "yes")

RETRY_DELAY = 2.0        # seconds between retries

# ---------------------------------------------------------------------------
# Failure detection — two tiers
# ---------------------------------------------------------------------------
#
# Tier 1: INFRASTRUCTURE failures — the CLI itself broke (not in PATH, network
#     down, auth expired, etc.).  These warrant retries and fallback to another
#     AI because the problem is environmental, not task-related.
#
# Tier 2: GENERAL failures (superset of Tier 1) — also includes patterns like
#     API-key mentions and non-zero exit codes.  Used only for legacy callers;
#     self-healing and retry logic use Tier 1 exclusively.
#
# The key principle: if the AI actually ran and produced a substantive response
# (even if it says "I can't do that"), that is NOT a failure — it is the AI
# communicating.  We only intervene when the CLI infrastructure broke.
# ---------------------------------------------------------------------------

# Tier 1 — infrastructure / CLI failures only
_INFRA_FAILURE_PATTERNS = re.compile(
    r"(?i)("
    r"error:.*not found in PATH"
    r"|Error: '[\w.-]+' not found in PATH"         # run_ai_popen FileNotFoundError
    r"|timed out after \d+s"
    r"|FileNotFoundError"
    r"|ConnectionRefusedError"
    r"|ConnectionResetError"
    r"|connection reset"
    r"|connection refused"
    r"|ECONNREFUSED"
    r"|ECONNRESET"
    r"|ETIMEDOUT"
    r"|502 Bad Gateway"
    r"|503 Service Unavailable"
    r"|504 Gateway Timeout"
    r"|500 Internal Server Error"
    r"|rate.?limit"
    r"|too many requests"
    r"|429"
    r"|oauth token has expired"
    r"|could not connect"
    r"|network.?error"
    r")"
)

# Match the exact format produced by run_ai_popen when the CLI process
# crashes: "(codex exited 1)" — only at the END of the output.
_EXIT_CODE_PATTERN = re.compile(r"\(\w+ exited [1-9]\d*\)\s*$")

# ---------------------------------------------------------------------------
# Explicit correction detection
# ---------------------------------------------------------------------------
# Signals that the user is rejecting / correcting the last AI response.
_CORRECTION_NEGATIVE = re.compile(
    r'\b(wrong|no|not right|incorrect|that\'?s wrong|not what i (want|asked|meant)'
    r'|undo|redo|try again|do it again|fix that|fix it|that\'?s not|start over'
    r'|revert|that\'?s incorrect|nope|nah|bad|terrible|awful|useless'
    r'|not (what|how|the|like)|i said|i meant|i asked for|again please)\b',
    re.IGNORECASE,
)
# Signals that the user is explicitly accepting the response.
_CORRECTION_POSITIVE = re.compile(
    r'\b(perfect|great|thanks|thank you|done|exactly|yes|correct|looks good'
    r'|nice|awesome|good job|well done|that\'?s it|that\'?s right)\b',
    re.IGNORECASE,
)


def _detect_correction(text: str, sess: dict, ai: str, task_type: str) -> None:
    """
    Scan incoming message for explicit correction/acceptance signals.
    Updates telemetry (3x weight for explicit_negative) and mines
    antipatterns from correction content. Never raises.
    """
    try:
        is_negative = bool(_CORRECTION_NEGATIVE.search(text))
        is_positive = bool(_CORRECTION_POSITIVE.search(text))

        if not is_negative and not is_positive:
            return

        feedback_type = "explicit_negative" if is_negative else "explicit_positive"
        weight = 3.0 if is_negative else 1.0

        # Update routing stats with feedback signal
        try:
            from helm.learning.router import update_stats
            update_stats(
                task_type=task_type,
                ai=ai,
                duration_seconds=0,
                success=not is_negative,
                cost_usd=0.0,
                weight=weight,
            )
        except Exception:
            logger.debug("Learning: couldn't record the correction in routing stats", exc_info=True)

        # Mine antipattern from correction content when negative
        if is_negative and len(text) > 10:
            try:
                from helm.learning.analyzer import _append_antipattern
                last_response = (sess.get("claude_msgs") or sess.get("ollama_messages") or [])
                last_ai_text = ""
                for m in reversed(last_response):
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        last_ai_text = str(m.get("content", ""))[:300]
                        break
                    elif isinstance(m, str):
                        last_ai_text = m[:300]
                        break

                antipattern = (
                    f"User correction detected for task_type={task_type}, ai={ai}.\n"
                    f"User said: {text[:200]}\n"
                    f"AI had responded: {last_ai_text[:200]}\n"
                    f"Action: review this pattern and avoid repeating it."
                )
                _append_antipattern(task_type, antipattern)
            except Exception:
                logger.debug("Learning: couldn't save the correction as an antipattern", exc_info=True)

        logger.info(
            "Correction detected: type=%s ai=%s task_type=%s weight=%.1f text=%r",
            feedback_type, ai, task_type, weight, text[:80],
        )
    except Exception:
        logger.debug("Learning: correction detection failed", exc_info=True)

# Match run_ai_popen's error wrapper: "(error: ...)"
_POPEN_ERROR_PATTERN = re.compile(r"^\(error:")

# Built-in AI keys (always available if CLI is installed)
_BUILTIN_AIS = ["claude", "ollama"]


def _is_infra_failure(output: str) -> bool:
    """Check if AI output indicates an INFRASTRUCTURE failure.

    Returns True only for CLI-level problems (binary not found, network errors,
    auth expired, process crashed, etc.) — NOT for cases where the AI ran
    successfully but said "I can't do that".

    This is the primary check used by the retry/fallback/self-healing logic.
    It intentionally does NOT flag:
      - Normal AI responses that mention error-like keywords in their content
      - AI responses declining a task ("I can't create images")
      - Long outputs where the AI clearly did work
    """
    if not output or output == "(no output)":
        return False

    stripped = output.strip()

    # If the AI produced a long, substantive response, the CLI worked fine.
    # The AI may have declined the task or mentioned errors, but that's the
    # AI communicating, not an infrastructure failure.
    if len(stripped) > 800:
        return False

    # run_ai_popen wraps errors in "(error: ...)"
    if _POPEN_ERROR_PATTERN.match(stripped):
        return True

    # CLI process exited non-zero: "(codex exited 1)" at end of output
    if _EXIT_CODE_PATTERN.search(stripped):
        return True

    # Known infrastructure error patterns
    if _INFRA_FAILURE_PATTERNS.search(stripped):
        return True

    return False


def _is_failure(output: str) -> bool:
    """Legacy/compat wrapper — delegates to _is_infra_failure.

    All retry, fallback, and self-healing logic now uses _is_infra_failure
    which only triggers on genuine CLI/infrastructure problems.
    """
    return _is_infra_failure(output)


# A1: availability probe cache — (backend_name) → (available: bool, checked_at: float)
_availability_cache: dict[str, tuple[bool, float]] = {}
_AVAILABILITY_TTL = 120.0  # seconds


def is_backend_available(ai_key: str) -> bool:
    """Return True if ai_key's CLI/integration is reachable right now.

    A1: Cached 120s so repeated probes on a healthy backend are free.
    Used by the agent executor to skip the selected backend before a 600s timeout.
    """
    cached = _availability_cache.get(ai_key)
    if cached:
        available, checked_at = cached
        if time.time() - checked_at < _AVAILABILITY_TTL:
            return available

    # Built-in CLI check
    if ai_key == "claude":
        from helm.signin import signed_in
        result = bool(shutil.which("claude")) and signed_in("claude")
    elif ai_key == "ollama":
        ready = (_st.integrations.get("ollama") or {}).get("ready")
        result = bool(shutil.which("ollama")) and (not callable(ready) or bool(ready()))
    elif ai_key == "openrouter":
        result = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
    elif ai_key == "groq":
        result = bool(os.environ.get("GROQ_API_KEY", "").strip())
    elif ai_key == "local_ai":
        # Available when LOCAL_AI_URL is set or when the default LM Studio port responds
        url = os.environ.get("LOCAL_AI_URL", "http://localhost:1234").rstrip("/")
        try:
            import urllib.request as _ur
            _ur.urlopen(f"{url}/v1/models", timeout=1)
            result = True
        except Exception:
            result = False
    elif ai_key == "openclaw":
        # OpenClaw is the direct host CLI integration. WSL probing belongs to
        # NemoClaw, not OpenClaw.
        result = bool(shutil.which("openclaw"))
    else:
        # Registered integration — check CLI binary first, then API key env vars
        info = _st.integrations.get(ai_key)
        if not info:
            result = False
        else:
            try:
                test_cmd = info["build_command"]("test", model=None)
                cli_name = test_cmd[0] if test_cmd else ai_key
                env_vars = info.get("env_vars", [])
                if cli_name == sys.executable and test_cmd[1:2] == ["-m"]:
                    # Python-subprocess integration — check env vars, not PATH
                    result = (
                        any(os.environ.get(v, "").strip() for v in env_vars)
                        if env_vars else True
                    )
                elif shutil.which(cli_name):
                    result = True
                else:
                    result = False
                from helm.signin import signed_in
                result = result and signed_in(ai_key)
                ready = info.get("ready")
                if result and callable(ready):
                    result = bool(ready())
            except Exception:
                result = False

    _availability_cache[ai_key] = (result, time.time())
    return result


def list_available_backends(exclude: str | None = None) -> list[str]:
    """Return all backends that pass is_backend_available(), optionally excluding one."""
    candidates = list(_BUILTIN_AIS) + [k for k in _st.integrations if k not in _BUILTIN_AIS]
    return [k for k in candidates if k != exclude and is_backend_available(k)]


def resolve_ai_spec(ai_spec: str) -> tuple[str, str | None]:
    """A6: Parse provider/model strings into (backend_key, model_override).

    Accepts:
      "claude"                          → ("claude", None)
      "anthropic/claude-sonnet-4.6"     → ("claude", "claude-sonnet-4.6")
      "ollama/llama3.2"                 → ("ollama", "llama3.2")
      "openrouter/anthropic/claude-3"   → ("openrouter", "anthropic/claude-3")
      "gemini/gemini-2.0-flash"         → ("gemini", "gemini-2.0-flash")
      any other "provider/model"        → (provider, model) — dispatched via integrations
    """
    if not ai_spec or "/" not in ai_spec:
        return ai_spec, None

    parts = ai_spec.split("/", 1)
    provider, model = parts[0].lower(), parts[1]

    # Map provider aliases to known backend keys
    _PROVIDER_MAP = {
        "anthropic": "claude",
        "claude":    "claude",
        "ollama":    "ollama",
        "gemini":    "gemini",
        "google":    "gemini",
        "openrouter": "openrouter",
        "codex":     "codex",
        "groq":      "groq",
        "local_ai":       "local_ai",
        "local":          "local_ai",
        "lmstudio":       "local_ai",
        "jan":            "local_ai",
        "github_models":  "github_models",
        "github":         "github_models",
        "openclaw":       "openclaw",
        "antigravity":    "antigravity",
        "agy":            "antigravity",
        "cursor":         "cursor",
        "cursor-agent":   "cursor",
        "kilocode":       "kilocode",
        "kilo":           "kilocode",
    }
    backend = _PROVIDER_MAP.get(provider, provider)
    return backend, model


def _find_available_ais(exclude: str) -> list[str]:
    """Return a list of available AI keys, excluding the failed one.

    Checks both built-in CLIs (claude, ollama) and registered integrations
    (gemini, codex, etc.) for availability.
    """
    available = []

    # Check built-in CLIs
    for ai_key in _BUILTIN_AIS:
        if ai_key == exclude:
            continue
        if ai_key == "claude" and shutil.which("claude"):
            available.append(ai_key)
        elif ai_key == "ollama" and shutil.which("ollama"):
            available.append(ai_key)

    # Check registered integrations via is_backend_available (uses cache).
    # Avoids the sys.executable / wsl.exe false-positive: both always pass
    # shutil.which even when the underlying binary or API key is absent.
    for ai_key in _st.integrations:
        if ai_key == exclude:
            continue
        try:
            if is_backend_available(ai_key):
                available.append(ai_key)
        except Exception:
            logger.debug("Couldn't check whether %s is available", ai_key, exc_info=True)

    return available


_ANSI_ESC_RE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


# ---------------------------------------------------------------------------
# Token parsing for CLI-based AIs (Gemini, Codex, etc.)
# ---------------------------------------------------------------------------

# Patterns to extract token counts from CLI output text
_TOKEN_PATTERNS = [
    # "Tokens: 1234 in / 567 out" or "1.2k input, 850 output"
    re.compile(r'[Tt]okens?[:\s]+([0-9,.]+[kKmM]?)\s*(?:in(?:put)?|prompt)\s*[/,]\s*([0-9,.]+[kKmM]?)\s*(?:out(?:put)?|completion)', re.IGNORECASE),
    # "input_tokens: 1234, output_tokens: 567"
    re.compile(r'input.?tokens?[:\s]+([0-9,.]+)\s*[,;]\s*output.?tokens?[:\s]+([0-9,.]+)', re.IGNORECASE),
    # "Usage: 1234 input tokens, 567 output tokens"
    re.compile(r'([0-9,.]+[kKmM]?)\s+input\s+tokens?\s*[,;]\s*([0-9,.]+[kKmM]?)\s+output\s+tokens?', re.IGNORECASE),
    # "Total tokens: 1801"
    re.compile(r'[Tt]otal\s+tokens?[:\s]+([0-9,.]+[kKmM]?)', re.IGNORECASE),
]


def _parse_token_number(s: str) -> int:
    """Parse a token count string like '1.2k', '3,456', '1.5M' into an integer."""
    s = s.strip().replace(",", "")
    multiplier = 1
    if s.endswith(("k", "K")):
        multiplier = 1000
        s = s[:-1]
    elif s.endswith(("m", "M")):
        multiplier = 1_000_000
        s = s[:-1]
    try:
        return int(float(s) * multiplier)
    except (ValueError, TypeError):
        return 0


def _extract_tokens_from_cli_output(output: str) -> dict | None:
    """Try to extract token counts from CLI text output.

    Returns {"input": int, "output": int} or None if no token info found.
    """
    if not output:
        return None
    for pat in _TOKEN_PATTERNS:
        m = pat.search(output)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return {
                    "input": _parse_token_number(groups[0]),
                    "output": _parse_token_number(groups[1]),
                }
            elif len(groups) == 1:
                # Total only — split roughly 60/40 input/output
                total = _parse_token_number(groups[0])
                return {"input": int(total * 0.6), "output": int(total * 0.4)}
    return None


# ---------------------------------------------------------------------------
# File deletion safety guard
# ---------------------------------------------------------------------------
_DESTRUCTIVE_PATTERNS = re.compile(
    r'\b(?:'
    r'rm\s+-[rf]|rm\s+|rmdir\s+|del\s+/|Remove-Item|'
    r'shutil\.rmtree|os\.remove|os\.unlink|pathlib.*\.unlink|'
    r'rimraf\s+|fs\.rm|fs\.unlink'
    r')\b',
    re.IGNORECASE,
)


def _log_deletion_warning(ai: str, session_id: str, output: str):
    """Log any destructive commands found in AI output to deletion_log.json."""
    import json
    from datetime import datetime
    matches = _DESTRUCTIVE_PATTERNS.findall(output)
    if not matches:
        return
    from helm.paths import user_data_dir
    log_path = str(user_data_dir() / "deletion_log.json")
    entry = {
        "timestamp": datetime.now().isoformat(),
        "ai": ai,
        "session_id": session_id,
        "commands_detected": matches,
        "snippet": output[:500],
    }
    try:
        existing = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        logger.warning("⚠️ Destructive command detected in %s output: %s", ai, matches)
    except Exception as exc:
        logger.warning("Could not write deletion_log.json: %s", exc)


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
                **hidden_kwargs(),
            )
        except Exception:
            logger.warning("Could not pre-install %s — skills may install it on demand", pkg)

from helm.paths import is_bundled as _is_bundled
if not _is_bundled():
    try:
        _ensure_doc_packages()
    except Exception:
        logger.warning("Couldn't pre-install the document packages", exc_info=True)


# A CLI saying the chosen model can't be used (wrong plan, retired, unknown).
_MODEL_REJECTED_RE = re.compile(
    r"model is not supported when using|model_not_found|"
    r"The model [`'\"][^`'\"]+[`'\"] does not exist", re.IGNORECASE)


def run_ai_popen(cmd: list[str], cwd: str, name: str, sess: dict,
                 timeout_override: float | None = None,
                 stdin_text: str | None = None,
                 extra_env: dict | None = None) -> str:
    """Run an AI CLI subprocess, storing the Popen handle in sess['proc'] so it
    can be killed externally by stop_session / interrupt handlers.

    timeout_override: explicit seconds; None → use CLAUDE_TIMEOUT (0 = unlimited).
    stdin_text: if provided, the prompt is piped via stdin instead of appearing
    on the command line — this avoids Windows cmd.exe 8 KB arg-length limits.
    extra_env: additional env vars merged into os.environ for this subprocess only.
    Integration AIs (Gemini, Codex, …) pass INTEGRATION_TIMEOUT to prevent an
    infinite hang when an invalid --model causes the CLI to enter an interactive
    picker with no terminal attached.
    """
    if timeout_override is not None:
        _timeout: float | None = timeout_override if timeout_override > 0 else None
    else:
        _timeout = CLAUDE_TIMEOUT if CLAUDE_TIMEOUT > 0 else None
    from helm.paths import child_env
    # RAPR_SESSION_ID lets tool calls made from inside the AI (helm/mcp/call_tool.py)
    # say which session they belong to, for approvals.
    _env = child_env(cmd, {**(extra_env or {}), "RAPR_SESSION_ID": str(sess.get("id", ""))})
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
            env=_env,
            **hidden_kwargs(),
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
        except OSError:
            pass
        sess["proc"] = None
        # Tell streaming wrappers this was a deliberate stop — they must not
        # treat it as a stream failure or fall back to a blocking re-run.
        sess["_user_killed"] = True


_kill_session_proc = kill_session_proc  # legacy alias


async def process_message(text: str, source: str = "web",
                          session_id: Optional[str] = None) -> str:
    """
    Route `text` to the given session (or focused session if session_id is None).
    Returns the response string. Broadcasts to all WS clients.
    """
    from helm.file_tracker import snapshot_dir, handle_diff

    # "@codex …" at the start: start that AI, or bring it into a group chat.
    if session_id is None or session_id == _st.focused_id:
        try:
            from helm.mention_router import route as _route_mentions
            _routed = await _route_mentions(text, source)
        except Exception as exc:
            logger.warning("mention routing failed: %s", exc)
            _routed = None
        if _routed is not None:
            return _routed

    sid  = session_id or _st.focused_id
    sess = _st.sessions.get(sid) if sid else None

    if not sess or sess["status"] == "stopped":
        msg = "No active session. Create or resume a session first."
        await push_message("system", msg, source=source)
        return msg

    # ── Per-session lock — prevent concurrent web + Telegram races ────────
    _sess_lock = sess.get("_lock")
    if _sess_lock and _sess_lock.locked():
        msg = f"⏳ **{sess['name']}** is already processing a task. Please wait."
        await push_message("system", msg, source=source, session_id=sid)
        return msg

    # ── Budget guardrail — block if AI has exceeded its daily cap ──────────
    ai_for_budget = sess.get("ai")
    if ai_for_budget and ai_for_budget != "shell":
        from helm.web_routes.usage_routes import check_budget
        budget = check_budget(ai_for_budget)
        if not budget["allowed"]:
            msg = f"🚫 **Budget limit reached** — {budget['reason']}"
            await push_message("system", msg, source=source, session_id=sid)
            return msg
        if budget.get("warn") and budget.get("reason"):
            await push_message("system", budget["reason"], source=source, session_id=sid)

    # ── /pipeline (ai_runner/slash_commands.py) ─────────────────────────────
    stripped = text.strip()
    reply = await slash_commands.handle_pipeline(stripped, sess, sid, source)
    if reply is not None:
        return reply

    # ── Auto-suggest pipeline for complex tasks ───────────────────────────
    if os.environ.get("PIPELINE_AUTO_SUGGEST", "1") == "1":
        from helm.pipeline.planner import looks_complex
        if looks_complex(stripped) and not (sess or {}).get("pipeline_id"):
            # Remember the prompt so the web UI's "Call the Kelvin crew" button
            # (WS command "crew") can re-run it as a pipeline.
            sess["crew_prompt"] = stripped
            await push_message(
                "system",
                f"💡 This looks like a big multi-step task. {(sess.get('ai') or 'The current AI').capitalize()} "
                "has started on it. The Kelvin crew can split it across several AIs and run "
                "independent parts in parallel instead: use the button below, or type /pipeline "
                "followed by your task.",
                source=source, session_id=sid,
            )
            await broadcast({"type": "crew_suggest", "session_id": sid})

    # ── /model and /remember (ai_runner/slash_commands.py) ──────────────────
    # After the crew suggestion, as they always have been.
    reply = await slash_commands.handle(stripped, sess, sid, source)
    if reply is not None:
        return reply

    # Acquire per-session lock to serialise concurrent messages safely
    if _sess_lock:
        await _sess_lock.acquire()

    task_started_at = time.time()
    sess["last_used"] = task_started_at
    sess["busy"]       = True
    sess["task_start"] = task_started_at
    await push_state()  # immediately reflect busy status on web UI and Telegram

    ai       = sess["ai"]
    cwd      = sess["cwd"]
    terminal = sess["terminal"]

    _task_id, _clf = task_started(text, ai, sess, sid, source)

    await push_message("user", text, ai=None, source=source, session_id=sid)

    # A background look (your brief, helm/brief.py) isn't you talking to the AI: its
    # instructions aren't corrections, and it teaches the learning system nothing.
    _background = bool(sess.get("read_only"))

    # Detect explicit correction/acceptance signals — 3x weight in routing stats
    if not _background:
        _detect_correction(text, sess, ai, _clf.get("task_type", "unknown"))

    safe_text = base_prompt(text, ai, _clf, background=_background)

    output = ""  # safe default — overwritten in every branch below
    actual_ai = ai  # tracks which AI actually produced the output (may change on fallback)
    try:
        # ── Dispatch with retry + fallback ─────────────────────────────────
        output, actual_ai = await _dispatch_with_recovery(
            ai=ai, sess=sess, text=text, safe_text=safe_text,
            cwd=cwd, terminal=terminal, source=source, sid=sid,
            snapshot_dir=snapshot_dir, handle_diff=handle_diff,
        )

    finally:
        started = sess.get("task_start") if sess else None
        elapsed = time.time() - (started if started is not None else task_started_at)
        if sess:
            sess["total_task_seconds"] = float(sess.get("total_task_seconds") or 0.0) + max(0.0, elapsed)
            sess["task_count"] = int(sess.get("task_count") or 0) + 1
        # Extract actual token counts from session (set by AI backends)
        _last_tok = sess.pop("_last_tokens", None) if sess else None
        _tok_in  = _last_tok["input"]  if _last_tok else None
        _tok_out = _last_tok["output"] if _last_tok else None
        if _last_tok:
            logger.info("Token handoff: ai=%s in=%s out=%s", actual_ai, _tok_in, _tok_out)
        else:
            logger.info("Token handoff: ai=%s — no actual tokens captured", actual_ai)
        record_usage_task(actual_ai, elapsed, prompt=text, output=output,
                          input_tokens=_tok_in, output_tokens=_tok_out)

        task_finished(_task_id, _clf, text=text, ai=actual_ai, sess=sess, sid=sid, output=output,
                      success=bool(output) and not _is_infra_failure(output), elapsed=elapsed,
                      tok_in=_tok_in, tok_out=_tok_out)

        # Audit: log any destructive file commands in the AI output
        if output:
            _log_deletion_warning(actual_ai, sid or "", output)
        # --- Context Window Management ---
        # Update token count and auto-compact if needed
        if sess:
            update_token_count(
                sess,
                input_tokens=_tok_in or 0,
                output_tokens=_tok_out or 0,
                prompt_text=text,
                output_text=output,
            )
            try:
                await check_and_compact(sess, source=source)
            except Exception as _ctx_err:
                logger.warning("Context compaction failed: %s", _ctx_err)
        sess["busy"]       = False
        sess["task_start"] = None
        if _sess_lock and _sess_lock.locked():
            _sess_lock.release()
        await push_state()  # flip session back to idle
        await tg_progress_notify(sess, output, elapsed, source, prompt_text=text)
        from .helpers import mirror_to_chat_apps
        await mirror_to_chat_apps(sess, output, source, prompt_text=text)
        if not _is_failure(output):
            from helm.kelvin_stickers import done_sticker_for_task
            done_sticker_for_task(elapsed, output, source)

    return output


_process_message = process_message  # legacy alias


# ---------------------------------------------------------------------------
# Self-Healing Skill Generation
# ---------------------------------------------------------------------------

# Track which (prompt_hash, ai) pairs have already attempted self-healing
# to prevent infinite retry loops.
_heal_attempts: set[str] = set()

# Lightweight coherence check — reject gibberish before wasting Claude
# credits on skill generation.  We look for a minimum number of common
# English words (verbs, nouns, prepositions, articles, etc.) that indicate
# the user expressed an *actionable* intent.  The threshold is deliberately
# low so that short but valid commands like "create a pdf" still pass.
_COMMON_WORDS = frozenset(
    # determiners / pronouns / prepositions / conjunctions
    "a an the this that these those my your our their its "
    "i me you we he she it they us him her them "
    "in on at to for from by with of about into through after "
    "and or but if so then because when while "
    # common verbs / action words
    "make create build write send read open close delete remove add edit "
    "update fix change set get find search show list run start stop check "
    "help generate convert move copy paste upload download install save "
    "do can could would should will please tell explain summarize analyze "
    "is are was were be been am has have had go went "
    "need want like use try look give take put let "
    .split()
)


def _is_coherent_task(text: str) -> bool:
    """
    Return True if *text* looks like a coherent user request rather than
    garbled transcription noise.

    Heuristics:
      1. Must have at least 2 words.
      2. At least 30 % of words (min 1) must be recognised common English
         words — gibberish transcriptions almost never hit this bar.
    """
    words = re.findall(r"[a-zA-Z]{2,}", text.lower())
    if len(words) < 2:
        return False
    recognised = sum(1 for w in words if w in _COMMON_WORDS)
    ratio = recognised / len(words) if words else 0
    return recognised >= 1 and ratio >= 0.30


# Action verbs / task indicators that signal the user wants something *done*.
_ACTION_VERBS = frozenset(
    "make create build write send read open close delete remove add edit "
    "update fix change set get find search show list run start stop check "
    "help generate convert move copy paste upload download install save "
    "deploy push pull merge commit test debug configure setup launch "
    "summarize analyze explain translate format compile clean reset restart "
    "schedule cancel rename replace monitor track fetch parse connect "
    "export import sync share publish draft compose design sort filter "
    "compare calculate resize crop extract fill optimize review migrate "
    "backup restore enable disable prepare plan organize research "
    "tell give need want can could please try do"
    .split()
)


def _has_actionable_intent(text: str) -> bool:
    """
    Return True if *text* contains at least one action verb or task-like
    keyword, suggesting the user wants a concrete action performed.

    This filters out messages that are coherent English but not tasks,
    e.g. "nice weather today" or "committed breakout session".
    """
    words = set(re.findall(r"[a-zA-Z]{2,}", text.lower()))
    return bool(words & _ACTION_VERBS)


async def _self_heal_with_skill(ai: str, sess: dict, text: str, safe_text: str,
                                 source: str, sid: str, error_output: str) -> Optional[str]:
    """
    Self-healing skill generation: when an AI fails a task and no matching
    skill existed, invoke Claude to create a high-quality skill, then retry
    the original task with the new skill injected.

    Returns the successful retry output, or None if healing failed/skipped.
    """
    # Guard 1: skip self-healing for gibberish / incoherent input (e.g. bad
    # voice transcriptions).  Only create skills for real, actionable tasks.
    if not _is_coherent_task(text):
        logger.info("_self_heal_with_skill: input text appears incoherent — skipping "
                     "(text=%r)", text[:120])
        await push_message(
            "system",
            "🤔 I couldn't understand that request. Could you please repeat "
            "or rephrase what you'd like me to do?",
            source=source, session_id=sid,
        )
        return None

    # Guard 2: even if coherent, the message must contain a clear actionable
    # intent (a verb / command) before we spend Claude credits on skill
    # creation.  Phrases like "hello" or "nice weather" are coherent but
    # not tasks.
    if not _has_actionable_intent(text):
        logger.info("_self_heal_with_skill: no actionable intent detected — asking "
                     "user to clarify (text=%r)", text[:120])
        await push_message(
            "system",
            f"⚠️ {ai} wasn't able to complete this. I'm not sure what task "
            "you'd like me to do — could you describe it more clearly so I "
            "can help?",
            source=source, session_id=sid,
        )
        return None

    # Prevent infinite loops — only attempt once per prompt+ai combo
    heal_key = f"{hash(text[:200])}::{ai}"
    if heal_key in _heal_attempts:
        logger.info("_self_heal_with_skill: already attempted for this prompt+ai — skipping")
        return None
    _heal_attempts.add(heal_key)

    # Cap the set size to prevent memory leaks in long-running servers
    if len(_heal_attempts) > 500:
        _heal_attempts.clear()

    # Check that at least one other AI is available for skill generation
    _available_for_heal = _find_available_ais(ai)
    if not _available_for_heal and not shutil.which("claude"):
        await push_message(
            "system",
            f"⚠️ {ai} couldn't complete this task and no other AI is "
            f"available to generate a skill. Try retrying manually.",
            source=source, session_id=sid,
        )
        return None

    await push_message(
        "system",
        f"🔧 **Self-healing:** {ai} encountered an infrastructure error. "
        f"Generating a skill to help with this task…",
        source=source, session_id=sid,
    )

    # generate_skill tries Claude first, then falls back to any available AI
    skill_name = await asyncio.to_thread(
        generate_skill, text, ai, error_output
    )

    if not skill_name:
        _alt_msg = ""
        if _available_for_heal:
            _alt_names = ", ".join(f"**{a}**" for a in _available_for_heal[:3])
            _alt_msg = f" Available AIs you can switch to: {_alt_names}."
        await push_message(
            "system",
            f"⚠️ Could not auto-generate a skill for this task.{_alt_msg} "
            f"Try switching AI or retry manually.",
            source=source, session_id=sid,
        )
        return None

    await push_message(
        "system",
        f"✅ **New skill created:** `{skill_name}` — retrying your task with it…",
        source=source, session_id=sid,
    )

    # Retry: re-inject the newly created skill into the prompt
    enriched_text = inject_skill_prefix(safe_text, ai=ai, match_text=text)
    enriched_text = inject_plugin_context(enriched_text)

    if ai == "ollama":
        from .ollama import _run_ollama_agent
        # Reset ollama messages so skill gets injected into system prompt
        sess.pop("ollama_messages", None)
        await push_thinking(True, ai, session_id=sid)
        retry_output = await _run_ollama_agent(sess, safe_text, source, sid)
        await push_thinking(False, session_id=sid)
        if not _is_failure(retry_output):
            await push_message("assistant", retry_output, ai=ai, source=source, session_id=sid)
            return retry_output
    elif ai in _st.integrations:
        from helm.file_tracker import snapshot_dir, handle_diff
        cwd = sess["cwd"]
        integration = _st.integrations[ai]
        use_stdin = integration.get("stdin_prompt", False)
        cmd = integration["build_command"](enriched_text, model=sess.get("model"))
        await push_thinking(True, ai, session_id=sid)
        before = await asyncio.to_thread(snapshot_dir, cwd)
        retry_output = await asyncio.to_thread(
            run_ai_popen, cmd, cwd, ai, sess, INTEGRATION_TIMEOUT,
            stdin_text=enriched_text if use_stdin else None,
            extra_env=integration.get("process_env") or None,
        )
        after = await asyncio.to_thread(snapshot_dir, cwd)
        await push_thinking(False, session_id=sid)
        if not _is_failure(retry_output):
            await push_message("assistant", retry_output, ai=ai, source=source, session_id=sid)
            await handle_diff(before, after, source, cwd, session_id=sid)
            return retry_output

    # Retry also failed — return None to let normal error flow continue
    logger.info("_self_heal_with_skill: retry with skill '%s' also failed for ai=%s",
                skill_name, ai)
    return None


# ---------------------------------------------------------------------------
# Error Recovery — dispatch with retry + fallback AI switching
# ---------------------------------------------------------------------------

async def _run_single_ai(ai: str, sess: dict, text: str, safe_text: str,
                         cwd: str, terminal, source: str, sid: str,
                         snapshot_dir, handle_diff) -> str:
    """Execute a single AI dispatch attempt. Returns output string.

    Raises no exceptions — errors are returned as string output.
    """
    sess["last_task_cwd"] = cwd   # see mention_router: has the session moved folder since?
    # ── Tier 2 native computer-use runners ─────────────────────────────────
    # When COMPUTER_USE=true AND COMPUTER_USE_TIER2=true AND the selected
    # AI has its API key, bypass the CLI path entirely and use the
    # provider's direct API with vision + function calling. Screenshots
    # are attached inline after every action, so latency drops to ~1-3s
    # per turn vs 5-15s for the CLI path. Falls through to Tier 1 on error.
    try:
        from helm.computer_runners import should_use_tier2
        if should_use_tier2(ai):
            from helm.computer_runners.base import primary_display_size
            display_w, display_h = primary_display_size()
            await push_thinking(True, ai, session_id=sid)
            try:
                if ai == "claude":
                    from helm.computer_runners import claude_native
                    return await claude_native.run(
                        safe_text, cwd, sid, display_w, display_h,
                        model=sess.get("model"),
                    )
                if ai == "gemini":
                    from helm.computer_runners import gemini_native
                    return await gemini_native.run(
                        safe_text, cwd, sid, model=sess.get("model"),
                    )
                if ai in ("codex", "openai"):
                    from helm.computer_runners import openai_native
                    return await openai_native.run(
                        safe_text, cwd, sid, model=sess.get("model"),
                    )
            finally:
                await push_thinking(False, ai, session_id=sid)
    except Exception:
        logger.exception("Tier 2 computer runner failed; falling back to Tier 1")

    if ai == "claude":
        from .claude import run_claude
        return await run_claude(sess, text, safe_text, cwd, source, sid,
                                snapshot_dir, handle_diff)
    if ai == "ollama":
        from .ollama import run_ollama
        return await run_ollama(ai, sess, text, safe_text, source, sid)
    if ai in _st.integrations:
        from .cli_runner import run_cli_ai
        return await run_cli_ai(ai, sess, text, safe_text, cwd, source, sid,
                                snapshot_dir, handle_diff)

    # Shell mode — no retry/fallback for shell
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
    return output


async def _dispatch_with_recovery(ai: str, sess: dict, text: str, safe_text: str,
                                   cwd: str, terminal, source: str, sid: str,
                                   snapshot_dir, handle_diff) -> tuple[str, str]:
    """Dispatch with retry logic and automatic AI fallback.

    Returns (output, actual_ai_used).
    """
    from helm.acp_session import is_acp, run_turn as _acp_turn
    if is_acp(ai):
        # An ACP agent: its reply is the output; permission questions go to approvals.
        output = await _acp_turn(sess, safe_text, sid, sess.get("name", ai))
        await push_message("assistant", output, ai=ai, source=source, session_id=sid)
        return output, ai

    # Shell mode — no recovery needed
    if ai not in ("claude", "ollama") and ai not in _st.integrations:
        output = await _run_single_ai(
            ai, sess, text, safe_text, cwd, terminal, source, sid,
            snapshot_dir, handle_diff,
        )
        return output, ai

    # A look for your brief runs once, on the AI you picked: another AI has other
    # apps, and its answer (e.g. a PR about rate limits) can read like a CLI error.
    # helm/brief.py reports a run that didn't work as a problem instead.
    if sess.get("read_only"):
        output = await _run_single_ai(
            ai, sess, text, safe_text, cwd, terminal, source, sid,
            snapshot_dir, handle_diff,
        )
        return output, ai

    # ── Retry loop with the primary AI ──────────────────────────────────
    last_output = ""
    max_retries = _max_retries()
    for attempt in range(1, max_retries + 1):
        logger.info("AI dispatch attempt %d/%d for %s", attempt, max_retries, ai)
        last_output = await _run_single_ai(
            ai, sess, text, safe_text, cwd, terminal, source, sid,
            snapshot_dir, handle_diff,
        )

        if not _is_failure(last_output):
            # Success
            return last_output, ai

        # Failed — notify user of retry (unless last attempt)
        if attempt < max_retries:
            retry_msg = (
                f"⚠️ **{ai}** encountered an error (attempt {attempt}/{max_retries}). "
                f"Retrying in {int(RETRY_DELAY)}s…"
            )
            logger.warning("AI %s attempt %d failed: %s", ai, attempt,
                           last_output[:200].replace('\n', ' '))
            await push_message("system", retry_msg, source=source, session_id=sid)
            await asyncio.sleep(RETRY_DELAY)

    # ── All retries exhausted — find a fallback AI ──────────────────────
    logger.warning("AI %s failed all %d attempts. Searching for fallback…", ai, max_retries)

    # Check if auto-switch is enabled
    if not _auto_switch_enabled():
        fail_msg = (
            f"❌ **{ai}** failed after {max_retries} attempts. "
            f"Auto-switch is disabled in settings.\n\n"
            f"Last error:\n{last_output[:500]}"
        )
        await push_message("system", fail_msg, source=source, session_id=sid)
        await push_agent_error(fail_msg, session_id=sid, source=source)
        return last_output, ai

    fallback_list = await asyncio.to_thread(_find_available_ais, ai)

    if not fallback_list:
        # No fallback available — deliver the error as-is
        fail_msg = (
            f"❌ **{ai}** failed after {max_retries} attempts and no other AI is available.\n\n"
            f"Last error:\n{last_output[:500]}"
        )
        await push_message("system", fail_msg, source=source, session_id=sid)
        await push_agent_error(fail_msg, session_id=sid, source=source)
        return last_output, ai

    fallback_ai = fallback_list[0]  # pick the first available

    # Notify user about the switch
    switch_msg = (
        f"🔄 **{ai}** failed after {max_retries} attempts. "
        f"Automatically switching to **{fallback_ai}** to complete your task…"
    )
    await push_message("system", switch_msg, source=source, session_id=sid)
    logger.info("Switching from %s to fallback AI: %s", ai, fallback_ai)

    # Temporarily switch session AI for the fallback dispatch
    original_ai = sess["ai"]
    sess["ai"] = fallback_ai

    try:
        fallback_output = await _run_single_ai(
            fallback_ai, sess, text, safe_text, cwd, terminal, source, sid,
            snapshot_dir, handle_diff,
        )

        if _is_failure(fallback_output):
            # Fallback also failed — try remaining AIs
            for backup_ai in fallback_list[1:]:
                backup_msg = f"🔄 **{fallback_ai}** also failed. Trying **{backup_ai}**…"
                await push_message("system", backup_msg, source=source, session_id=sid)
                sess["ai"] = backup_ai
                fallback_output = await _run_single_ai(
                    backup_ai, sess, text, safe_text, cwd, terminal, source, sid,
                    snapshot_dir, handle_diff,
                )
                if not _is_failure(fallback_output):
                    # Notify about permanent switch
                    done_msg = (
                        f"✅ Task completed by **{backup_ai}** (original AI: {ai}). "
                        f"Session AI has been switched to **{backup_ai}**."
                    )
                    await push_message("system", done_msg, source=source, session_id=sid)
                    await push_state()
                    return fallback_output, backup_ai

            # ALL AIs failed
            sess["ai"] = original_ai  # restore original
            all_fail_msg = (
                f"❌ All available AIs failed. Last error from **{fallback_list[-1]}**:\n"
                f"{fallback_output[:500]}"
            )
            await push_message("system", all_fail_msg, source=source, session_id=sid)
            await push_agent_error(all_fail_msg, session_id=sid, source=source)
            await push_state()
            return fallback_output, fallback_list[-1]

        # Fallback succeeded
        done_msg = (
            f"✅ Task completed by **{fallback_ai}** (original AI: {ai}). "
            f"Session AI has been switched to **{fallback_ai}**."
        )
        await push_message("system", done_msg, source=source, session_id=sid)
        await push_state()
        return fallback_output, fallback_ai

    except Exception as exc:
        logger.error("Fallback AI %s raised exception: %s", fallback_ai, exc)
        sess["ai"] = original_ai  # restore original
        await push_state()
        error_msg = f"❌ Fallback to **{fallback_ai}** failed with error: {exc}"
        await push_message("system", error_msg, source=source, session_id=sid)
        await push_agent_error(error_msg, session_id=sid, source=source)
        return str(exc), ai
