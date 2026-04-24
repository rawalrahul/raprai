"""
helm/agent/executor.py - Agent DAG execution engine.

Traverses the agent graph in topological order, launching ready nodes
concurrently, injecting parent context, streaming chunks via WebSocket,
and routing nodes by type.
"""

import asyncio
import os
import pathlib
import re
import time

import helm.state as _st
from helm.config import logger
from helm.session_mgr import make_session

from .context import build_node_prompt, extract_var_assignments
from .models import (
    find_node,
    is_run_done,
    parent_nodes,
    ready_nodes,
    run_state_payload,
)


# Node types that have external side effects — skipped in dry-run mode.
_SIDE_EFFECT_TYPES: frozenset[str] = frozenset(("shell", "http", "deliver"))


async def broadcast_run_update(run: dict):
    """Broadcast full run state to all WS clients."""
    from helm.broadcast import broadcast
    try:
        await broadcast({"type": "agent_run_update", "run": run_state_payload(run)})
    except Exception as exc:
        logger.error("Failed to broadcast agent run update: %s", exc)


async def broadcast_run_stream(run_id: str, node_id: str, chunk: str):
    """Broadcast a live stream chunk for a running node."""
    from helm.broadcast import broadcast
    try:
        await broadcast({
            "type": "agent_run_stream",
            "run_id": run_id,
            "node_id": node_id,
            "chunk": chunk,
        })
    except Exception as exc:
        logger.debug("agent_run_stream broadcast error: %s", exc)


def _max_parallel() -> int:
    return max(1, int(os.environ.get("PIPELINE_MAX_PARALLEL", "3")))


def _extract_retry_request(output: str) -> str | None:
    """Return RETRY_PARENT reason from node output, if present."""
    match = re.search(r"RETRY_PARENT\s*:\s*(.+)", output or "", re.IGNORECASE)
    return match.group(1).strip() if match else None


def _should_retry_node(run: dict, node: dict) -> bool:
    """Return True if node should be retried, incrementing its counter.

    NOTE — retry counter compounding (B13):
    Node retries (retry_max) and feedback retries (manager_max_iter) operate
    independently — total max attempts per feedback cycle = retry_max × manager_max_iter.
    Keep both limits small to avoid runaway execution costs.
    """
    max_retries = node.get("retry_max", 0)
    if not max_retries:
        return False
    retries = run.setdefault("node_retries", {})
    count = retries.get(node["id"], 0)
    if count < max_retries:
        retries[node["id"]] = count + 1
        return True
    return False


_TRUTHY = frozenset({"true", "yes", "1", "y", "correct", "positive"})
_FALSY = frozenset({"false", "no", "0", "n", "incorrect", "negative"})


def _normalise_condition_output(output: str) -> bool:
    """Return True if output signals the true/yes branch; False otherwise.

    B6: AI may return 'True', 'YES', 'yes\n', 'true.' etc.  Strip punctuation,
    lowercase, match against known truthy/falsy sets.  Defaults to False on
    ambiguous output so the workflow fails safe.
    """
    cleaned = output.strip().lower().rstrip(".,;!?")
    # take only first word in case AI appended explanation
    first_word = cleaned.split()[0] if cleaned.split() else ""
    return first_word in _TRUTHY or cleaned in _TRUTHY


def _apply_condition_skips(run: dict) -> None:
    """Skip the unselected branch after completed condition nodes."""
    for node in run["nodes"]:
        if node.get("type") != "condition" or node.get("status") != "completed":
            continue
        children = node.get("children", [])
        if len(children) < 2:
            continue
        branch_true = _normalise_condition_output(node.get("output") or "")
        skip_id = children[1] if branch_true else children[0]
        skipped = find_node(run, skip_id)
        if skipped and skipped.get("status") == "pending":
            skipped["status"] = "skipped"
            skipped["output"] = "(skipped - condition branch not taken)"


def _is_final_worker_node(run: dict, node: dict) -> bool:
    """Return True when this node is an executable leaf before manager review."""
    if node.get("type") == "manager":
        return False
    child_ids = set(node.get("children", []))
    if not child_ids:
        return True
    for child in run.get("nodes", []):
        if child.get("id") in child_ids and child.get("type") != "manager":
            return False
    return True


def _non_manager_nodes_done(run: dict) -> bool:
    """Return True when all executable workflow nodes are in a terminal state."""
    from .models import TERMINAL_STATES

    workflow_nodes = [n for n in run.get("nodes", []) if n.get("type") != "manager"]
    return bool(workflow_nodes) and all(n.get("status") in TERMINAL_STATES for n in workflow_nodes)


