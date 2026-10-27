"""
helm/telegram_bot/schedule.py — /schedule: create, list and remove scheduled tasks.
"""

import asyncio
from datetime import datetime

import helm.state as _st
from helm.config import CRONITER_OK

from .auth import authorized_only


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
