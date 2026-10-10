"""helm/web_routes/safety_routes.py — approval rules and the audit log."""

import time

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from helm import approval_rules as rules
from helm import audit

router = APIRouter()


class RulesBody(BaseModel):
    rules: list[dict]


@router.get("/api/approval-rules")
async def get_rules():
    return JSONResponse({"rules": rules.load_rules(), "actions": list(rules.ACTIONS)})


@router.put("/api/approval-rules")
async def put_rules(body: RulesBody):
    try:
        rules.save_rules(body.rules)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"ok": True, "rules": rules.load_rules()})


@router.get("/api/audit")
async def get_audit(since_days: float = Query(0, ge=0), event: str = "", q: str = "", limit: int = Query(200, ge=1, le=2000)):
    since = time.time() - since_days * 86400 if since_days else 0.0
    return JSONResponse({"entries": audit.read(since=since, event=event or None, query=q, limit=limit)})


@router.get("/api/audit.csv")
async def get_audit_csv(since_days: float = Query(0, ge=0)):
    since = time.time() - since_days * 86400 if since_days else 0.0
    return PlainTextResponse(audit.to_csv(audit.read(since=since, limit=100000)), media_type="text/csv")
