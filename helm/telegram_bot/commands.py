"""
helm/telegram_bot/commands.py — All /command handlers for Telegram bot.

Covers: tg_start, tg_menu, tg_launch, tg_claude, tg_codex, tg_gemini, tg_stop_ai,
        tg_clear, tg_cmd, tg_status, tg_interrupt, tg_stop, tg_cwd, tg_timeout,
        tg_schedule, tg_history, tg_resume, tg_clear_context, tg_text.
"""

import asyncio

import helm.state as _st
from helm.config import WEB_PORT
from helm.paths import user_data_dir

from .auth import authorized_only, tg_send_chunks
from .keyboards import sessions_keyboard, session_controls_keyboard, new_session_keyboard


@authorized_only
async def tg_start(update, context):
    """Welcome message — show session list or prompt to create first session."""
    if _st.sessions:
        await update.message.reply_text(
            "👋 *RAPR AI* — Multi-Session Mode\n\n"
            "Tap a session to focus it, or create a new one.\n"
            f"Web UI: http://localhost:{WEB_PORT}",
            parse_mode="Markdown",
            reply_markup=sessions_keyboard(),
        )
    else:
        await update.message.reply_text(
            "👋 *RAPR AI* — Multi-Session Mode\n\n"
            "No sessions yet. Create your first session:\n"
            f"Web UI: http://localhost:{WEB_PORT}",
            parse_mode="Markdown",
            reply_markup=new_session_keyboard(),
        )


@authorized_only
async def tg_menu(update, context):
    """/menu — show sessions or controls for focused session."""
    from helm.session_mgr import focused_session
    fs = focused_session()
    if fs:
        ai_label = fs["emoji"] + " " + (fs["ai"] or "Shell")
        await update.message.reply_text(
            f"*RAPR AI — {fs['name']}*\n"
            f"AI: {ai_label}  ·  Status: {fs['status']}\n"
            f"📂 `{fs['cwd']}`",
            parse_mode="Markdown",
            reply_markup=session_controls_keyboard(),
        )
    else:
        await update.message.reply_text(
            "*RAPR AI — Sessions*\nNo session focused. Pick one:",
            parse_mode="Markdown",
            reply_markup=sessions_keyboard(),
        )


@authorized_only
async def tg_launch(update, context):
    """Create a new shell session (quick shortcut)."""
    from helm.session_mgr import make_session, session_cwd
    from helm.broadcast import push_message, push_state
    from helm.config import IDLE_TIMEOUT
    sess = make_session(None, cwd=session_cwd())  # None = shell
    _st.focused_id = sess["id"]
    output = await asyncio.to_thread(sess["terminal"].drain, IDLE_TIMEOUT, 10.0, 5.0)
    await push_state()
    await push_message("system", f"Session created: {sess['name']} (via Telegram).",
                       source="telegram", session_id=sess["id"])
    if output:
        await push_message("assistant", output, ai="shell", source="telegram",
                           session_id=sess["id"])
    await update.message.reply_text(
        f"✅ {sess['name']} started. Type to send shell commands:",
        reply_markup=session_controls_keyboard(),
    )


@authorized_only
async def tg_claude(update, context):
    """Create or focus a Claude Code session."""
    from helm.session_mgr import make_session, session_cwd
    from helm.broadcast import push_message, push_state
    sess = make_session("claude", cwd=session_cwd())
    _st.focused_id = sess["id"]
    await push_state()
    await push_message("system", f"{sess['name']} created (via Telegram).", source="telegram",
                       session_id=sess["id"])
    await update.message.reply_text(
        f"🤖 *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=session_controls_keyboard(),
    )


@authorized_only
async def tg_codex(update, context):
    """Create a new Codex session (if plugin is loaded)."""
    from helm.session_mgr import make_session, session_cwd
    from helm.broadcast import push_state
    if "codex" not in _st.integrations:
        await update.message.reply_text("Codex integration not loaded.")
        return
    sess = make_session("codex", cwd=session_cwd())
    _st.focused_id = sess["id"]
    await push_state()
    await update.message.reply_text(
        f"💻 *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=session_controls_keyboard(),
    )


