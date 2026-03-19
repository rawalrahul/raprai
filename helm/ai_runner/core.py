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

import helm.state as _st
from helm.broadcast import push_message, push_state, push_thinking
from helm.config import CLAUDE_TIMEOUT, INTEGRATION_TIMEOUT, logger
from helm.history import save_cwd_to_log
from helm.session_mgr import focused_session, record_usage_task
from helm.skills import (
    inject_skill_prefix, detect_skill, auto_create_skill_template,
    claude_generate_skill,
)
from helm.plugins import inject_plugin_context
from helm.mcp.inject import inject_mcp_context
from helm.context_manager import update_token_count, check_and_compact

from .claude import build_claude_cmd, parse_claude_json_output
from .helpers import tg_progress_notify, _clean_output


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

# Patterns in AI output that indicate a failure worth retrying
_FAILURE_PATTERNS = re.compile(
    r"(?i)("
    r"error:.*not found in PATH"
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
    r"|\(error:"
    r"|could not connect"
    r"|network.?error"
    r"|api.?key.*(missing|invalid|not set)"
    r"|OPENAI_API_KEY"
    r"|GEMINI_API_KEY"
    r"|exited [1-9]"
    r")"
)

# Built-in AI keys (always available if CLI is installed)
_BUILTIN_AIS = ["claude", "ollama"]


def _is_failure(output: str) -> bool:
    """Check if AI output indicates a recoverable failure."""
    if not output or output == "(no output)":
        return False
    return bool(_FAILURE_PATTERNS.search(output))


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

    # Check registered integration CLIs
    for ai_key, info in _st.integrations.items():
        if ai_key == exclude:
            continue
        # Integration build_command returns a list; the first element is the CLI name
        try:
            test_cmd = info["build_command"]("test", model=None)
            cli_name = test_cmd[0] if test_cmd else ai_key
            if shutil.which(cli_name):
                available.append(ai_key)
        except Exception:
            pass  # skip broken integrations

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
_SAFETY_PREAMBLE = (
    "\n[SAFETY RULE — FILE DELETION]\n"
    "You MUST NEVER delete, remove, or overwrite any file or directory without "
    "explicitly asking the user for permission first and receiving confirmation. "
    "This applies to ALL destructive operations: rm, del, rmdir, shutil.rmtree, "
    "os.remove, os.unlink, pathlib.Path.unlink, rimraf, Remove-Item, etc. "
    "Always list the exact files/folders you intend to delete and wait for the "
    "user to say 'yes' before proceeding. If in doubt, DO NOT delete.\n\n"
)

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
            )
        except Exception:
            logger.warning("Could not pre-install %s — skills may install it on demand", pkg)

