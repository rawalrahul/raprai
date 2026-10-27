"""
helm/telegram_bot/media.py — Voice notes and files sent to the bot.
"""

import asyncio
import os
import shutil
import time

import helm.state as _st
from helm.config import logger

from .auth import authorized_only, tg_send_chunks
from .keyboards import sessions_keyboard, session_controls_keyboard, new_session_keyboard


# ---------------------------------------------------------------------------
# Voice message handler — Whisper speech-to-text → process_message
# ---------------------------------------------------------------------------

def _agent_file_input_payload(path: str, filename: str, caption: str = "") -> str:
    """Build text payload for a Telegram file sent to a waiting agent input node."""
    try:
        from helm.web_routes.agent_routes import _extract_agent_input_file_text
        extracted = _extract_agent_input_file_text(path, filename)
    except Exception as exc:
        extracted = f"(file uploaded, but text extraction failed: {exc})"
    caption_block = f"\n\nUser note:\n{caption}" if caption else ""
    return (
        f"Uploaded file: {filename}\n"
        f"Saved path: {path}{caption_block}\n\n"
        f"=== Extracted File Text ===\n{extracted}\n=== End Extracted File Text ==="
    )


@authorized_only
async def tg_voice(update, context):
    """Transcribe voice/audio messages via Whisper and forward to the active AI."""
    from helm.session_mgr import focused_session
    from helm.ai_runner import process_message
    import os
    import tempfile

    from helm.mention_router import parse_kelvin

    async def _needs_session() -> bool:
        """Without "Hey Kelvin", a voice message needs a running focused session."""
        if not _st.focused_id or _st.focused_id not in _st.sessions:
            if _st.sessions:
                await update.message.reply_text(
                    "👋 Tap a session first (or start with \"Hey Kelvin\"), then send a voice message:",
                    reply_markup=sessions_keyboard(),
                )
            else:
                await update.message.reply_text(
                    "👋 No sessions yet. Create one first, or start with \"Hey Kelvin\":",
                    reply_markup=new_session_keyboard(),
                )
            return True
        sess = _st.sessions.get(_st.focused_id)
        if sess and sess["status"] == "stopped":
            await update.message.reply_text(
                f"✨ *{sess['name']}* is stopped. Resume it or switch session:",
                parse_mode="Markdown",
                reply_markup=sessions_keyboard(),
            )
            return True
        return False

    # Download the voice/audio file from Telegram
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("⚠️ No audio found in message.",
                                        reply_markup=session_controls_keyboard())
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
        shutil.rmtree(tmp_dir, ignore_errors=True)

        if not transcript or not transcript.strip():
            await update.message.reply_text("⚠️ Could not transcribe audio — no speech detected.",
                                            reply_markup=session_controls_keyboard())
            return

        to_kelvin = parse_kelvin(transcript) is not None
        if not to_kelvin and await _needs_session():
            return

        # Show the transcript to the user
        fs = focused_session()
        label = f"{fs['emoji']} {fs['name']}" if fs else "session"
        if to_kelvin:
            label = "🐧 Kelvin"
        import helm.groupchat as _gc
        _grp = _gc.active_group("telegram")
        if _grp:
            label = f"👥 {_grp['name']}"
        await update.message.reply_text(
            f"🎤 *Transcript:* {transcript}\n\nThinking... [{label}]",
            parse_mode="Markdown",
        )

        # Route to a waiting Agent Builder input node before falling through to AI.
        # Mirrors tg_text behavior so voice messages can satisfy human-in-the-loop steps.
        try:
            from helm.agent.nodes.input_node import resume_run_for_session
            if fs and resume_run_for_session(fs.get("id"), transcript):
                await update.message.reply_text(
                    "Input received. Continuing the agent workflow...",
                    reply_markup=session_controls_keyboard(),
                )
                return
        except Exception as exc:
            logger.warning("Could not resume agent input from Telegram voice: %s", exc)

        # In a group chat the transcript goes to the group, like typed text.
        from .groups import handle_group_text
        if await handle_group_text(update, transcript):
            return

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
                    await _update.message.reply_text(
                        f"⚠️ Error: {exc}",
                        reply_markup=session_controls_keyboard(),
                    )
                except Exception:
                    logger.debug("Couldn't send the error to Telegram", exc_info=True)

        asyncio.create_task(_tg_voice_fire())

    except Exception as exc:
        logger.warning("Voice transcription error: %s", exc)
        await update.message.reply_text(f"⚠️ Voice transcription failed: {exc}",
                                        reply_markup=session_controls_keyboard())


# Whisper speech-to-text lives in helm/voice.py, shared with the other chat apps.
from helm.voice import transcribe_file as _transcribe_audio  # noqa: E402


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
        await update.message.reply_text("⚠️ Unsupported attachment type.",
                                        reply_markup=session_controls_keyboard())
        return

    # Save to session CWD
    save_path = os.path.join(cwd, filename)
    try:
        await file_obj.download_to_drive(save_path)
    except Exception as exc:
        await update.message.reply_text(f"⚠️ Failed to save file: {exc}",
                                        reply_markup=session_controls_keyboard())
        return

    fs = focused_session()
    label = f"{fs['emoji']} {fs['name']}" if fs else "session"

    try:
        from helm.agent.nodes.input_node import resume_run_for_session
        if fs and resume_run_for_session(
            fs.get("id"),
            _agent_file_input_payload(save_path, filename, caption),
        ):
            await update.message.reply_text(
                f"Saved `{filename}` and sent it to the waiting agent. Continuing workflow...",
                parse_mode="Markdown",
                reply_markup=session_controls_keyboard(),
            )
            return
    except Exception as exc:
        logger.warning("Could not resume agent input from Telegram file: %s", exc)

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
                    await _update.message.reply_text(
                        f"⚠️ Error: {exc}",
                        reply_markup=session_controls_keyboard(),
                    )
                except Exception:
                    logger.debug("Couldn't send the error to Telegram", exc_info=True)

        asyncio.create_task(_tg_file_fire())
    else:
        # Just save, no AI processing
        await update.message.reply_text(
            f"📎 Saved `{filename}` to project folder.\n"
            f"Send a message to tell the AI what to do with it.",
            parse_mode="Markdown",
            reply_markup=session_controls_keyboard(),
        )
