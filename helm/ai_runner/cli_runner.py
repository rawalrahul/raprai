"""
helm/ai_runner/cli_runner.py — run a message through a command-line AI
(Codex, Gemini, Antigravity, OpenCode… everything in integrations/).
"""

import asyncio

import helm.state as _st
from helm.broadcast import push_message, push_thinking
from helm.config import INTEGRATION_TIMEOUT, logger
from helm.mcp.inject import inject_mcp_context
from helm.skills import auto_create_skill_template, detect_skill

from .helpers import _clean_output
from .prompt import enrich_prompt
from .streaming import activity_emitter


async def run_cli_ai(ai: str, sess: dict, text: str, safe_text: str, cwd: str,
                     source: str, sid: str, snapshot_dir, handle_diff) -> str:
    """Run one message through the command-line AI *ai* and show its answer."""
    from . import core
    from .core import (_MODEL_REJECTED_RE, _extract_tokens_from_cli_output, _is_coherent_task,
                       _is_failure, _self_heal_with_skill)
    run_ai_popen = core.run_ai_popen   # looked up per call, so tests can stand in for it

    await push_thinking(True, ai, session_id=sid)
    skill_matched = detect_skill(text)
    enriched_text = enrich_prompt(safe_text, text, ai, sess)

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

    # ── MCP tool strategy ──────────────────────────────────────────────
    #
    # Give the AI ALL tools and let it behave natively.
    #
    # CLIs with native MCP (Gemini, Codex) already have servers synced
    # to their config files.  We ALSO inject tool descriptions into the
    # prompt so the agent loop can catch anything native can't reach.
    # If the AI handles everything natively, the agent loop wrapper
    # exits on first iteration (no <tool_call> tags) — zero overhead.
    #
    # This way: CLI skill + native MCP + agent loop are ALL available.
    # The AI picks the best approach — we don't limit or choose for it.
    _NATIVE_MCP_AIS = {"gemini", "antigravity", "codex"}

    from helm.mcp import get_manager as _get_mcp_mgr2
    from helm.builtin_tools import is_computer_use_enabled as _is_cu2
    _mcp_mgr2 = _get_mcp_mgr2()
    _has_mcp2 = _mcp_mgr2 and _mcp_mgr2.has_running_servers()
    _computer_on2 = _is_cu2()
    _needs_tools2 = bool(_has_mcp2 or _computer_on2)

    # ── Live-progress helper for Codex/Gemini (default ON; RAPR_LIVE_PROGRESS=1) ──
    # Streams their JSONL step events to the UI and returns the final text. Any
    # problem falls back to the normal blocking run, so the reply is unchanged.
    _emit2 = activity_emitter(sid, ai)

    async def _integration_raw(_cmd, _stdin):
        out = await _integration_raw_once(_cmd, _stdin)
        # Codex refuses a model your sign-in can't use ("The 'gpt-…' model is not
        # supported when using Codex with a ChatGPT account"). Forget that model
        # and run once more on Codex's own default.
        if (ai == "codex" and sess.get("model") and "--model" in _cmd
                and _MODEL_REJECTED_RE.search(out or "")):
            bad = sess["model"]
            sess["model"] = None
            try:
                from helm.model_prefs import get_model_pref, set_model_pref
                if get_model_pref(ai) == bad:
                    set_model_pref(ai, None)
            except Exception:
                logger.debug("Couldn't forget the rejected model", exc_info=True)
            logger.info("codex rejected model %s; retrying with its default", bad)
            await push_message(
                "system",
                f"Codex can't use `{bad}` with your sign-in, so RAPR switched this "
                f"session to Codex's default model. Use /model to pick another.",
                source=source, session_id=sid)
            i = _cmd.index("--model")
            out = await _integration_raw_once(_cmd[:i] + _cmd[i + 2:], _stdin)
        return out

    async def _integration_raw_once(_cmd, _stdin):
        # Each CLI has its own stream-json reader. Any mismatch raises
        # StreamUnavailable and falls back to a blocking run.
        if ai in ("codex", "gemini", "antigravity"):
            try:
                from helm.ai_runner.streaming import (
                    live_progress_enabled, run_codex_stream, run_gemini_stream,
                    run_agy_stream, StreamUnavailable, mark_unavailable,
                )
                _lp = live_progress_enabled(ai)
                logger.info("%s: live_progress enabled=%s", ai, _lp)
                if _lp:
                    _fn = {"codex": run_codex_stream,
                           "antigravity": run_agy_stream}.get(ai, run_gemini_stream)
                    _to = INTEGRATION_TIMEOUT if INTEGRATION_TIMEOUT > 0 else None
                    try:
                        return await asyncio.to_thread(
                            _fn, _cmd, cwd, sess, _emit2, _stdin,
                            integration.get("process_env") or None, _to,
                        )
                    except StreamUnavailable as _su:
                        if sess.pop("_user_killed", None):
                            logger.info("%s stream stopped by user — no fallback rerun", ai)
                            return "(stopped)"
                        logger.info("live progress unavailable (%s): %s", ai, _su)
                        mark_unavailable(str(_su), ai)
                    except Exception as _e:
                        logger.warning("live progress error (%s): %s", ai, _e)
                        mark_unavailable(str(_e), ai)
            except Exception as _e2:
                logger.warning("live progress disabled (import): %s", _e2)
        return await asyncio.to_thread(
            run_ai_popen, _cmd, cwd, ai, sess, INTEGRATION_TIMEOUT,
            stdin_text=_stdin, extra_env=integration.get("process_env") or None,
        )

    if _needs_tools2:
        # Inject tool descriptions (MCP + computer_use). inject_mcp_context
        # itself decides what to include based on the flags.
        enriched_text = inject_mcp_context(enriched_text, code_exec=use_stdin)
        _cli_has_native_mcp = ai in _NATIVE_MCP_AIS
        logger.info(
            "%s: tool layers active (mcp=%s, computer_use=%s, native_mcp=%s)",
            ai, _has_mcp2, _computer_on2, _cli_has_native_mcp,
        )

        from .agent_loop import run_with_tools

        async def _integration_run_fn(prompt: str) -> str:
            cmd = integration["build_command"](prompt, model=sess.get("model"))
            out = await _integration_raw(cmd, prompt if use_stdin else None)
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
        # No MCP servers — pure CLI, no tool wrappers needed
        cmd    = integration["build_command"](enriched_text, model=sess.get("model"))
        before = await asyncio.to_thread(snapshot_dir, cwd)
        output = await _integration_raw(cmd, enriched_text if use_stdin else None)
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
    if ai == "gemini" and output and ("IneligibleTier" in output or ("410" in output and "Gone" in output)):
        # Google stopped the Gemini CLI for personal accounts in June 2026.
        output += ("\n\n⚠️ Google no longer serves the Gemini CLI for personal Google "
                   "accounts. Install Antigravity CLI (agy), Google's replacement, and "
                   "choose 🪐 Antigravity in RAPR. (A Gemini API key still works here.)")

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
        if not skill_matched and _is_coherent_task(text) and not sess.get("read_only"):
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