def _is_telegram_deliver_node(node: dict) -> bool:
    """Return True when a deliver node already sends its payload to Telegram."""
    return (
        node.get("type") == "deliver"
        and str(node.get("deliver_channel", "")).lower() == "telegram"
    )


def _normalise_path(path: str) -> str:
    try:
        return str(pathlib.Path(path).resolve()).casefold()
    except Exception:
        return str(path).casefold()


def _path_is_under(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def _add_unique_path(paths: list[str], path: str) -> None:
    seen = {_normalise_path(p) for p in paths}
    if _normalise_path(path) not in seen:
        paths.append(path)


def _record_node_generated_files(run: dict, node: dict, cwd: str, before: dict, after: dict) -> None:
    """Track files newly created by a node for end-of-run cleanup."""
    try:
        from helm.file_tracker import diff_snapshots
        diff = diff_snapshots(before, after)
    except Exception:
        return

    new_files = [str(pathlib.Path(p).resolve()) for p in diff.get("new", [])]
    if not new_files:
        return

    node_id = node.get("id")
    if node_id:
        by_node = run.setdefault("_generated_files_by_node", {})
        existing = by_node.setdefault(node_id, [])
        seen = {_normalise_path(p) for p in existing}
        for path in new_files:
            norm = _normalise_path(path)
            if norm not in seen:
                existing.append(path)
                seen.add(norm)

    all_generated = run.setdefault("_generated_files", [])
    seen_all = {_normalise_path(p) for p in all_generated}
    for path in new_files:
        norm = _normalise_path(path)
        if norm not in seen_all:
            all_generated.append(path)
            seen_all.add(norm)

    cwds = run.setdefault("_workflow_cwds", [])
    norm_cwds = {_normalise_path(c) for c in cwds}
    cwd_norm = _normalise_path(cwd)
    if cwd_norm not in norm_cwds:
        cwds.append(str(pathlib.Path(cwd).resolve()))


def _safe_output_stem(run: dict, node: dict) -> str:
    raw = f"{run.get('agent_name') or 'agent'} {node.get('title') or 'output'}"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-").lower()
    return stem[:80] or "agent_output"


def _looks_like_deliver_status(output: str) -> bool:
    lowered = (output or "").strip().lower()
    return lowered.startswith("ok: delivered") or lowered.startswith("error delivering")


def _unique_output_path(path: pathlib.Path) -> pathlib.Path:
    """Return a non-conflicting output path without overwriting user files."""
    if not path.exists():
        return path
    for idx in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{idx}{path.suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{path.stem}_{int(time.time())}{path.suffix}")


async def _persist_final_text_output(run: dict, node: dict, cwd: str, output: str) -> str | None:
    """Write final chat text only when the workflow did not create an output file."""
    if not _is_final_worker_node(run, node):
        return None
    if node.get("type") == "file" and _explicit_file_output_path(node):
        return None
    if _is_telegram_deliver_node(node):
        return None
    if _final_output_file_paths(run):
        return None

    text = (output or "").strip()
    if not text or _looks_like_deliver_status(text):
        return None

    stem = _safe_output_stem(run, node)
    run_suffix = str(run.get("id") or "run")[-8:]
    path = _unique_output_path(pathlib.Path(cwd) / f"{stem}_{run_suffix}.txt")

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    try:
        await asyncio.to_thread(_write)
    except Exception as exc:
        logger.warning("Could not persist final agent output file %s: %s", path, exc)
        return None

    resolved = str(path.resolve())
    _add_unique_path(run.setdefault("_generated_files", []), resolved)
    node_id = node.get("id")
    if node_id:
        _add_unique_path(run.setdefault("_generated_files_by_node", {}).setdefault(node_id, []), resolved)
    _add_unique_path(run.setdefault("_final_output_files", []), resolved)
    _add_unique_path(run.setdefault("_workflow_cwds", []), str(pathlib.Path(cwd).resolve()))
    node["final_output_file"] = resolved
    logger.info("Agent run %s final output written to %s", run.get("id", "")[:8], resolved)
    return resolved


def _explicit_file_output_path(node: dict) -> str | None:
    """Return a file node's written path, if this node writes output."""
    if node.get("type") != "file":
        return None
    if node.get("file_op", "read") not in {"write", "append"}:
        return None
    file_path = str(node.get("file_path") or "").strip()
    if not file_path:
        return None
    cwd = node.get("_cwd")
    path = pathlib.Path(file_path)
    if not path.is_absolute() and cwd:
        path = pathlib.Path(cwd) / path
    try:
        return str(path.resolve())
    except Exception:
        return str(path)


def _nearest_file_output_ancestor_ids(
    run: dict,
    node_id: str,
    seen: set[str] | None = None,
) -> set[str]:
    """Find nearest upstream explicit file-output nodes for a delivery node."""
    seen = seen or set()
    if node_id in seen:
        return set()
    seen.add(node_id)

    result: set[str] = set()
    for parent in parent_nodes(run.get("nodes", []), node_id, include_manager=False):
        parent_id = parent.get("id")
        if not parent_id:
            continue
        if _explicit_file_output_path(parent):
            result.add(parent_id)
        else:
            result.update(_nearest_file_output_ancestor_ids(run, parent_id, seen))
    return result


def _final_output_node_ids(run: dict) -> set[str]:
    """Return node ids whose generated files should be preserved as outputs."""
    nodes = run.get("nodes", [])
    generated_by_node = run.get("_generated_files_by_node") or {}

    deliver_nodes = [
        n for n in nodes
        if n.get("type") == "deliver" and n.get("status") == "completed"
    ]
    if deliver_nodes:
        output_ids: set[str] = set()
        for deliver in deliver_nodes:
            deliver_id = deliver.get("id")
            if deliver_id and (generated_by_node.get(deliver_id) or _explicit_file_output_path(deliver)):
                output_ids.add(deliver_id)
            output_ids.update(_nearest_file_output_ancestor_ids(run, deliver_id or ""))
        if output_ids:
            return output_ids
        return {n.get("id") for n in deliver_nodes if n.get("id")}

    return {
        n.get("id") for n in nodes
        if n.get("id") and n.get("status") == "completed" and _is_final_worker_node(run, n)
    }


def _final_output_file_paths(run: dict) -> set[str]:
    """Return generated file paths that represent the final workflow output."""
    output_node_ids = _final_output_node_ids(run)
    generated_by_node = run.get("_generated_files_by_node") or {}
    keep: set[str] = {
        _normalise_path(path)
        for path in run.get("_final_output_files", [])
        if path
    }

    for node in run.get("nodes", []):
        node_id = node.get("id")
        if node_id not in output_node_ids:
            continue
        explicit = _explicit_file_output_path(node)
        if explicit:
            keep.add(_normalise_path(explicit))
        for path in generated_by_node.get(node_id, []):
            if path:
                keep.add(_normalise_path(path))

    return keep


def _final_output_file_display_paths(run: dict) -> list[str]:
    """Return existing final output file paths with original path casing."""
    keep = _final_output_file_paths(run)
    if not keep:
        return []

    paths: list[str] = []
    seen: set[str] = set()
    for raw_path in list(run.get("_final_output_files", [])) + list(run.get("_generated_files", [])):
        norm = _normalise_path(raw_path)
        if norm not in keep or norm in seen:
            continue
        try:
            resolved = pathlib.Path(raw_path).resolve()
            if resolved.is_file():
                paths.append(str(resolved))
                seen.add(norm)
        except Exception:
            continue

    for node in run.get("nodes", []):
        explicit = _explicit_file_output_path(node)
        norm = _normalise_path(explicit) if explicit else ""
        if explicit and norm in keep and norm not in seen:
            try:
                resolved = pathlib.Path(explicit).resolve()
                if resolved.is_file():
                    paths.append(str(resolved))
                    seen.add(norm)
            except Exception:
                continue
    return paths


async def _announce_final_output_files(run: dict, node: dict) -> None:
    """Show final output file paths once in the UI chat."""
    if not _is_final_worker_node(run, node):
        return
    paths = _final_output_file_display_paths(run)
    if not paths:
        return

    announced = run.setdefault("_announced_final_output_files", [])
    new_paths = []
    for path in paths:
        if _normalise_path(path) not in {_normalise_path(p) for p in announced}:
            new_paths.append(path)
            _add_unique_path(announced, path)
    if not new_paths:
        return

    try:
        from helm.broadcast import push_message
        label = "Final output file" if len(new_paths) == 1 else "Final output files"
        body = label + ":\n" + "\n".join(f"- {path}" for path in new_paths)
        await push_message(
            "system",
            body,
            source="agent",
            session_id=run.get("session_id"),
        )
    except Exception as exc:
        logger.debug("Could not announce final output files: %s", exc)


async def _cleanup_intermediate_generated_files(run: dict) -> list[str]:
    """Delete workflow-created intermediate files, preserving final outputs."""
    generated = run.get("_generated_files") or []
    if not generated:
        return []

    keep = _final_output_file_paths(run)
    allowed_roots = [
        pathlib.Path(cwd).resolve()
        for cwd in run.get("_workflow_cwds", [])
        if cwd
    ]
    if not allowed_roots:
        return []

    deleted: list[str] = []
    for raw_path in generated:
        norm = _normalise_path(raw_path)
        if norm in keep:
            continue
        path = pathlib.Path(raw_path)
        try:
            resolved = path.resolve()
            if not any(_path_is_under(resolved, root) for root in allowed_roots):
                continue
            if not resolved.is_file() or resolved.is_symlink():
                continue
            await asyncio.to_thread(resolved.unlink)
            deleted.append(str(resolved))
        except FileNotFoundError:
            continue
        except Exception as exc:
            logger.warning("Could not clean intermediate agent file %s: %s", raw_path, exc)

    if deleted:
        logger.info("Agent run %s cleaned %d intermediate file(s)", run.get("id", "")[:8], len(deleted))
    return deleted


async def _cleanup_after_workflow_outputs(run: dict) -> None:
    """Clean intermediate files after outputs are available, before manager review."""
    if run.get("_workflow_output_cleanup_done"):
        return
    if not _non_manager_nodes_done(run):
        return
    await _cleanup_intermediate_generated_files(run)
    run["_workflow_output_cleanup_done"] = True


async def _send_final_node_output_to_telegram(run: dict, node: dict) -> None:
    """Send only final executable node output to Telegram."""
    if not _is_final_worker_node(run, node):
        return

    output = node.get("output") or ""

    try:
        import helm.state as _st_inner
        if not (_st_inner.telegram_app and _st_inner.telegram_chat_id):
            return

        if output.strip() and not _is_telegram_deliver_node(node):
            title = node.get("title") or "Final output"
            message = f"Final output - {title}\n\n{output}"
            bot = _st_inner.telegram_app.bot
            for chunk_start in range(0, len(message), 4000):
                await bot.send_message(
                    chat_id=_st_inner.telegram_chat_id,
                    text=message[chunk_start:chunk_start + 4000],
                )

        sent_files = run.setdefault("_telegram_sent_final_files", [])
        try:
            from helm.file_tracker import send_file_to_telegram
            for path in _final_output_file_display_paths(run):
                if _normalise_path(path) in {_normalise_path(p) for p in sent_files}:
                    continue
                await send_file_to_telegram(path, source="agent")
                _add_unique_path(sent_files, path)
        except Exception as exc:
            logger.warning("Final agent Telegram file delivery failed: %s", exc)
    except Exception as exc:
        logger.warning("Final agent Telegram delivery failed: %s", exc)


async def _execute_node(run: dict, node: dict, semaphore: asyncio.Semaphore):
    """Execute one typed node."""
    from helm.agent.context import build_node_context
    from helm.agent.nodes.condition import execute_condition_node
    from helm.agent.nodes.deliver import execute_deliver_node
    from helm.agent.nodes.file import execute_file_node
    from helm.agent.nodes.http import execute_http_node
    from helm.agent.nodes.input_node import execute_input_node
    from helm.agent.nodes.join import execute_join_node
    from helm.agent.nodes.loop import parse_list_from_output
    from helm.agent.nodes.manager import execute_manager_node
    from helm.agent.nodes.shell import execute_shell_node

    async with semaphore:
        # Status already set to "running" in _run_loop (B1); keep started_at fresh
        # for nodes re-entering after retry reset.
        node["status"] = "running"
        node["started_at"] = node.get("started_at") or time.time()
        node["_last_activity"] = time.time()  # A3: watchdog heartbeat baseline
        node["stream_buffer"] = ""
        await broadcast_run_update(run)

        from helm.session_mgr import focused_session, session_cwd
        fs = focused_session()
        cwd = fs["cwd"] if fs else session_cwd()
        node["_cwd"] = cwd

        try:
            from helm.file_tracker import snapshot_dir
            node_file_snapshot_before = await asyncio.to_thread(snapshot_dir, cwd)
        except Exception:
            node_file_snapshot_before = {}

        node_type = node.get("type", "ai")
        context = build_node_context(run, node)

        from helm.agent.context import substitute_vars
        from helm.agent.nodes.transform import execute_transform_node
        # Apply var substitution to node task text for all node types
        task_text = substitute_vars(node.get("task", ""), run)

        # Dry-run: skip side-effect nodes, return descriptive mock output
        _dry_run = run.get("dry_run", False)

        try:
            if _dry_run and node_type in _SIDE_EFFECT_TYPES:
                task_preview = (task_text or node.get("task", "")).strip()[:120]
                output = (
                    f"[DRY RUN] {node_type.upper()} node skipped — would execute:\n{task_preview}"
                )
            elif node_type == "shell":
                shell_node = dict(node)
                shell_node["task"] = task_text
                output = await execute_shell_node(shell_node, context=context, cwd=cwd)
            elif node_type == "http":
                http_node = dict(node)
                http_node["task"] = task_text
                if node.get("http_url"):
                    http_node["http_url"] = substitute_vars(node["http_url"], run)
                if node.get("http_body"):
                    http_node["http_body"] = substitute_vars(node["http_body"], run)
                output = await execute_http_node(http_node, context=context)
            elif node_type == "file":
                output = await execute_file_node(node, context=context)
            elif node_type == "deliver":
                output = await execute_deliver_node(node, context=context)
            elif node_type == "condition":
                output = await execute_condition_node(node, context=context)
            elif node_type == "transform":
                output = await execute_transform_node(node, context=context)
            elif node_type == "join":
                output = await execute_join_node(node, context=context)
            elif node_type == "manager":
                run["status"] = "waiting_input"
                await broadcast_run_update(run)
                output = await execute_manager_node(node, run=run, context=context)
                run["status"] = "running"
                if output == "RERUN":
                    run["_workflow_output_cleanup_done"] = False
                    node["status"] = "pending"
                    node["output"] = None
                    return
            elif node_type == "input":
                if not parent_nodes(run["nodes"], node["id"], include_manager=False) and run.get("input_data"):
                    output = run["input_data"]
                else:
                    run["status"] = "waiting_input"
                    await broadcast_run_update(run)
                    output = await execute_input_node(node, run=run, context=context)
                    run["status"] = "running"
            elif node_type == "loop":
                items = parse_list_from_output(context, max_items=node.get("loop_max", 10))
                output = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))
                if not items:
                    output = "(no items to iterate)"
            else:
                from helm.ai_runner.core import process_message, is_backend_available, list_available_backends, resolve_ai_spec

                # A6: resolve provider/model strings — "anthropic/claude-sonnet-4.6" → ("claude", "claude-sonnet-4.6")
                ai_spec = node.get("ai", "claude")
                requested_ai, _model_override = resolve_ai_spec(ai_spec)

                # A1: availability-driven fallback — only triggers when selected
                # backend is unavailable, not on task-level errors.
                actual_ai = requested_ai
                fallback_reason: str | None = None

                if node.get("ai_fallback", True) and not is_backend_available(requested_ai):
                    alternatives = list_available_backends(exclude=requested_ai)
                    if alternatives:
                        actual_ai = alternatives[0]
                        fallback_reason = f"{requested_ai} unavailable; using {actual_ai}"
                        logger.warning(
                            "A1 fallback: node %s (%s) — %s",
                            node["id"], node.get("title", "?"), fallback_reason,
                        )
                    else:
                        raise RuntimeError(
                            f"No AI backend available: {requested_ai} unavailable and no alternatives"
                        )

                node["ai_requested"] = ai_spec  # store original spec
                node["ai_used"] = actual_ai
                if fallback_reason:
                    node["ai_fallback_reason"] = fallback_reason

                child_sess = make_session(actual_ai, cwd=cwd)
                if _model_override:
                    child_sess["model"] = _model_override  # A6: pass model override
                child_sess["agent_run_id"] = run["id"]
                child_sess["agent_node_id"] = node["id"]
                child_sess["agent_silent_telegram"] = True
                child_sess["agent_send_files_to_telegram"] = _is_final_worker_node(run, node)
                node["session_id"] = child_sess["id"]

                prompt = build_node_prompt(run, node)
                stream_count = [0]

                async def _stream_hook(chunk: str):
                    node["stream_buffer"] = (node.get("stream_buffer", "") + chunk)[-2000:]
                    node["_last_activity"] = time.time()  # A3: watchdog heartbeat
                    stream_count[0] += 1
                    if stream_count[0] % 5 == 0:
                        await broadcast_run_stream(run["id"], node["id"], chunk)

                child_sess["_pipeline_stream_hook"] = _stream_hook
                ai_timeout = node.get("timeout", 600)
                try:
                    output = await asyncio.wait_for(
                        process_message(prompt, source="agent", session_id=child_sess["id"]),
                        timeout=ai_timeout,
                    )
                except asyncio.TimeoutError as exc:
                    raise TimeoutError(f"AI node timed out after {ai_timeout}s") from exc

            retry_reason = _extract_retry_request(output)
            if retry_reason and node_type == "ai":
                retries = run.setdefault("feedback_retries", {})
                count = retries.get(node["id"], 0)
                if count < 3:
                    retries[node["id"]] = count + 1
                    for parent in parent_nodes(run["nodes"], node["id"], include_manager=False):
                        if parent.get("type", "ai") == "ai":
                            parent["status"] = "pending"
                            parent["output"] = None
                            parent["output_summary"] = None
                            parent["error"] = None
                            parent["_feedback"] = f"\n\n[Feedback from child node]: {retry_reason}"
                    node["status"] = "pending"
                    node["output"] = None
                    node["error"] = None
                    return

            node["output"] = output

            # Extract and store any SET_VAR assignments into run scratchpad
            assignments = extract_var_assignments(output)
            if assignments:
                run.setdefault("vars", {}).update(assignments)

            node["status"] = "completed"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            node["stream_buffer"] = ""
            node["output_summary"] = await _maybe_summarize(output, node.get("ai", "claude"))

            # A2: Layer 1+2 memory — index output + persist summary
            try:
                from helm.agent.memory import after_node_complete
                await after_node_complete(run, node)
            except Exception:
                pass

            elapsed = f"{node['elapsed_seconds']:.1f}s"
            logger.info(
                "Agent run %s node %s (%s) completed in %s",
                run["id"][:8], node["id"], node["title"], elapsed,
            )

            if node_file_snapshot_before:
                try:
                    from helm.file_tracker import snapshot_dir
                    node_file_snapshot_after = await asyncio.to_thread(snapshot_dir, cwd)
                    _record_node_generated_files(
                        run,
                        node,
                        cwd,
                        node_file_snapshot_before,
                        node_file_snapshot_after,
                    )
                except Exception as exc:
                    logger.debug("Agent generated-file tracking failed: %s", exc)

            await _persist_final_text_output(run, node, cwd, output)
            await _announce_final_output_files(run, node)
            await _send_final_node_output_to_telegram(run, node)
            await _cleanup_after_workflow_outputs(run)

        except asyncio.CancelledError:
            node["status"] = "skipped"
            node["output"] = "(cancelled)"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            raise

        except Exception as exc:
            if _should_retry_node(run, node):
                attempt = run.get("node_retries", {}).get(node["id"], 1)
                logger.info("Retrying node %s (attempt %d)", node["id"], attempt)
                node["status"] = "pending"
                node["error"] = None
                node["output"] = None
                return
            node["status"] = "failed"
            node["error"] = str(exc)
            node["output"] = f"Error: {exc}"
            node["completed_at"] = time.time()
            node["elapsed_seconds"] = node["completed_at"] - node["started_at"]
            logger.error("Agent run %s node %s failed: %s", run["id"][:8], node["id"], exc)
            if run.get("trigger") == "telegram":
                await _tg_notify(run, f"Failed: {node['title']} - {exc}")
            # A5: auto-replan — if agent has auto_replan=True, trigger manager
            # with synthetic feedback so it can fix the failing node and rerun.
            await _maybe_auto_replan(run, node)

        finally:
            await broadcast_run_update(run)
            if not (run.get("timed_out") or run.get("status") == "cancelled"):
                try:
                    from .storage import save_run
                    await save_run(run)
                except Exception as e:
                    logger.warning("Could not save agent run: %s", e)


