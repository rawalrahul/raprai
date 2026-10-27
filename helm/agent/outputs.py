"""
helm/agent/outputs.py — What a finished agent run leaves behind: the files its
steps wrote, the final text saved to a file, and the results sent to Telegram.

The run loop that calls these is in executor.py.
"""

import asyncio
import pathlib
import re
import time

from helm.config import logger

from .models import parent_nodes


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


async def _save_node_output_to_dir(run: dict, node: dict, cwd: str, output: str) -> None:
    """Save every non-manager node's output to the agent's output_dir (or cwd if unset)."""
    if node.get("type") == "manager":
        return
    text = (output or "").strip()
    if not text:
        return
    base_dir = (run.get("output_dir") or "").strip() or cwd
    stem = _safe_output_stem(run, node)
    run_suffix = str(run.get("id") or "run")[-8:]
    path = _unique_output_path(pathlib.Path(base_dir) / f"{stem}_{run_suffix}.txt")

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    try:
        await asyncio.to_thread(_write)
        resolved = str(path.resolve())
        _add_unique_path(run.setdefault("_generated_files", []), resolved)
        node_id = node.get("id")
        if node_id:
            _add_unique_path(run.setdefault("_generated_files_by_node", {}).setdefault(node_id, []), resolved)
        _add_unique_path(run.setdefault("_workflow_cwds", []), str(pathlib.Path(base_dir).resolve()))
        node["node_output_file"] = resolved
        logger.info("Agent run %s node %s output saved to %s", run.get("id", "")[:8], node.get("id", ""), resolved)
    except Exception as exc:
        logger.warning("Could not save node output file %s: %s", path, exc)


async def _cleanup_intermediate_generated_files(run: dict) -> list[str]:
    """No-op: file deletion disabled so all output files remain for user verification."""
    return []


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
