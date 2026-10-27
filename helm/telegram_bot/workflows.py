"""
helm/telegram_bot/workflows.py — /pipeline and /agent.
"""


import helm.state as _st
from helm.config import logger

from .auth import authorized_only


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# /pipeline — Task Pipeline & AI Delegation
# ---------------------------------------------------------------------------

@authorized_only
async def tg_pipeline(update, context):
    """/pipeline <prompt> — Decompose a complex task into a multi-AI pipeline."""
    from helm.session_mgr import focused_session, session_cwd
    from helm.pipeline.planner import plan_pipeline
    from helm.pipeline.models import pipeline_progress
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


# ---------------------------------------------------------------------------
# /agent — Agent workflow automation
# ---------------------------------------------------------------------------

@authorized_only
async def tg_agent(update, context):
    """/agent [name] — List agents or run a named agent."""
    from helm.agent.models import agent_slug_match
    from helm.agent.runner import trigger_agent_run
    from helm.session_mgr import focused_session
    from .keyboards import agent_list_keyboard

    text = (update.message.text or "").partition(" ")[2].strip()

    # /agent with no args → list all agents as inline buttons
    if not text:
        if not _st.agents:
            await update.message.reply_text(
                "✦ *Agents*\n\n"
                "No agents yet. Build one in the web UI:\n"
                "• Open the *Agents* tab\n"
                "• Click *New Agent* to design your workflow\n"
                "• Then use `/agent <name>` to run it here",
                parse_mode="Markdown",
            )
            return

        lines = ["✦ *Agents* — tap to run:"]
        for ag in sorted(_st.agents.values(), key=lambda a: a.get("name", "")):
            rc = ag.get("run_count", 0)
            lines.append(f"  • {ag['name']} ({len(ag.get('nodes', []))} nodes, {rc} runs)")

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=agent_list_keyboard(),
        )
        return

    # /agent <name> → find agent by slug and run it
    slug = text.strip()
    matched = None
    for ag in _st.agents.values():
        if agent_slug_match(ag["name"], slug):
            matched = ag
            break

    if not matched:
        # Try partial name match
        slug_lower = slug.lower().replace("-", " ").replace("_", " ")
        for ag in _st.agents.values():
            if slug_lower in ag["name"].lower():
                matched = ag
                break

    if not matched:
        names = ", ".join(f"`{ag['name']}`" for ag in _st.agents.values())
        await update.message.reply_text(
            f"❌ No agent found matching `{slug}`.\n\n"
            f"Available: {names or '(none yet)'}",
            parse_mode="Markdown",
        )
        return

    fs = focused_session()
    session_id = fs["id"] if fs else None

    await update.message.reply_text(
        f"✦ Starting agent: *{matched['name']}* ({len(matched.get('nodes', []))} nodes)…",
        parse_mode="Markdown",
    )

    run = await trigger_agent_run(matched["id"], trigger="telegram", session_id=session_id)
    if not run:
        await update.message.reply_text("❌ Failed to start agent — it may have no nodes.")
        return

    await update.message.reply_text(
        f"✦ *{matched['name']}* is running (`{run['id'][:8]}`).\n"
        f"I'll message you here only when input is needed or the final output is ready.",
        parse_mode="Markdown",
    )
