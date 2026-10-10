"""
helm/telegram_bot/callbacks.py — Inline keyboard callback routing.

Covers: action_callback, browse_callback (callback routing for inline keyboards).
"""

import asyncio
import pathlib
from typing import Optional

import helm.state as _st
from helm.config import ALLOWED_USER_IDS, HISTORY_ID_RE

from .keyboards import (
    sessions_keyboard, session_controls_keyboard, new_session_keyboard,
)
from .browse import show_browse
from .commands import perform_resume

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
except ImportError:
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None


async def action_callback(update, context):
    """Handle all ms:* and action:* inline keyboard button presses."""
    from helm.session_mgr import focused_session, make_session, session_cwd, usage_summary_text
    from helm.ai_runner import kill_session_proc, change_cwd
    from helm.file_tracker import emit_session_end_summary
    from helm.broadcast import push_message, push_state
    from helm.history import get_session_display_name
    from helm.terminal import TerminalSession

    query = update.callback_query
    user_id = query.from_user.id
    if not ALLOWED_USER_IDS or user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()

    data = query.data  # e.g. "ms:focus:s1", "ms:new_ai:claude:", "action:history"

    # --- ms: multi-session actions ---
    if data.startswith("ms:"):
        parts = data.split(":")
        verb  = parts[1] if len(parts) > 1 else ""

        if verb == "list":
            txt = "📋 *Sessions* — tap to focus:" if _st.sessions else "No sessions yet."
            await query.edit_message_text(txt, parse_mode="Markdown",
                                          reply_markup=sessions_keyboard())

        elif verb == "usage":
            fs = focused_session()
            await query.edit_message_text(
                usage_summary_text(),
                reply_markup=session_controls_keyboard() if fs else sessions_keyboard(),
            )

        elif verb == "new":
            await query.edit_message_text("Choose AI for new session:",
                                          reply_markup=new_session_keyboard())

        elif verb == "new_ai":
            # ms:new_ai:{ai}:{resume_sid}
            ai_key     = parts[2] if len(parts) > 2 else "shell"
            resume_sid = parts[3] if len(parts) > 3 else ""
            if ai_key == "shell":
                ai_key = None
            if resume_sid and resume_sid in _st.sessions:
                # Resume a stopped session with a (possibly different) AI
                sess = _st.sessions[resume_sid]
                sess["ai"]     = ai_key
                sess["status"] = "running"
                sess["claude_msgs"] = []
                if ai_key == "claude":
                    sess["emoji"] = "🤖"; sess["color"] = "#f59e0b"
                elif ai_key and ai_key in _st.integrations:
                    info = _st.integrations[ai_key]
                    sess["emoji"] = info["emoji"]; sess["color"] = info["color"]
                else:
                    sess["emoji"] = "🐚"; sess["color"] = "#6b7280"
                # Restart terminal
                sess["terminal"].stop()
                t = TerminalSession()
                if ai_key is None:
                    t.launch()
                sess["terminal"] = t
                _st.focused_id = resume_sid
            else:
                sess = make_session(ai_key, cwd=session_cwd())
                _st.focused_id = sess["id"]
            await push_state()
            label = f"✨ *{sess['name']}*"
            await push_message("system", f"Session ready: {sess['name']} (via Telegram).",
                               source="telegram", session_id=sess["id"])
            await query.edit_message_text(
                f"{label} is ready.\nJust type your task.",
                parse_mode="Markdown",
                reply_markup=session_controls_keyboard(),
            )

        elif verb == "focus":
            sid = parts[2] if len(parts) > 2 else ""
            if sid in _st.sessions:
                sess = _st.sessions[sid]
                if sess["status"] == "stopped":
                    await query.edit_message_text(
                        f"✨ *{sess['name']}* is stopped. Resume as:",
                        parse_mode="Markdown",
                        reply_markup=new_session_keyboard(resume_sid=sid),
                    )
                else:
                    _st.focused_id = sid
                    await push_state()
                    # Picking a session leaves group-chat mode on Telegram.
                    import helm.groupchat as _gc
                    if _gc.active_group("telegram"):
                        _gc.set_active_group("telegram", None)
                    fs = _st.sessions[sid]
                    ai_lbl = fs["emoji"] + " " + (fs["ai"] or "Shell")
                    await query.edit_message_text(
                        f"✅ *{fs['name']}* focused\n"
                        f"AI: {ai_lbl} · 📁 {pathlib.Path(fs['cwd']).name or fs['cwd']}\n\n"
                        f"Type your message to send to this session:",
                        parse_mode="Markdown",
                        reply_markup=session_controls_keyboard(),
                    )
            else:
                await query.edit_message_text("Session not found.", reply_markup=sessions_keyboard())

        elif verb == "stop":
            sess = focused_session()
            if sess:
                kill_session_proc(sess)
                sess["terminal"].stop()
                await emit_session_end_summary(sess, ended_as="stopped", source="telegram")
                sess["status"] = "stopped"
                sess["busy"] = False
                sess["task_start"] = None
                await push_state()
                await query.edit_message_text(
                    f"✨ *{sess['name']}* stopped. Sessions:",
                    parse_mode="Markdown",
                    reply_markup=sessions_keyboard(),
                )
            else:
                await query.edit_message_text("No focused session.", reply_markup=sessions_keyboard())

        elif verb == "delete":
            sess = focused_session()
            if sess:
                kill_session_proc(sess)
                sess["terminal"].stop()
                await emit_session_end_summary(sess, ended_as="deleted", source="telegram")
                sid  = sess["id"]
                name = sess["name"]
                # Cache CWD so late-arriving messages still log to the right file
                _st.deleted_session_cwds[sid] = sess.get("cwd") or _st.last_cwd
                del _st.sessions[sid]
                _st.focused_id = (max(_st.sessions, key=lambda k: _st.sessions[k]["last_used"],
                                      default=None) if _st.sessions else None)
                await push_state()
                await query.edit_message_text(
                    f"🗑️ *{name}* deleted. Sessions:",
                    parse_mode="Markdown",
                    reply_markup=sessions_keyboard(),
                )
            else:
                await query.edit_message_text("No focused session.", reply_markup=sessions_keyboard())

        elif verb == "switch":
            await query.edit_message_text("Switch AI for this session - pick one:",
                                          reply_markup=new_session_keyboard(
                                              resume_sid=_st.focused_id or ""))

        elif verb == "interrupt":
            sess = focused_session()
            if sess:
                try:
                    sess["terminal"].send_interrupt()
                    await push_message("system", "Ctrl+C sent (via Telegram).",
                                       source="telegram", session_id=sess["id"])
                    await query.edit_message_text("⏸ Interrupted.",
                                                  reply_markup=session_controls_keyboard())
                except RuntimeError as e:
                    await query.edit_message_text(str(e))
            else:
                await query.edit_message_text("No focused session.", reply_markup=sessions_keyboard())

        elif verb == "browse":
            if query.message:
                cwd = focused_session()["cwd"] if focused_session() else _st.last_cwd
                await show_browse(query.message, query.from_user.id, cwd, edit=False, page=0)

        elif verb == "model":
            # Show model picker for the focused session's AI
            from helm.web_routes.helpers import _fetch_ollama_models
            fs = focused_session()
            if not fs or not fs.get("ai"):
                await query.edit_message_text(
                    "No AI session active.", reply_markup=session_controls_keyboard()
                )
                return

            ai_key = fs["ai"]
            current_model = fs.get("model") or None

            # CLI + OAuth AIs don't support model switching
            _CLI_AIS = {"claude", "gemini", "codex", "openai"}
            if ai_key in _CLI_AIS:
                await query.edit_message_text(
                    f"ℹ️ *Model switching is not available for {ai_key.title()}.*\n\n"
                    f"{ai_key.title()} runs as a CLI tool authenticated via OAuth — "
                    f"it uses the model assigned to your account.\n\n"
                    f"Model switching is available for *Ollama* sessions, which use "
                    f"a local REST API with locally installed models.",
                    parse_mode="Markdown",
                    reply_markup=session_controls_keyboard(),
                )
                return

            # Fetch available Ollama models
            try:
                models = await asyncio.to_thread(_fetch_ollama_models)
            except Exception:
                models = []

            rows: list = []
            for m in models[:12]:  # cap at 12 to avoid overly long keyboards
                label = ("✅ " if m == current_model else "") + m
                rows.append([InlineKeyboardButton(label, callback_data=f"ms:model_set:{m}")])

            rows.append([InlineKeyboardButton("↩️ Reset to default", callback_data="ms:model_set:")])
            rows.append([InlineKeyboardButton("← Back", callback_data="ms:list")])

            if current_model:
                hint = f"`{current_model}`"
            else:
                hint = f"(default — `{models[0]}`)" if models else "(default)"

            no_models_note = ""
            if not models:
                no_models_note = "\n\n_No models found — is Ollama running? Start it with_ `ollama serve`"

            await query.edit_message_text(
                f"🎯 *Model picker* for *Ollama*\n"
                f"Current: {hint}{no_models_note}\n\n"
                f"Tap a model to switch, or type `/model <name>` in chat:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(rows),
            )

        elif verb == "model_set":
            # ms:model_set:<name>  — name may itself contain colons (e.g. qwen2.5:7b)
            model_name = ":".join(parts[2:]) if len(parts) > 2 else ""
            fs = focused_session()
            if fs:
                fs["model"] = model_name if model_name else None
                await push_state()
                label = f"`{model_name}`" if model_name else "default"
                await query.edit_message_text(
                    f"✅ Model set to {label}.",
                    parse_mode="Markdown",
                    reply_markup=session_controls_keyboard(),
                )
            else:
                await query.edit_message_text("No focused session.", reply_markup=sessions_keyboard())

        return  # end of ms: handling

    # --- action: legacy / shared actions ---
    action = data.split(":", 1)[1] if ":" in data else data

    if action == "history":
        from helm.db import get_db
        try:
            db = get_db()
            hid_rows = db.execute(
                """SELECT DISTINCT history_id FROM messages
                   WHERE type = 'message'
                   ORDER BY id DESC"""
            ).fetchall()
        except Exception:
            hid_rows = []
        # Filter to valid history IDs and limit to 20
        history_ids = [
            r["history_id"] for r in hid_rows
            if HISTORY_ID_RE.fullmatch(r["history_id"])
        ][:20]
        if not history_ids:
            await query.answer("No chat history yet.", show_alert=True)
            return
        rows: list = []
        for date_str in history_ids:
            display = get_session_display_name(date_str)
            rows.append([InlineKeyboardButton(display, callback_data=f"action:resume_date:{date_str}")])
        rows.append([InlineKeyboardButton("← Back", callback_data="ms:list")])
        if query.message:
            await query.edit_message_text(
                "💬 *Past Chats* — tap a session to resume it:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(rows),
            )

    elif action.startswith("resume_date:"):
        date_str = action[len("resume_date:"):]
        # Use HISTORY_ID_RE (fixes bug: original code used undefined HISTORY_DATE_RE)
        if HISTORY_ID_RE.fullmatch(date_str) and query.message:
            await query.edit_message_text("⌛ Resuming session...")
            await perform_resume(query.message, date_str=date_str)
        else:
            await query.answer("Invalid session.", show_alert=True)

    elif action == "browse":
        if query.message:
            cwd = focused_session()["cwd"] if focused_session() else _st.last_cwd
            await show_browse(query.message, query.from_user.id, cwd, edit=False, page=0)

    elif action == "resume":
        if query.message:
            await query.edit_message_text("⌛ Loading last session...")
            await perform_resume(query.message, date_str="")