@authorized_only
async def tg_antigravity(update, context):
    """Create a new Antigravity (agy) session."""
    from helm.session_mgr import make_session, session_cwd
    from helm.broadcast import push_state
    from helm.ai_runner.core import is_backend_available
    if "antigravity" not in _st.integrations or not is_backend_available("antigravity"):
        await update.message.reply_text(
            "Antigravity CLI (agy) isn't installed on the RAPR computer. "
            "Install it from antigravity.google/docs/cli-using and run agy once to sign in.")
        return
    sess = make_session("antigravity", cwd=session_cwd())
    _st.focused_id = sess["id"]
    await push_state()
    await update.message.reply_text(
        f"🪐 *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=session_controls_keyboard(),
    )


@authorized_only
async def tg_gemini(update, context):
    """Create a new Gemini session (if plugin is loaded)."""
    from helm.session_mgr import make_session, session_cwd
    from helm.broadcast import push_state
    if "gemini" not in _st.integrations:
        await update.message.reply_text(
            "The Gemini CLI isn't installed (Google stopped it for personal accounts). "
            "Use /antigravity instead — Google's replacement.")
        return
    sess = make_session("gemini", cwd=session_cwd())
    _st.focused_id = sess["id"]
    await push_state()
    await update.message.reply_text(
        f"✨ *{sess['name']}* is ready.\nJust type your task.",
        parse_mode="Markdown",
        reply_markup=session_controls_keyboard(),
    )


@authorized_only
async def tg_stop_ai(update, context):
    """Stop the focused session's AI (switch to shell)."""
    from helm.session_mgr import focused_session
    from helm.broadcast import push_state
    sess = focused_session()
    if not sess:
        await update.message.reply_text("No session focused.", reply_markup=sessions_keyboard())
        return
    sess["ai"] = None
    sess["emoji"] = "🐚"
    sess["color"] = "#6b7280"
    await push_state()
    await update.message.reply_text(
        f"🐚 {sess['name']} switched to Shell mode.",
        reply_markup=session_controls_keyboard(),
    )


@authorized_only
async def tg_clear(update, context):
    """Clear conversation history."""
    from helm.session_mgr import focused_session
    from helm.broadcast import push_message
    sess = focused_session()
    sid = sess["id"] if sess else None
    if sess:
        sess["claude_msgs"] = []
    await push_message("system", "Claude history cleared (via Telegram).",
                       source="telegram", session_id=sid)
    await update.message.reply_text("Conversation history cleared.")


@authorized_only
async def tg_cmd(update, context):
    """Execute a shell command directly."""
    from helm.session_mgr import focused_session
    from helm.broadcast import push_message
    text = (update.message.text or "").partition(" ")[2].strip()
    if not text:
        await update.message.reply_text("Usage: /cmd <command>")
        return
    sess = focused_session()
    if not sess or not sess["terminal"].is_alive():
        await update.message.reply_text("No active session terminal. Create a session first.")
        return
    await push_message("user", f"/cmd {text}", source="telegram", session_id=sess["id"])
    sess["terminal"].write(text)
    output = await asyncio.to_thread(sess["terminal"].drain)
    output = output or "(no output)"
    await push_message("assistant", output, ai="shell", source="telegram", session_id=sess["id"])
    await tg_send_chunks(update, output)


