"""
helm/ai_runner/slash_commands.py — the chat commands RAPR answers itself.

/pipeline, /model and /remember never reach an AI: process_message hands them
here first. Each function returns RAPR's reply, or None when the message isn't
its command.
"""

import asyncio
import os
from typing import Optional

import helm.state as _st
from helm.broadcast import push_message, push_state
from helm.config import logger


async def handle_pipeline(stripped: str, sess: dict, sid: str, source: str) -> Optional[str]:
    """/pipeline <task>: plan the task as steps for several AIs."""
    if not stripped.lower().startswith("/pipeline"):
        return None
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


async def handle(stripped: str, sess: dict, sid: str, source: str) -> Optional[str]:
    """/model and /remember."""
    if stripped.lower().startswith("/model"):
        return await _model(stripped, sess, sid, source)
    if stripped.lower().startswith("/remember"):
        return await _remember(stripped, sess, sid, source)
    return None


async def _model(stripped: str, sess: dict, sid: str, source: str) -> str:
    """/model: show the session's model and the ones available, or switch it."""
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

    # ── CLI agents with a --model flag: live model discovery + switch ───
    # Model lists are fetched live (CLI's own cache / OAuth creds / API key /
    # installed-bundle scan) — never hardcoded, since names change often.
    if ai_key in ("claude", "gemini", "codex", "antigravity"):
        if not arg or arg_lower in ("list", "ls", "show", "?"):
            current_model = sess.get("model") or "(CLI default)"
            try:
                from helm.web_routes.helpers import (
                    _fetch_claude_models,
                    _fetch_openai_models,
                    _fetch_gemini_models,
                    _fetch_antigravity_models,
                )
                _fetch_fn = {
                    "claude":      _fetch_claude_models,
                    "codex":       _fetch_openai_models,
                    "gemini":      _fetch_gemini_models,
                    "antigravity": _fetch_antigravity_models,
                }[ai_key]
                available = await asyncio.to_thread(_fetch_fn)
            except Exception:
                available = []
            if available:
                _shown = available[:30]
                hints = "\n".join(
                    f"  • `{m}`" + (" ✅" if m == sess.get("model") else "")
                    for m in _shown
                )
                if len(available) > len(_shown):
                    hints += f"\n  … and {len(available) - len(_shown)} more"
                hints_section = f"**Available models (fetched live):**\n{hints}"
            else:
                hints_section = (
                    "_Could not fetch a live model list. Make sure you are logged in "
                    f"(`{ai_key}` CLI) or have the API key set._\n\n"
                    f"You can still switch directly: `/model <name>` — any model id "
                    f"your account supports is passed straight to the CLI's `--model` flag."
                )
            msg = (
                f"**Current model:** `{current_model}`\n"
                f"**AI:** {ai_key.title()}\n\n"
                f"{hints_section}\n\n"
                f"To switch: `/model <name>` — To reset: `/model default`"
            )
            await push_message("system", msg, source=source, session_id=sid)
            return msg
        if arg_lower == "default":
            sess["model"] = None
            from helm.model_prefs import set_model_pref
            set_model_pref(ai_key, None)
            await push_state()
            msg = f"✅ Model reset to default for {ai_key.title()}."
            await push_message("system", msg, source=source, session_id=sid)
            return msg
        sess["model"] = arg
        from helm.model_prefs import set_model_pref
        set_model_pref(ai_key, arg)
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
            current_line = "**Current model:** (AI's built-in default)"

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
        from .ollama import installed_models
        _local = await asyncio.to_thread(installed_models)
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
        # If ollama list fails, don't block the switch.
        logger.debug("Couldn't check Ollama's installed models", exc_info=True)

    msg = f"✅ Model switched to `{arg}`."
    await push_message("system", msg, source=source, session_id=sid)
    return msg


async def _remember(stripped: str, sess: dict, sid: str, source: str) -> str:
    """/remember: save a memory every AI gets, or list them."""
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

    add_memory(
        content=content,
        category=category,
        source_ai=sess.get("ai", "unknown"),
        session_id=sid,
    )
    msg = f"🧠 Remembered: **[{category}]** {content}"
    await push_message("system", msg, source=source, session_id=sid)
    return msg
