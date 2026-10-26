"""Other web sites can't reach RAPR through your browser.

- /ws: browsers don't apply CORS to WebSockets, so without a PIN any page you
  visited could connect to ws://localhost:<port>/ws and chat with your AIs.
- /login?error=...: the text went into the page's script with only " escaped,
  so a link could end the script and run its own on RAPR's login page.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from helm import auth


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PIN_SALT", raising=False)
    monkeypatch.delenv("PIN_HASH", raising=False)
    (tmp_path / ".env").write_text("RAPR_HEADLESS=1\n")
    from helm.web_routes import app as webapp
    return TestClient(webapp)


def _first_message(c, headers):
    with c.websocket_connect("/ws", headers=headers) as ws:
        return json.loads(ws.receive_text())


def test_ws_from_the_rapr_page_works(client):
    assert _first_message(client, {"Origin": "http://testserver"})["type"] == "state"


def test_ws_without_origin_works(client):
    """Scripts and RAPR's own clients don't send Origin."""
    assert _first_message(client, {})["type"] == "state"


@pytest.mark.parametrize("origin", [
    "https://evil.example", "http://localhost:3000", "http://testserver.evil.example", "null",
])
def test_ws_from_another_site_refused_without_pin(client, origin):
    with pytest.raises(WebSocketDisconnect) as e:
        _first_message(client, {"Origin": origin})
    assert e.value.code == 4403


def test_ws_with_pin_still_needs_login(client, monkeypatch):
    salt, h = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", h)
    with pytest.raises(WebSocketDisconnect) as e:
        _first_message(client, {"Origin": "http://testserver"})
    assert e.value.code == 4401


@pytest.mark.parametrize("error", [
    '</script><script>alert(1)</script>',
    '"; alert(1); "',
    '\\"; alert(1); //',
    '<img src=x onerror=alert(1)>',
    'line break',
])
def test_login_error_cannot_run_script(client, monkeypatch, error):
    salt, h = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", h)
    html = client.get("/login", params={"error": error}).text
    assert "alert(1)</script>" not in html and "<img src=x" not in html
    line = next(l for l in html.splitlines() if l.startswith("var msg = "))
    # The whole value is one JS string literal that decodes back to the text
    assert json.loads(line[len("var msg = "):].rstrip(";")) == error


def test_login_error_message_still_shows(client, monkeypatch):
    salt, h = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", h)
    html = client.get("/login", params={"error": "Incorrect PIN. 4 attempt(s) remaining."}).text
    assert 'var msg = "Incorrect PIN. 4 attempt(s) remaining.";' in html
