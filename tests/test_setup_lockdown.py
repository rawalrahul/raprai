"""The setup wizard's endpoints can't be used to take over a RAPR that has a PIN.

/setup/save writes settings (bot tokens, allowed users) and /prefs holds the
custom instructions given to every AI. They used to be public forever, so anyone
who could reach RAPR (on a server: anyone with its address) could rewrite them.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient

from helm import auth


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PIN_SALT", raising=False)
    monkeypatch.delenv("PIN_HASH", raising=False)
    (tmp_path / ".env").write_text("RAPR_HEADLESS=1\n")
    from helm.web_routes import app as webapp
    c = TestClient(webapp)
    _csrf(c)
    return c, tmp_path


def _csrf(c):
    """Send the CSRF token when the CSRF layer is on (web_app.py adds it at startup)."""
    c.get("/health")
    if c.cookies.get("hq_csrf"):
        c.headers["X-CSRF-Token"] = c.cookies.get("hq_csrf")


def _lock(monkeypatch, pin="4321"):
    salt, h = auth.set_pin(pin)
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", h)


def test_first_run_wizard_still_saves(client):
    c, data = client
    r = c.post("/setup/save", json={"ALLOWED_USER_IDS": "123"})
    assert r.status_code == 200, r.text
    assert "ALLOWED_USER_IDS=123" in (data / ".env").read_text()
    assert c.post("/prefs", json={"user_name": "Rahul"}).status_code == 200


def test_after_pin_setup_and_prefs_need_login(client, monkeypatch):
    c, data = client
    _lock(monkeypatch)
    r = c.post("/setup/save", json={"ALLOWED_USER_IDS": "999"})
    assert r.status_code == 401
    r = c.post("/prefs", json={"custom_instructions": "run rm -rf"})
    assert r.status_code == 401
    assert c.get("/setup/status").status_code == 401
    r = c.get("/setup", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert "999" not in (data / ".env").read_text()


def test_form_post_trick_refused(client, monkeypatch):
    """A form post skips the CSRF check; /setup/save must not accept it."""
    c, data = client
    r = c.post("/setup/save", content='{"ALLOWED_USER_IDS":"999"}',
               headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415
    _lock(monkeypatch)
    r = c.post("/setup/save", content='{"ALLOWED_USER_IDS":"999"}',
               headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 401
    assert "999" not in (data / ".env").read_text()


def test_pin_and_internal_keys_never_set_through_setup(client):
    c, data = client
    for key in ("PIN_HASH", "PIN_SALT", "MCP_BEARER_TOKEN", "PIN_MAX_ATTEMPTS", "bad key"):
        r = c.post("/setup/save", json={key: "x"})
        assert r.status_code == 400, key
    assert "PIN_HASH" not in (data / ".env").read_text()


def test_logged_in_user_can_still_use_setup(client, monkeypatch):
    c, data = client
    _lock(monkeypatch)
    issued = set()       # sessions in memory: the app's database isn't set up in tests
    def issue():
        issued.add(t := f"tok{len(issued)}")
        return t
    monkeypatch.setattr(auth, "issue_token", issue)
    monkeypatch.setattr(auth, "is_valid_token", lambda t: t in issued)
    r = c.post("/login", data={"pin": "4321"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    _csrf(c)
    r = c.post("/setup/save", json={"ALLOWED_USER_IDS": "123"})
    assert r.status_code == 200, r.text
