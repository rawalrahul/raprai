"""
helm/agent/nodes/manager.py — Manager node executor.

Orchestrates the agent run by collecting user feedback after completion,
identifying which node to improve, updating it, and triggering a re-run.

Node config:
  task:                Optional instructions/persona for the manager AI
  manager_max_iter:    Max improvement cycles (default 3)
  deliver_channel:     "telegram" | "ui" — where to send summary + ask for feedback
  deliver_to:          recipient (for telegram)
"""

import json
import re
from helm.config import logger

APPROVAL_KEYWORDS = {
    "yes", "yep", "yeah", "ok", "okay", "approved", "approve",
    "lgtm", "looks good", "good", "great", "perfect", "done",
    "ship it", "correct", "right", "exactly",
}


def is_approval(reply: str) -> bool:
    """Return True if reply indicates user approval."""
    normalized = reply.strip().lower()
    # Short single-word approval
    if normalized in APPROVAL_KEYWORDS:
        return True
    # Phrase-level check
    for kw in APPROVAL_KEYWORDS:
        if kw in normalized and len(normalized) < 30:
            return True
    return False


def parse_manager_reply(reply: str) -> dict:
    """Parse user reply into {approved: bool, feedback: str}."""
    return {
        "approved": is_approval(reply),
        "feedback": reply.strip(),
    }


async def build_run_summary(run: dict) -> str:
    """Compile all node outputs into a readable summary for the user."""
    lines = [f"Agent: {run['agent_name']}", ""]
    for node in run["nodes"]:
        if node.get("type") == "manager":
            continue
        status = node.get("status", "?")
        output = node.get("output") or "(no output)"
        if len(output) > 500:
            output = output[:500] + "..."
        lines.append(f"**{node['title']}** [{status}]")
        lines.append(output)
        lines.append("")
    return "\n".join(lines)


async def identify_and_fix_node(
    run: dict,
    feedback: str,
    agent_nodes: list[dict],
) -> dict | None:
    """
    Use AI to identify which node caused the issue and generate an improved task.
    Returns {"node_id": str, "new_task": str} or None if identification fails.
    """
    from helm.ai_runner.core import process_message
    import helm.state as _st

    # Build context: all node titles + tasks + outputs
    node_summary = ""
    for n in agent_nodes:
        if n.get("type") == "manager":
            continue
        node_summary += (
            f"Node ID: {n['id']}\n"
            f"Title: {n['title']}\n"
            f"Type: {n.get('type','ai')}\n"
            f"Current task: {n.get('task','')[:300]}\n\n"
        )

    run_outputs = ""
    for n in run["nodes"]:
        if n.get("type") == "manager":
            continue
        out = n.get("output") or "(none)"
        run_outputs += f"[{n['title']}]: {out[:300]}\n\n"

    prompt = f"""You are a workflow improvement assistant.

The user ran an agent and gave this feedback:
"{feedback}"

Here are the agent's nodes:
{node_summary}

Here are the outputs from this run:
{run_outputs}

Task:
1. Identify EXACTLY which node (by ID) is most responsible for the user's complaint.
2. Write an improved task prompt for that node that addresses the feedback.

Respond with ONLY a JSON object in this exact format (no markdown, no code fences):
{{"node_id": "<the node id>", "new_task": "<the complete improved task text>"}}
"""

    sess = _st.sessions.get(run.get("manager_session_id"))
    if not sess:
        from helm.session_mgr import make_session, session_cwd
        sess = make_session("claude", cwd=session_cwd())
        sess["name"] = run.get("agent_name") or "Agent Manager"
        sess["emoji"] = "🧭"
        sess["agent_manager"] = True
        sess["agent_manager_run_id"] = run.get("id")
        sess["agent_id"] = run.get("agent_id")
        run["manager_session_id"] = sess["id"]
    try:
        response = await process_message(prompt, source="agent", session_id=sess["id"])
    except Exception as exc:
        logger.warning("Manager node AI call failed: %s", exc)
        return None

    # B10: parse JSON first; fall back to regex if AI adds prose or code fences.
    parsed = _parse_manager_fix_response(response)
    if not parsed:
        logger.warning("Manager node: could not parse AI response: %s", response[:200])
    return parsed


