"""What login, logout and the PIN lockout do when the database fails.

These errors used to be swallowed:
- a failed write of a wrong-PIN attempt turned the lockout off;
- a session that couldn't be saved logged you in and straight back out;
- a session that couldn't be deleted stayed valid after "logging out".
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi.testclient import TestClient

import helm.db as db
from helm import auth


class _FailingDB:
    """The real connection, except statements containing *fail_on* raise."""

    def __init__(self, conn, fail_on):
        self._conn, self._fail_on = conn, fail_on

    def execute(self, sql, *args):
        if self._fail_on in sql:
            raise sqlite3.OperationalError("database is locked")
        return self._conn.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """A new database in tmp_path. Other tests share this thread's cached
    connection, so it's put back afterwards rather than closed."""
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(db, "_init_done", False)     # init_db runs once per process
    previous = getattr(db._local, "conn", None)
    db._local.conn = None
    db.init_db()
    auth.load_lockout_from_db()                      # what startup does
    auth._failed.clear()
    yield tmp_path
    auth._failed.clear()
    mine = db._local.conn
    if mine is not None and mine is not previous:
        mine.close()
    db._local.conn = previous


def _fail(monkeypatch, fail_on):
    real = db.get_db
    monkeypatch.setattr(db, "get_db", lambda: _FailingDB(real(), fail_on))
    return real


def test_lockout_still_counts_when_attempts_cant_be_saved(fresh_db, monkeypatch):
    _fail(monkeypatch, "INSERT INTO lockout_attempts")
    for _ in range(auth.MAX_ATTEMPTS):
        auth.record_failure("203.0.113.9")
    assert auth.is_locked_out("203.0.113.9")


def test_lockout_counts_each_attempt_once(fresh_db):
    for _ in range(auth.MAX_ATTEMPTS - 1):
        auth.record_failure("203.0.113.9")
    assert not auth.is_locked_out("203.0.113.9")
    auth.load_lockout_from_db()            # what startup does; mustn't double-count
    assert not auth.is_locked_out("203.0.113.9")
    auth.record_failure("203.0.113.9")
    assert auth.is_locked_out("203.0.113.9")


@pytest.fixture
def client(fresh_db, monkeypatch):
    salt, h = auth.set_pin("4321")
    monkeypatch.setenv("PIN_SALT", salt)
    monkeypatch.setenv("PIN_HASH", h)
    (fresh_db / ".env").write_text("RAPR_HEADLESS=1\n")
    from helm.web_routes import app as webapp
    c = TestClient(webapp)
    c.get("/health")
    if c.cookies.get("hq_csrf"):
        c.headers["X-CSRF-Token"] = c.cookies.get("hq_csrf")
    return c


def _login(c):
    return c.post("/login", data={"pin": "4321"}, follow_redirects=False)


def test_login_works(client):
    r = _login(client)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert client.cookies.get(auth.COOKIE_NAME)


def test_login_says_so_when_the_session_cant_be_saved(client, monkeypatch):
    _fail(monkeypatch, "INSERT INTO auth_sessions")
    r = _login(client)
    assert r.status_code == 303 and r.headers["location"].startswith("/login?error=")
    assert "couldn't+save+your+session" in r.headers["location"]
    assert not client.cookies.get(auth.COOKIE_NAME)


def test_logout_ends_the_session(client):
    _login(client)
    token = client.cookies.get(auth.COOKIE_NAME)
    r = client.post("/logout", follow_redirects=False)
    assert r.headers["location"] == "/login"
    assert not auth.is_valid_token(token)


def test_logout_says_so_when_the_session_cant_be_ended(client, monkeypatch):
    _login(client)
    token = client.cookies.get(auth.COOKIE_NAME)
    real = _fail(monkeypatch, "DELETE FROM auth_sessions")
    r = client.post("/logout", follow_redirects=False)
    assert r.headers["location"].startswith("/login?error=")
    monkeypatch.setattr(db, "get_db", real)
    assert auth.is_valid_token(token)      # still valid, and the user was told


def test_migration_ignores_only_an_existing_column():
    from helm.db_migrate import _add_column
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (a)")
    _add_column(conn, "t", "b TEXT")
    _add_column(conn, "t", "b TEXT")       # already there: fine
    with pytest.raises(sqlite3.OperationalError):
        _add_column(conn, "missing_table", "b TEXT")


def test_quick_attempts_each_count_even_when_the_clock_doesnt_move(fresh_db, monkeypatch):
    """Windows' clock moves in ~15 ms steps: a burst of guesses got one timestamp
    and counted as a single attempt, so it was never locked out."""
    monkeypatch.setattr(auth.time, "time", lambda: 1_800_000_000.0)
    for _ in range(auth.MAX_ATTEMPTS):
        auth.record_failure("203.0.113.9")
    assert auth.is_locked_out("203.0.113.9")
