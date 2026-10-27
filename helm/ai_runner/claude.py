"""
helm/ai_runner/claude.py — Claude-specific logic.

Covers: build_claude_cmd, parse_claude_json_output, and related utilities.
"""

import json
import os
import re


def build_claude_cmd(prompt: str, has_history: bool,
                     model: str | None = None,
                     auto_approve: bool = False,
                     mcp_config: str | None = None,
                     settings: str | None = None) -> list[str]:
    """Build the command-line arguments to invoke the Claude CLI.

    Uses --output-format json to get structured output including token counts.
    auto_approve: if True, adds --dangerously-skip-permissions so Claude
                  won't pause for file/command approvals (required for
                  non-interactive pipeline steps and background sessions).
    mcp_config:   path to a JSON file for --mcp-config (native MCP tool
                  calling — lets Claude connect to MCP servers directly
                  instead of going through the text-based agent loop).
    settings:     JSON for --settings: the hook that asks you before Claude
                  acts in a connected app (helm/outward.py).
    """
    cmd = ["claude"]
    if model:
        cmd.extend(["--model", model])
    if has_history:
        cmd.append("--continue")
    if auto_approve:
        # Override via CLAUDE_SKIP_PERMS_FLAG if Anthropic renames this flag.
        cmd.append(os.environ.get("CLAUDE_SKIP_PERMS_FLAG", "--dangerously-skip-permissions"))
    if mcp_config:
        cmd.extend(["--mcp-config", mcp_config])
    if settings:
        cmd.extend(["--settings", settings])
    cmd.extend(["--output-format", "json", "-p", prompt])
    return cmd


