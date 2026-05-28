"""
helm/web_routes/learning_routes.py — API endpoints for self-improvement dashboard.

Endpoints:
    GET  /learning/summary          — 30-day stats summary
    GET  /learning/trends           — daily trend data for charts
    GET  /learning/routing          — routing table recommendations
    GET  /learning/playbooks        — playbook stats
    GET  /learning/proposals        — list pending proposals
    POST /learning/proposals/{id}/approve
    POST /learning/proposals/{id}/reject
    POST /learning/proposals/{id}/snooze
    POST /learning/proposals/{id}/apply
    POST /learning/index/refresh    — regenerate LEARNING_INDEX.md
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/learning", tags=["learning"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RejectRequest(BaseModel):
    reason: str = ""


class SnoozeRequest(BaseModel):
    days: int = 7


class FeedbackRequest(BaseModel):
    session_id: str
    positive: bool


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
async def summary():
    """30-day stats summary including per-AI breakdown."""
    try:
        from helm.learning.metrics import get_summary
        data = get_summary()
        return {"ok": True, **data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/trends")
async def trends():
    """Daily trend data for charts."""
    try:
        from helm.learning.metrics import get_trends
        data = get_trends()
        return {"ok": True, **data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/routing")
async def routing():
    """Routing table recommendations."""
    try:
        from helm.learning.metrics import get_routing_summary
        data = get_routing_summary()
        return {"ok": True, **data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/playbooks")
async def playbooks():
    """Playbook stats."""
    try:
        from helm.learning.metrics import get_playbook_stats
        data = get_playbook_stats()
        return {"ok": True, **data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/proposals")
async def list_proposals(status: str = "pending"):
    """List skill proposals filtered by status."""
    try:
        from helm.learning.skill_proposals import list_proposals as _list
        proposals = _list(status=status)
        return {"ok": True, "proposals": proposals, "count": len(proposals)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Proposal action endpoints
# ---------------------------------------------------------------------------

@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str):
    """Approve a skill proposal."""
    try:
        from helm.learning.skill_proposals import approve_proposal as _approve
        ok = _approve(proposal_id)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, req: RejectRequest = RejectRequest()):
    """Reject a skill proposal with optional reason."""
    try:
        from helm.learning.skill_proposals import reject_proposal as _reject
        ok = _reject(proposal_id, reason=req.reason)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/proposals/{proposal_id}/snooze")
async def snooze_proposal(proposal_id: str, req: SnoozeRequest = SnoozeRequest()):
    """Snooze a skill proposal for N days."""
    try:
        from helm.learning.skill_proposals import snooze_proposal as _snooze
        ok = _snooze(proposal_id, days=req.days)
        return {"ok": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str):
    """Apply a skill proposal (write changes to disk)."""
    try:
        from helm.learning.skill_proposals import apply_proposal as _apply
        ok, message = _apply(proposal_id)
        return {"ok": ok, "message": message}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Human feedback
# ---------------------------------------------------------------------------

@router.post("/feedback")
async def feedback(req: FeedbackRequest):
    """Record explicit thumbs up/down feedback for last task in session."""
    try:
        from helm.learning.telemetry import record_explicit_feedback
        found = record_explicit_feedback(req.session_id, req.positive)
        return {"ok": True, "found": found}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Routing suggestion
# ---------------------------------------------------------------------------

@router.get("/suggest")
async def suggest(text: str = "", session_ai: str = ""):
    """
    Classify text, return routing recommendation if confidence > 0.6.
    Returns {recommend: bool, recommended_ai, confidence, task_type, reason}
    """
    try:
        if not text.strip():
            return {"recommend": False}
        from helm.learning.classifier import classify_and_fingerprint
        from helm.learning.router import get_recommendation
        clf = classify_and_fingerprint(text)
        task_type = clf.get("task_type", "unknown")
        if task_type in ("chat", "unknown"):
            return {"recommend": False}
        available = ["claude", "gemini", "codex", "ollama"]
        rec = get_recommendation(task_type, available)
        recommended = rec.get("recommended_ai")
        confidence = float(rec.get("confidence", 0.0))
        if not recommended or confidence < 0.6:
            return {"recommend": False}
        if recommended == session_ai:
            return {"recommend": False}
        return {
            "recommend": True,
            "recommended_ai": recommended,
            "confidence": round(confidence, 2),
            "task_type": task_type,
            "reason": rec.get("reason", ""),
            "budget_warn": rec.get("budget_warn", False),
        }
    except Exception as e:
        return {"recommend": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Cross-AI insights
# ---------------------------------------------------------------------------

@router.get("/insights")
async def insights(limit: int = 20):
    """List cross-AI performance insights sorted by gap ratio."""
    try:
        from helm.learning.cross_ai import list_insights as _list_insights
        items = _list_insights(limit=limit)
        return {"ok": True, "insights": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Index refresh
# ---------------------------------------------------------------------------

@router.post("/index/refresh")
async def refresh_index():
    """Regenerate LEARNING_INDEX.md."""
    try:
        from helm.learning.index_updater import update_learning_index
        update_learning_index()
        return {"ok": True, "message": "LEARNING_INDEX.md regenerated"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Kill switch endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def learning_status():
    """Return whether learning is enabled (ENABLED sentinel present)."""
    try:
        from helm.learning import is_learning_enabled
        return {"enabled": is_learning_enabled()}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.post("/enable")
async def learning_enable():
    """Create ENABLED sentinel — resume learning."""
    try:
        from helm.learning import enable_learning
        enable_learning()
        return {"ok": True, "enabled": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/disable")
async def learning_disable():
    """Delete ENABLED sentinel — pause all learning (kill switch)."""
    try:
        from helm.learning import disable_learning
        disable_learning()
        return {"ok": True, "enabled": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# User context endpoints
# ---------------------------------------------------------------------------

class ContextUpdateRequest(BaseModel):
    prefer_speed_vs_quality: Optional[float] = None
    trusted_ai: Optional[str] = None
    avoid_apps: Optional[list] = None


@router.get("/context")
async def get_user_context():
    """Return detected user environment context."""
    try:
        from helm.learning.user_context import load_context
        return load_context()
    except Exception as e:
        return {"error": str(e)}


@router.put("/context")
async def update_user_context(req: ContextUpdateRequest):
    """Update user preferences in user_context.json."""
    try:
        from helm.learning.user_context import update_context
        updates = {k: v for k, v in req.dict().items() if v is not None}
        ctx = update_context(updates)
        return {"ok": True, "context": ctx}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/context/refresh")
async def refresh_user_context():
    """Re-run OS/screen/browser detection and update user_context.json."""
    try:
        from helm.learning.user_context import detect_and_save
        import asyncio
        ctx = await asyncio.to_thread(detect_and_save)
        return {"ok": True, "context": ctx}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Similarity index endpoints
# ---------------------------------------------------------------------------

class MergeRequest(BaseModel):
    src: str
    canonical: str


@router.get("/similarity/stats")
async def similarity_stats():
    """Return SQLite similarity index statistics."""
    try:
        from helm.learning.db import get_stats
        return {"ok": True, **get_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/similarity/find")
async def similarity_find(fingerprint: str, task_type: str = "", limit: int = 5):
    """Find similar fingerprints. Provide fingerprint + optional task_type."""
    try:
        from helm.learning.db import find_similar, resolve
        canonical = resolve(fingerprint)
        results = find_similar(canonical, task_type, [], [], limit=limit)
        return {"ok": True, "canonical": canonical, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/similarity/merge")
async def similarity_merge(req: MergeRequest):
    """Mark two fingerprints as equivalent (user-defined)."""
    try:
        from helm.learning.db import merge_fingerprints
        merge_fingerprints(req.src, req.canonical)
        return {"ok": True, "src": req.src, "canonical": req.canonical}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/similarity/rebuild")
async def similarity_rebuild():
    """Rebuild SQLite index from all task_logs/ JSON files."""
    try:
        import asyncio
        from helm.learning.db import rebuild_from_logs
        result = await asyncio.to_thread(rebuild_from_logs)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Export / import / rollback endpoints (thin wrappers over cli.py)
# ---------------------------------------------------------------------------

class RollbackPlaybookRequest(BaseModel):
    name: str


class RollbackRoutingRequest(BaseModel):
    days: int = 1


class RollbackSkillRequest(BaseModel):
    skill_path: str


class MergeFingerprintsRequest(BaseModel):
    src: str
    canonical: str


@router.post("/export")
async def export_bundle():
    """Export learning bundle to helm/learning/learning_bundle.tar.gz."""
    try:
        import asyncio
        from pathlib import Path
        from helm.learning.cli import cmd_export
        out = Path(__file__).parent.parent / "learning" / "learning_bundle.tar.gz"
        import argparse
        args = argparse.Namespace(path=str(out))
        await asyncio.to_thread(cmd_export, args)
        return {"ok": True, "path": str(out)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/snapshot")
async def routing_snapshot():
    """Write a routing table snapshot to routing_history/."""
    try:
        import asyncio
        import argparse
        from helm.learning.cli import cmd_snapshot
        await asyncio.to_thread(cmd_snapshot, argparse.Namespace())
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/rollback/playbook")
async def rollback_playbook(req: RollbackPlaybookRequest):
    """Roll back a playbook to its previous version."""
    try:
        import asyncio
        import argparse
        from helm.learning.cli import cmd_rollback
        args = argparse.Namespace(command="rollback", sub="playbook", name=req.name)
        rc = await asyncio.to_thread(cmd_rollback, args)
        return {"ok": rc == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/rollback/routing")
async def rollback_routing(req: RollbackRoutingRequest):
    """Restore routing table from a snapshot N days ago."""
    try:
        import asyncio
        import argparse
        from helm.learning.cli import cmd_rollback
        args = argparse.Namespace(command="rollback", sub="routing", days=req.days)
        rc = await asyncio.to_thread(cmd_rollback, args)
        return {"ok": rc == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/rollback/skill")
async def rollback_skill(req: RollbackSkillRequest):
    """Restore a skill file from its backup."""
    try:
        import asyncio
        import argparse
        from helm.learning.cli import cmd_rollback
        args = argparse.Namespace(command="rollback", sub="skill", skill_path=req.skill_path)
        rc = await asyncio.to_thread(cmd_rollback, args)
        return {"ok": rc == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Multi-user namespace endpoints
# ---------------------------------------------------------------------------

@router.get("/multiuser/status")
async def multiuser_status():
    """Return whether multi-user namespace mode is active."""
    try:
        from helm.learning.namespace import is_multi_user
        return {"enabled": is_multi_user()}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.post("/multiuser/enable")
async def multiuser_enable():
    """Enable multi-user namespace mode (creates MULTI_USER sentinel)."""
    try:
        from helm.learning.namespace import enable_multi_user
        enable_multi_user()
        return {"ok": True, "enabled": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/multiuser/disable")
async def multiuser_disable():
    """Disable multi-user namespace mode."""
    try:
        from helm.learning.namespace import disable_multi_user
        disable_multi_user()
        return {"ok": True, "enabled": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}
