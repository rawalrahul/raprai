"""
helm/learning/skill_proposals.py

Skill proposal system for Helm HQ.
Proposals suggest edits to skill files, new files, CLAUDE.md rules, or deprecations.
All functions: try/except, never raise.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
_PROPOSALS_DIR = _HERE / "skill_proposals"
_PROPOSALS_FILE = _PROPOSALS_DIR / "proposals.json"
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # MyPersonalAssistant/
_CLAUDE_MD = _PROJECT_ROOT / "CLAUDE.md"

# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _write_error(msg: str) -> None:
    try:
        log = _HERE / "telemetry_errors.log"
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} skill_proposals: {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _load_proposals() -> list[dict]:
    """Load proposals list from disk. Returns [] on any error."""
    try:
        _PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        if not _PROPOSALS_FILE.exists():
            return []
        return json.loads(_PROPOSALS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        _write_error(f"_load_proposals error: {e}")
        return []


def _save_proposals(proposals: list[dict]) -> bool:
    """Atomic write. Windows-safe: unlink before rename. Returns True on success."""
    try:
        _PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _PROPOSALS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(proposals, indent=2, ensure_ascii=False), encoding="utf-8")
        if _PROPOSALS_FILE.exists():
            _PROPOSALS_FILE.unlink()
        tmp.rename(_PROPOSALS_FILE)
        return True
    except Exception as e:
        _write_error(f"_save_proposals error: {e}")
        return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rationale_hash(target_file: str, rationale: str) -> str:
    key = f"{target_file}||{rationale}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_proposals(status: str = "pending") -> list[dict]:
    """
    Returns proposals filtered by status.
    Excludes snoozed proposals where snoozed_until > now.
    """
    try:
        now = datetime.now(timezone.utc)
        proposals = _load_proposals()
        result = []
        for p in proposals:
            if p.get("status") != status:
                continue
            # Exclude still-active snoozes even if status changed back somehow
            snoozed_until = p.get("snoozed_until")
            if snoozed_until:
                try:
                    until_dt = datetime.fromisoformat(snoozed_until)
                    if until_dt > now:
                        continue
                except Exception:
                    pass
            result.append(p)
        return result
    except Exception as e:
        _write_error(f"list_proposals error: {e}")
        return []


def get_proposal(proposal_id: str) -> Optional[dict]:
    """Returns proposal dict by id, or None if not found."""
    try:
        proposals = _load_proposals()
        for p in proposals:
            if p.get("id") == proposal_id:
                return p
        return None
    except Exception as e:
        _write_error(f"get_proposal error: {e}")
        return None


def add_proposal(
    target_file: str,
    change_type: str,
    diff: str,
    rationale: str,
    confidence: float,
    source_task_ids: list,
    source_task_type: str,
) -> str:
    """
    Add a new proposal. Dedup by target_file + rationale hash.
    Returns proposal_id (existing if duplicate, new otherwise).
    """
    try:
        proposals = _load_proposals()
        r_hash = _rationale_hash(target_file, rationale)

        # Dedup check
        for p in proposals:
            if (
                p.get("target_file") == target_file
                and p.get("status") == "pending"
                and p.get("_rationale_hash") == r_hash
            ):
                return p["id"]

        proposal_id = str(uuid.uuid4())
        proposal = {
            "id": proposal_id,
            "created_at": _now_iso(),
            "target_file": target_file,
            "change_type": change_type,
            "diff": diff,
            "rationale": rationale,
            "confidence": confidence,
            "status": "pending",
            "snoozed_until": None,
            "source_task_ids": list(source_task_ids),
            "source_task_type": source_task_type,
            "applied_at": None,
            "rejected_reason": None,
            "_rationale_hash": r_hash,
        }
        proposals.append(proposal)
        _save_proposals(proposals)
        return proposal_id
    except Exception as e:
        _write_error(f"add_proposal error: {e}")
        return ""


def approve_proposal(proposal_id: str) -> bool:
    """Sets status='approved'. Returns True if found."""
    try:
        proposals = _load_proposals()
        for p in proposals:
            if p.get("id") == proposal_id:
                p["status"] = "approved"
                return _save_proposals(proposals)
        return False
    except Exception as e:
        _write_error(f"approve_proposal error: {e}")
        return False


def reject_proposal(proposal_id: str, reason: str = "") -> bool:
    """Sets status='rejected', records reason."""
    try:
        proposals = _load_proposals()
        for p in proposals:
            if p.get("id") == proposal_id:
                p["status"] = "rejected"
                p["rejected_reason"] = reason
                return _save_proposals(proposals)
        return False
    except Exception as e:
        _write_error(f"reject_proposal error: {e}")
        return False


def snooze_proposal(proposal_id: str, days: int = 7) -> bool:
    """Sets status='snoozed', snoozed_until=now+days."""
    try:
        proposals = _load_proposals()
        for p in proposals:
            if p.get("id") == proposal_id:
                p["status"] = "snoozed"
                p["snoozed_until"] = (
                    datetime.now(timezone.utc) + timedelta(days=days)
                ).isoformat()
                return _save_proposals(proposals)
        return False
    except Exception as e:
        _write_error(f"snooze_proposal error: {e}")
        return False


def apply_proposal(proposal_id: str) -> tuple[bool, str]:
    """
    Apply the change described in the proposal to the target file.
    Creates a .bak backup before any modification.
    Returns (success, message).
    """
    try:
        proposals = _load_proposals()
        proposal = None
        for p in proposals:
            if p.get("id") == proposal_id:
                proposal = p
                break

        if proposal is None:
            return False, f"Proposal {proposal_id} not found"

        change_type = proposal.get("change_type", "edit")
        target_rel = proposal.get("target_file", "")
        diff_content = proposal.get("diff", "")

        if not target_rel:
            return False, "Proposal has no target_file"

        target_path = _PROJECT_ROOT / target_rel

        # --- edit: full replacement ---
        if change_type == "edit":
            if target_path.exists():
                bak = target_path.with_suffix(target_path.suffix + ".bak")
                try:
                    shutil.copy2(target_path, bak)
                except Exception as e:
                    return False, f"Backup failed: {e}"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = target_path.with_suffix(target_path.suffix + ".tmp")
            tmp.write_text(diff_content, encoding="utf-8")
            if target_path.exists():
                target_path.unlink()
            tmp.rename(target_path)

        # --- new: create new file ---
        elif change_type == "new":
            if target_path.exists():
                bak = target_path.with_suffix(target_path.suffix + ".bak")
                try:
                    shutil.copy2(target_path, bak)
                except Exception as e:
                    return False, f"Backup failed: {e}"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = target_path.with_suffix(target_path.suffix + ".tmp")
            tmp.write_text(diff_content, encoding="utf-8")
            if target_path.exists():
                target_path.unlink()
            tmp.rename(target_path)

        # --- claude_md: append rule to CLAUDE.md ---
        elif change_type == "claude_md":
            if _CLAUDE_MD.exists():
                bak = _CLAUDE_MD.with_suffix(".md.bak")
                try:
                    shutil.copy2(_CLAUDE_MD, bak)
                except Exception as e:
                    return False, f"Backup failed: {e}"
            _CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
            with _CLAUDE_MD.open("a", encoding="utf-8") as f:
                f.write(diff_content)

        # --- deprecate: rename to .deprecated.md ---
        elif change_type == "deprecate":
            if not target_path.exists():
                return False, f"Target file not found: {target_rel}"
            bak = target_path.with_suffix(target_path.suffix + ".bak")
            try:
                shutil.copy2(target_path, bak)
            except Exception as e:
                return False, f"Backup failed: {e}"
            stem = target_path.stem
            deprecated_path = target_path.with_name(f"{stem}.deprecated.md")
            if deprecated_path.exists():
                deprecated_path.unlink()
            target_path.rename(deprecated_path)

        else:
            return False, f"Unknown change_type: {change_type}"

        # Update proposal status
        proposal["status"] = "applied"
        proposal["applied_at"] = _now_iso()
        _save_proposals(proposals)
        return True, f"Applied {change_type} to {target_rel}"

    except Exception as e:
        _write_error(f"apply_proposal error: {e}")
        return False, f"Exception: {e}"


def generate_claude_md_proposal(
    pattern: str,
    rationale: str,
    source_task_ids: list,
) -> Optional[str]:
    """
    Creates a proposal to append an auto-learned rule to CLAUDE.md.
    Returns proposal_id or None on error.
    """
    try:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        diff = f"\n\n## Auto-learned rule ({date_str})\n{pattern}\n"
        proposal_id = add_proposal(
            target_file="CLAUDE.md",
            change_type="claude_md",
            diff=diff,
            rationale=rationale,
            confidence=0.6,
            source_task_ids=source_task_ids,
            source_task_type="claude_md_rule",
        )
        return proposal_id if proposal_id else None
    except Exception as e:
        _write_error(f"generate_claude_md_proposal error: {e}")
        return None