def _parse_manager_fix_response(response: str) -> dict | None:
    """Parse node_id + new_task from AI response. JSON preferred, regex fallback."""
    # Try JSON — strip optional markdown fences first.
    json_text = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()
    try:
        obj = json.loads(json_text)
        node_id = obj.get("node_id", "").strip()
        new_task = obj.get("new_task", "").strip()
        if node_id and new_task:
            return {"node_id": node_id, "new_task": new_task}
    except (json.JSONDecodeError, AttributeError):
        pass

    # Regex fallback for prose-formatted AI responses.
    node_id_match = re.search(r"NODE_ID:\s*(\S+)", response)
    task_match = re.search(r"NEW_TASK:\s*(.+)", response, re.DOTALL)
    if node_id_match and task_match:
        return {
            "node_id": node_id_match.group(1).strip(),
            "new_task": task_match.group(1).strip(),
        }
    return None


async def focus_manager_session(
    node: dict,
    run: dict,
    summary: str = "",
    waiting_node: dict | None = None,
) -> dict:
    """Create/reuse the Manager AI session, focus it, and mark it as waiting."""
    import helm.state as _st
    from helm.broadcast import push_message, push_state
    from helm.session_mgr import make_session, session_cwd
    from helm.agent.nodes.input_node import mark_session_waiting_for_run

    sid = node.get("session_id") or run.get("manager_session_id")
    sess = _st.sessions.get(sid) if sid else None
    if not sess:
        source_sess = _st.sessions.get(run.get("session_id"))
        cwd = source_sess.get("cwd") if source_sess else session_cwd()
        sess = make_session("claude", cwd=cwd)
        sess["name"] = run.get("agent_name") or "Agent Manager"
        sess["emoji"] = "🧭"
        sess["agent_manager"] = True
        sess["agent_manager_run_id"] = run.get("id")
        sess["agent_manager_node_id"] = node.get("id")
        sess["agent_id"] = run.get("agent_id")
        sess["agent_name"] = run.get("agent_name")
        sess["agent_manager_waiting_run_id"] = run.get("id")
        sess["agent_manager_waiting_kind"] = "input" if waiting_node else "feedback"
        if waiting_node:
            sess["agent_manager_waiting_node_id"] = waiting_node.get("id")
        node["session_id"] = sess["id"]
        run["manager_session_id"] = sess["id"]
    else:
        sess["agent_manager"] = True
        sess["agent_manager_run_id"] = run.get("id")
        sess["agent_manager_node_id"] = node.get("id")
        sess["agent_manager_waiting_run_id"] = run.get("id")
        sess["agent_manager_waiting_kind"] = "input" if waiting_node else "feedback"
        if waiting_node:
            sess["agent_manager_waiting_node_id"] = waiting_node.get("id")
        else:
            sess.pop("agent_manager_waiting_node_id", None)

    mark_session_waiting_for_run(sess["id"], run.get("id"), node_id=node.get("id"))
    _st.focused_id = sess["id"]
    await push_state()

    if not sess.get("_agent_manager_intro_sent"):
        if waiting_node:
            intro = (
                "Manager session is now focused for this workflow. "
                f"The step \"{waiting_node.get('title', 'Input step')}\" needs your input. "
                "Reply here and I will pass it to the waiting step."
            )
        else:
            intro = (
                "Manager session is now focused for this workflow. "
                "Reply here with YES if the output is good, or describe what should change. "
                "I will use that feedback to update the responsible node and rerun the workflow."
            )
        if summary:
            intro += "\n\nWorkflow summary:\n" + summary[:3000]
        await push_message("system", intro, source="agent", session_id=sess["id"])
        sess["_agent_manager_intro_sent"] = True

    return sess