async def _maybe_auto_replan(run: dict, failed_node: dict) -> None:
    """A5: If agent has auto_replan=True, inject synthetic feedback into the
    manager node so it can fix the failing node and trigger a RERUN without
    human intervention.  Fires at most once per node per run to avoid loops."""
    import helm.state as _st_inner
    agent = _st_inner.agents.get(run.get("agent_id", ""))
    if not agent or not agent.get("auto_replan"):
        return
    if run.get("_auto_replan_triggered", {}).get(failed_node["id"]):
        return  # already tried this node once

    manager_node = next(
        (n for n in run["nodes"] if n.get("type") == "manager"),
        None,
    )
    if not manager_node:
        return

    run.setdefault("_auto_replan_triggered", {})[failed_node["id"]] = True
    synthetic_feedback = (
        f"Node '{failed_node.get('title', failed_node['id'])}' failed automatically: "
        f"{failed_node.get('error', 'unknown error')}. "
        "Please identify the root cause, improve the failing node's task, and rerun."
    )
    logger.info(
        "A5 auto-replan: run %s node %s failed — injecting synthetic feedback to manager",
        run["id"][:8], failed_node["id"],
    )
    from helm.agent.nodes.input_node import resume_run
    resume_run(run["id"], synthetic_feedback, node_id=manager_node["id"])


