"""helm/web_routes/push_routes.py — phone notifications (Web Push)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from helm import push

router = APIRouter()


class SubscribeBody(BaseModel):
    endpoint: str
    keys: dict


@router.get("/api/push/key")
async def public_key():
    return JSONResponse({"publicKey": push.vapid_keys()["public"]})


@router.post("/api/push/subscribe")
async def subscribe(body: SubscribeBody):
    try:
        push.add_subscription(body.model_dump())
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"ok": True, "devices": len(push.subscriptions())})


@router.post("/api/push/unsubscribe")
async def unsubscribe(body: dict):
    push.remove_subscription(str(body.get("endpoint", "")))
    return JSONResponse({"ok": True})


@router.post("/api/push/test")
async def test():
    return JSONResponse({"sent": push.send("RAPR AI", "Notifications are working.", tag="test")})
