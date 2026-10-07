"""
helm/web_routes/chat_ws.py — WebSocket endpoint and web command dispatcher.
"""

import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import helm.state as _st
from helm.config import logger
from helm.session_mgr import focused_session, make_session, session_cwd, sessions_state_payload
from helm.broadcast import push_message, push_state, push_thinking
from helm.history import ts
from helm.ai_runner import change_cwd, forward_to_telegram, process_message, tg_update_focus, kill_session_proc
from helm.scheduler import (
    make_sched_task, next_cron_run, run_scheduled_task,
    save_scheduled_tasks, sched_tasks_payload,
)
from helm.file_tracker import emit_session_end_summary
import helm.auth as _auth


router = APIRouter()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    # Reject unauthenticated WebSocket connections when a PIN is configured
    if _auth.pin_is_set():
        token = websocket.cookies.get(_auth.COOKIE_NAME)
        if not _auth.is_valid_token(token):
            logger.warning(
                "WS auth rejected — PIN is set but client cookie is %s. "
                "Client should re-login at /login to get a fresh auth cookie.",
                "missing" if not token else "expired/invalid",
            )
            await websocket.close(code=4401, reason="auth_required")
            return
    await websocket.accept()
    _st.ws_clients.add(websocket)
    logger.info("WS client connected (total: %d)", len(_st.ws_clients))

    try:
        try:
            fs = focused_session()
            state_msg = {
                "type": "state",
                "sessions": sessions_state_payload(),
                "focused_id": _st.focused_id,
                "focused_ai": fs["ai"] if fs else None,
                "focused_cwd": fs["cwd"] if fs else _st.last_cwd,
                "focused_status": fs["status"] if fs else None,
            }
            await websocket.send_text(json.dumps(state_msg, default=str))
        except Exception as init_err:
            logger.error("WS init-state error: %s", init_err, exc_info=True)
            await websocket.send_text(json.dumps({
                "type": "state", "sessions": [], "focused_id": None,
                "focused_ai": None, "focused_cwd": _st.last_cwd,
                "focused_status": None,
            }))

        # Replay recent chat history
        for msg in _st.chat_history[-50:]:
            try:
                await websocket.send_text(json.dumps(msg, default=str))
            except Exception:
                break

        # Main receive loop
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                content = data.get("content", "").strip()
                if not content:
                    continue
                # Allow client to target a specific session (e.g. voice auto-send)
                _dispatch_sid = data.get("session_id") or _st.focused_id
                sess = _st.sessions.get(_dispatch_sid) if _dispatch_sid else None
                manager_waiting_run_id = sess.get("agent_manager_waiting_run_id") if sess else None
                if manager_waiting_run_id:
                    try:
                        from helm.agent.nodes.input_node import resume_run
                        if resume_run(manager_waiting_run_id, content):
                            waiting_kind = sess.get("agent_manager_waiting_kind")
                            sess.pop("agent_manager_waiting_run_id", None)
                            sess.pop("agent_manager_waiting_kind", None)
                            sess.pop("agent_manager_waiting_node_id", None)
                            await push_message("user", content, source="web", session_id=_dispatch_sid)
                            system_text = (
                                "Input received. Passing it to the waiting workflow step."
                                if waiting_kind == "input"
                                else "Manager feedback received. Updating the workflow and rerunning the affected steps."
                            )
                            await push_message(
                                "system",
                                system_text,
                                source="agent",
                                session_id=_dispatch_sid,
                            )
                            continue
                    except Exception as exc:
                        logger.warning("Could not route manager feedback from focused session: %s", exc)

                try:
                    from helm.agent.nodes.input_node import resume_run_for_session
                    if resume_run_for_session(_dispatch_sid, content):
                        await push_message("user", content, source="web", session_id=_dispatch_sid)
                        await push_message(
                            "system",
                            "Input received. Passing it to the waiting workflow step.",
                            source="agent",
                            session_id=_dispatch_sid,
                        )
                        continue
                except Exception as exc:
                    logger.warning("Could not route agent input from focused session: %s", exc)

                # Track chat message usage
                try:
                    from helm.device_link import track_usage
                    track_usage("chat", "message_sent", {
                        "source": "web",
                        "ai": sess.get("ai") if sess else None,
                        "model": sess.get("model") if sess else None,
                    })
                except Exception:
                    pass

                async def _fire_and_forward(
                    _text: str = content,
                    _sid: str = _dispatch_sid,
                ) -> None:
                    response = await process_message(_text, source="web", session_id=_sid)
                    # Telegram notification is handled by tg_progress_notify()
                    # inside process_message — no need to forward again here.

                asyncio.create_task(_fire_and_forward())

            elif data.get("type") == "command":
                cmd = data.get("command", "")
                if cmd == "cwd":
                    await change_cwd(data.get("path", ""), source="web")
                else:
                    try:
                        await handle_web_command(cmd, websocket)
                    except Exception as _cmd_err:
                        logger.warning("Command error (%s): %s", cmd, _cmd_err)
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "message", "role": "system",
                                "content": f"⚠️ Command failed: {_cmd_err}",
                                "source": "web", "timestamp": ts(),
                            }))
                        except Exception:
                            pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WS error: %s", e, exc_info=True)
    finally:
        _st.ws_clients.discard(websocket)
        logger.info("WS client disconnected (total: %d)", len(_st.ws_clients))


