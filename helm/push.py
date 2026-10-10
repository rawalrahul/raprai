"""
helm/push.py — Notifications on your phone, free (Web Push).

Install RAPR on your phone as a web app, allow notifications, and it can tell
you when an action needs your approval, even when the app is closed. Web Push
goes through the browser's own push service (Google's, Apple's, Mozilla's): no
account or paid service is needed on our side.

The server holds a key pair (created once, in user data/push_keys.json) and the
list of subscribed phones/browsers (push_subscriptions.json).
"""

from __future__ import annotations

import base64
import json
import threading
from typing import Optional

from helm.config import logger

_lock = threading.Lock()


def _dir():
    from helm.paths import user_data_dir
    return user_data_dir()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def vapid_keys() -> dict:
    """The server's key pair (public + private, base64url). Created on first use."""
    path = _dir() / "push_keys.json"
    with _lock:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = ec.generate_private_key(ec.SECP256R1())
        public = key.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        private = key.private_numbers().private_value.to_bytes(32, "big")
        keys = {"public": _b64(public), "private": _b64(private)}
        path.write_text(json.dumps(keys), encoding="utf-8")
        return keys


def _subs_path():
    return _dir() / "push_subscriptions.json"


def subscriptions() -> list[dict]:
    try:
        return json.loads(_subs_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []


def add_subscription(sub: dict) -> None:
    endpoint = sub.get("endpoint", "")
    keys = sub.get("keys") or {}
    if not endpoint.startswith("https://") or not keys.get("p256dh") or not keys.get("auth"):
        raise ValueError("not a valid push subscription")
    with _lock:
        subs = [s for s in subscriptions() if s.get("endpoint") != endpoint]
        subs.append({"endpoint": endpoint, "keys": {"p256dh": keys["p256dh"], "auth": keys["auth"]}})
        _subs_path().write_text(json.dumps(subs), encoding="utf-8")


def remove_subscription(endpoint: str) -> None:
    with _lock:
        subs = [s for s in subscriptions() if s.get("endpoint") != endpoint]
        _subs_path().write_text(json.dumps(subs), encoding="utf-8")


def payload(title: str, body: str, tag: str = "rapr", url: str = "/") -> str:
    return json.dumps({"title": title[:80], "body": body[:200], "tag": tag, "url": url})


def send(title: str, body: str, tag: str = "rapr", url: str = "/") -> int:
    """Send to every subscribed device. Returns how many were sent. Never raises."""
    subs = subscriptions()
    if not subs:
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.info("Phone notifications need pywebpush (pip install pywebpush)")
        return 0
    keys = vapid_keys()
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload(title, body, tag, url),
                vapid_private_key=keys["private"],
                vapid_claims={"sub": "mailto:rapr-notifications@example.invalid"},
                ttl=3600,
            )
            sent += 1
        except WebPushException as exc:
            # 404/410: the phone unsubscribed or the browser forgot it; forget it too.
            if exc.response is not None and exc.response.status_code in (404, 410):
                remove_subscription(sub["endpoint"])
            logger.debug("push to a device failed: %s", exc)
        except Exception as exc:
            logger.debug("push failed: %s", exc)
    return sent


def notify_approval(description: str, req_id: str) -> int:
    return send("RAPR needs your OK", description, tag=f"approval-{req_id}", url="/#approvals")
