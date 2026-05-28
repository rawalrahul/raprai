"""
helm/learning/telemetry.py

Fire-and-forget telemetry layer for Helm HQ task recording.
All public methods are sync and non-blocking; writes go through a bounded
background-thread queue so callers (including async code) never stall.
"""

from __future__ import annotations

import json
import os
import platform
import queue
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).parent
_LOG_DIR = _BASE_DIR / "task_logs"
_ERROR_LOG = _BASE_DIR / "telemetry_errors.log"

# ---------------------------------------------------------------------------
# PII redaction patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
_PHONE_RE = re.compile(r"""(?x)
    (?:\+?\d{1,3}[\s\-.])?        # optional country code
    (?:\(?\d{2,4}\)?[\s\-.])?     # optional area code
    \d{3,4}[\s\-.]                 # first group
    \d{3,4}                        # second group
""")

# C:\Users\<anything>\ or /home/<anything>/
_USER_HOME = os.environ.get("USERPROFILE", "")
_PATH_RE = re.compile(
    r"(?:"
    + re.escape(_USER_HOME).replace("\\\\", "\\\\|/") + r"|"
    + r"[A-Za-z]:\\\\Users\\\\[^\\\\]+\\\\"
    + r"|/home/[^/]+/"
    + r")[^\s\"']*",
    re.IGNORECASE,
)

# API key: 20+ base64url chars not already consumed by email/path
_APIKEY_RE = re.compile(r"[A-Za-z0-9_\-]{20,}")


def _redact(text: str) -> str:
    """Strip PII from text. Order matters: paths first, then emails, phones, keys."""
    text = _PATH_RE.sub("[PATH]", text)
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _APIKEY_RE.sub("[KEY]", text)
    return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _time_bucket() -> str:
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _os_name() -> str:
    system = platform.system()
    if system == "Windows":
        release = platform.release()
        return f"Windows {release}"
    return system


def _hash_session(session_id: str) -> str:
    """One-way hash so raw session IDs are not persisted."""
    import hashlib
    return hashlib.sha256(session_id.encode()).hexdigest()[:16]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _month_dir() -> Path:
    now = datetime.now()
    return _LOG_DIR / now.strftime("%Y-%m")


def _write_error(msg: str) -> None:
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _ERROR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{_iso_now()} {msg}\n")
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# TaskTelemetry
# ---------------------------------------------------------------------------

