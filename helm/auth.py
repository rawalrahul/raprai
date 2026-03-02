"""
helm/auth.py — PIN-based authentication for Helm HQ.

Provides:
  - PIN hashing (SHA-256 + random salt, stored in .env)
  - Session token issuance and validation (in-memory + HttpOnly cookie)
  - Brute-force lockout (in-memory counter, configurable threshold)
  - check_auth() helper used by route guards
"""

import hashlib
import os
import secrets
import time
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

# ---------------------------------------------------------------------------
# Constants (can be overridden via .env)
# ---------------------------------------------------------------------------

SESSION_DAYS    = int(os.environ.get("SESSION_DAYS",      "7"))
MAX_ATTEMPTS    = int(os.environ.get("PIN_MAX_ATTEMPTS",  "5"))
LOCKOUT_SECONDS = int(os.environ.get("PIN_LOCKOUT_SECS",  "300"))   # 5 minutes
COOKIE_NAME     = "hq_session"

# ---------------------------------------------------------------------------
# In-memory stores (survive for the lifetime of the server process)
# ---------------------------------------------------------------------------

_sessions: dict[str, float] = {}       # token -> expiry Unix timestamp
_failed:   dict[str, list]  = {}       # client_ip -> [attempt_timestamps]

# ---------------------------------------------------------------------------
# PIN hashing
# ---------------------------------------------------------------------------

def _hash_pin(pin: str, salt: str) -> str:
    """Return a deterministic SHA-256 hex digest for (salt, pin)."""
    return hashlib.sha256(f"{salt}{pin}".encode("utf-8")).hexdigest()


def _get_stored() -> tuple[str, str]:
    """Return (salt, hashed_pin) from live environment, or ('', '') if not set."""
    return (
        os.environ.get("PIN_SALT", ""),
        os.environ.get("PIN_HASH", ""),
    )


def pin_is_set() -> bool:
    """True if a PIN has already been configured."""
    salt, hashed = _get_stored()
    return bool(salt and hashed)


def set_pin(new_pin: str) -> tuple[str, str]:
    """
    Hash *new_pin* with a fresh random salt.

    Returns (salt, hashed_pin) — the caller is responsible for persisting
    both values to .env and reloading os.environ.
    """
    salt   = secrets.token_hex(16)
    hashed = _hash_pin(new_pin, salt)
    return salt, hashed


def verify_pin(pin: str) -> bool:
    """Return True if *pin* matches the stored hash."""
    salt, stored_hash = _get_stored()
    if not salt or not stored_hash:
        return False
    return _hash_pin(pin, salt) == stored_hash

# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

def _prune(ip: str) -> list:
    """Return only the recent failure timestamps for *ip* (within lockout window)."""
    now = time.time()
    recent = [t for t in _failed.get(ip, []) if now - t < LOCKOUT_SECONDS]
    _failed[ip] = recent
    return recent


def is_locked_out(ip: str) -> bool:
    return len(_prune(ip)) >= MAX_ATTEMPTS


def record_failure(ip: str) -> None:
    _failed.setdefault(ip, []).append(time.time())


def clear_failures(ip: str) -> None:
    _failed.pop(ip, None)


def seconds_until_unlock(ip: str) -> int:
    """How many seconds remain before the lockout expires for *ip*."""
    attempts = _prune(ip)
    if not attempts:
        return 0
    oldest    = min(attempts)
    remaining = LOCKOUT_SECONDS - (time.time() - oldest)
    return max(0, int(remaining))

# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------

def issue_token() -> str:
    """Generate a new session token and store its expiry."""
    token  = secrets.token_urlsafe(32)
    expiry = time.time() + SESSION_DAYS * 86_400
    _sessions[token] = expiry
    return token


def is_valid_token(token: Optional[str]) -> bool:
    """Return True if *token* exists and has not expired."""
    if not token:
        return False
    expiry = _sessions.get(token)
    if expiry is None:
        return False
    if time.time() > expiry:
        _sessions.pop(token, None)
        return False
    return True


def revoke_token(token: str) -> None:
    _sessions.pop(token, None)

# ---------------------------------------------------------------------------
# FastAPI helpers
# ---------------------------------------------------------------------------

