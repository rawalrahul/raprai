"""Human-in-the-loop input node executor."""

import asyncio

# B3: key futures by (run_id, node_id) so manager + input node can wait concurrently
# on the same run without overwriting each other's futures.
_pending_inputs: dict[tuple[str, str | None], asyncio.Future] = {}
# session_id → (run_id, node_id) so resume-by-session knows exactly which node to resolve.
_pending_input_sessions: dict[str, tuple[str, str | None]] = {}
_telegram_notified_runs: set[str] = set()


def _find_pending_key(run_id: str, node_id: str | None = None) -> tuple[str, str | None] | None:
    """Locate a pending future's key. If node_id is None, return any pending key for run_id."""
    if node_id is not None:
        key = (run_id, node_id)
        return key if key in _pending_inputs else None
    for key in _pending_inputs:
        if key[0] == run_id:
            return key
    return None


async def wait_for_input(run_id: str, timeout: int = 3600, node_id: str | None = None) -> str:
    """Wait for resume_run() to resolve this run's input future."""
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    key = (run_id, node_id)
    _pending_inputs[key] = fut
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        return f"(timed out after {timeout}s - no user input received)"
    finally:
        _pending_inputs.pop(key, None)
        for session_id, pending in list(_pending_input_sessions.items()):
            if pending == key:
                _pending_input_sessions.pop(session_id, None)


def resume_run(run_id: str, user_input: str, node_id: str | None = None) -> bool:
    """Resume a waiting input node. If node_id omitted, resolve any pending future for run_id."""
    key = _find_pending_key(run_id, node_id)
    if key is None:
        return False
    fut = _pending_inputs.get(key)
    if fut and not fut.done():
        fut.set_result(user_input)
        return True
    return False


def resume_run_for_session(session_id: str | None, user_input: str) -> bool:
    """Resume the input node currently waiting in a UI/Telegram session."""
    if not session_id:
        return False
    pending = _pending_input_sessions.get(session_id)
    if not pending:
        return False
    run_id, node_id = pending
    return resume_run(run_id, user_input, node_id=node_id)


def mark_session_waiting_for_run(
    session_id: str | None,
    run_id: str | None,
    node_id: str | None = None,
) -> None:
    """Map a focused chat/Telegram session to a waiting agent run+node."""
    if session_id and run_id:
        _pending_input_sessions[session_id] = (run_id, node_id)


async def execute_input_node(node: dict, run: dict, context: str) -> str:
    """Broadcast a question and wait for user input."""
    question = node.get("task", "Please provide input:").strip()
    timeout = node.get("input_timeout", 3600)
    from helm.broadcast import broadcast
    from helm.broadcast import push_message

    session_id = run.get("session_id")
    if session_id:
        mark_session_waiting_for_run(session_id, run["id"], node_id=node["id"])
    await broadcast({
        "type": "agent_run_waiting_input",
        "run_id": run["id"],
        "node_id": node["id"],
        "question": question,
        "session_id": session_id,
        "kind": "input",
    })
    if session_id:
        try:
            node_title = node.get("title") or "Input step"
            await push_message(
                "system",
                f"{node_title} needs input:\n\n{question}",
                source="agent",
                session_id=session_id,
            )
        except Exception:
            pass
    await _notify_telegram_input_needed(run, node, question, session_id)
    user_input = await wait_for_input(run["id"], timeout=timeout, node_id=node["id"])
    return user_input


async def _notify_telegram_input_needed(
    run: dict,
    node: dict,
    question: str,
    session_id: str | None,
) -> None:
    """Send an actual Telegram bot message when a run is blocked on input."""
    run_id = run.get("id")
    notify_key = f"{run_id}:{node.get('id')}"
    if not run_id or notify_key in _telegram_notified_runs:
        return
    try:
        import helm.state as _st
        if not (_st.telegram_app and _st.telegram_chat_id):
            return

        agent_name = run.get("agent_name") or "Agent"
        node_title = node.get("title") or "Input step"
        text = (
            f"{agent_name} is waiting for your input.\n\n"
            f"Step: {node_title}\n\n"
            f"{question}\n\n"
            "Reply to this chat with the required text, or upload the resume/document here. "
            "I will attach it to the waiting workflow and continue automatically."
        )

        reply_markup = None
        try:
            from helm.telegram_bot import session_controls_keyboard
            reply_markup = session_controls_keyboard()
        except Exception:
            pass

        await _st.telegram_app.bot.send_message(
            chat_id=_st.telegram_chat_id,
            text=text,
            reply_markup=reply_markup,
        )
        _telegram_notified_runs.add(notify_key)

        try:
            from helm.broadcast import push_message
            await push_message(
                "system",
                text,
                source="agent",
                session_id=session_id,
            )
        except Exception:
            pass
    except Exception:
        pass


async def extract_file_text_from_telegram(
    file_id: str | None,
    mime_type: str | None,
    bot,
) -> str | None:
    """
    Download a Telegram file and extract its text content.
    Returns text string or None if unsupported/failed.
    Supported: text/*, application/pdf, application/vnd.openxmlformats (docx)
    """
    if not file_id or not bot:
        return None

    supported_mime_prefixes = ("text/", "application/pdf", "application/vnd.openxmlformats")
    if mime_type and not any(mime_type.startswith(p) for p in supported_mime_prefixes):
        return None

    try:
        import os
        import tempfile
        import time as _time

        tg_file = await bot.get_file(file_id)
        suffix = ".bin"
        if mime_type == "application/pdf":
            suffix = ".pdf"
        elif "openxmlformats" in (mime_type or ""):
            suffix = ".docx"
        elif mime_type and mime_type.startswith("text/"):
            suffix = ".txt"

        # B7: NamedTemporaryFile with delete=False + explicit close before download
        # prevents Windows from holding the handle open during download_to_drive.
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(tmp_fd)  # release handle so download_to_drive can open the file

        try:
            await tg_file.download_to_drive(tmp_path)

            if suffix == ".pdf":
                from pdfminer.high_level import extract_text
                text = extract_text(tmp_path)
            elif suffix == ".docx":
                from docx import Document
                doc = Document(tmp_path)
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            else:
                with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            return text.strip() or None
        finally:
            # B7: retry unlink once on Windows where antivirus/indexer may hold handle briefly.
            for _attempt in range(2):
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    break
                except OSError:
                    if _attempt == 0:
                        _time.sleep(0.1)

    except Exception as exc:
        from helm.config import logger
        logger.warning("Failed to extract Telegram file text: %s", exc)
        return None
