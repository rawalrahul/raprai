"""The token vault says so when it can't save a token.

It used to log a warning and carry on. Callers then replaced the .env value
with "vault-managed", so the token was gone at the next restart; and with an
unreadable key it quietly stored the token in plain text.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from helm import db, token_vault


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(db, "_init_done", False)
    previous = getattr(db._local, "conn", None)
    db._local.conn = None
    db.init_db()
    yield tmp_path
    mine = db._local.conn
    if mine is not None and mine is not previous:
        mine.close()
    db._local.conn = previous


def _stored(key):
    token_vault._ensure_table()
    row = db.get_db().execute("SELECT cipher FROM token_vault WHERE env_key = ?", (key,)).fetchone()
    return row["cipher"] if row else None


def test_a_saved_token_is_encrypted_and_reads_back(data):
    token_vault.store_token("RAPR_TEST_TOKEN", "s3cret")
    assert _stored("RAPR_TEST_TOKEN") not in (None, "s3cret")
    assert token_vault.load_token("RAPR_TEST_TOKEN") == "s3cret"


def test_a_failed_write_is_an_error(data, monkeypatch):
    def broken_db():
        raise OSError("disk full")
    monkeypatch.setattr(db, "get_db", broken_db)
    with pytest.raises(OSError):
        token_vault.store_token("RAPR_TEST_TOKEN", "s3cret")


def test_no_plain_text_when_the_key_cant_be_loaded(data, monkeypatch):
    def no_key():
        raise OSError("key file unreadable")
    monkeypatch.setattr(token_vault, "_get_or_create_key", no_key)
    with pytest.raises(RuntimeError):
        token_vault.store_token("RAPR_TEST_TOKEN", "s3cret")
    assert _stored("RAPR_TEST_TOKEN") is None


def test_moving_keys_into_the_vault_never_drops_one(data, monkeypatch):
    """If a key can't be stored, its .env copy must stay (not become "vault-managed")."""
    monkeypatch.setenv("RAPR_TEST_TOKEN", "s3cret")
    scrubbed = []
    import importlib
    app_module = importlib.import_module("helm.web_routes.app")
    monkeypatch.setattr(app_module, "update_env", lambda k, v: scrubbed.append((k, v)))
    monkeypatch.setattr(token_vault, "_get_or_create_key", lambda: (_ for _ in ()).throw(OSError("no key")))
    assert token_vault.migrate_env_tokens(["RAPR_TEST_TOKEN"]) == 0
    assert scrubbed == []
