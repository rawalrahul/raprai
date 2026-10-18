"""helm/web_routes/recap_routes.py — your month with RAPR (worked out locally, never sent)."""

import re
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import helm.recap as recap

router = APIRouter()


@router.get("/api/recap")
async def get_recap(month: Optional[str] = None):
    """month: 'YYYY-MM' (default: this month)."""
    if month and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        return JSONResponse({"error": "month must look like 2026-10"}, status_code=400)
    try:
        data = recap.build(month)
        data["first_month"] = recap.first_month()
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    return JSONResponse(data)