# ---------------------------------------------------------------------------
# Web command handler
# ---------------------------------------------------------------------------

CREW_WAIT_SECONDS = 15


async def call_kelvin_crew(sess: dict) -> bool:
    """Stop the session's solo run (if any) and re-run its last big task as a pipeline.

    Returns True when the pipeline was started.
    """
    prompt = sess.get("crew_prompt")
    if not prompt:
        await push_message("system", "There's no recent task for the Kelvin crew to pick up.",
                           source="web", session_id=sess["id"])
        return False

    lock = sess.get("_lock")
    if lock and lock.locked():
        kill_session_proc(sess)
        sess["busy"] = False
        sess["task_start"] = None
        await push_thinking(False, session_id=sess["id"])
        await push_message("system", "⏸ Stopped the solo run. Calling the Kelvin crew…",
                           source="web", session_id=sess["id"])
        waited = 0.0
        while lock.locked() and waited < CREW_WAIT_SECONDS:
            await asyncio.sleep(0.2)
            waited += 0.2
        if lock.locked():
            await push_message(
                "system",
                "The current run hasn't stopped yet, so the crew can't start. "
                "Try again when it finishes.",
                source="web", session_id=sess["id"],
            )
            return False

    sess.pop("crew_prompt", None)
    asyncio.create_task(process_message(f"/pipeline {prompt}", source="web", session_id=sess["id"]))
    return True