def parse_claude_json_output(raw: str) -> dict:
    """Parse Claude CLI JSON output to extract text and token counts.

    Claude CLI with --output-format json returns:
    {
      "type": "result",
      "result": "the text response",
      "cost_usd": 0.012,
      "duration_ms": 3500,
      "is_error": false,
      "num_turns": 1,
      "session_id": "...",
      "total_cost_usd": 0.05,
      "usage": {
        "input_tokens": 1234,
        "output_tokens": 567
      }
    }

    Returns dict with: text, input_tokens, output_tokens, cost_usd, is_json
    """
    if not raw or not raw.strip():
        return {"text": raw or "(no output)", "input_tokens": None,
                "output_tokens": None, "cost_usd": None, "is_json": False}

    text = raw.strip()

    # Try parsing as JSON
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON — might be plain text (older CLI version or error)
        # Try to find a JSON object containing "result"
        m = re.search(r'\{[^{}]*"result"[^{}]*\}', text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {"text": text, "input_tokens": None,
                        "output_tokens": None, "cost_usd": None, "is_json": False}
        else:
            return {"text": text, "input_tokens": None,
                    "output_tokens": None, "cost_usd": None, "is_json": False}

    if not isinstance(data, dict):
        return {"text": text, "input_tokens": None,
                "output_tokens": None, "cost_usd": None, "is_json": False}

    # Extract the response text
    result_text = data.get("result", "")
    if not result_text and data.get("is_error"):
        result_text = data.get("error", text)

    # Extract token counts
    usage = data.get("usage", {})
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")

    # Extract cost
    cost_usd = data.get("cost_usd")

    return {
        "text": result_text or "(no output)",
        "input_tokens": int(input_tokens) if input_tokens is not None else None,
        "output_tokens": int(output_tokens) if output_tokens is not None else None,
        "cost_usd": float(cost_usd) if cost_usd is not None else None,
        "is_json": True,
    }


_build_claude_cmd = build_claude_cmd  # legacy alias


async def run_claude(sess: dict, text: str, safe_text: str, cwd: str,
                     source: str, sid: str, snapshot_dir, handle_diff) -> str:
    """Run one message through Claude Code and show its answer. Returns the output."""
    import asyncio
    from helm.broadcast import push_message, push_thinking
    from helm.config import CLAUDE_TIMEOUT, logger
    from helm.mcp.inject import inject_mcp_context
    from helm.skill_creation import auto_create_skill_template
    from helm.skills import detect_skill
    from . import core
    from .core import _is_coherent_task, _is_failure
    from .prompt import enrich_prompt
    from .streaming import activity_emitter
    run_ai_popen = core.run_ai_popen   # looked up per call, so tests can stand in for it

    await push_thinking(True, "claude", session_id=sid)
    has_history = len(sess["claude_msgs"]) > 0
    # A read-only look (your brief) gets no skill guide: it should only look.
    enriched_text = enrich_prompt(safe_text, text, "claude", sess)

    sess["claude_msgs"].append(text)

    # ── Claude MCP strategy ────────────────────────────────────────────
    # Give Claude ALL tools — let it behave as it would natively.
    #
    # --mcp-config: subprocess MCP servers (direct protocol, unlimited)
    # Agent loop: tool descriptions in prompt (catches anything native misses)
    # CLI skills: bash commands injected via skill prefix
    #
    # All three layers active simultaneously. Claude decides what to use.
    # If it handles everything natively, agent loop exits immediately.
    #
    from helm.mcp import get_manager as _get_mcp_mgr
    from helm.builtin_tools import is_computer_use_enabled as _is_cu
    _mcp_mgr = _get_mcp_mgr()
    _has_mcp = _mcp_mgr and _mcp_mgr.has_running_servers()
    _computer_on = _is_cu()
    _needs_tools = bool(_has_mcp or _computer_on)
    _mcp_config_path = None
    _needs_agent_loop = False

    if _needs_tools:
        # Give Claude ALL tools — let it decide what to use.
        # Native MCP (--mcp-config) for subprocess servers,
        # agent loop (tool descriptions in prompt) as a safety net.
        # If Claude handles everything natively, the agent loop wrapper
        # sees no <tool_call> tags and exits immediately — zero overhead.
        if _has_mcp:
            _mcp_config_path = _mcp_mgr.export_claude_mcp_config(cwd)
            if _mcp_config_path:
                logger.info("Claude: native MCP via --mcp-config (%d subprocess servers)",
                            len(_mcp_mgr._get_subprocess_servers()))

        # Inject tool descriptions (covers MCP tools + computer_use tools).
        # inject_mcp_context decides what to include based on flags.
        enriched_text = inject_mcp_context(enriched_text, code_exec=False)
        logger.info(
            "Claude: tool layers active (mcp=%s, computer_use=%s)",
            _has_mcp, _computer_on,
        )

    # Ask before Claude acts in a connected app: RAPR's MCP servers, the ones
    # added to Claude Code and claude.ai connectors alike (helm/outward.py).
    from helm.outward import claude_hook_settings
    _gate_settings = claude_hook_settings(sid)

    # Build command — with native MCP if subprocess servers exist
    cmd = build_claude_cmd(
        enriched_text, has_history,
        model=sess.get("model"),
        auto_approve=True,
        mcp_config=_mcp_config_path,
        settings=_gate_settings,
    )

    # ── Live-progress helper (default OFF; RAPR_LIVE_PROGRESS=1) ──────────
    # Streams Claude stream-json step events to the UI for a live activity
    # timeline. The final answer always comes from the result event via the
    # unchanged parser, and any problem falls back to the normal blocking run.
    _emit = activity_emitter(sid, "claude")

    async def _claude_raw(_cmd):
        _dbg = "disabled"
        try:
            from helm.ai_runner.streaming import (
                live_progress_enabled, run_claude_stream, StreamUnavailable,
                mark_unavailable,
            )
            _lp = live_progress_enabled("claude")
            logger.info("claude: live_progress enabled=%s", _lp)
            if _lp:
                _to = CLAUDE_TIMEOUT if CLAUDE_TIMEOUT > 0 else None
                try:
                    return await asyncio.to_thread(
                        run_claude_stream, _cmd, cwd, sess, _emit, _to,
                    )
                except StreamUnavailable as _su:
                    if sess.pop("_user_killed", None):
                        logger.info("claude stream stopped by user — no fallback rerun")
                        return ""  # parse_claude_json_output handles empty
                    _dbg = f"stream unavailable: {_su}"
                    logger.info("live progress unavailable, using blocking run: %s", _su)
                    mark_unavailable(str(_su), "claude")
                except Exception as _e:
                    _dbg = f"stream error: {_e}"
                    logger.warning("live progress error, using blocking run: %s", _e)
                    mark_unavailable(str(_e), "claude")
            else:
                _dbg = "disabled (RAPR_LIVE_PROGRESS=0 or auto-disabled)"
        except Exception as _e2:
            _dbg = f"import failed: {_e2}"
            logger.warning("live progress disabled (import): %s", _e2)
        logger.info("claude: blocking run (%s)", _dbg)
        return await asyncio.to_thread(run_ai_popen, _cmd, cwd, "claude", sess)

    if _needs_tools:
        # Agent loop wrapper: watches for <tool_call> XML in output.
        # If Claude uses native MCP for everything, wrapper exits on
        # first iteration (no tool calls found) — no interference.
        from .agent_loop import run_with_tools

        async def _claude_run_fn(prompt: str) -> str:
            _cmd = build_claude_cmd(
                prompt, has_history,
                model=sess.get("model"),
                auto_approve=True,
                mcp_config=_mcp_config_path,
                settings=_gate_settings,
            )
            raw = await _claude_raw(_cmd)
            parsed = parse_claude_json_output(raw)
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
        # No MCP servers — pure Claude, no tool wrappers needed
        before = await asyncio.to_thread(snapshot_dir, cwd)
        raw_output = await _claude_raw(cmd)
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

    # Clean up temp MCP config
    if _mcp_config_path:
        try:
            os.remove(_mcp_config_path)
        except OSError:
            pass

    await push_thinking(False, session_id=sid)

    # If successful, broadcast and handle file diff
    if not _is_failure(output):
        await push_message("assistant", output, ai="claude", source=source, session_id=sid)
        await handle_diff(before, after, source, cwd, session_id=sid)
        if not detect_skill(text) and _is_coherent_task(text) and not sess.get("read_only"):
            asyncio.create_task(
                asyncio.to_thread(auto_create_skill_template, text, "claude", output)
            )
    return output
