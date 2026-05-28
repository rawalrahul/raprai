"""
helm/learning/analyzer.py

Post-task analyzer for Helm HQ.
Called after each task completes; runs async analysis without blocking callers.

Entry points:
  enqueue(task_record)  — non-blocking, fire-and-forget
  drain_queue()         — async, call periodically to flush the queue
  analyze_task(record)  — async, direct call (used by drain_queue)
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_LOG_DIR = _HERE / "task_logs"
_ANTIPATTERNS_DIR = _HERE / "antipatterns"

# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _write_error(msg: str) -> None:
    try:
        log = _HERE / "telemetry_errors.log"
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} analyzer: {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

_analyzer_queue: Optional[asyncio.Queue] = None


def get_queue() -> asyncio.Queue:
    global _analyzer_queue
    if _analyzer_queue is None:
        _analyzer_queue = asyncio.Queue(maxsize=200)
    return _analyzer_queue


def enqueue(task_record: dict) -> None:
    """Non-blocking enqueue. Drop silently if queue full."""
    try:
        q = get_queue()
        q.put_nowait(task_record)
    except asyncio.QueueFull:
        _write_error(
            f"analyzer queue full — dropped task_id={task_record.get('task_id', '?')}"
        )
    except Exception as e:
        _write_error(f"enqueue error: {e}")


async def drain_queue() -> None:
    """Process up to 50 pending analysis jobs. Call periodically."""
    q = get_queue()
    processed = 0
    while not q.empty() and processed < 50:
        try:
            record = q.get_nowait()
            await analyze_task(record)
            q.task_done()
            processed += 1
        except asyncio.QueueEmpty:
            break
        except Exception as e:
            _write_error(f"drain_queue error: {e}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def analyze_task(task_record: dict) -> None:
    """
    Run post-task analysis.
    Called as asyncio.create_task() — never awaited directly.
    All exceptions caught internally. Never raises.
    """
    try:
        task_type = task_record.get("task_type", "unknown")
        fingerprint = task_record.get("task_fingerprint")
        success = task_record.get("success", False)
        success_conf = task_record.get("success_confidence", 0.0)

        # Skip low-value tasks
        if task_type in ("chat", "unknown") or not fingerprint:
            return

        # 1. Update existing playbook outcome if one matches
        await _update_playbook_outcome(task_type, fingerprint, success)

        # 2. Check if we should generate a new draft playbook
        if success and success_conf >= 0.7:
            await _maybe_generate_playbook(task_record)

        # 3. Extract antipatterns from errors
        if task_record.get("errors_hit"):
            await _extract_antipattern(task_record)

        # 4. Check if skill update proposal is warranted
        await _maybe_propose_skill_update(task_record)

    except Exception as e:
        _write_error(f"analyze_task error: {e}")


# ---------------------------------------------------------------------------
# Sub-steps
# ---------------------------------------------------------------------------


async def _update_playbook_outcome(
    task_type: str, fingerprint: str, success: bool
) -> None:
    """If a playbook exists for this fingerprint, record its outcome."""
    try:
        from helm.learning.playbook import get_best_playbook, promote_playbook, record_outcome

        pb = await asyncio.to_thread(get_best_playbook, task_type, fingerprint)
        if pb:
            await asyncio.to_thread(record_outcome, task_type, pb["name"], success)
            if success:
                await asyncio.to_thread(promote_playbook, task_type, pb["name"])
    except Exception as e:
        _write_error(f"_update_playbook_outcome error: {e}")


async def _maybe_generate_playbook(task_record: dict) -> None:
    """
    If 3+ successful tasks share the same fingerprint and no active playbook
    exists: generate a draft playbook from the task summaries.
    No AI API calls — purely pattern-based.
    """
    try:
        from helm.learning.playbook import get_best_playbook, save_playbook

        task_type = task_record.get("task_type", "unknown")
        fingerprint = task_record.get("task_fingerprint")

        if not fingerprint:
            return

        # Scan matching tasks from disk (blocking I/O → thread)
        matches = await asyncio.to_thread(
            _scan_matching_tasks,
            fingerprint,
            task_type,
            True,
            0.7,
        )

        if len(matches) < 3:
            return

        # If an active playbook already exists, skip generation
        existing = await asyncio.to_thread(get_best_playbook, task_type, fingerprint)
        if existing:
            meta = existing.get("meta", {})
            if meta.get("status") == "active":
                return

        # Derive playbook name from first record's task_summary
        first = matches[0]
        raw_summary = first.get("task_summary", "task") or "task"
        pb_name = _slugify(raw_summary, max_len=30)

        # Build content
        content = _build_playbook_content(matches, task_type)

        source_ids = [r.get("task_id", "") for r in matches]
        model_version = task_record.get("ai_model_version")

        await asyncio.to_thread(
            save_playbook,
            pb_name,
            task_type,
            content,
            fingerprint,
            source_ids,
            model_version,
        )
    except Exception as e:
        _write_error(f"_maybe_generate_playbook error: {e}")


async def _extract_antipattern(task_record: dict) -> None:
    """
    Append new error patterns to the task_type antipatterns file.
    Deduplicates by error string — only appends if not already present.
    """
    try:
        task_type = task_record.get("task_type", "unknown")
        errors: list = task_record.get("errors_hit", [])
        if not errors:
            return

        safe_type = re.sub(r"[^\w]", "_", task_type).strip("_")
        ap_file = _ANTIPATTERNS_DIR / f"{safe_type}.md"

        # Read existing content (blocking I/O → thread)
        existing = await asyncio.to_thread(_read_file_safe, ap_file)

        new_entries: list[str] = []
        for error_type in errors:
            if not isinstance(error_type, str) or not error_type.strip():
                continue
            if error_type in existing:
                continue  # already recorded
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            entry = (
                f"\n## AUTO-{ts}: {error_type}\n"
                f"**Seen in task:** {str(task_record.get('task_id', '?'))[:8]}\n"
                f"**Task type:** {task_type}\n"
                f"**AI:** {task_record.get('ai_used', 'unknown')}\n"
                f"**Action:** Review and refine this entry — add context about how to avoid it.\n"
            )
            new_entries.append(entry)
            existing += entry  # update in-memory to prevent same-run dups

        if not new_entries:
            return

        append_text = "".join(new_entries)
        await asyncio.to_thread(_append_file, ap_file, append_text)
    except Exception as e:
        _write_error(f"_extract_antipattern error: {e}")


async def _maybe_propose_skill_update(task_record: dict) -> None:
    """
    After a task: check if repeated corrections suggest a skill needs updating.
    If task type has 5+ logged instances with user_feedback='explicit_negative'
    or high retry_count — propose a skill update.

    Only runs on non-chat, non-unknown task types.
    Only proposes when at least 3 negative outcomes found for same fingerprint.
    """
    try:
        task_type = task_record.get("task_type", "unknown")
        fingerprint = task_record.get("task_fingerprint")
        if task_type in ("chat", "unknown") or not fingerprint:
            return

        # Count negative outcomes for this fingerprint
        records = await asyncio.to_thread(
            _scan_matching_tasks, fingerprint, task_type,
            require_success=False, min_confidence=0.0
        )
        negative = [r for r in records if r.get("success") is False or r.get("retry_count", 0) >= 2]
        if len(negative) < 3:
            return

        # Check if proposal already exists for this task_type (avoid spam)
        try:
            from helm.learning.skill_proposals import list_proposals, add_proposal
            existing = list_proposals(status="pending")
            already = any(p.get("source_task_type") == task_type for p in existing)
            if already:
                return
        except Exception:
            return

        # Generate proposal
        ai_names = list({r.get("ai_used", "unknown") for r in negative})
        rationale = (
            f"Task type '{task_type}' has {len(negative)} failed/high-retry instances "
            f"(fingerprint: {fingerprint[:8]}). "
            f"AIs involved: {', '.join(ai_names)}. "
            f"Consider updating the skill or playbook for this task pattern."
        )
        diff = (
            f"# Suggested review for task type: {task_type}\n\n"
            f"## Evidence\n"
            f"- {len(negative)} negative outcomes recorded\n"
            f"- Fingerprint: {fingerprint}\n"
            f"- AIs: {', '.join(ai_names)}\n\n"
            f"## Suggested action\n"
            f"Review and update the skill or playbook handling '{task_type}' tasks.\n"
            f"Common issues: missing context, wrong tool selection, insufficient fallback handling.\n"
        )
        target = f".skills/skills/{task_type.replace('.', '/')}.md"
        add_proposal(
            target_file=target,
            change_type="edit",
            diff=diff,
            rationale=rationale,
            confidence=0.5,
            source_task_ids=[r["task_id"] for r in negative[:5]],
            source_task_type=task_type,
        )
    except Exception as e:
        _write_error(f"_maybe_propose_skill_update error: {e}")


# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------


def _scan_matching_tasks(
    fingerprint: str,
    task_type: str,
    require_success: bool = True,
    min_confidence: float = 0.7,
) -> list[dict]:
    """
    Scan last 2 months of task logs for records matching fingerprint + task_type.
    Sync — safe to call from asyncio.to_thread().
    """
    results: list[dict] = []
    now = datetime.now(timezone.utc)

    months: list[str] = []
    # Current month
    months.append(now.strftime("%Y-%m"))
    # Previous month (simple rollback)
    if now.month == 1:
        prev = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
    else:
        prev = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
    months.append(prev.strftime("%Y-%m"))

    # Resolve all log base dirs (multi-user: per-user subdirs; single-user: _LOG_DIR)
    try:
        from helm.learning.namespace import all_user_log_dirs
        base_dirs = all_user_log_dirs(_LOG_DIR)
    except Exception:
        base_dirs = [_LOG_DIR]

    for base_dir in base_dirs:
        for month in months:
            month_dir = base_dir / month
            if not month_dir.is_dir():
                continue
            for log_file in month_dir.glob("task_*.json"):
                try:
                    data = json.loads(log_file.read_text(encoding="utf-8"))
                except Exception:
                    continue

                if data.get("task_fingerprint") != fingerprint:
                    continue
                if data.get("task_type") != task_type:
                    continue
                if require_success:
                    if not data.get("success", False):
                        continue
                    if data.get("success_confidence", 0.0) < min_confidence:
                        continue
                results.append(data)

    return results


def _slugify(text: str, max_len: int = 30) -> str:
    """Lowercase, spaces→underscores, strip non-alnum/underscore, truncate."""
    text = text.lower().strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w]", "", text)  # keep word chars (alnum + _)
    return text[:max_len].strip("_") or "playbook"


def _build_playbook_content(matches: list[dict], task_type: str) -> str:
    """Synthesize playbook markdown from matching task records."""
    lines: list[str] = []
    first = matches[0]
    title = first.get("task_summary", "Task Playbook") or "Task Playbook"

    lines.append(f"# {title}\n")
    lines.append(f"**Task type:** `{task_type}`\n")
    lines.append(
        f"**Generated from:** {len(matches)} successful tasks\n"
    )
    lines.append("")

    # AI + duration stats
    ai_set: set[str] = set()
    durations: list[float] = []
    for r in matches:
        ai = r.get("ai_used")
        if ai:
            ai_set.add(ai)
        dur = r.get("duration_seconds")
        if isinstance(dur, (int, float)):
            durations.append(float(dur))

    if ai_set:
        lines.append(f"**Successful AIs:** {', '.join(sorted(ai_set))}\n")
    if durations:
        avg_dur = sum(durations) / len(durations)
        lines.append(f"**Avg duration:** {avg_dur:.1f}s\n")
    lines.append("")

    # Steps section
    lines.append("## Steps\n")
    numbered_re = re.compile(r"^\s*(\d+[\.\)]\s+.+)", re.MULTILINE)

    step_counter = 1
    seen_steps: set[str] = set()
    for r in matches:
        summary = r.get("task_summary", "") or ""
        numbered = numbered_re.findall(summary)
        if numbered:
            for step in numbered:
                clean = step.strip()
                if clean not in seen_steps:
                    seen_steps.add(clean)
                    lines.append(f"{step_counter}. {clean}\n")
                    step_counter += 1
        else:
            if summary and summary not in seen_steps:
                seen_steps.add(summary)
                lines.append(f"{step_counter}. {summary.strip()}\n")
                step_counter += 1

    lines.append("")
    lines.append("## Notes\n")
    lines.append(
        "_Auto-generated draft. Review and refine before activating._\n"
    )

    return "".join(lines)


def _read_file_safe(path: Path) -> str:
    """Read text file, return empty string if missing or unreadable."""
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def _append_file(path: Path, text: str) -> None:
    """Append text to file, creating parent dirs as needed. Best-effort atomic."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        _write_error(f"_append_file({path}): {e}")


def _append_antipattern(task_type: str, antipattern_text: str) -> None:
    """
    Public helper: append an antipattern entry to antipatterns/{task_type}.md.
    Called by core.py correction detection (sync, never raises).
    Deduplicates by checking if first 80 chars already appear in the file.
    """
    try:
        filename = task_type.replace(".", "_") + ".md"
        path = _ANTIPATTERNS_DIR / filename
        existing = _read_file_safe(path)
        # Simple dedup: skip if the key phrase already exists
        key = antipattern_text[:80].strip()
        if key and key in existing:
            return
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = f"\n---\n<!-- correction signal {ts} -->\n{antipattern_text.strip()}\n"
        _append_file(path, entry)
    except Exception:
        pass