def _build_failure_summary(nodes: list[dict]) -> str:
    """Build human-readable failure summary for Telegram notification."""
    failed = [n for n in nodes if n.get("status") == "failed"]
    if not failed:
        return ""
    lines = ["Agent run failed. Failed steps:"]
    for n in failed:
        err = n.get("error", "unknown error")
        lines.append(f"  ✗ {n['title']}: {err[:120]}")
    return "\n".join(lines)


def _expand_loop_children(loop_node: dict, all_nodes: list[dict]) -> list[dict]:
    """
    After a loop node completes, replace its children with per-item clones.
    Returns the updated nodes list.
    Each clone gets _loop_item set to the item text.
    loop_node["children"] is updated to point to clone IDs.
    """
    import copy as _copy
    from helm.agent.nodes.loop import parse_list_from_output
    from helm.agent.models import make_node_id

    items = parse_list_from_output(
        loop_node.get("output", ""),
        max_items=loop_node.get("loop_max", 10),
    )
    if not items:
        return all_nodes

    # B12: persist original children IDs and deep-copy of their node defs so a
    # manager RERUN can restore the pre-expansion state.
    orig_child_ids = list(loop_node.get("_orig_children") or loop_node.get("children", []))
    loop_node["_orig_children"] = list(orig_child_ids)
    orig_children = [n for n in all_nodes if n["id"] in orig_child_ids]
    if not orig_children:
        return all_nodes
    # Save pristine copies so RERUN can re-insert them after cloning cleared originals.
    loop_node["_orig_child_nodes"] = [_copy.deepcopy(n) for n in orig_children]

    # Drop originals and any previous clones before re-cloning.
    def _is_previous_clone(n: dict) -> bool:
        return bool(n.get("_loop_item"))

    keep = [
        n for n in all_nodes
        if n["id"] not in orig_child_ids and not _is_previous_clone(n)
    ]

    new_child_ids = []
    for item in items:
        item_suffix = make_node_id()
        for orig in orig_children:
            clone = _copy.deepcopy(orig)
            clone["id"] = f"{orig['id']}-{item_suffix}"
            clone["status"] = "pending"
            clone["output"] = None
            clone["error"] = None
            clone["_loop_item"] = item
            keep.append(clone)
        # First clone of first original child is the "entry" for this item
        new_child_ids.append(f"{orig_children[0]['id']}-{item_suffix}")

    loop_node["children"] = new_child_ids
    return keep


