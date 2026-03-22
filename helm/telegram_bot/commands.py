"""
helm/telegram_bot/commands.py — All /command handlers for Telegram bot.

Covers: tg_start, tg_menu, tg_launch, tg_claude, tg_codex, tg_gemini, tg_stop_ai,
        tg_clear, tg_cmd, tg_status, tg_interrupt, tg_stop, tg_cwd, tg_timeout,
        tg_schedule, tg_history, tg_resume, tg_clear_context, tg_text.
"""

import asyncio
import json
import os
import pathlib
from datetime import datetime, timedelta
from typing import Optional

import helm.state as _st
from helm.config import (
    ALLOWED_USER_IDS, CRONITER_OK, HISTORY_ID_RE,
    WEB_PORT, logger,
)
from helm.paths import user_data_dir

from .auth import authorized_only, tg_send_chunks
from .browse import show_browse
from .keyboards import (
    sessions_keyboard, session_controls_keyboard, new_session_keyboard,
)

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import ContextTypes
    _TG_OK = True
except ImportError:
    _TG_OK = False
    Update = None
    ContextTypes = None


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
async def tg_gemini(update, context):
    """Create a new Gemini session (if plugin is loaded)."""
    from helm.session_mgr import make_session, session_cwd
    from helm.broadcast import push_state
    if "gemini" not in _st.integrations:
        await update.message.reply_text("Gemini integration not loaded.")
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
    from helm.session_mgr import session_status_icon
    from helm.config import CLAUDE_TIMEOUT
    if not _st.sessions:
        await update.message.reply_text("No sessions. Use /start to create one.")
        return
    lines = ["*Active Sessions:*"]
    for sess in sorted(_st.sessions.values(), key=lambda s: s["last_used"], reverse=True):
        icon = session_status_icon(sess)
        focused = " ← focused" if sess["id"] == _st.focused_id else ""
        lines.append(f"✨ *{sess['name']}* [{sess['ai'] or 'shell'}]{focused}\n"
                     f"  📂 {sess['cwd']}")
    timeout_label = "unlimited" if CLAUDE_TIMEOUT == 0 else f"{int(CLAUDE_TIMEOUT)}s"
    lines.append(f"\n⌛ Timeout: {timeout_label}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                    reply_markup=sessions_keyboard())


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
    from helm.session_mgr import focused_session, session_cwd
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


@authorized_only
async def tg_schedule(update, context):
    """/schedule [list | add <when> <ai> <prompt> | delete <id> | on <id> | off <id>]"""
    from helm.scheduler import (
        natural_to_cron, next_cron_run, make_sched_task,
        save_scheduled_tasks, run_scheduled_task,
    )
    text  = (update.message.text or "").strip()
    parts = text.split(None, 2)
    sub   = parts[1].strip().lower() if len(parts) > 1 else "list"
    rest  = parts[2].strip() if len(parts) > 2 else ""

    # --- list ---
    if sub in ("list", "ls", "") or not sub:
        if not _st.scheduled_tasks:
            await update.message.reply_text(
                "No scheduled tasks.\n"
                "Add one: /schedule add 0 9 * * * claude Review git diff"
            )
            return
        lines = ["*Scheduled Tasks:*"]
        for task in _st.scheduled_tasks.values():
            ico = "✅" if task["enabled"] else "⏸"
            nr  = datetime.fromtimestamp(task["next_run"]).strftime("%m/%d %H:%M") \
                  if task.get("next_run") else "—"
            lines.append(
                f"{ico} `{task['id']}` *{task['name']}*\n"
                f"  `{task['cron']}`  ·  {task['ai'] or 'shell'}  ·  next: {nr}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # --- add <schedule> <ai> <prompt> ---
    if sub == "add":
        tokens = rest.split()
        if len(tokens) < 3:
            await update.message.reply_text(
                "Usage: /schedule add <when> <ai> <prompt>\n\n"
                "Natural language examples:\n"
                "  /schedule add daily at 9am claude Review git diff\n"
                "  /schedule add every monday at 5pm claude Weekly report\n"
                "  /schedule add weekdays at 8am shell backup.sh\n"
                "  /schedule add monthly on the 1st at 9am claude Monthly summary\n\n"
                "AI options: claude  shell  (or any integration key)"
            )
            return

        known_ais = {"claude", "shell", *_st.integrations.keys()}
        ai_pos = None
        for i, tok in enumerate(tokens):
            if tok.lower() in known_ais:
                ai_pos = i
                break

        if ai_pos is None or ai_pos == 0:
            await update.message.reply_text(
                "❌ Couldn't find an AI target (claude / shell). "
                "Example: /schedule add daily at 9am *claude* Review git diff",
                parse_mode="Markdown",
            )
            return

        ai_key   = tokens[ai_pos].lower() if tokens[ai_pos].lower() in known_ais else None
        prompt   = " ".join(tokens[ai_pos + 1:]).strip()
        if not prompt:
            await update.message.reply_text("❌ Please include a prompt after the AI target.")
            return

        sched_text = " ".join(tokens[:ai_pos])
        cron_expr = natural_to_cron(sched_text)

        if cron_expr is None or next_cron_run(cron_expr) is None:
            if not CRONITER_OK:
                await update.message.reply_text("❌ croniter not installed — run: pip install croniter")
            else:
                await update.message.reply_text(
                    f"❌ Couldn't parse schedule: `{sched_text}`\n\n"
                    "Try phrases like:\n"
                    "• *daily at 9am*\n"
                    "• *every monday at 5pm*\n"
                    "• *weekdays at 8am*\n"
                    "• *monthly on the 1st at 9am*",
                    parse_mode="Markdown",
                )
            return

        task = make_sched_task(cron_expr, ai_key, prompt)
        _st.scheduled_tasks[task["id"]] = task
        save_scheduled_tasks()
        nr = datetime.fromtimestamp(task["next_run"]).strftime("%Y-%m-%d %H:%M")
        await update.message.reply_text(
            f"✅ Scheduled *{task['name']}* (`{task['id']}`)\n"
            f"`{cron_expr}` · {ai_key or 'shell'}\n"
            f"Next run: {nr}",
            parse_mode="Markdown",
        )
        return

    # --- delete <id> ---
    if sub in ("delete", "del", "rm", "remove"):
        tid = rest.strip()
        if tid in _st.scheduled_tasks:
            name = _st.scheduled_tasks[tid]["name"]
            del _st.scheduled_tasks[tid]
            save_scheduled_tasks()
            await update.message.reply_text(f"🗑️ Deleted: {name}")
        else:
            await update.message.reply_text(f"❌ Task not found: `{tid}`", parse_mode="Markdown")
        return

    # --- on / off <id> ---
    if sub in ("on", "off", "enable", "disable"):
        tid    = rest.strip()
        enable = sub in ("on", "enable")
        if tid in _st.scheduled_tasks:
            _st.scheduled_tasks[tid]["enabled"] = enable
            if enable:
                _st.scheduled_tasks[tid]["next_run"] = next_cron_run(_st.scheduled_tasks[tid]["cron"])
            save_scheduled_tasks()
            icon  = "✅" if enable else "⏸"
            state = "enabled" if enable else "paused"
            await update.message.reply_text(f"{icon} Task `{tid}` {state}.", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Task not found: `{tid}`", parse_mode="Markdown")
        return

    # --- run <id> (manual trigger) ---
    if sub in ("run", "trigger", "now"):
        tid = rest.strip()
        if tid in _st.scheduled_tasks:
            task = _st.scheduled_tasks[tid]
            await update.message.reply_text(f"▶️ Running *{task['name']}* now...", parse_mode="Markdown")
            asyncio.create_task(run_scheduled_task(task))
        else:
            await update.message.reply_text(f"❌ Task not found: `{tid}`", parse_mode="Markdown")
        return

    await update.message.reply_text(
        "Subcommands:\n"
        "  /schedule list\n"
        "  /schedule add <when> <ai> <prompt>\n"
        "  /schedule delete <id>\n"
        "  /schedule on <id>  /  off <id>\n"
        "  /schedule run <id>   ← manual trigger"
    )


@authorized_only
async def tg_history(update, context):
    """/history [n] — show last n user+assistant messages from the database (default 5, max 20)."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    try:
        n = max(1, min(20, int(arg))) if arg else 5
    except ValueError:
        n = 5

    # Query recent messages from SQLite
    from helm.db import get_db
    try:
        db = get_db()
        rows = db.execute(
            """SELECT role, content, ai, timestamp, ts
               FROM messages
               WHERE type = 'message' AND role IN ('user', 'assistant')
               ORDER BY id DESC
               LIMIT ?""",
            (n,),
        ).fetchall()
    except Exception:
        await update.message.reply_text("Could not read history from database.")
        return

    if not rows:
        await update.message.reply_text("No history found.")
        return

    # Reverse to show oldest-first
    rows = list(reversed(rows))

    lines_out = []
    for m in rows:
        role = "You" if m["role"] == "user" else (m["ai"] or "AI").title()
        ts = (m["timestamp"] or "")[:16].replace("T", " ")
        preview = (m["content"] or "")[:200]
        if len(m["content"] or "") > 200:
            preview += "..."
        lines_out.append(f"[{ts}] {role}:\n{preview}")

    await tg_send_chunks(update, "\n\n".join(lines_out))


async def perform_resume(message, date_str: str = "") -> None:
    """Core resume logic — usable from both /resume command and inline button."""
    from helm.session_mgr import make_session
    from helm.ai_runner import change_cwd
    from helm.history import load_chat_names
    from helm.broadcast import push_state

    # --- Resolve history_id (from SQLite) ---
    from helm.db import get_db
    from helm.history import get_history_messages

    if date_str:
        # Verify this history_id exists in the DB
        db = get_db()
        exists = db.execute(
            "SELECT 1 FROM messages WHERE history_id = ? AND type = 'message' LIMIT 1",
            (date_str,),
        ).fetchone()
        if not exists:
            await message.reply_text(f"❌ No history found for {date_str}.")
            return
    else:
        # Find the most recent history_id
        db = get_db()
        row = db.execute(
            """SELECT DISTINCT history_id FROM messages
               WHERE type = 'message'
               ORDER BY id DESC LIMIT 1"""
        ).fetchone()
        if not row:
            await message.reply_text("No chat history saved yet.")
            return
        date_str = row["history_id"]

    # --- Read messages from SQLite ---
    messages: list[dict] = get_history_messages(date_str)
    if not messages:
        await message.reply_text(f"No conversation messages found in session {date_str}.")
        return

    # --- Get CWD and AI from the history's own records ---
    last_cwd: Optional[str] = None
    last_ai:  Optional[str] = None

    db = get_db()
    cwd_row = db.execute(
        """SELECT path FROM messages
           WHERE history_id = ? AND type = 'cwd' AND path IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (date_str,),
    ).fetchone()
    if cwd_row:
        last_cwd = cwd_row["path"]

    ai_row = db.execute(
        """SELECT model FROM messages
           WHERE history_id = ? AND type = 'ai' AND model IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (date_str,),
    ).fetchone()
    if ai_row:
        last_ai = ai_row["model"]

    # --- Fallback: load CWD/AI from session_state table ---
    if not last_cwd or not last_ai:
        try:
            state_row = db.execute(
                "SELECT value FROM session_state WHERE key = 'sessions'"
            ).fetchone()
            if state_row:
                sessions_saved = json.loads(state_row["value"])
                if sessions_saved:
                    first = next(iter(sessions_saved.values()))
                    if not last_cwd:
                        last_cwd = first.get("cwd") or None
                    if not last_ai:
                        last_ai = first.get("ai") or None
        except Exception:
            pass

    # --- Build context string from last 10 exchanges ---
    turns = messages[-10:]
    lines_ctx = []
    for m in turns:
        role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
        body = (m.get("content") or "")[:300]
        if len(m.get("content", "")) > 300:
            body += "..."
        lines_ctx.append(f"{role}: {body}")

    label = load_chat_names().get(date_str) or date_str
    context_prefix = (
        f"[Previous conversation — {label}]\n"
        + "\n".join(lines_ctx)
        + "\n[End context]\n\n"
    )

    # --- Create a new session for the resumed work ---
    valid_ai = last_ai and (last_ai == "claude" or last_ai in _st.integrations)
    ai_to_use = last_ai if valid_ai else None
    sess = make_session(ai_to_use, cwd=last_cwd)
    _st.focused_id = sess["id"]

    cwd_note = ""
    if last_cwd:
        cwd_ok = await change_cwd(last_cwd, source="telegram", session_id=sess["id"])
        cwd_note = (
            f"\n📂 Directory restored: `{last_cwd}`"
            if cwd_ok
            else f"\n⚠️ Could not restore directory: `{last_cwd}`"
        )

    # Inject the context prefix into the next message sent to this session
    _st.pending_tg_context = context_prefix

    await push_state()

    if valid_ai:
        if last_ai == "claude":
            ai_label = "🤖 Claude Code"
        elif last_ai in _st.integrations:
            info = _st.integrations[last_ai]
            ai_label = f"{info['emoji']} {info['name']}"
        else:
            ai_label = last_ai.title()
        ai_note = f"\n{ai_label} re-activated — just type to continue."
    else:
        ai_note = "\nPick an AI below to continue:"

    await message.reply_text(
        f"✅ *Resumed: {label}* ({len(turns)} exchanges loaded){cwd_note}{ai_note}",
        parse_mode="Markdown",
        reply_markup=session_controls_keyboard() if valid_ai else sessions_keyboard(),
    )


_perform_resume = perform_resume  # legacy alias


@authorized_only
async def tg_resume(update, context):
    """/resume [date] — restore a past session's directory, AI model, and context."""
    arg = (update.message.text or "").partition(" ")[2].strip()
    await perform_resume(update.message, date_str=arg)


@authorized_only
async def tg_clear_context(update, context):
    """Discard any pending resume context without sending it."""
    if _st.pending_tg_context:
        _st.pending_tg_context = None
        await update.message.reply_text("✅ Pending context cleared.")
    else:
        await update.message.reply_text("No pending context to clear.")


@authorized_only
async def tg_text(update, context):
    """Forward plain text — with natural language shortcut detection."""
    from helm.session_mgr import focused_session, make_session, session_cwd
    from helm.ai_runner import process_message
    from helm.broadcast import push_state

    text = (update.message.text or "").strip()
    low = text.lower()

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

    # --- Auto-pipeline detection for complex tasks ---
    pipeline_auto = os.environ.get("PIPELINE_AUTO_SUGGEST", "true").lower()
    if pipeline_auto == "true" and len(text) > 100:
        try:
            from helm.pipeline.planner import looks_complex
            if looks_complex(text):
                # Auto-invoke pipeline instead of sending to a single AI
                from helm.pipeline.planner import plan_pipeline, discover_available_ais
                from helm.pipeline.models import pipeline_state_payload, pipeline_progress
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
                await _update.message.reply_text(f"⚠️ Error: {exc}")
            except Exception:
                pass

    asyncio.create_task(_tg_fire())


# ---------------------------------------------------------------------------
# Voice message handler — Whisper speech-to-text → process_message
# ---------------------------------------------------------------------------

@authorized_only
async def tg_voice(update, context):
    """Transcribe voice/audio messages via Whisper and forward to the active AI."""
    from helm.session_mgr import focused_session
    from helm.ai_runner import process_message
    from helm.broadcast import push_state
    import os
    import subprocess
    import sys
    import tempfile

    # Must have a focused session
    if not _st.focused_id or _st.focused_id not in _st.sessions:
        if _st.sessions:
            await update.message.reply_text(
                "👋 Tap a session first, then send a voice message:",
                reply_markup=sessions_keyboard(),
            )
        else:
            await update.message.reply_text(
                "👋 No sessions yet. Create one first:",
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

    # Download the voice/audio file from Telegram
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("⚠️ No audio found in message.")
        return

    await update.message.reply_text("🎤 Transcribing voice message...")

    try:
        tg_file = await voice.get_file()
        # Save to temp .ogg file
        tmp_dir = tempfile.mkdtemp(prefix="helm_voice_")
        ogg_path = os.path.join(tmp_dir, "voice.ogg")
        await tg_file.download_to_drive(ogg_path)

        # Transcribe using Whisper
        transcript = await asyncio.get_event_loop().run_in_executor(
            None, _transcribe_audio, ogg_path
        )

        # Clean up temp files
        try:
            os.remove(ogg_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass

        if not transcript or not transcript.strip():
            await update.message.reply_text("⚠️ Could not transcribe audio — no speech detected.")
            return

        # Show the transcript to the user
        fs = focused_session()
        label = f"{fs['emoji']} {fs['name']}" if fs else "session"
        await update.message.reply_text(
            f"🎤 *Transcript:* {transcript}\n\nThinking... [{label}]",
            parse_mode="Markdown",
        )

        # Forward transcript to the active AI — same flow as tg_text
        async def _tg_voice_fire(
            _text: str = transcript,
            _update=update,
        ) -> None:
            try:
                response = await process_message(_text, source="telegram")
                await tg_send_chunks(
                    _update, response,
                    reply_markup=session_controls_keyboard(),
                )
            except Exception as exc:
                logger.warning("tg_voice_fire error: %s", exc)
                try:
                    await _update.message.reply_text(f"⚠️ Error: {exc}")
                except Exception:
                    pass

        asyncio.create_task(_tg_voice_fire())

    except Exception as exc:
        logger.warning("Voice transcription error: %s", exc)
        await update.message.reply_text(f"⚠️ Voice transcription failed: {exc}")


def _ensure_ffmpeg():
    """Make sure ffmpeg is on PATH. Uses static-ffmpeg as fallback on Windows."""
    import shutil, subprocess, sys
    from helm.subprocess_utils import hidden_kwargs
    if shutil.which("ffmpeg"):
        return  # already available
    # Install static-ffmpeg which bundles the binary
    try:
        import static_ffmpeg
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "static-ffmpeg", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **hidden_kwargs(),
        )
        import static_ffmpeg
    static_ffmpeg.add_paths()


def _transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file using Whisper. Runs in a thread pool."""
    _ensure_ffmpeg()

    try:
        import whisper
    except ImportError:
        import subprocess, sys
        from helm.subprocess_utils import hidden_kwargs
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "openai-whisper", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            **hidden_kwargs(),
        )
        import whisper

    model = whisper.load_model("base")
    result = model.transcribe(audio_path, fp16=False)
    return (result.get("text") or "").strip()


# ---------------------------------------------------------------------------
# File / Photo attachment handler — save to CWD and notify AI
# ---------------------------------------------------------------------------

@authorized_only
async def tg_file(update, context):
    """Handle photos and document attachments from Telegram.

    Saves the file to the active session's CWD and optionally asks the AI
    to process it (if a caption is provided).
    """
    from helm.session_mgr import focused_session
    from helm.ai_runner import process_message
    import tempfile

    # Must have a focused session
    if not _st.focused_id or _st.focused_id not in _st.sessions:
        if _st.sessions:
            await update.message.reply_text(
                "👋 Tap a session first, then send a file:",
                reply_markup=sessions_keyboard(),
            )
        else:
            await update.message.reply_text(
                "👋 No sessions yet. Create one first:",
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

    cwd = sess.get("cwd", os.getcwd())

    # Determine file type
    photo = update.message.photo
    document = update.message.document
    caption = (update.message.caption or "").strip()

    if photo:
        # Get highest resolution photo
        file_obj = await photo[-1].get_file()
        filename = f"telegram_photo_{int(time.time())}.jpg"
    elif document:
        file_obj = await document.get_file()
        filename = document.file_name or f"telegram_file_{int(time.time())}"
    else:
        await update.message.reply_text("⚠️ Unsupported attachment type.")
        return

    # Save to session CWD
    save_path = os.path.join(cwd, filename)
    try:
        await file_obj.download_to_drive(save_path)
    except Exception as exc:
        await update.message.reply_text(f"⚠️ Failed to save file: {exc}")
        return

    fs = focused_session()
    label = f"{fs['emoji']} {fs['name']}" if fs else "session"

    if caption:
        # User wants the AI to process this file
        prompt = f"[File attached: {filename} saved to {cwd}]\n\n{caption}"
        await update.message.reply_text(
            f"📎 Saved `{filename}` to project folder.\n\nProcessing with [{label}]...",
            parse_mode="Markdown",
        )

        async def _tg_file_fire(
            _text: str = prompt,
            _update=update,
        ) -> None:
            try:
                response = await process_message(_text, source="telegram")
                await tg_send_chunks(
                    _update, response,
                    reply_markup=session_controls_keyboard(),
                )
            except Exception as exc:
                logger.warning("tg_file_fire error: %s", exc)
                try:
                    await _update.message.reply_text(f"⚠️ Error: {exc}")
                except Exception:
                    pass

        asyncio.create_task(_tg_file_fire())
    else:
        # Just save, no AI processing
        await update.message.reply_text(
            f"📎 Saved `{filename}` to project folder.\n"
            f"Send a message to tell the AI what to do with it.",
            parse_mode="Markdown",
            reply_markup=session_controls_keyboard(),
        )


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# /pipeline — Task Pipeline & AI Delegation
# ---------------------------------------------------------------------------

@authorized_only
async def tg_pipeline(update, context):
    """/pipeline <prompt> — Decompose a complex task into a multi-AI pipeline."""
    from helm.session_mgr import focused_session, session_cwd
    from helm.broadcast import push_message, push_state
    from helm.pipeline.planner import plan_pipeline, discover_available_ais
    from helm.pipeline.models import pipeline_state_payload, pipeline_progress
    from helm.pipeline.executor import broadcast_pipeline_update
    from .keyboards import pipeline_approval_keyboard, pipeline_list_keyboard
    import os

    text = (update.message.text or "").partition(" ")[2].strip()

    # /pipeline with no args → list existing pipelines
    if not text:
        if not _st.pipelines:
            await update.message.reply_text(
                "🔀 *Task Pipelines*\n\n"
                "No pipelines yet. Create one:\n"
                "`/pipeline <your complex task>`\n\n"
                "Example:\n"
                "`/pipeline Research AI trends, create a report, then summarize key findings`",
                parse_mode="Markdown",
            )
            return
        lines = ["🔀 *Pipelines:*"]
        for pl in sorted(_st.pipelines.values(), key=lambda p: p.get("created_at", 0), reverse=True)[:10]:
            prog = pipeline_progress(pl)
            status_icon = {"running": "🔵", "completed": "✅", "failed": "❌",
                          "paused": "⏸", "awaiting_approval": "🟡", "cancelled": "⚫"}.get(pl["status"], "❓")
            prompt_preview = pl["original_prompt"][:60]
            if len(pl["original_prompt"]) > 60:
                prompt_preview += "…"
            lines.append(
                f"{status_icon} `{pl['id'][:8]}` *{pl['status']}*\n"
                f"  {prompt_preview}\n"
                f"  {prog['completed']}/{prog['total']} steps"
            )
        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode="Markdown",
            reply_markup=pipeline_list_keyboard(),
        )
        return

    # Create a new pipeline
    fs = focused_session()
    cwd = fs["cwd"] if fs else session_cwd()
    sid = fs["id"] if fs else None

    planner_ai = os.environ.get("PIPELINE_PLANNER_AI", "claude")
    await update.message.reply_text("🔀 Planning pipeline — analyzing your task…")

    try:
        pipeline = await plan_pipeline(
            prompt=text,
            session_id=sid,
            cwd=cwd,
            planner_ai=planner_ai,
        )
        _st.pipelines[pipeline["id"]] = pipeline
        await broadcast_pipeline_update(pipeline)

        # Show plan for approval with cost + fallback info
        lines = [f"🔀 *Pipeline Plan* (`{pipeline['id'][:8]}`)"]
        est_cost = pipeline.get("estimated_total_cost", 0)
        if est_cost > 0:
            lines[0] += f"\n💰 Est. cost: ${est_cost:.4f}"
        lines[0] += "\n"
        for i, step in enumerate(pipeline["steps"], 1):
            deps = ""
            if step["depends_on"]:
                deps = f" ← after {', '.join(step['depends_on'])}"
            cost_hint = ""
            if step.get("estimated_cost_usd", 0) > 0:
                cost_hint = f" (~${step['estimated_cost_usd']:.4f})"
            fb = ""
            if step.get("fallback_ais"):
                fb = f" [↩ {','.join(step['fallback_ais'])}]"
            cond = ""
            if step.get("condition"):
                cond = " ⚡conditional"
            lines.append(
                f"*{i}. {step['title']}*\n"
                f"  🤖 {step['assigned_ai']}{cost_hint}{fb}{cond}{deps}\n"
                f"  _{step['description'][:80]}{'…' if len(step['description']) > 80 else ''}_"
            )

        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode="Markdown",
            reply_markup=pipeline_approval_keyboard(pipeline["id"]),
        )

    except Exception as exc:
        logger.error("Pipeline planning failed: %s", exc)
        await update.message.reply_text(f"❌ Pipeline planning failed: {str(exc)[:200]}")