def get_token(request: Request) -> Optional[str]:
    """Extract the session cookie value from the request."""
    return request.cookies.get(COOKIE_NAME)


def check_auth(request: Request) -> bool:
    """
    Return True if the request is authenticated.

    When no PIN is configured we allow everything through so the setup
    wizard remains accessible without a login step.
    """
    if not pin_is_set():
        return True
    return is_valid_token(get_token(request))


# ---------------------------------------------------------------------------
# Embedded login-page HTML
# ---------------------------------------------------------------------------

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Helm HQ — Login</title>
<link rel="icon" href="/static/logo.png" type="image/png">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0d0d0d;--surface:#141414;--surface2:#1c1c1c;--border:#242424;
  --text:#e2e2e2;--muted:#555;--dim:#888;
  --accent:#3b82f6;--ok:#22c55e;--err:#ef4444;
}
html,body{height:100%;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.5}
.wrap{display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  width:100%;max-width:380px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,.5)}
.card-head{padding:24px 28px 20px;border-bottom:1px solid var(--border)}
.logo-row{display:flex;align-items:center;gap:10px;margin-bottom:4px}
.logo-row img{width:28px;height:28px;border-radius:6px;object-fit:contain}
.logo-row .app{font-size:16px;font-weight:700}
.subtitle{font-size:12px;color:var(--dim)}
.card-body{padding:28px}
.field{margin-bottom:18px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--dim);
  text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
.field input{
  width:100%;background:var(--surface2);border:1px solid var(--border);
  border-radius:6px;padding:10px 12px;font-size:14px;color:var(--text);
  outline:none;font-family:inherit;transition:border-color .15s;letter-spacing:.15em}
.field input:focus{border-color:#3a3a3a}
.field input::placeholder{letter-spacing:normal;font-size:13px;color:var(--muted)}
.btn{
  width:100%;padding:10px;border-radius:6px;font-size:14px;font-weight:600;
  cursor:pointer;border:none;background:var(--accent);color:#fff;
  font-family:inherit;transition:opacity .15s}
.btn:hover:not(:disabled){opacity:.85}
.btn:disabled{opacity:.4;cursor:not-allowed}
.alert{
  padding:10px 14px;border-radius:7px;font-size:12px;margin-bottom:18px;
  line-height:1.65;display:none}
.alert-err{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.2);color:#fca5a5}
.alert-lock{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.2);color:#fcd34d}
#countdown{font-weight:700}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <div class="card-head">
      <div class="logo-row">
        <img src="/static/logo.png" alt="Helm HQ">
        <span class="app">Helm HQ</span>
      </div>
      <div class="subtitle">Enter your PIN to continue</div>
    </div>
    <div class="card-body">
      <div id="alert-err"  class="alert alert-err"></div>
      <div id="alert-lock" class="alert alert-lock">
        Too many failed attempts. Try again in <span id="countdown">__WAIT__</span>s.
      </div>
      <form id="loginForm" method="post" action="/login">
        <div class="field">
          <label for="pin">PIN</label>
          <input id="pin" name="pin" type="password"
                 inputmode="numeric" autocomplete="current-password"
                 placeholder="Enter PIN" autofocus __DISABLED__>
        </div>
        <button class="btn" type="submit" __DISABLED__>Unlock</button>
      </form>
    </div>
  </div>
</div>
<script>
(function(){
  var wait = __WAIT__;
  if(wait <= 0) return;
  var cd   = document.getElementById('countdown');
  var lock = document.getElementById('alert-lock');
  var pin  = document.getElementById('pin');
  var btn  = document.querySelector('.btn');
  lock.style.display='block';
  pin.disabled = true; btn.disabled = true;
  function tick(){
    cd.textContent = wait;
    if(--wait < 0){
      lock.style.display='none';
      pin.disabled=false; btn.disabled=false;
      pin.focus();
    } else {
      setTimeout(tick, 1000);
    }
  }
  setTimeout(tick, 1000);
})();
var msg = "__ERROR__";
if(msg){ var el=document.getElementById('alert-err'); el.textContent=msg; el.style.display='block'; }
</script>
</body>
</html>
"""