async def execute_agent_run(run_id: str) -> None:
    """Execute an AgentRun from start to finish."""
    run = _st.agent_runs.get(run_id)
    if not run:
        logger.error("execute_agent_run: run %s not found", run_id)
        return

    agent_id = run["agent_id"]
    agent = _st.agents.get(agent_id)
    logger.info(
        "Agent run %s starting (%s, %d nodes)",
        run_id[:8], run["agent_name"], len(run["nodes"]),
    )

    semaphore = asyncio.Semaphore(_max_parallel())

    run_timeout = (agent or {}).get("run_timeout", 1800) if agent else 1800
    active_tasks: set[asyncio.Task] = set()
    node_tasks: dict[str, asyncio.Task] = {}  # A3: node_id → task for watchdog cancel
    _watchdog_stop = asyncio.Event()

    async def _watchdog():
        """A3: Sweep every 15s; cancel nodes with no activity > stuck_threshold."""
        while not _watchdog_stop.is_set():
            try:
                await asyncio.wait_for(
                    asyncio.shield(asyncio.ensure_future(_watchdog_stop.wait())),
                    timeout=15,
                )
                return
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                return
            now = time.time()
            for n in run["nodes"]:
                if n.get("status") != "running":
                    continue
                if n.get("type") in ("input", "manager"):
                    continue  # user-waiting; no heartbeat needed
                last = n.get("_last_activity") or n.get("started_at") or now
                threshold = n.get("stuck_threshold", 300)
                if now - last > threshold:
                    t = node_tasks.get(n["id"])
                    if t and not t.done():
                        idle = int(now - last)
                        logger.warning(
                            "Watchdog: run %s node %s (%s) idle %ds > threshold %ds — cancelling",
                            run_id[:8], n["id"], n.get("title", "?"), idle, threshold,
                        )
                        n["error"] = f"stuck: no activity for {idle}s"
                        t.cancel()

    async def _run_loop():
        while True:
            if run["status"] == "cancelled":
                break
            if is_run_done(run):
                break
            pending_ready = ready_nodes(run["nodes"])
            if not pending_ready:
                still_running = [n for n in run["nodes"] if n["status"] == "running"]
                if not still_running:
                    for n in run["nodes"]:
                        if n["status"] == "pending":
                            n["status"] = "skipped"
                    break
                await asyncio.sleep(0.2)
                continue
            # B1: mark scheduled BEFORE create_task so next ready_nodes call
            # cannot re-pick them while they queue on the semaphore.
            for node in pending_ready:
                node["status"] = "running"
                node["started_at"] = node.get("started_at") or time.time()
            tasks = [
                asyncio.create_task(_execute_node(run, node, semaphore))
                for node in pending_ready
            ]
            # A3: register tasks so watchdog can cancel by node_id
            for node, task in zip(pending_ready, tasks):
                node_tasks[node["id"]] = task
            active_tasks.update(tasks)
            done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            active_tasks.difference_update(done)
            _apply_condition_skips(run)

            # Expand any newly-completed loop nodes
            for n in run["nodes"]:
                if n.get("type") == "loop" and n.get("status") == "completed" and not n.get("_expanded"):
                    n["_expanded"] = True
                    run["nodes"] = _expand_loop_children(n, run["nodes"])
                    await broadcast_run_update(run)

    watchdog_task = asyncio.create_task(_watchdog())
    try:
        if run_timeout and run_timeout > 0:
            await asyncio.wait_for(_run_loop(), timeout=run_timeout)
        else:
            await _run_loop()
    except asyncio.TimeoutError:
        run["timed_out"] = True
        run["status"] = "failed"
        for task in list(active_tasks):
            task.cancel()
        if active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*active_tasks, return_exceptions=True),
                    timeout=2,
                )
            except asyncio.TimeoutError:
                logger.warning("Agent run %s timed out while cancelling active node tasks", run_id[:8])
            active_tasks.clear()
        for n in run["nodes"]:
            if n["status"] in ("pending", "running"):
                n["status"] = "skipped"
                n["error"] = "run timed out"
        logger.warning("Agent run %s timed out after %ss", run_id[:8], run_timeout)
        if run.get("trigger") == "telegram":
            await _tg_notify(run, f"Agent timed out after {run_timeout}s")
    except asyncio.CancelledError:
        run["status"] = "cancelled"
        for task in list(active_tasks):
            task.cancel()
        if active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*active_tasks, return_exceptions=True),
                    timeout=2,
                )
            except asyncio.TimeoutError:
                logger.warning("Agent run %s timed out while cancelling active node tasks", run_id[:8])
            active_tasks.clear()
        for n in run["nodes"]:
            if n["status"] in ("pending", "running"):
                n["status"] = "skipped"
        logger.info("Agent run %s cancelled", run_id[:8])

    finally:
        _watchdog_stop.set()
        watchdog_task.cancel()
        try:
            await asyncio.wait_for(asyncio.gather(watchdog_task, return_exceptions=True), timeout=1)
        except Exception:
            pass

        if run["status"] in ("running", "waiting_input"):
            failed = any(n["status"] == "failed" for n in run["nodes"])
            run["status"] = "failed" if failed else "completed"

        if run["status"] == "completed":
            await _cleanup_intermediate_generated_files(run)

        run["completed_at"] = time.time()
        await broadcast_run_update(run)

        if agent:
            agent["last_run_at"] = run["completed_at"]
            agent["run_count"] = agent.get("run_count", 0) + 1
            try:
                from .storage import save_agent
                await asyncio.to_thread(save_agent, agent)
            except Exception as e:
                logger.warning("Could not update agent stats: %s", e)

        try:
            from .storage import save_run
            await save_run(run)
        except Exception as e:
            logger.warning("Could not save final agent run: %s", e)

        _st.agent_runs.pop(run_id, None)

        # A2: Layer 3 — write run observation to claude-mem (best-effort)
        try:
            from helm.agent.memory import write_run_observation
            await write_run_observation(run)
        except Exception:
            pass

        progress = {s: 0 for s in ("completed", "failed", "skipped")}
        for n in run["nodes"]:
            progress[n["status"]] = progress.get(n["status"], 0) + 1
        total = len(run["nodes"])
        done = progress.get("completed", 0)

        if run.get("trigger") == "telegram" and run["status"] != "completed":
            failure_msg = _build_failure_summary(run["nodes"])
            await _tg_notify(
                run,
                failure_msg or f"Agent finished with errors - {done}/{total} succeeded",
            )

        logger.info(
            "Agent run %s finished: %s (%d/%d succeeded)",
            run_id[:8], run["status"], done, total,
        )


