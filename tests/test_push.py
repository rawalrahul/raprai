"""Phone notifications: keys, subscriptions, sending (network calls are faked)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.push as push


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(push, "_dir", lambda: tmp_path)
    return tmp_path


def sub(n=1):
    return {"endpoint": f"https://push.example.com/{n}", "keys": {"p256dh": "AAA", "auth": "BBB"}}


def test_keys_are_made_once_and_kept(data):
    k1 = push.vapid_keys()
    k2 = push.vapid_keys()
    assert k1 == k2
    assert len(k1["public"]) >= 80 and len(k1["private"]) >= 40


def test_subscriptions_are_added_once_and_removable(data):
    push.add_subscription(sub(1))
    push.add_subscription(sub(1))
    push.add_subscription(sub(2))
    assert len(push.subscriptions()) == 2
    push.remove_subscription(sub(1)["endpoint"])
    assert [s["endpoint"] for s in push.subscriptions()] == [sub(2)["endpoint"]]


def test_invalid_subscriptions_are_refused(data):
    with pytest.raises(ValueError):
        push.add_subscription({"endpoint": "http://insecure", "keys": {"p256dh": "a", "auth": "b"}})
    with pytest.raises(ValueError):
        push.add_subscription({"endpoint": "https://ok", "keys": {}})


def test_send_reaches_every_device_and_forgets_gone_ones(data, monkeypatch):
    import pywebpush
    push.add_subscription(sub(1))
    push.add_subscription(sub(2))
    sent_to = []

    def fake_webpush(subscription_info, data, **kw):
        sent_to.append(subscription_info["endpoint"])
        if subscription_info["endpoint"].endswith("/2"):
            resp = type("R", (), {"status_code": 410})()
            raise pywebpush.WebPushException("gone", response=resp)
    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)
    n = push.send("Approval", "Delete build?", tag="t")
    assert n == 1 and len(sent_to) == 2
    assert [s["endpoint"] for s in push.subscriptions()] == [sub(1)["endpoint"]]


def test_no_devices_means_nothing_sent(data):
    assert push.send("x", "y") == 0


def test_payload_is_short_and_json(data):
    p = json.loads(push.payload("T" * 200, "B" * 500, tag="g", url="/"))
    assert len(p["title"]) == 80 and len(p["body"]) == 200