class TaskTelemetry:
    """
    Singleton telemetry recorder.

    Public API is fully sync / fire-and-forget. A daemon thread drains the
    internal queue and persists records as JSON.
    """

    def __init__(self, queue_maxsize: int = 500) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._q: queue.Queue = queue.Queue(maxsize=queue_maxsize)
        self._worker = threading.Thread(
            target=self._drain, name="telemetry-writer", daemon=True
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # Sampling gate
    # ------------------------------------------------------------------

    def should_sample(self, task_type: str, ai: str) -> bool:  # noqa: ARG002
        """Return True if this task should be recorded. Always True for now."""
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        session_id: str,
        ai: str,
        model: Optional[str],
        prompt: str,
        source: str,
    ) -> str:
        """
        Open a task record. Returns task_id.
        Non-blocking — record is held in memory until finish() is called.
        """
        try:
            task_id = str(uuid.uuid4())
            summary_raw = prompt[:200] if prompt else ""
            record: Dict[str, Any] = {
                "task_id": task_id,
                "timestamp": _iso_now(),
                "ai_used": ai,
                "ai_model_version": model,
                "task_type": "unknown",
                "task_fingerprint": None,
                "task_summary": _redact(summary_raw),
                "user_id": _hash_session(session_id),
                "duration_seconds": 0.0,
                "token_input": 0,
                "token_output": 0,
                "estimated_cost_usd": 0.0,
                "success": None,
                "success_confidence": 0.0,
                "success_signals": [],
                "user_feedback": "unknown",
                "tool_call_sequence": [],
                "tools_used": [],
                "errors_hit": [],
                "retry_count": 0,
                "session_id": session_id,
                "parent_task_id": None,
                "source": source,
                "environment": {
                    "os": _os_name(),
                    "time_of_day_bucket": _time_bucket(),
                },
                "schema_version": "1.0",
                "redaction_applied": True,
            }
            with self._lock:
                self._records[task_id] = record
            return task_id
        except Exception as exc:  # noqa: BLE001
            _write_error(f"start() error: {exc}")
            return str(uuid.uuid4())  # return a dummy id so callers never crash

    def finish(
        self,
        task_id: str,
        duration: float,
        input_tokens: int,
        output_tokens: int,
        output_text: str,
        cost_usd: float,
        errors: Optional[List[str]] = None,
    ) -> None:
        """Complete a record and enqueue it for disk write."""
        try:
            with self._lock:
                record = self._records.pop(task_id, None)
            if record is None:
                _write_error(f"finish() unknown task_id={task_id}")
                return

            record["duration_seconds"] = round(duration, 4)
            record["token_input"] = input_tokens
            record["token_output"] = output_tokens
            record["estimated_cost_usd"] = round(cost_usd, 8)
            record["errors_hit"] = errors or []

            # Infer success from absence of errors if not already set
            if record["success"] is None and not record["errors_hit"]:
                record["success"] = True
                record["success_confidence"] = 0.5

            # Track last completed task per session for feedback lookup
            try:
                sid_hash = record.get("user_id") or _hash_session(record.get("session_id", ""))
                snapshot = {
                    "task_type": record["task_type"],
                    "ai_used": record["ai_used"],
                    "duration_seconds": record["duration_seconds"],
                    "cost_usd": record["estimated_cost_usd"],
                }
                with _last_by_session_lock:
                    _last_by_session[sid_hash] = snapshot
            except Exception:
                pass

            if not self.should_sample(record["task_type"], record["ai_used"]):
                return

            try:
                self._q.put_nowait(record)
            except queue.Full:
                _write_error(
                    f"queue full — dropped task_id={task_id} ai={record['ai_used']}"
                )
        except Exception as exc:  # noqa: BLE001
            _write_error(f"finish() error task_id={task_id}: {exc}")

    def mark_success(
        self,
        task_id: str,
        confidence: float = 1.0,
        signals: Optional[List[str]] = None,
    ) -> None:
        """Update success state on an in-flight record."""
        try:
            with self._lock:
                record = self._records.get(task_id)
                if record is not None:
                    record["success"] = True
                    record["success_confidence"] = confidence
                    record["success_signals"] = signals or []
        except Exception as exc:  # noqa: BLE001
            _write_error(f"mark_success() error task_id={task_id}: {exc}")

    def mark_failure(self, task_id: str, error_type: str) -> None:
        """Mark an in-flight record as failed."""
        try:
            with self._lock:
                record = self._records.get(task_id)
                if record is not None:
                    record["success"] = False
                    record["success_confidence"] = 1.0
                    if error_type not in record["errors_hit"]:
                        record["errors_hit"].append(error_type)
        except Exception as exc:  # noqa: BLE001
            _write_error(f"mark_failure() error task_id={task_id}: {exc}")

    # ------------------------------------------------------------------
    # Background writer
    # ------------------------------------------------------------------

    def _drain(self) -> None:
        """Worker thread: pop records from queue and write to disk."""
        while True:
            try:
                record: Dict[str, Any] = self._q.get(timeout=2)
                self._persist(record)
                self._q.task_done()
            except queue.Empty:
                continue
            except Exception as exc:  # noqa: BLE001
                _write_error(f"_drain() error: {exc}")

    def _persist(self, record: Dict[str, Any]) -> None:
        try:
            task_id = record["task_id"]
            # Derive month from the record timestamp to avoid clock skew
            ts_str = record.get("timestamp", _iso_now())
            try:
                ts = datetime.fromisoformat(ts_str)
            except ValueError:
                ts = datetime.now(timezone.utc)

            try:
                from helm.learning.namespace import user_log_dir as _user_log_dir
                uid = record.get("user_id", "")
                base = _user_log_dir(_LOG_DIR, uid)
            except Exception:
                base = _LOG_DIR
            out_dir = base / ts.strftime("%Y-%m")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"task_{task_id}.json"
            with out_path.open("w", encoding="utf-8") as fh:
                json.dump(record, fh, ensure_ascii=False, indent=2)

            # Index fingerprint in SQLite similarity DB (best-effort)
            try:
                fp = record.get("task_fingerprint")
                tt = record.get("task_type")
                if fp and tt:
                    from helm.learning.db import upsert as _db_upsert, _extract_keywords
                    summary = record.get("task_summary", "") or ""
                    kws = _extract_keywords(summary) if summary else []
                    tools: list = record.get("tools_used") or []
                    if isinstance(tools, str):
                        tools = [tools]
                    _db_upsert(fp, tt, kws, tools)
            except Exception:
                pass
        except Exception as exc:  # noqa: BLE001
            _write_error(f"_persist() error task_id={record.get('task_id', '?')}: {exc}")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_telemetry: Optional[TaskTelemetry] = None
_init_lock = threading.Lock()

# Last completed task per session (session_id_hash → task snapshot)
# Used by /learning/feedback to find which task to update
_last_by_session: dict = {}
_last_by_session_lock = threading.Lock()


def get_telemetry() -> "TaskTelemetry":
    """Return (or create) the module-level singleton."""
    global _telemetry
    if _telemetry is None:
        with _init_lock:
            if _telemetry is None:
                _telemetry = TaskTelemetry()
    return _telemetry


def record_explicit_feedback(session_id: str, positive: bool) -> bool:
    """
    Record explicit human feedback (thumbs up/down) for the last task in session.
    Updates routing stats with 3x weight. Returns True if a task was found.
    Never raises.
    """
    try:
        sid_hash = _hash_session(session_id)
        with _last_by_session_lock:
            snapshot = _last_by_session.get(sid_hash)
        if not snapshot:
            return False

        task_type = snapshot.get("task_type", "unknown")
        ai = snapshot.get("ai_used", "unknown")
        duration = float(snapshot.get("duration_seconds", 0.0))
        cost = float(snapshot.get("cost_usd", 0.0))

        from helm.learning.router import update_stats as _update_stats
        # Call 3 times to give explicit feedback 3x weight in rolling window
        for _ in range(3):
            _update_stats(
                task_type=task_type,
                ai=ai,
                duration_seconds=duration,
                success=positive,
                cost_usd=cost,
            )
        return True
    except Exception as exc:
        _write_error(f"record_explicit_feedback: {exc}")
        return False
