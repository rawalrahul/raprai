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


def test_device_linking_is_first_run_only(client, monkeypatch):
    """Linking to raprai.com is optional now, so it isn't public either."""
    c, data = client
    assert c.get("/device/status").status_code == 200        # first run: open
    _lock(monkeypatch)
    assert c.get("/device/status").status_code == 401
    assert c.post("/device/activate", json={"code": "RAPR-AAAA-BBBB"}).status_code == 401
    assert c.post("/device/unlink").status_code == 401
    r = c.get("/activate", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_no_activation_gate(client, monkeypatch):
    """An unlinked RAPR opens the app (it used to send you to /activate)."""
    c, data = client
    from helm import device_link
    monkeypatch.setattr(device_link, "get_device_token", lambda: None)
    r = c.get("/", follow_redirects=False)
    assert r.status_code == 200, r.headers.get("location")


def test_first_pin_logs_the_owner_in(client, monkeypatch):
    c, data = client
    issued = set()
    def issue():
        issued.add(t := f"tok{len(issued)}")
        return t
    monkeypatch.setattr(auth, "issue_token", issue)
    monkeypatch.setattr(auth, "is_valid_token", lambda t: t in issued)
    r = c.post("/auth/set-pin", json={"pin": "4321"})
    assert r.status_code == 200 and r.cookies.get(auth.COOKIE_NAME) in issued
    # The wizard's next steps work without a separate login.
    assert c.get("/setup/status").status_code == 200
    assert c.get("/device/status").status_code == 200
    # Changing the PIN later doesn't hand out a new login.
    r = c.post("/auth/set-pin", json={"pin": "9999", "old_pin": "4321"})
    assert r.status_code == 200 and not r.cookies.get(auth.COOKIE_NAME)


def test_unlink_forgets_the_token(tmp_path, monkeypatch):
    from helm import device_link
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    (tmp_path / ".env").write_text("A=1\nRAPR_DEVICE_TOKEN=secret\n")
    monkeypatch.setenv("RAPR_DEVICE_TOKEN", "secret")
    monkeypatch.setattr(device_link, "_device_token", "secret")
    device_link.track_usage("chat")
    device_link.unlink_device()
    assert device_link.get_device_token() is None
    assert "RAPR_DEVICE_TOKEN" not in (tmp_path / ".env").read_text()
    assert device_link.get_link_status()["pending_telemetry"] == 0
    assert device_link.flush_telemetry() is False      # nothing is sent when unlinked