async def pipeline_callback(update, context):
    """Handle all pl:* inline keyboard button presses for pipelines."""
    from helm.pipeline.models import pipeline_progress
    from helm.pipeline.executor import (
        broadcast_pipeline_update, execute_pipeline, retry_step,
    )
    from .keyboards import pipeline_controls_keyboard

    query = update.callback_query
    user_id = query.from_user.id
    if not ALLOWED_USER_IDS or user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()

    parts = query.data.split(":")
    verb = parts[1] if len(parts) > 1 else ""
    pipeline_id = parts[2] if len(parts) > 2 else ""

    pl = _st.pipelines.get(pipeline_id)
    if not pl:
        await query.edit_message_text("Pipeline not found.")
        return

    if verb == "approve":
        if pl["status"] != "awaiting_approval":
            await query.edit_message_text(
                f"Pipeline is already '{pl['status']}'.",
                reply_markup=pipeline_controls_keyboard(pipeline_id, pl["status"]),
            )
            return
        # Start execution
        asyncio.create_task(execute_pipeline(pipeline_id))
        prog = pipeline_progress(pl)
        await query.edit_message_text(
            f"🚀 *Pipeline started!*\n"
            f"{prog['total']} steps, executing now…\n\n"
            f"I'll send updates as steps complete.",
            parse_mode="Markdown",
            reply_markup=pipeline_controls_keyboard(pipeline_id, "running"),
        )

    elif verb == "cancel":
        pl["status"] = "cancelled"
        for step in pl["steps"]:
            if step["status"] == "pending":
                step["status"] = "skipped"
        await broadcast_pipeline_update(pl)
        await query.edit_message_text(
            f"⚫ Pipeline cancelled.",
            reply_markup=pipeline_controls_keyboard(pipeline_id, "cancelled"),
        )

    elif verb == "pause":
        if pl["status"] == "running":
            pl["status"] = "paused"
            await broadcast_pipeline_update(pl)
        await query.edit_message_text(
            f"⏸ Pipeline paused.",
            reply_markup=pipeline_controls_keyboard(pipeline_id, "paused"),
        )

    elif verb == "resume":
        if pl["status"] in ("paused", "failed"):
            # For failed pipelines, retry all failed steps
            if pl["status"] == "failed":
                for step in pl["steps"]:
                    if step["status"] == "failed":
                        step["status"] = "pending"
                        step["error"] = None
                        step["retry_count"] = step.get("retry_count", 0) + 1
            pl["status"] = "running"
            asyncio.create_task(execute_pipeline(pipeline_id))
            await broadcast_pipeline_update(pl)
        await query.edit_message_text(
            f"▶️ Pipeline resumed.",
            reply_markup=pipeline_controls_keyboard(pipeline_id, "running"),
        )

    elif verb == "status":
        prog = pipeline_progress(pl)
        status_icon = {"running": "🔵", "completed": "✅", "failed": "❌",
                      "paused": "⏸", "awaiting_approval": "🟡", "cancelled": "⚫"}.get(pl["status"], "❓")
        cost_str = ""
        actual_cost = pl.get("actual_total_cost", 0)
        est_cost = pl.get("estimated_total_cost", 0)
        if actual_cost > 0:
            cost_str = f"\n💰 Cost: ${actual_cost:.4f}"
        elif est_cost > 0:
            cost_str = f"\n💰 Est: ~${est_cost:.4f}"

        lines = [f"{status_icon} *Pipeline — {pl['status']}*{cost_str}\n"]
        for step in pl["steps"]:
            s_icon = {"pending": "⏳", "running": "🔵", "completed": "✅",
                     "failed": "❌", "skipped": "⏭"}.get(step["status"], "❓")
            elapsed = ""
            if step.get("elapsed_seconds"):
                elapsed = f" ({step['elapsed_seconds']:.1f}s)"
            error = ""
            if step.get("error"):
                error = f"\n  ⚠️ _{step['error'][:80]}_"
            fb_info = ""
            if step.get("fallback_ais") and step.get("fallback_index", 0) > 0:
                fb_info = f" (fallback #{step['fallback_index']})"
            cond_info = " ⚡" if step.get("condition") else ""
            lines.append(f"{s_icon} *{step['title']}* — {step['assigned_ai']}{fb_info}{cond_info}{elapsed}{error}")

        lines.append(f"\n📊 {prog['completed']}/{prog['total']} completed, "
                     f"{prog['failed']} failed, {prog['skipped']} skipped")

        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=pipeline_controls_keyboard(pipeline_id, pl["status"]),
        )


