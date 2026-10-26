"""helm/web_routes/whatsapp_routes.py — Link / unlink WhatsApp (Settings → WhatsApp)."""

import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import helm.whatsapp_bridge as wa
from helm.config import logger

router = APIRouter()


class WhatsAppSettings(BaseModel):
    allowed_numbers: str = ""


@router.get("/api/whatsapp/status")
async def whatsapp_status():
    return JSONResponse(wa.public_state())


@router.post("/api/whatsapp/connect")
async def whatsapp_connect():
    return JSONResponse(await wa.start())


@router.post("/api/whatsapp/disconnect")
async def whatsapp_disconnect():
    """Unlink RAPR from the phone and forget the saved session."""
    return JSONResponse(await wa.stop(logout=True))


@router.post("/api/whatsapp/settings")
async def whatsapp_settings(req: WhatsAppSettings):
    import re
    nums = ",".join(n for n in (re.sub(r"\D", "", x) for x in req.allowed_numbers.split(",")) if n)
    os.environ["WHATSAPP_ALLOWED_NUMBERS"] = nums
    try:
        from helm.telegram_bot.commands import _update_env
        _update_env("WHATSAPP_ALLOWED_NUMBERS", nums)
    except Exception:
        # Applied, but a restart would bring back the old list: say so.
        logger.error("WhatsApp: couldn't save the allowed numbers to .env", exc_info=True)
        return JSONResponse({"error": "Couldn't save the allowed numbers, so they last only "
                                      "until RAPR restarts. Check the log."}, status_code=500)
    return JSONResponse(wa.public_state())
