"""
helm/telegram_bot/callbacks.py — Inline keyboard callback routing.

Covers: action_callback, browse_callback (callback routing for inline keyboards).
"""

import asyncio
import pathlib
from typing import Optional

import helm.state as _st
from helm.config import ALLOWED_USER_IDS, CHAT_LOG_DIR, HISTORY_ID_RE

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
            from helm.web_routes import (
                _fetch_claude_models, _fetch_ollama_models,
                _fetch_gemini_models, _fetch_openai_models,
            )
            fs = focused_session()
            if not fs or not fs.get("ai"):
                await query.edit_message_text(
                    "No AI session active.", reply_markup=session_controls_keyboard()
                )
                return

            ai_key = fs["ai"]
            current_model = fs.get("model") or None

            # AIs that use local OAuth auth can't list models via API —
            # inform the user and let them type a model name manually.
            _oauth_only_ais = {"claude", "gemini", "codex"}

            # Fetch available models live for this AI
            try:
                if ai_key == "claude":
                    models = await asyncio.to_thread(_fetch_claude_models)
                elif ai_key == "ollama":
                    models = await asyncio.to_thread(_fetch_ollama_models)
                elif ai_key == "gemini":
                    models = await asyncio.to_thread(_fetch_gemini_models)
                elif ai_key in ("codex", "openai"):
                    models = await asyncio.to_thread(_fetch_openai_models)
                else:
                    models = []
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

            # Build the appropriate note when no models are found
            if not models and ai_key in _oauth_only_ais:
                no_models_note = (
                    "\n\n⚠️ _Model listing is not available for local OAuth auth._\n"
                    "_You can still switch models manually — type_ `/model <name>` _in chat._\n"
                    "_Example:_ `/model claude-sonnet-4-5-20250514`"
                )
            elif not models:
                no_models_note = "\n\n_No models found — check that the AI service is running._"
            else:
                no_models_note = ""

            await query.edit_message_text(
                f"🎯 *Model picker* for *{ai_key}*\n"
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
        if not CHAT_LOG_DIR.exists():
            await query.answer("No chat history yet.", show_alert=True)
            return
        log_files = sorted(
            [f for f in CHAT_LOG_DIR.glob("*.jsonl") if HISTORY_ID_RE.fullmatch(f.stem)],
            reverse=True,
        )[:20]
        if not log_files:
            await query.answer("No chat history yet.", show_alert=True)
            return
        rows: list = []
        for f in log_files:
            date_str = f.stem
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