async def _maybe_summarize(output: str, ai: str) -> str:
    """Return output as-is if short, otherwise summarize via AI."""
    threshold = int(os.environ.get("PIPELINE_CONTEXT_THRESHOLD", "2000"))
    if not output or len(output) <= threshold:
        return output or ""

    truncated = output[:8000]
    summary_prompt = (
        "Summarize the following AI output concisely. "
        "Preserve ALL key information: file names, code snippets, decisions, numbers, conclusions. "
        "Keep it under 1500 characters.\n\n"
        f"---\n{truncated}\n---"
    )
    try:
        from helm.pipeline.planner import _call_planner_ai
        planner = os.environ.get("PIPELINE_PLANNER_AI", ai)
        summary = await _call_planner_ai(planner, summary_prompt, ".")
        if summary and len(summary) < len(output):
            return summary
    except Exception as exc:
        logger.warning("Agent context summarisation failed: %s", exc)

    return output[:threshold] + "\n\n...(output truncated)"


async def _tg_notify(run: dict, text: str):
    """Send a Telegram message in the context of the run's session."""
    try:
        from helm.broadcast import push_message
        await push_message("system", text, source="agent", session_id=run.get("session_id"))
    except Exception as exc:
        logger.debug("agent tg_notify error: %s", exc)
