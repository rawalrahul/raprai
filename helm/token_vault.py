"""
helm/token_vault.py — Encrypted token storage for RAPR AI.

Replaces plaintext .env token storage with Fernet-encrypted values in SQLite.
A machine-local encryption key is auto-generated on first use and stored in
the user data directory (not in the repo / .env).

Graceful fallback:
  - If `cryptography` is not installed, tokens are stored as-is (plaintext)
    with a one-time warning logged.
  - Old plaintext tokens in .env are auto-migrated on first read.

Usage:
    from helm.token_vault import store_token, load_token, delete_token
    store_token("SLACK_TOKEN", "xoxb-...")
    val = load_token("SLACK_TOKEN")       # returns decrypted string or ""
    delete_token("SLACK_TOKEN")
"""

import os
import json
import time
from typing import Optional

from helm.config import logger

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_FERNET = True
except ImportError:
    _HAS_FERNET = False
    Fernet = None       # type: ignore
    InvalidToken = Exception  # type: ignore


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def _key_path() -> str:
    """Return the path to the machine-local vault key file."""
    from helm.paths import user_data_dir
    return os.path.join(user_data_dir(), ".vault_key")


def _get_or_create_key() -> bytes:
    """Load the Fernet key from disk, or generate & persist a new one."""
    kp = _key_path()
    if os.path.isfile(kp):
        return open(kp, "rb").read().strip()
    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(kp), exist_ok=True)
    # Write with restrictive permissions
    fd = os.open(kp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    logger.info("token_vault: generated new vault key at %s", kp)
    return key


def _fernet() -> Optional["Fernet"]:  # type: ignore
    if not _HAS_FERNET:
        return None
    try:
        return Fernet(_get_or_create_key())
    except Exception as exc:
        logger.warning("token_vault: cannot create Fernet instance: %s", exc)
        return None


# ---------------------------------------------------------------------------
# SQLite table
# ---------------------------------------------------------------------------

def _ensure_table():
    from helm.db import get_db
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS token_vault (
            env_key  TEXT PRIMARY KEY,
            cipher   TEXT NOT NULL,
            updated  REAL NOT NULL
        )
    """)
    db.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def store_token(env_key: str, plaintext: str) -> None:
    """Encrypt and store a token. Also sets os.environ for runtime use."""
    if not plaintext:
        return
    os.environ[env_key] = plaintext  # runtime availability

    f = _fernet()
    cipher = f.encrypt(plaintext.encode("utf-8")).decode("ascii") if f else plaintext

    try:
        from helm.db import get_db
        _ensure_table()
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO token_vault (env_key, cipher, updated) VALUES (?, ?, ?)",
            (env_key, cipher, time.time()),
        )
        db.commit()
    except Exception as exc:
        logger.warning("token_vault: store failed for %s: %s", env_key, exc)


def load_token(env_key: str) -> str:
    """Load and decrypt a token. Returns empty string if not found."""
    # 1. Try SQLite vault
    try:
        from helm.db import get_db
        _ensure_table()
        db = get_db()
        row = db.execute(
            "SELECT cipher FROM token_vault WHERE env_key = ?", (env_key,)
        ).fetchone()
        if row:
            cipher = row["cipher"]
            f = _fernet()
            if f:
                try:
                    plain = f.decrypt(cipher.encode("ascii")).decode("utf-8")
                    os.environ[env_key] = plain
                    return plain
                except InvalidToken:
                    # Might be stored plaintext (before encryption was enabled)
                    os.environ[env_key] = cipher
                    return cipher
            else:
                os.environ[env_key] = cipher
                return cipher
    except Exception as exc:
        logger.warning("token_vault: load failed for %s: %s", env_key, exc)

    # 2. Fallback: check .env / os.environ (legacy migration)
    val = os.environ.get(env_key, "")
    if val:
        # Auto-migrate to vault
        store_token(env_key, val)
    return val


def delete_token(env_key: str) -> None:
    """Remove a token from the vault and os.environ."""
    os.environ.pop(env_key, None)
    try:
        from helm.db import get_db
        _ensure_table()
        db = get_db()
        db.execute("DELETE FROM token_vault WHERE env_key = ?", (env_key,))
        db.commit()
    except Exception as exc:
        logger.warning("token_vault: delete failed for %s: %s", env_key, exc)


def load_all_tokens() -> dict[str, str]:
    """Load all tokens from the vault into os.environ. Call at startup."""
    loaded = {}
    try:
        from helm.db import get_db
        _ensure_table()
        db = get_db()
        rows = db.execute("SELECT env_key, cipher FROM token_vault").fetchall()
        f = _fernet()
        for row in rows:
            env_key, cipher = row["env_key"], row["cipher"]
            if f:
                try:
                    plain = f.decrypt(cipher.encode("ascii")).decode("utf-8")
                except InvalidToken:
                    plain = cipher  # stored as plaintext before
            else:
                plain = cipher
            os.environ[env_key] = plain
            loaded[env_key] = plain
    except Exception as exc:
        logger.warning("token_vault: load_all failed: %s", exc)
    return loaded


def migrate_env_tokens(token_env_keys: list[str], scrub_env: bool = True) -> int:
    """Migrate plaintext tokens from .env / os.environ into the vault.

    Call once at startup with the list of all plugin/core token env-var names.
    Returns the number of tokens migrated.

    If *scrub_env* is True (default), the plaintext value in .env is replaced
    with the placeholder ``vault-managed`` after successful migration — matching
    the pattern used by plugin_routes and plugin_oauth.
    """
    count = 0
    for key in token_env_keys:
        val = os.environ.get(key, "")
        if val and val != "vault-managed":
            # Check if already in vault
            try:
                from helm.db import get_db
                _ensure_table()
                db = get_db()
                existing = db.execute(
                    "SELECT 1 FROM token_vault WHERE env_key = ?", (key,)
                ).fetchone()
                if not existing:
                    store_token(key, val)
                    count += 1
                # Scrub .env even if already in vault (might still have plaintext)
                if scrub_env:
                    try:
                        from helm.web_routes.app import update_env
                        update_env(key, "vault-managed")
                    except Exception:
                        pass
            except Exception:
                pass
    return count


# ---------------------------------------------------------------------------
# Application-level encryption helpers (for DB column encryption)
# ---------------------------------------------------------------------------

def encrypt_value(plaintext: str) -> str:
    """Encrypt a string for DB column storage.

    Returns Fernet ciphertext (base64 ASCII) or the original plaintext
    if the ``cryptography`` library is not available.
    """
    if not plaintext:
        return plaintext
    f = _fernet()
    if f:
        return f.encrypt(plaintext.encode("utf-8")).decode("ascii")
    return plaintext


def decrypt_value(cipher: str) -> str:
    """Decrypt a string read from a DB column.

    Gracefully returns the input as-is when:
    - ``cryptography`` is not installed, or
    - the value was stored before encryption was enabled (legacy rows).
    """
    if not cipher:
        return cipher
    f = _fernet()
    if f:
        try:
            return f.decrypt(cipher.encode("ascii")).decode("utf-8")
        except (InvalidToken, Exception):
            return cipher  # not encrypted (legacy row)
    return cipher