@authorized_only
async def tg_status(update, context):
    """Show status of all active sessions."""
    from helm.config import CLAUDE_TIMEOUT
    if not _st.sessions:
        await update.message.reply_text("No sessions. Use /start to create one.")
        return
    lines = ["*Active Sessions:*"]
    for sess in sorted(_st.sessions.values(), key=lambda s: s["last_used"], reverse=True):
        focused = " ← focused" if sess["id"] == _st.focused_id else ""
        lines.append(f"✨ *{sess['name']}* [{sess['ai'] or 'shell'}]{focused}\n"
                     f"  📂 {sess['cwd']}")
    timeout_label = "unlimited" if CLAUDE_TIMEOUT == 0 else f"{int(CLAUDE_TIMEOUT)}s"
    lines.append(f"\n⌛ Timeout: {timeout_label}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                    reply_markup=sessions_keyboard())


@authorized_only
async def tg_kelvin(update, context):
    """'Is Kelvin on?' — uptime, what's running, approvals, next schedule, keep-awake."""
    from helm.kelvin_report import kelvin_report
    from helm.kelvin_status import status
    from helm.kelvin_stickers import send_kelvin_sticker
    mood = status.mood()
    await send_kelvin_sticker(mood if mood in ("approval", "error", "working", "done") else "idle")
    await update.message.reply_text(kelvin_report())


@authorized_only
async def tg_interrupt(update, context):
    """Interrupt the currently-running AI task."""
    from helm.session_mgr import focused_session
    from helm.ai_runner import kill_session_proc
    from helm.broadcast import push_message, push_state, push_thinking
    sess = focused_session()
    if not sess:
        await update.message.reply_text("No session focused.")
        return
    try:
        if sess["ai"]:
            # AI session — kill the subprocess
            kill_session_proc(sess)
            sess["busy"]       = False
            sess["task_start"] = None
            await push_thinking(False, session_id=sess["id"])
            await push_state()
            await push_message("system", "⏹ AI task interrupted (via Telegram).",
                               source="telegram", session_id=sess["id"])
            await update.message.reply_text("⏹ AI task interrupted.",
                                            reply_markup=session_controls_keyboard())
        else:
            sess["terminal"].send_interrupt()
            await push_message("system", "Ctrl+C sent (via Telegram).", source="telegram",
                               session_id=sess["id"])
            await update.message.reply_text("⏸ Ctrl+C sent.",
                                            reply_markup=session_controls_keyboard())
    except RuntimeError as e:
        await update.message.reply_text(str(e))


@authorized_only
async def tg_stop(update, context):
    """Stop the focused session completely."""
    from helm.session_mgr import focused_session
    from helm.ai_runner import kill_session_proc
    from helm.file_tracker import emit_session_end_summary
    from helm.broadcast import push_state, push_thinking
    sess = focused_session()
    if not sess:
        await update.message.reply_text("No session focused.", reply_markup=sessions_keyboard())
        return
    kill_session_proc(sess)
    sess["terminal"].stop()
    await emit_session_end_summary(sess, ended_as="stopped", source="telegram")
    sess["status"]    = "stopped"
    sess["busy"]      = False
    sess["task_start"] = None
    await push_thinking(False, session_id=sess["id"])
    await push_state()
    await update.message.reply_text(
        f"🛑 {sess['name']} stopped.\nSessions:",
        reply_markup=sessions_keyboard(),
    )


@authorized_only
async def tg_cwd(update, context):
    """Show or change the working directory of the focused session."""
    from helm.session_mgr import focused_session
    from helm.ai_runner import change_cwd
    arg = (update.message.text or "").partition(" ")[2].strip()
    sess = focused_session()
    if not arg:
        cwd = sess["cwd"] if sess else _st.last_cwd
        await update.message.reply_text(f"📂 Current directory:\n{cwd}")
        return
    ok = await change_cwd(arg, source="telegram")
    if ok:
        sess = focused_session()
        cwd = sess["cwd"] if sess else _st.last_cwd
        await update.message.reply_text(f"📂 Working directory changed to:\n{cwd}")


@authorized_only
async def tg_timeout(update, context):
    """Get or set the AI timeout: /timeout  or  /timeout <seconds>  or  /timeout 0 for unlimited"""
    from helm.broadcast import push_message
    from helm.session_mgr import focused_session
    import helm.config as _cfg
    arg = (update.message.text or "").partition(" ")[2].strip()
    if not arg:
        limit_str = ("unlimited (AI tool controls its own timeout)"
                     if _cfg.CLAUDE_TIMEOUT == 0 else f"{int(_cfg.CLAUDE_TIMEOUT)}s")
        await update.message.reply_text(
            f"⌛ Current AI timeout: {limit_str}\n"
            f"Use /timeout <seconds> to set a hard cap, or /timeout 0 for unlimited."
        )
        return
    try:
        value = float(arg)
        if value < 0:
            await update.message.reply_text("❌ Use 0 for unlimited, or a positive number of seconds.")
            return
        if 0 < value < 10:
            await update.message.reply_text("❌ Minimum timeout is 10 seconds (or 0 for unlimited).")
            return
        _cfg.CLAUDE_TIMEOUT = value
        _update_env("CLAUDE_TIMEOUT", str(int(value)))
        label = "unlimited" if value == 0 else f"{int(value)}s"
        fs = focused_session()
        sid = fs["id"] if fs else None
        await push_message("system", f"⌛ AI timeout set to {label}",
                           source="telegram", session_id=sid)
        await update.message.reply_text(f"⌛ Timeout updated to {label} (saved to .env)")
    except ValueError:
        await update.message.reply_text("❌ Invalid value. Use seconds (e.g. /timeout 1800) or 0 for unlimited.")


def _update_env(key: str, value: str):
    """Update or add a key=value line in the .env file."""
    env_path = user_data_dir() / ".env"
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
