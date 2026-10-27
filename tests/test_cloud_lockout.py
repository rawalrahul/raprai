"""PIN lockout on a cloud server.

There, every visitor arrives through RAPR's Cloudflare tunnel, so they all had
the tunnel's address: a stranger's 5 wrong PINs locked the owner out too, and
the shared limit still let anyone guess a short PIN in days.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient

import helm.auth as auth


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    salt, hashed = auth.set_pin("correct-horse")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", hashed)
    auth._failed.clear()
    from helm.web_routes import app as webapp
    yield TestClient(webapp, follow_redirects=False)
    auth._failed.clear()


def _wrong_pins(c, ip, n=auth.MAX_ATTEMPTS):
    for _ in range(n):
        c.post("/login", data={"pin": "nope"}, headers={"cf-connecting-ip": ip})


def test_behind_the_tunnel_a_stranger_only_locks_out_themselves(client, monkeypatch):
    monkeypatch.setenv("RAPR_BEHIND_TUNNEL", "1")
    _wrong_pins(client, "203.0.113.9")
    assert auth.is_locked_out("203.0.113.9")
    assert not auth.is_locked_out("198.51.100.7")          # the owner, elsewhere


def test_without_the_tunnel_the_header_is_ignored(client):
    """Anyone could send the header; a fresh fake address per guess must not reset the count."""
    for i in range(auth.MAX_ATTEMPTS):
        _wrong_pins(client, f"10.0.0.{i}", n=1)
    assert auth.is_locked_out("testclient")


def test_a_cloud_pin_needs_8_characters(client, monkeypatch):
    monkeypatch.setenv("RAPR_BEHIND_TUNNEL", "1")
    monkeypatch.delenv("PIN_SALT")
    monkeypatch.delenv("PIN_HASH")
    r = client.post("/auth/set-pin", json={"pin": "1234567"})
    assert r.status_code == 400 and "8 characters" in r.json()["error"]


def test_the_cloud_server_is_set_up_behind_the_tunnel():
    from helm.cloud import plan
    compose = plan.compose_file(plan.CloudOptions(host="h", name="rapr", pin_salt="s", pin_hash="h"))
    assert 'RAPR_BEHIND_TUNNEL: "1"' in compose and "ports:" not in compose
