"""
helm/learning/hooks.py — what the learning system records around each task.

process_message calls task_started before the AI runs and task_finished after.
Learning is a side job: a failure here is logged and never stops a reply.
"""

import asyncio

from helm.config import logger


def task_started(text: str, ai: str, sess: dict, sid: str | None, source: str) -> tuple[str | None, dict]:
    """Classify the task and open its telemetry record. Returns (task_id, classification)."""
    clf: dict = {"task_type": "unknown", "task_fingerprint": None}
    try:
        from helm.learning.classifier import classify_and_fingerprint
        from helm.learning.telemetry import get_telemetry
        clf = classify_and_fingerprint(text)
        task_id = get_telemetry().start(
            session_id=sid or "",
            ai=ai,
            model=sess.get("model"),
            prompt=text,
            source=source,
        )
        return task_id, clf
    except Exception:
        logger.debug("Learning: couldn't open the task record", exc_info=True)
        return None, clf


def task_finished(task_id: str | None, clf: dict, *, text: str, ai: str, sess: dict,
                  sid: str | None, output: str, success: bool, elapsed: float,
                  tok_in: int | None, tok_out: int | None) -> None:
    """Close the telemetry record, update routing stats, and queue the task for
    analysis. Background looks (your brief) teach the learning system nothing."""
    task_type = clf.get("task_type", "unknown")
    try:
        if task_id is not None:
            from helm.learning.telemetry import get_telemetry
            from helm.learning.router import update_stats
            cost = float(sess.pop("_last_cost_usd", 0.0) or 0.0) if sess else 0.0
            get_telemetry().finish(
                task_id=task_id,
                duration=elapsed,
                input_tokens=tok_in or 0,
                output_tokens=tok_out or 0,
                output_text=(output or "")[:500],
                cost_usd=cost,
                errors=None,
            )
            update_stats(task_type=task_type, ai=ai, duration_seconds=elapsed,
                         success=success, cost_usd=cost)
    except Exception:
        logger.debug("Learning: couldn't close the task record", exc_info=True)

    if sess.get("read_only"):
        return
    record = {
        "task_id": task_id or "",
        "task_type": task_type,
        "task_fingerprint": clf.get("task_fingerprint"),
        "task_summary": (text or "")[:200],
        "ai_used": ai,
        "ai_model_version": sess.get("model"),
        "duration_seconds": elapsed,
        "success": success,
        "success_confidence": 0.7 if success else 0.3,
        "errors_hit": [],
        "session_id": sid or "",
    }
    # Playbook generation and antipattern extraction run in the background.
    try:
        from helm.learning.analyzer import enqueue, drain_queue
        enqueue(record)
        asyncio.create_task(drain_queue())
    except Exception:
        logger.debug("Learning: couldn't queue the task for analysis", exc_info=True)
    try:
        from helm.learning.cross_ai import record_task
        record_task(record)
    except Exception:
        logger.debug("Learning: couldn't record the task for AI comparison", exc_info=True)