from helm.paths import is_bundled as _is_bundled
if not _is_bundled():
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

    # ── /pipeline slash command — task decomposition ─────────────────────────
    stripped = text.strip()
    if stripped.lower().startswith("/pipeline"):
        parts_cmd = stripped.split(None, 1)
        pipeline_prompt = parts_cmd[1].strip() if len(parts_cmd) == 2 else ""
        if not pipeline_prompt:
            msg = (
                "📋 **Pipeline Mode** — Decompose complex tasks into subtasks "
                "assigned to different AIs.\n\n"
                "Usage: `/pipeline <your complex task>`\n\n"
                "Example: `/pipeline Research competitor pricing, create a comparison "
                "spreadsheet, write a summary report, and generate a presentation`"
            )
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        planner_ai = os.environ.get("PIPELINE_PLANNER_AI", "claude")
        pipeline_cwd = sess.get("cwd") or _st.last_cwd or "."
        await push_message(
            "system",
            f"🧠 Planning pipeline via **{planner_ai}**…",
            source=source, session_id=sid,
        )

        try:
            from helm.pipeline.planner import plan_pipeline as _plan_pipeline
            pipeline = await _plan_pipeline(
                prompt=pipeline_prompt,
                session_id=sid,
                cwd=pipeline_cwd,
                planner_ai=planner_ai,
            )
            _st.pipelines[pipeline["id"]] = pipeline

            from helm.pipeline.executor import broadcast_pipeline_update
            await broadcast_pipeline_update(pipeline)

            # Build a readable summary for chat
            step_lines = []
            for i, s in enumerate(pipeline["steps"], 1):
                deps = ""
                if s["depends_on"]:
                    deps = f" (after {', '.join(s['depends_on'])})"
                step_lines.append(
                    f"  {i}. **{s['title']}** → {s['assigned_ai']}{deps}"
                )
            steps_text = "\n".join(step_lines)

            msg = (
                f"📋 **Pipeline plan ready** — {len(pipeline['steps'])} steps\n\n"
                f"{steps_text}\n\n"
                f"Review the pipeline graph above. Click **Execute** to start, "
                f"or edit AI assignments before running."
            )
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        except Exception as pipe_err:
            logger.error("Pipeline planning failed: %s", pipe_err, exc_info=True)
            err_msg = (
                f"❌ **Pipeline planning failed**\n\n"
                f"**Planner AI:** {planner_ai}\n"
                f"**Error:** `{str(pipe_err)[:300]}`\n\n"
                f"Possible fixes:\n"
                f"• Check that **{planner_ai}** is installed and running\n"
                f"• Try a different planner AI in Settings → Pipeline → Planner AI\n"
                f"• Run the task directly (without `/pipeline`) with the current AI"
            )
            await push_message("system", err_msg, source=source, session_id=sid)
            return err_msg

    # ── Auto-suggest pipeline for complex tasks ───────────────────────────
    if os.environ.get("PIPELINE_AUTO_SUGGEST", "1") == "1":
        from helm.pipeline.planner import looks_complex
        if looks_complex(stripped) and not (sess or {}).get("pipeline_id"):
            await push_message(
                "system",
                "💡 This looks like a complex multi-step task. Want me to break it "
                "into a pipeline with different AIs handling each part?\n\n"
                "Type `/pipeline` followed by your task to decompose it, "
                "or just press Enter to run it directly with the current AI.",
                source=source, session_id=sid,
            )

    # ── /model slash command — handled before routing to any AI ──────────────
    if stripped.lower().startswith("/model"):
        from helm.web_routes.helpers import _fetch_ollama_models
        parts_cmd = stripped.split(None, 1)
        arg = parts_cmd[1].strip() if len(parts_cmd) == 2 else ""
        arg_lower = arg.lower()
        ai_key = sess.get("ai") or "shell"

        # ── Shell / OpenAI: model switching not supported ──────
        if ai_key in ("shell", "openai"):
            msg = (
                f"ℹ️ **Model switching is not available for {ai_key.title()}.**\n\n"
                f"{ai_key.title()} does not support model switching via CLI."
            )
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        # ── Claude / Gemini / Codex: support --model flag ──────
        if ai_key in ("claude", "gemini", "codex"):
            if not arg or arg_lower in ("list", "ls", "show", "?"):
                current_model = sess.get("model") or "(default)"
                _model_hints = {
                    "claude": "claude-sonnet-4-20250514, claude-opus-4-20250514, claude-haiku-3-5-20241022",
                    "gemini": "gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash",
                    "codex": "o4-mini, o3, gpt-4.1",
                }
                hints = _model_hints.get(ai_key, "")
                msg = (
                    f"**Current model:** `{current_model}`\n"
                    f"**AI:** {ai_key.title()}\n\n"
                    f"**Available models:** {hints}\n\n"
                    f"To switch: `/model <name>` — To reset: `/model default`"
                )
                await push_message("system", msg, source=source, session_id=sid)
                return msg
            if arg_lower == "default":
                sess["model"] = None
                await push_state()
                msg = f"✅ Model reset to default for {ai_key.title()}."
                await push_message("system", msg, source=source, session_id=sid)
                return msg
            sess["model"] = arg
            await push_state()
            msg = f"✅ {ai_key.title()} model switched to `{arg}`."
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        # ── /model  or  /model list  → show status (Ollama only) ────────────
        if not arg or arg_lower in ("list", "ls", "show", "?"):
            current_model = sess.get("model") or None

            # Fetch available Ollama models
            try:
                available = await asyncio.to_thread(_fetch_ollama_models)
            except Exception:
                available = []

            default_model = _st.default_models.get(ai_key, "")
            if current_model:
                current_line = f"**Current model:** `{current_model}`"
            elif default_model:
                current_line = f"**Current model:** `{default_model}` (configured default)"
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
                    "\n\n_Could not fetch model list — is Ollama running?_ "
                    "_Start it with `ollama serve` and make sure you have at least "
                    "one model pulled (e.g. `ollama pull qwen2.5-coder:7b`)._"
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

        # ── /model <name>  → switch to named model (Ollama) ─────────────────
        sess["model"] = arg
        await push_state()

        # Warn if the requested model isn't installed locally
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

    # ── /remember slash command — save a memory ──────────────────────────────
    if stripped.lower().startswith("/remember"):
        from helm.memory import add_memory, list_memories, VALID_CATEGORIES

        arg = stripped[9:].strip()

        if not arg or arg.lower() == "list":
            # List memories
            mems = list_memories(limit=20)
            if not mems:
                msg = "🧠 No memories saved yet. Use `/remember <fact>` to add one."
            else:
                lines = ["🧠 **Shared AI Memory** (%d entries):\n" % len(mems)]
                for m in mems:
                    pin = "📌 " if m.get("pinned") else ""
                    lines.append(f"  {pin}**[{m['category']}]** {m['content']}")
                msg = "\n".join(lines)
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        if arg.lower() == "help":
            msg = (
                "🧠 **Memory Commands:**\n"
                "  `/remember <fact>` — save a memory\n"
                "  `/remember [category] <fact>` — save with category\n"
                "  `/remember list` — show all memories\n\n"
                f"Categories: {', '.join(sorted(VALID_CATEGORIES))}"
            )
            await push_message("system", msg, source=source, session_id=sid)
            return msg

        # Check if first word is a category
        words = arg.split(None, 1)
        category = "fact"
        content = arg
        if len(words) >= 2 and words[0].lower().rstrip(":") in VALID_CATEGORIES:
            category = words[0].lower().rstrip(":")
            content = words[1]

        mid = add_memory(
            content=content,
            category=category,
            source_ai=ai,
            session_id=sid,
        )
        msg = f"🧠 Remembered: **[{category}]** {content}"
        await push_message("system", msg, source=source, session_id=sid)
        return msg
    # ── end /remember ────────────────────────────────────────────────────────

    task_started_at = time.time()
    sess["last_used"] = task_started_at
    sess["busy"]       = True
    sess["task_start"] = task_started_at
    await push_state()  # immediately reflect busy status on web UI and Telegram

    ai       = sess["ai"]
    cwd      = sess["cwd"]
    terminal = sess["terminal"]

    await push_message("user", text, ai=None, source=source, session_id=sid)

    # Inject file-deletion safety preamble into every AI prompt
    safe_text = _SAFETY_PREAMBLE + text

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
        await push_state()  # flip session back to idle
        await tg_progress_notify(sess, output, elapsed, source, prompt_text=text)

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

    await push_message(
        "system",
        f"🔧 **Self-healing:** {ai} couldn't complete this task. "
        f"Asking Claude to create a skill for it…",
        source=source, session_id=sid,
    )

    # Invoke Claude in a background thread to generate the skill
    skill_name = await asyncio.to_thread(
        claude_generate_skill, text, ai, error_output
    )

    if not skill_name:
        await push_message(
            "system",
            "⚠️ Could not auto-generate a skill (Claude CLI unavailable or timed out). "
            "Try switching to Claude or retry manually.",
            source=source, session_id=sid,
        )
        return None

    await push_message(
        "system",
        f"✅ **New skill created:** `{skill_name}` — retrying your task with it…",
        source=source, session_id=sid,
    )

    # Retry: re-inject the newly created skill into the prompt
    enriched_text = inject_skill_prefix(safe_text, ai=ai)
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
    if ai == "claude":
        await push_thinking(True, "claude", session_id=sid)
        has_history = len(sess["claude_msgs"]) > 0
        enriched_text = inject_skill_prefix(safe_text, ai="claude")
        enriched_text = inject_plugin_context(enriched_text)

        # Inject shared AI memory into prompt
        try:
            from helm.memory import get_memory_block
            _mem = get_memory_block(prompt=safe_text)
            if _mem:
                enriched_text = _mem + enriched_text
        except Exception:
            pass

        sess["claude_msgs"].append(text)

        # Check if MCP tools are available — use agent loop if so
        from helm.mcp import get_manager as _get_mcp_mgr
        _mcp_mgr = _get_mcp_mgr()
        _has_mcp = _mcp_mgr and _mcp_mgr.has_running_servers()

        if _has_mcp:
            # Inject MCP context ONLY when agent loop will process tool calls
            enriched_text = inject_mcp_context(enriched_text, code_exec=False)
            logger.info("Claude: MCP context injected, agent loop enabled (%d servers)",
                        len(_mcp_mgr.list_servers()))

            # Agent loop: AI can call MCP tools via <tool_call> tags
            from .agent_loop import run_with_tools

            async def _claude_run_fn(prompt: str) -> str:
                cmd = build_claude_cmd(
                    prompt, has_history,
                    model=sess.get("model"),
                    auto_approve=True,
                )
                raw = await asyncio.to_thread(run_ai_popen, cmd, cwd, "claude", sess)
                parsed = parse_claude_json_output(raw)
                # Track tokens from latest call
                if parsed.get("input_tokens") is not None or parsed.get("output_tokens") is not None:
                    sess["_last_tokens"] = {
                        "input": parsed.get("input_tokens", 0),
                        "output": parsed.get("output_tokens", 0),
                    }
                    if parsed.get("cost_usd") is not None:
                        sess["_last_cost_usd"] = parsed["cost_usd"]
                return parsed["text"]

            before = await asyncio.to_thread(snapshot_dir, cwd)
            output = await run_with_tools(
                run_fn=_claude_run_fn,
                initial_prompt=enriched_text,
                cwd=cwd,
                session_id=sid,
                source=source,
            )
            after = await asyncio.to_thread(snapshot_dir, cwd)
        else:
            # Single-turn: no MCP tools available
            cmd = build_claude_cmd(
                enriched_text, has_history,
                model=sess.get("model"),
                auto_approve=True,
            )
            before = await asyncio.to_thread(snapshot_dir, cwd)
            raw_output = await asyncio.to_thread(run_ai_popen, cmd, cwd, "claude", sess)
            after  = await asyncio.to_thread(snapshot_dir, cwd)

            parsed = parse_claude_json_output(raw_output)
            output = parsed["text"]
            if parsed.get("input_tokens") is not None or parsed.get("output_tokens") is not None:
                sess["_last_tokens"] = {
                    "input": parsed.get("input_tokens", 0),
                    "output": parsed.get("output_tokens", 0),
                }
                if parsed.get("cost_usd") is not None:
                    sess["_last_cost_usd"] = parsed["cost_usd"]
                logger.info("Claude tokens: %s in + %s out, cost=$%s",
                            parsed.get("input_tokens"), parsed.get("output_tokens"),
                            parsed.get("cost_usd"))

        await push_thinking(False, session_id=sid)

        # If successful, broadcast and handle file diff
        if not _is_failure(output):
            await push_message("assistant", output, ai="claude", source=source, session_id=sid)
            await handle_diff(before, after, source, cwd, session_id=sid)
            if not detect_skill(text) and _is_coherent_task(text):
                asyncio.create_task(
                    asyncio.to_thread(auto_create_skill_template, text, "claude", output)
                )
        return output

    elif ai == "ollama":
        from .ollama import _run_ollama_agent
        await push_thinking(True, ai, session_id=sid)
        skill_matched = detect_skill(text)
        output = await _run_ollama_agent(sess, safe_text, source, sid)
        await push_thinking(False, session_id=sid)
        if not _is_failure(output):
            await push_message("assistant", output, ai=ai, source=source, session_id=sid)
            if not skill_matched and _is_coherent_task(text):
                asyncio.create_task(
                    asyncio.to_thread(auto_create_skill_template, text, "ollama", output)
                )
        else:
            # Clear conversation history after a failed turn so the next
            # request starts fresh — stale error context confuses the model.
            sess.pop("ollama_messages", None)
            # Self-healing: AI failed and no skill existed → ask Claude to create one
            if not skill_matched:
                healed = await _self_heal_with_skill(ai, sess, text, safe_text,
                                                     source, sid, output)
                if healed:
                    return healed
        return output

    elif ai in _st.integrations:
        await push_thinking(True, ai, session_id=sid)
        skill_matched = detect_skill(text)
        enriched_text = inject_skill_prefix(safe_text, ai=ai)
        enriched_text = inject_plugin_context(enriched_text)

        # Inject shared AI memory into prompt
        try:
            from helm.memory import get_memory_block
            _mem = get_memory_block(prompt=safe_text)
            if _mem:
                enriched_text = _mem + enriched_text
        except Exception:
            pass

        integration = _st.integrations[ai]
        use_stdin   = integration.get("stdin_prompt", False)

        # Pseudo-history for single-turn AIs: inject prior exchanges as context
        _hist = sess.get("_integration_history", [])
        if _hist:
            hist_block = "[Prior conversation in this session]\n"
            # Keep last 3 exchanges to avoid prompt bloat
            for h in _hist[-3:]:
                hist_block += f"User: {h['q'][:200]}\nAssistant: {h['a'][:300]}\n\n"
            hist_block += "[Current request]\n"
            enriched_text = hist_block + enriched_text

        # Check if MCP tools are available — use agent loop if so
        from helm.mcp import get_manager as _get_mcp_mgr2
        _mcp_mgr2 = _get_mcp_mgr2()
        _has_mcp2 = _mcp_mgr2 and _mcp_mgr2.has_running_servers()

        if _has_mcp2:
            # Inject MCP context ONLY when agent loop will process tool calls
            # Code-executing AIs (Codex, Gemini) get HTTP API instructions
            enriched_text = inject_mcp_context(enriched_text, code_exec=use_stdin)
            logger.info("%s: MCP context injected (code_exec=%s), agent loop enabled", ai, use_stdin)

            from .agent_loop import run_with_tools

            async def _integration_run_fn(prompt: str) -> str:
                cmd = integration["build_command"](prompt, model=sess.get("model"))
                out = await asyncio.to_thread(
                    run_ai_popen, cmd, cwd, ai, sess, INTEGRATION_TIMEOUT,
                    stdin_text=prompt if use_stdin else None,
                )
                cli_tokens = _extract_tokens_from_cli_output(out)
                if cli_tokens:
                    sess["_last_tokens"] = cli_tokens
                return out

            before = await asyncio.to_thread(snapshot_dir, cwd)
            output = await run_with_tools(
                run_fn=_integration_run_fn,
                initial_prompt=enriched_text,
                cwd=cwd,
                session_id=sid,
                source=source,
            )
            after = await asyncio.to_thread(snapshot_dir, cwd)
        else:
            cmd    = integration["build_command"](enriched_text, model=sess.get("model"))
            before = await asyncio.to_thread(snapshot_dir, cwd)
            output = await asyncio.to_thread(
                run_ai_popen, cmd, cwd, ai, sess, INTEGRATION_TIMEOUT,
                stdin_text=enriched_text if use_stdin else None,
            )
            after  = await asyncio.to_thread(snapshot_dir, cwd)

            # Try to extract token counts from CLI output (Gemini, Codex, etc.)
            cli_tokens = _extract_tokens_from_cli_output(output)
            if cli_tokens:
                sess["_last_tokens"] = cli_tokens
                logger.info("%s tokens (parsed from CLI): %d in + %d out",
                            ai, cli_tokens["input"], cli_tokens["output"])

        await push_thinking(False, session_id=sid)

        # Clean stderr noise (Node.js warnings etc.) from integration output
        output = _clean_output(output) or output

        if not _is_failure(output):
            await push_message("assistant", output, ai=ai, source=source, session_id=sid)
            await handle_diff(before, after, source, cwd, session_id=sid)
            # Store exchange in pseudo-history for single-turn AIs
            if "_integration_history" not in sess:
                sess["_integration_history"] = []
            sess["_integration_history"].append({
                "q": text[:500],
                "a": output[:500],
            })
            # Cap history at 10 exchanges
            if len(sess["_integration_history"]) > 10:
                sess["_integration_history"] = sess["_integration_history"][-10:]
            if not skill_matched and _is_coherent_task(text):
                asyncio.create_task(
                    asyncio.to_thread(auto_create_skill_template, text, ai, output)
                )
        else:
            # Self-healing: AI failed and no skill existed → ask Claude to create one
            if not skill_matched:
                # Enrich error context with model info for better skill generation
                model = sess.get("model", "default")
                enriched_error = f"[AI: {ai}, Model: {model}]\n{output}"
                healed = await _self_heal_with_skill(ai, sess, text, safe_text,
                                                     source, sid, enriched_error)
                if healed:
                    return healed
        return output

    else:
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
    # Shell mode — no recovery needed
    if ai not in ("claude", "ollama") and ai not in _st.integrations:
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
        return last_output, ai

    fallback_list = await asyncio.to_thread(_find_available_ais, ai)

    if not fallback_list:
        # No fallback available — deliver the error as-is
        fail_msg = (
            f"❌ **{ai}** failed after {max_retries} attempts and no other AI is available.\n\n"
            f"Last error:\n{last_output[:500]}"
        )
        await push_message("system", fail_msg, source=source, session_id=sid)
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
        return str(exc), ai
