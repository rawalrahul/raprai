"""Saving who may use RAPR over WhatsApp.

The allowed numbers apply at once and are saved to .env for the next start.
A failed save used to be swallowed: the page said "Saved", and a restart
quietly brought back the old list, numbers you'd removed included.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PIN_SALT", raising=False)
    monkeypatch.delenv("PIN_HASH", raising=False)
    monkeypatch.setenv("WHATSAPP_ALLOWED_NUMBERS", "111")
    (tmp_path / ".env").write_text("RAPR_HEADLESS=1\nWHATSAPP_ALLOWED_NUMBERS=111\n")
    from helm.web_routes import app as webapp
    c = TestClient(webapp)
    c.get("/health")
    if c.cookies.get("hq_csrf"):
        c.headers["X-CSRF-Token"] = c.cookies.get("hq_csrf")
    return c, tmp_path


def test_allowed_numbers_are_saved(client):
    c, data = client
    r = c.post("/api/whatsapp/settings", json={"allowed_numbers": "+44 7700 900123, 222"})
    assert r.status_code == 200
    assert os.environ["WHATSAPP_ALLOWED_NUMBERS"] == "447700900123,222"
    assert "WHATSAPP_ALLOWED_NUMBERS=447700900123,222" in (data / ".env").read_text()


def test_a_failed_save_is_reported(client, monkeypatch):
    import helm.telegram_bot.commands as commands

    def disk_full(key, value):
        raise OSError("No space left on device")
    monkeypatch.setattr(commands, "_update_env", disk_full)
    c, _ = client
    r = c.post("/api/whatsapp/settings", json={"allowed_numbers": "222"})
    assert r.status_code == 500
    assert "until RAPR restarts" in r.json()["error"]