async def execute_manager_node(node: dict, run: dict, context: str) -> str:
    """
    Send run summary to user, wait for feedback, fix agent if needed.
    Returns "APPROVED" (run done), "RERUN" (nodes reset, run again), or "TIMEOUT".
    """
    from helm.agent.nodes.input_node import wait_for_input
    import helm.state as _st

    max_iter = node.get("manager_max_iter", 3)
    iterations = run.get("manager_iterations", 0)

    if iterations >= max_iter:
        logger.info("Manager node: max iterations (%d) reached — auto-approving", max_iter)
        return "APPROVED"

    # Build and send summary
    summary = await build_run_summary(run)
    manager_session = await focus_manager_session(node, run, summary=summary)
    question = (
        f"{summary}\n\n"
        f"--- Iteration {iterations + 1}/{max_iter} ---\n"
        "Reply YES if this looks good, or tell me what's wrong and I'll fix it."
    )

    # Notify user
    channel = node.get("deliver_channel", "telegram")
    if channel == "telegram" and run.get("session_id"):
        try:
            from helm.integrations import get_telegram_bot
            bot = get_telegram_bot()
            if bot:
                chunks = [question[i:i+4000] for i in range(0, len(question), 4000)]
                for chunk in chunks:
                    await bot.send_message(chat_id=run["session_id"], text=chunk)
        except Exception as exc:
            logger.warning("Manager node Telegram notify failed: %s", exc)

    from helm.broadcast import broadcast
    await broadcast({
        "type": "agent_run_waiting_input",
        "run_id": run["id"],
        "node_id": node["id"],
        "question": question,
        "session_id": manager_session["id"],
        "kind": "feedback",
    })
    try:
        from helm.broadcast import push_message
        await push_message("system", question[:4000], source="agent", session_id=manager_session["id"])
    except Exception:
        pass

    run["status"] = "waiting_input"

    timeout = node.get("input_timeout", 3600)
    user_reply = await wait_for_input(run["id"], timeout=timeout, node_id=node["id"])
    manager_session.pop("agent_manager_waiting_run_id", None)
    manager_session.pop("agent_manager_waiting_kind", None)
    manager_session.pop("agent_manager_waiting_node_id", None)
    run["status"] = "running"

    if not user_reply or "timed out" in user_reply.lower():
        return "TIMEOUT"

    parsed = parse_manager_reply(user_reply)

    if parsed["approved"]:
        return "APPROVED"

    # Not approved — find and fix the offending node
    agent = _st.agents.get(run["agent_id"])
    if not agent:
        return "APPROVED"  # Can't fix without live agent

    fix = await identify_and_fix_node(run, parsed["feedback"], agent["nodes"])
    if fix:
        # Update live agent definition
        for ag_node in agent["nodes"]:
            if ag_node["id"] == fix["node_id"]:
                ag_node["task"] = fix["new_task"]
                logger.info(
                    "Manager node: updated node %s (%s) with improved task",
                    fix["node_id"], ag_node.get("title"),
                )
                break
        # Persist updated agent
        try:
            from helm.agent.storage import save_agent
            save_agent(agent)
        except Exception as exc:
            logger.warning("Manager node: could not save updated agent: %s", exc)

        # B12: undo any loop expansion before resetting — drop clones and
        # restore each loop node's original children list.
        import copy as _copy
        restored_nodes: list[dict] = []
        seen_ids: set[str] = set()
        for rn in run["nodes"]:
            if rn.get("_loop_item"):
                continue  # previous clone, discard
            if rn.get("type") == "loop" and rn.get("_expanded"):
                rn.pop("_expanded", None)
                orig_ids = rn.get("_orig_children") or []
                if orig_ids:
                    rn["children"] = list(orig_ids)
                # Re-insert pristine copies of original child nodes that the
                # first expansion removed from the snapshot.
                restored_originals = rn.get("_orig_child_nodes") or []
                for orig in restored_originals:
                    if orig["id"] in seen_ids:
                        continue
                    clone = _copy.deepcopy(orig)
                    restored_nodes.append(clone)
                    seen_ids.add(clone["id"])
            if rn["id"] not in seen_ids:
                restored_nodes.append(rn)
                seen_ids.add(rn["id"])
        run["nodes"] = restored_nodes

        # Reset all non-manager nodes in this run for re-execution
        for rn in run["nodes"]:
            if rn.get("type") == "manager":
                continue
            rn["status"] = "pending"
            rn["output"] = None
            rn["output_summary"] = None
            rn["error"] = None
            rn["stream_buffer"] = ""
            rn["session_id"] = None
            rn["started_at"] = None
            rn["completed_at"] = None
            rn["elapsed_seconds"] = 0.0
            # Apply updated task to run snapshot
            if rn["id"] == fix["node_id"]:
                rn["task"] = fix["new_task"]

        run["manager_iterations"] = iterations + 1

    return "RERUN"
