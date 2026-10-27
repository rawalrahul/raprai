"""Connecting an app (OAuth) needs a login.

/plugins/<id>/oauth/start used to be open. Anyone who could reach RAPR could
start a flow, then send its state to the callback with a token of their own:
RAPR saved it as that app's token and turned the plugin on.
"""
import os
import sys
import urllib.parse as up

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    from helm import db
    monkeypatch.setattr(db, "_init_done", False)      # init_db runs once per process
    previous = getattr(db._local, "conn", None)
    db._local.conn = None
    db.init_db()
    import helm.auth as auth
    salt, hashed = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", hashed)
    from helm.web_routes import app as webapp
    yield TestClient(webapp, follow_redirects=False)
    mine = db._local.conn
    if mine is not None and mine is not previous:
        mine.close()
    db._local.conn = previous


@pytest.mark.parametrize("path", ["/plugins/github/oauth/start", "/plugins/github/connect"])
def test_starting_a_connection_needs_a_login(client, path):
    r = client.get(path)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_the_callback_is_open_but_only_finishes_a_flow_you_started(client):
    r = client.get("/plugins/oauth/callback?token=SOMEONE-ELSES&state=made-up")
    assert r.status_code == 200 and "Invalid or expired state" in r.text


def test_logged_in_you_can_still_connect(client):
    import helm.auth as auth
    client.cookies.set(auth.COOKIE_NAME, auth.issue_token())
    r = client.get("/plugins/github/oauth/start")
    assert r.status_code == 307
    state = up.parse_qs(up.urlparse(r.headers["location"]).query).get("state", [""])[0]
    assert state
