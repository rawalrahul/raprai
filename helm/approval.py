"""
helm/approval.py — Approval queue for destructive & sensitive actions.

When an AI or pipeline step wants to perform a destructive action
(delete files, modify system settings, etc.), Helm creates an approval
request visible in both the Web UI and Telegram.

The user can approve or deny from either interface.
"""

import asyncio
import re
import time
import uuid
from typing import Optional

import helm.state as _st
from helm.config import logger


# ── Destructive pattern detection ─────────────────────────────────────────

_DESTRUCTIVE_KEYWORDS = re.compile(
    r'\b(?:delete|remove|rm\b|rmdir|unlink|shutil\.rmtree|os\.remove|'
    r'drop\s+table|truncate|destroy|wipe|erase|purge|overwrite\s+all|'
    r'format\s+disk|clean\s+all)\b',
    re.IGNORECASE,
)


def looks_destructive(text: str) -> bool:
    """Return True if text suggests destructive file/data operations."""
    return bool(_DESTRUCTIVE_KEYWORDS.search(text))


# ── Approval request lifecycle ────────────────────────────────────────────

def create_request(
    session_id: str,
    action: str,
    description: str,
    details: list[str] | None = None,
    pipeline_id: str | None = None,
    step_id: str | None = None,
) -> dict:
    """Create a new pending approval request."""
    req_id = f"appr-{uuid.uuid4().hex[:8]}"
    req = {
        "id": req_id,
        "session_id": session_id,
        "pipeline_id": pipeline_id,
        "step_id": step_id,
        "action": action,
        "description": description,
        "details": details or [],
        "status": "pending",
        "created_at": time.time(),
        "resolved_at": None,
        "resolved_by": None,
        "_event": asyncio.Event(),
    }
    _st.approval_queue[req_id] = req
    logger.info("Approval request created: %s — %s", req_id, description)
    return req


def resolve(req_id: str, status: str, source: str = "web") -> bool:
    """Resolve an approval: status = 'approved' | 'denied'. Returns True on success."""
    req = _st.approval_queue.get(req_id)
    if not req or req["status"] != "pending":
        return False
    req["status"] = status
    req["resolved_at"] = time.time()
    req["resolved_by"] = source
    req["_event"].set()
    logger.info("Approval %s %s (via %s)", req_id, status, source)
    return True


async def wait(req_id: str, timeout: float = 300.0) -> str:
    """Block until the request is resolved. Returns 'approved', 'denied', or 'timeout'."""
    req = _st.approval_queue.get(req_id)
    if not req:
        return "denied"
    try:
        await asyncio.wait_for(req["_event"].wait(), timeout=timeout)
    except asyncio.TimeoutError:
        req["status"] = "timeout"
        req["resolved_at"] = time.time()
        req["resolved_by"] = "system"
        logger.warning("Approval %s timed out after %.0fs", req_id, timeout)
        return "timeout"
    return req["status"]


def payload(req: dict) -> dict:
    """Serialisable version (strips internal asyncio.Event)."""
    return {k: v for k, v in req.items() if not k.startswith("_")}


def pending() -> list[dict]:
    """All currently pending requests (serialisable)."""
    return [
        payload(r) for r in _st.approval_queue.values()
        if r["status"] == "pending"
    ]


def cleanup(max_age: float = 3600.0) -> int:
    """Remove resolved requests older than max_age seconds. Returns count removed."""
    now = time.time()
    expired = [
        rid for rid, r in _st.approval_queue.items()
        if r["status"] != "pending" and (now - r.get("resolved_at", now)) > max_age
    ]
    for rid in expired:
        del _st.approval_queue[rid]
    return len(expired)


# ── Broadcast helpers ─────────────────────────────────────────────────────

async def broadcast_approval(req: dict):
    """Send an approval request to both Web UI (WebSocket) and Telegram."""
    from helm.broadcast import broadcast

    await broadcast({
        "type": "approval_request",
        "approval": payload(req),
    })

    # Send to Telegram with inline keyboard
    try:
        await _send_approval_to_telegram(req)
    except Exception as exc:
        logger.debug("Could not send approval to Telegram: %s", exc)


async def broadcast_resolution(req: dict):
    """Notify UI and Telegram that an approval was resolved."""
    from helm.broadcast import broadcast

    await broadcast({
        "type": "approval_resolved",
        "approval": payload(req),
    })


async def _send_approval_to_telegram(req: dict):
    """Send an approval request to Telegram with Approve/Deny inline buttons."""
    if not _st.telegram_app or not _st.telegram_chat_id:
        return

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    except ImportError:
        return

    req_id = req["id"]
    action_icon = {
        "pipeline_step": "🔧",
        "file_delete": "🗑️",
        "destructive_command": "⚠️",
    }.get(req["action"], "❓")

    text = (
        f"{action_icon} **Approval Required**\n\n"
        f"{req['description']}\n"
    )
    if req.get("details"):
        details_text = "\n".join(f"  • {d[:100]}" for d in req["details"][:5])
        text += f"\n{details_text}\n"

    text += "\nApprove or deny this action:"

    from helm.kelvin_stickers import send_kelvin_sticker
    await send_kelvin_sticker("approval")  # no-op unless the user opted in

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"appr:approve:{req_id}"),
            InlineKeyboardButton("❌ Deny", callback_data=f"appr:deny:{req_id}"),
        ],
    ])

    await _st.telegram_app.bot.send_message(
        chat_id=_st.telegram_chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