async def handle_web_command(command: str, ws: WebSocket):
    """Handle control commands sent from the web UI (multi-session aware)."""
    from helm.terminal import TerminalSession

    # --- new_session:{ai}[|cwd[|model]] ---
    if command.startswith("new_session:"):
        payload = command.split(":", 1)[1].strip()
        ai_key = None
        target_cwd = session_cwd()
        chosen_model: str | None = None

        parts = payload.split("|")
        ai_key     = parts[0] if len(parts) > 0 else ""
        target_cwd = parts[1] if len(parts) > 1 and parts[1].strip() else session_cwd()
        chosen_model = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None

        if ai_key == "shell":
            ai_key = None

        sess = make_session(ai_key, cwd=target_cwd, model=chosen_model)
        _st.focused_id = sess["id"]
        await push_state()
        label = sess["emoji"] + " " + sess["name"]

        # Track session creation
        try:
            from helm.device_link import track_usage
            track_usage("session", "created", {"ai": ai_key or "shell", "model": chosen_model})
        except Exception:
            pass
        actual_model = sess.get("model")
        if chosen_model:
            model_note = f" [{chosen_model}]"
        elif actual_model:
            model_note = f" [default: {actual_model}]"
        else:
            model_note = ""
        await push_message("system", f"Session created: {label}{model_note}", source="web",
                           session_id=sess["id"])
        await tg_update_focus()
        return

    # --- set_model:{model_name} ---
    if command.startswith("set_model:"):
        import subprocess as _sp
        model_val = command.split(":", 1)[1].strip()
        sess = focused_session()
        if sess:
            sess["model"] = model_val or None
            ai_key = sess.get("ai") or ""
            if ai_key in ("claude", "gemini", "codex", "ollama"):
                try:
                    from helm.model_prefs import set_model_pref
                    set_model_pref(ai_key, model_val or None)
                except Exception:
                    pass
            await push_state()
            label = f"`{model_val}`" if model_val else "default"
            await push_message("system", f"✅ Model switched to {label}", source="web",
                               session_id=sess["id"])
            # For Ollama: warn if the selected model isn't installed locally
            if model_val and sess.get("ai") == "ollama":
                try:
                    _r = _sp.run(
                        ["ollama", "list"],
                        capture_output=True, text=True, timeout=5,
                    )
                    _local = []
                    for _ln in _r.stdout.strip().splitlines()[1:]:
                        _p = _ln.split()
                        if _p:
                            _local.append(_p[0].strip())
                    if _local and model_val not in _local:
                        _names = ", ".join(f"`{m}`" for m in _local)
                        await push_message(
                            "system",
                            f"⚠️ **`{model_val}`** is not installed locally.\n"
                            f"Locally available: {_names}\n"
                            f"Ollama will attempt to pull `{model_val}` from the registry "
                            f"on your next message. Use `/model default` to revert.",
                            source="web", session_id=sess["id"],
                        )
                except Exception:
                    pass
        return

    # --- focus:{sid} ---
    if command.startswith("focus:"):
        sid = command.split(":", 1)[1]
        if sid in _st.sessions:
            _st.focused_id = sid
            await push_state()
            await tg_update_focus()
        return

    # --- stop_session ---
    if command == "stop_session":
        sess = focused_session()
        if sess:
            kill_session_proc(sess)
            sess["terminal"].stop()
            await emit_session_end_summary(sess, ended_as="stopped", source="web")
            sess["status"] = "stopped"
            sess["busy"]      = False
            sess["task_start"] = None
            # Preserve the CWD so next session starts on the same path
            if sess.get("cwd"):
                _st.last_cwd = sess["cwd"]
            await push_thinking(False, session_id=sess["id"])
            await push_state()
        return

    # --- delete_session ---
    if command == "delete_session":
        sess = focused_session()
        if sess:
            kill_session_proc(sess)
            sess["terminal"].stop()
            await emit_session_end_summary(sess, ended_as="deleted", source="web")
            sid = sess["id"]
            # Preserve the CWD so next session starts on the same path
            if sess.get("cwd"):
                _st.last_cwd = sess["cwd"]
            # Cache CWD so late-arriving messages still log to the right file
            _st.deleted_session_cwds[sid] = sess.get("cwd") or _st.last_cwd
            del _st.sessions[sid]
            _st.focused_id = max(_st.sessions, key=lambda k: _st.sessions[k]["last_used"],
                                 default=None) if _st.sessions else None
            await push_state()
        return

    # --- switch_ai:{ai} ---
    if command.startswith("switch_ai:"):
        sess = focused_session()
        if sess:
            ai_key = command.split(":", 1)[1].strip()
            if ai_key == "shell":
                ai_key = None
                if not sess["terminal"].is_alive():
                    await asyncio.to_thread(sess["terminal"].launch)
            sess["ai"] = ai_key
            sess["claude_msgs"] = []
            if ai_key == "claude":
                sess["emoji"] = "🤖"; sess["color"] = "#f59e0b"
            elif ai_key and ai_key in _st.integrations:
                info = _st.integrations[ai_key]
                sess["emoji"] = info["emoji"]; sess["color"] = info["color"]
            else:
                sess["emoji"] = "🐚"; sess["color"] = "#6b7280"
            await push_state()
            await push_message("system",
                f"Switched to {sess['emoji']} {ai_key or 'Shell'}", source="web",
                session_id=sess["id"])
        return

    # --- interrupt ---
    if command == "interrupt":
        sess = focused_session()
        if sess:
            try:
                if sess["ai"]:
                    kill_session_proc(sess)
                    sess["busy"]       = False
                    sess["task_start"] = None
                    await push_thinking(False, session_id=sess["id"])
                    await push_state()
                    await push_message("system", "⏸ Task cancelled.", source="web",
                                       session_id=sess["id"])
                else:
                    sess["terminal"].send_interrupt()
                    await push_message("system", "Ctrl+C sent.", source="web",
                                       session_id=sess["id"])
            except RuntimeError as e:
                await push_message("system", str(e), source="web")
        return

    # --- crew: re-run the last big task as a parallel pipeline ---
    if command == "crew":
        sess = focused_session()
        if sess:
            await call_kelvin_crew(sess)
        return

    # --- clear ---
    if command == "clear":
        sess = focused_session()
        if sess:
            sess["claude_msgs"] = []
            await push_message("system", "Claude conversation history cleared.", source="web",
                               session_id=sess["id"])
        return

    # --- compact (context window compaction) ---
    if command == "compact":
        sess = focused_session()
        if sess:
            from helm.context_manager import force_compact
            result = await force_compact(sess, source="web")
            await push_message("system", result, source="web", session_id=sess["id"])
            await push_state()
        return

    # --- schedule_list ---
    if command == "schedule_list":
        await ws.send_text(json.dumps({
            "type":  "schedule_list",
            "tasks": sched_tasks_payload(),
        }))
        return

    # --- schedule_add:<cron>|<ai>|<cwd>|<prompt> ---
    if command.startswith("schedule_add:"):
        parts = command[len("schedule_add:"):].split("|", 3)
        if len(parts) < 4:
            await push_message("system", "❌ Invalid schedule_add format.", source="web")
            return
        cron_expr = parts[0].strip()
        ai_key    = parts[1].strip() or None
        task_cwd  = parts[2].strip() or session_cwd()
        prompt    = parts[3].strip()

        if not prompt:
            await push_message("system", "❌ Prompt cannot be empty.", source="web")
            return
        if next_cron_run(cron_expr) is None:
            await push_message("system",
                f"❌ Invalid cron expression: {cron_expr}  (needs 5 fields, e.g. 0 9 * * *)",
                source="web")
            return
        if ai_key not in ("claude", None, "", *_st.integrations):
            ai_key = None

        task = make_sched_task(cron_expr, ai_key or None, prompt, cwd=task_cwd)
        _st.scheduled_tasks[task["id"]] = task
        save_scheduled_tasks()
        nr = datetime.fromtimestamp(task["next_run"]).strftime("%Y-%m-%d %H:%M") \
             if task.get("next_run") else "?"
        await push_message("system",
            f"⏰ Scheduled *{task['name']}* (`{task['id']}`)\n"
            f"`{cron_expr}` · {ai_key or 'shell'} · next: {nr}",
            source="web")
        await ws.send_text(json.dumps({"type": "schedule_list", "tasks": sched_tasks_payload()}))
        return

    # --- schedule_delete:<id> ---
    if command.startswith("schedule_delete:"):
        tid = command[len("schedule_delete:"):].strip()
        if tid in _st.scheduled_tasks:
            name = _st.scheduled_tasks[tid]["name"]
            del _st.scheduled_tasks[tid]
            save_scheduled_tasks()
            await push_message("system", f"🗑️ Deleted scheduled task: {name}", source="web")
        await ws.send_text(json.dumps({"type": "schedule_list", "tasks": sched_tasks_payload()}))
        return

    # --- schedule_toggle:<id> ---
    if command.startswith("schedule_toggle:"):
        tid = command[len("schedule_toggle:"):].strip()
        if tid in _st.scheduled_tasks:
            task = _st.scheduled_tasks[tid]
            task["enabled"] = not task["enabled"]
            if task["enabled"]:
                task["next_run"] = next_cron_run(task["cron"])
            save_scheduled_tasks()
        await ws.send_text(json.dumps({"type": "schedule_list", "tasks": sched_tasks_payload()}))
        return

    # --- schedule_run:<id> ---
    if command.startswith("schedule_run:"):
        tid = command[len("schedule_run:"):].strip()
        if tid in _st.scheduled_tasks:
            task = _st.scheduled_tasks[tid]
            await push_message("system", f"▶️ Running *{task['name']}* now...", source="web")
            asyncio.create_task(run_scheduled_task(task))
        return


_handle_web_command = handle_web_command  # legacy alias
