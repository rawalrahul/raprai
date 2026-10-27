"""
helm/telegram_bot/text.py — Plain text sent to the bot: routes it to a command or the focused session.
"""

import asyncio
import os

import helm.state as _st
from helm.config import logger

from .auth import authorized_only, tg_send_chunks
from .keyboards import sessions_keyboard, session_controls_keyboard, new_session_keyboard
from .commands import tg_claude, tg_cwd, tg_interrupt, tg_launch, tg_menu, tg_status, tg_stop
from .history import perform_resume, tg_history


@authorized_only
async def tg_text(update, context):
    """Forward plain text — with natural language shortcut detection."""
    from helm.session_mgr import focused_session, make_session, session_cwd
    from helm.ai_runner import process_message
    from helm.broadcast import push_state

    text = (update.message.text or "").strip()
    low = text.lower()

    # --- In a group chat: the message goes to the whole group ---
    from .groups import handle_group_text
    if await handle_group_text(update, text):
        return

    # --- "@codex …": start that AI, or bring it into a group with the open session ---
    # --- "Hey Kelvin …": Auto picks the AI (or the one named right after) ---
    from helm.mention_router import parse_kelvin, parse_leading
    if parse_leading(text) or parse_kelvin(text) is not None:
        async def _tg_mention(_text: str = text, _update=update) -> None:
            from helm.mention_router import route
            try:
                reply = await route(_text, "telegram")
                if reply is None:
                    reply = await process_message(_text, source="telegram")
                await tg_send_chunks(_update, reply, reply_markup=session_controls_keyboard())
            except Exception as exc:
                logger.warning("tg mention error: %s", exc)
                await _update.message.reply_text(f"⚠️ Error: {exc}")
        asyncio.create_task(_tg_mention())
        return

    # --- Natural language shortcuts ---
    if low in ("menu", "help", "options", "?"):
        await tg_menu.__wrapped__(update, context)
        return
    if low in ("sessions", "list sessions", "show sessions"):
        await tg_status.__wrapped__(update, context)
        return
    if low in ("stop", "quit", "kill", "exit session"):
        await tg_stop.__wrapped__(update, context)
        return
    if low in ("interrupt", "cancel", "ctrl+c", "ctrl c"):
        await tg_interrupt.__wrapped__(update, context)
        return
    if low in ("history", "show history", "past sessions"):
        await tg_history.__wrapped__(update, context)
        return
    if low in ("resume", "continue", "load context"):
        await perform_resume(update.message, date_str="")
        return
    if low in ("status", "session status"):
        await tg_status.__wrapped__(update, context)
        return
    if low in ("folder", "cwd", "directory", "show folder"):
        await tg_cwd.__wrapped__(update, context)
        return
    if low in ("new session", "create session", "new claude", "start claude", "use claude",
               "claude code"):
        await tg_claude.__wrapped__(update, context)
        return
    # Dynamic NL shortcuts for all loaded integrations
    for _ikey, _iinfo in _st.integrations.items():
        _n = _ikey.lower()
        if any(low.startswith(p) for p in (f"new {_n}", f"start {_n}", f"use {_n}",
                                            f"switch to {_n}")):
            if _ikey in _st.integrations:
                sess = make_session(_ikey, cwd=session_cwd())
                _st.focused_id = sess["id"]
                await push_state()
                await update.message.reply_text(
                    f"✨ *{sess['name']}* created.\nJust type your task.",
                    parse_mode="Markdown",
                    reply_markup=session_controls_keyboard(),
                )
                return
    if low in ("shell", "shell mode", "new shell"):
        await tg_launch.__wrapped__(update, context)
        return

    # --- No focused session -> show session list / new session picker ---
    if not _st.focused_id or _st.focused_id not in _st.sessions:
        if _st.sessions:
            await update.message.reply_text(
                "👋 Tap a session to focus it, or create a new one:",
                reply_markup=sessions_keyboard(),
            )
        else:
            await update.message.reply_text(
                "👋 No sessions yet. Create your first one:",
                reply_markup=new_session_keyboard(),
            )
        return

    sess = _st.sessions.get(_st.focused_id)
    if sess and sess["status"] == "stopped":
        await update.message.reply_text(
            f"✨ *{sess['name']}* is stopped. Resume it or switch session:",
            parse_mode="Markdown",
            reply_markup=sessions_keyboard(),
        )
        return

    try:
        from helm.agent.nodes.input_node import resume_run_for_session
        if resume_run_for_session(sess.get("id"), text):
            await update.message.reply_text(
                "Input received. Continuing the agent workflow...",
                reply_markup=session_controls_keyboard(),
            )
            return
    except Exception as exc:
        logger.warning("Could not resume agent input from Telegram text: %s", exc)

    # --- Auto-pipeline detection for complex tasks ---
    pipeline_auto = os.environ.get("PIPELINE_AUTO_SUGGEST", "true").lower()
    if pipeline_auto == "true" and len(text) > 100:
        try:
            from helm.pipeline.planner import looks_complex
            if looks_complex(text):
                # Auto-invoke pipeline instead of sending to a single AI
                from helm.pipeline.planner import plan_pipeline
                from helm.pipeline.executor import broadcast_pipeline_update
                from .keyboards import pipeline_approval_keyboard

                fs = focused_session()
                cwd = fs["cwd"] if fs else session_cwd()
                sid = fs["id"] if fs else None
                planner_ai = os.environ.get("PIPELINE_PLANNER_AI", "claude")

                await update.message.reply_text(
                    "🔀 This looks like a complex multi-step task. "
                    "Automatically creating a pipeline plan…"
                )

                pipeline = await plan_pipeline(
                    prompt=text, session_id=sid, cwd=cwd, planner_ai=planner_ai,
                )
                _st.pipelines[pipeline["id"]] = pipeline
                await broadcast_pipeline_update(pipeline)

                # Show plan for approval
                lines = [f"🔀 *Pipeline Plan* (`{pipeline['id'][:8]}`)\n"]
                est_cost = pipeline.get("estimated_total_cost", 0)
                if est_cost > 0:
                    lines[0] += f"💰 Est. cost: ${est_cost:.4f}\n"
                for i, step in enumerate(pipeline["steps"], 1):
                    deps = ""
                    if step["depends_on"]:
                        deps = f" ← after {', '.join(step['depends_on'])}"
                    cost_hint = ""
                    if step.get("estimated_cost_usd", 0) > 0:
                        cost_hint = f" (~${step['estimated_cost_usd']:.4f})"
                    fb = ""
                    if step.get("fallback_ais"):
                        fb = f" [fallback: {','.join(step['fallback_ais'])}]"
                    lines.append(
                        f"*{i}. {step['title']}*\n"
                        f"  🤖 {step['assigned_ai']}{cost_hint}{fb}{deps}\n"
                        f"  _{step['description'][:80]}{'…' if len(step['description']) > 80 else ''}_"
                    )

                await update.message.reply_text(
                    "\n\n".join(lines),
                    parse_mode="Markdown",
                    reply_markup=pipeline_approval_keyboard(pipeline["id"]),
                )
                return
        except Exception as exc:
            logger.error("Auto-pipeline detection failed: %s", exc, exc_info=True)
            await update.message.reply_text(
                f"⚠️ Pipeline planning failed: `{str(exc)[:150]}`\n"
                f"Falling back to direct AI execution.",
                parse_mode="Markdown",
            )

    # --- Focused session is active -> forward message ---
    if _st.pending_tg_context:
        text = _st.pending_tg_context + text
        _st.pending_tg_context = None
        await update.message.reply_text("📌 Context injected. Thinking...")
    else:
        fs = focused_session()
        label = f"{fs['emoji']} {fs['name']}" if fs else "session"
        await update.message.reply_text(f"Thinking... [{label}]")

    async def _tg_fire(
        _text: str = text,
        _update = update,
    ) -> None:
        try:
            response = await process_message(_text, source="telegram")
            await tg_send_chunks(_update, response,
                                  reply_markup=session_controls_keyboard())
        except Exception as exc:
            logger.warning("tg_fire error: %s", exc)
            try:
                await _update.message.reply_text(
                    f"⚠️ Error: {exc}",
                    reply_markup=session_controls_keyboard(),
                )
            except Exception:
                logger.debug("Couldn't send the error to Telegram", exc_info=True)

    asyncio.create_task(_tg_fire())