async def agent_callback(update, context):
    """Handle ag:run:<agent_id> inline keyboard button presses."""
    from helm.agent.runner import trigger_agent_run
    from helm.session_mgr import focused_session

    query = update.callback_query
    user_id = query.from_user.id
    if not ALLOWED_USER_IDS or user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    agent_id = parts[2] if len(parts) > 2 else ""

    if action != "run" or not agent_id:
        await query.edit_message_text("Unknown agent action.")
        return

    ag = _st.agents.get(agent_id)
    if not ag:
        await query.edit_message_text("Agent not found.")
        return

    fs = focused_session()
    session_id = fs["id"] if fs else None

    await query.edit_message_text(
        f"✦ Starting agent: *{ag['name']}* ({len(ag.get('nodes', []))} nodes)…",
        parse_mode="Markdown",
    )

    run = await trigger_agent_run(agent_id, trigger="telegram", session_id=session_id)
    if not run:
        await query.edit_message_text("❌ Failed to start agent — it may have no nodes.")
        return

    import asyncio as _asyncio
    try:
        await query.edit_message_text(
            f"✦ *{ag['name']}* is running (`{run['id'][:8]}`).\n"
            f"You'll receive step-by-step updates here.",
            parse_mode="Markdown",
        )
    except Exception:
        pass


async def approval_callback(update, context):
    """Handle appr:approve:<id> and appr:deny:<id> inline keyboard buttons."""
    import helm.approval as _appr

    query = update.callback_query
    user_id = query.from_user.id
    if not ALLOWED_USER_IDS or user_id not in ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    await query.answer()

    parts = query.data.split(":")
    verb = parts[1] if len(parts) > 1 else ""
    req_id = parts[2] if len(parts) > 2 else ""

    if verb not in ("approve", "deny"):
        await query.edit_message_text("Unknown approval action.")
        return

    status = "approved" if verb == "approve" else "denied"
    ok = _appr.resolve(req_id, status, source="telegram")

    if ok:
        # Broadcast resolution to Web UI
        req = _st.approval_queue.get(req_id)
        if req:
            await _appr.broadcast_resolution(req)

        icon = "✅" if status == "approved" else "❌"
        await query.edit_message_text(
            f"{icon} Action **{status}** (via Telegram).",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            "⚠️ This approval request was already resolved or expired."
        )
