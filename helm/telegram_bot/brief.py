"""
helm/telegram_bot/brief.py — Your brief on Telegram.

  /brief        your latest brief, with a button per item
  /brief now    put a fresh one together (asks the AIs you picked to look)

Buttons: ▶ hands an item to its AI in a new session (the reply comes back
here), ✕ drops it, ✅/❌ answer an approval without leaving the brief.
"""

import helm.config as _cfg   # read ALLOWED_USER_IDS live: startup replaces it after the vault loads

from .auth import authorized_only


@authorized_only
async def tg_brief(update, context):
    from helm import brief
    args = [a.lower() for a in (context.args or [])]
    latest = brief.latest()
    if args[:1] == ["now"] or not latest:
        await update.message.reply_text("🐧 Putting your brief together…")
        latest = await brief.run("manual", deliver=False)
        if latest is None:
            await update.message.reply_text("A brief is already being put together; it'll arrive shortly.")
            return
    await update.message.reply_text(brief.text(latest, how_to_act=False)[:4000],
                                    reply_markup=brief.telegram_keyboard(latest))


async def brief_callback(update, context):
    """brief:do:<n>, brief:skip:<n>, brief:ok:<approval id>, brief:no:<approval id>."""
    import helm.approval as appr
    import helm.state as _st
    from helm import brief
    from helm.ai_runner import forward_to_telegram, process_message

    query = update.callback_query
    if not _cfg.ALLOWED_USER_IDS or query.from_user.id not in _cfg.ALLOWED_USER_IDS:
        await query.answer("Not authorized.", show_alert=True)
        return
    parts = query.data.split(":", 2)
    verb = parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else ""

    if verb in ("ok", "no"):
        status = "approved" if verb == "ok" else "denied"
        if appr.resolve(arg, status, source="telegram"):
            req = _st.approval_queue.get(arg)
            if req:
                await appr.broadcast_resolution(req)
            await query.answer("✅ Approved" if status == "approved" else "❌ Denied")
        else:
            await query.answer("That was already decided.")
        return

    if verb == "skip":
        await query.answer("Dropped" if brief.set_status(arg, "dismissed") else "Not in your latest brief")
        await brief._broadcast(brief.latest())
        return

    if verb == "do":
        sess, prompt = await brief.start_item(arg, source="telegram")
        if not sess:
            await query.answer(prompt[:190], show_alert=True)
            return
        await query.answer("Started")
        it = brief.item(brief.latest(), arg) or {}
        await forward_to_telegram(f"▶ {sess['emoji']} {sess['name']} is on it: {it.get('title', '')}\n"
                                  "Anything it wants to send or change will ask you first.")
        reply = await process_message(prompt, source="telegram", session_id=sess["id"])
        text = reply or "(no output)"
        for i in range(0, len(text), 3800):
            await forward_to_telegram(text[i:i + 3800])
        return

    await query.answer()
