"""
helm/web_routes/auth_routes.py — Login, logout, PIN setup, auth status endpoints.
"""

import os
import pathlib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

import helm.auth as _auth
from helm.config import logger
from helm.paths import user_data_dir
from helm.setup_wizard import _SETUP_HTML
from .app import update_env


router = APIRouter()


# ---------------------------------------------------------------------------
# Setup wizard
# ---------------------------------------------------------------------------

@router.get("/setup", response_class=HTMLResponse)
async def setup_page():
    from .app import _USE_SEPARATED_FRONTEND, _FRONTEND_DIR
    if _USE_SEPARATED_FRONTEND:
        setup_path = _FRONTEND_DIR / "setup.html"
        if setup_path.exists():
            return HTMLResponse(content=setup_path.read_text(encoding="utf-8"))
    return HTMLResponse(content=_SETUP_HTML)


@router.get("/setup/status")
async def setup_status():
    """Return what's already configured so the wizard can jump to the right step."""
    import asyncio
    from dotenv import dotenv_values
    from .app import _find_cli

    env_path = user_data_dir() / ".env"
    vals = dotenv_values(env_path) if env_path.exists() else {}

    def _check_clis():
        import subprocess
        codex_ok = _find_cli("codex")
        ollama_ok = False
        if _find_cli("ollama"):
            try:
                result = subprocess.run(
                    ["ollama", "list"], capture_output=True, text=True, timeout=5,
                )
                lines = [l for l in result.stdout.splitlines()[1:] if l.strip()]
                ollama_ok = len(lines) > 0
            except Exception:
                pass
        return {
            "gemini_ready":  _find_cli("gemini"),
            "claude_ready":  _find_cli("claude"),
            "codex_ready":   codex_ok,
            "ollama_ready":  ollama_ok,
        }

    cli_status = await asyncio.to_thread(_check_clis)

    # Check for bot token: prefer os.environ (vault-decrypted) over .env
    # (after vault migration .env contains "vault-managed" placeholder)
    bot_token_raw = vals.get("TELEGRAM_BOT_TOKEN", "").strip()
    bot_token_env = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    has_bot_token = bool(bot_token_env and bot_token_env != "vault-managed") or bool(
        bot_token_raw and bot_token_raw != "vault-managed"
    )
    # Fallback: if .env says vault-managed, the vault has it → configured
    if not has_bot_token and bot_token_raw == "vault-managed":
        has_bot_token = True

    return JSONResponse({
        "env_exists":    env_path.exists(),
        "has_bot_token": has_bot_token,
        "has_user_ids":  bool(vals.get("ALLOWED_USER_IDS", "").strip()),
        **cli_status,
    })


@router.post("/setup/save")
async def setup_save(request: Request):
    """Write one or more key=value pairs to the .env file and reload env.

    Secret keys (API tokens, credentials) are stored in the encrypted vault
    and their .env entry is replaced with a ``vault-managed`` placeholder.
    Non-secret keys (ALLOWED_USER_IDS, etc.) are written to .env as before.
    """
    try:
        from helm.security import VAULT_ELIGIBLE_KEYS
        from helm.token_vault import store_token

        body = await request.json()
        for key, value in body.items():
            if not (isinstance(key, str) and isinstance(value, str) and value.strip()):
                continue
            value = value.strip()

            if key in VAULT_ELIGIBLE_KEYS:
                # Store secret in encrypted vault; .env gets a placeholder
                store_token(key, value)
                update_env(key, "vault-managed")
            else:
                # Non-secret (e.g. ALLOWED_USER_IDS) → plaintext .env
                update_env(key, value)

        # Persist the MCP bearer token now that .env exists
        from helm.web_routes.app import MCP_BEARER_TOKEN
        update_env("MCP_BEARER_TOKEN", MCP_BEARER_TOKEN)

        # Reload so the running process picks up new values immediately
        from helm.web_routes.app import reload_env
        reload_env()

        # Hot-start Telegram bot if token was just saved and bot isn't running yet
        if "TELEGRAM_BOT_TOKEN" in body and body["TELEGRAM_BOT_TOKEN"].strip():
            import asyncio
            import helm.state as _st
            hot_start = getattr(_st, "_hot_start_telegram", None)
            if hot_start and not _st.telegram_app:
                asyncio.create_task(hot_start())

        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error("setup/save error: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Login / logout / PIN management
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    """Render the PIN entry page."""
    # If already authenticated, go straight to the UI
    if _auth.check_auth(request):
        return RedirectResponse(url="/", status_code=303)

    ip   = request.client.host if request.client else "unknown"
    wait = _auth.seconds_until_unlock(ip)

    disabled = "disabled" if wait > 0 else ""

    # Use separated frontend login.html if available
    from .app import _USE_SEPARATED_FRONTEND, _FRONTEND_DIR
    if _USE_SEPARATED_FRONTEND:
        login_path = _FRONTEND_DIR / "login.html"
        if login_path.exists():
            html = login_path.read_text(encoding="utf-8")
        else:
            html = _auth.LOGIN_HTML
    else:
        html = _auth.LOGIN_HTML

    html = html.replace("__WAIT__",     str(wait))
    html = html.replace("__DISABLED__", disabled)
    html = html.replace("__ERROR__",    error.replace('"', "&quot;"))
    return HTMLResponse(content=html)


@router.post("/login")
async def login_post(request: Request):
    """Verify PIN, issue session cookie, redirect home (or back to login on failure)."""
    ip = request.client.host if request.client else "unknown"

    # Locked out?
    if _auth.is_locked_out(ip):
        wait = _auth.seconds_until_unlock(ip)
        return RedirectResponse(
            url=f"/login?error=Too+many+attempts.+Try+again+in+{wait}s.",
            status_code=303,
        )

    form = await request.form()
    pin  = str(form.get("pin", "")).strip()

    if not _auth.verify_pin(pin):
        _auth.record_failure(ip)
        remaining = _auth.MAX_ATTEMPTS - len(_auth._failed.get(ip, []))
        if remaining <= 0:
            wait = _auth.seconds_until_unlock(ip)
            return RedirectResponse(
                url=f"/login?error=Too+many+failed+attempts.+Locked+for+{wait}s.",
                status_code=303,
            )
        return RedirectResponse(
            url=f"/login?error=Incorrect+PIN.+{remaining}+attempt(s)+remaining.",
            status_code=303,
        )

    # Correct PIN — issue token and set cookie
    _auth.clear_failures(ip)
    token    = _auth.issue_token()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key      = _auth.COOKIE_NAME,
        value    = token,
        httponly = True,
        samesite = "lax",
        max_age  = _auth.SESSION_DAYS * 86_400,
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    """Revoke the current session and redirect to login."""
    token = _auth.get_token(request)
    if token:
        _auth.revoke_token(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(_auth.COOKIE_NAME)
    return response


@router.post("/auth/set-pin")
async def set_pin_endpoint(request: Request):
    """
    Set or change the PIN.

    Body: { "pin": "...", "old_pin": "..." }
    If a PIN is already set, old_pin must be provided and correct.
    """
    try:
        body    = await request.json()
        new_pin = str(body.get("pin", "")).strip()
        old_pin = str(body.get("old_pin", "")).strip()

        if len(new_pin) < 4:
            return JSONResponse({"error": "PIN must be at least 4 characters."}, status_code=400)

        if _auth.pin_is_set():
            if not old_pin:
                return JSONResponse({"error": "Current PIN required to change PIN."}, status_code=400)
            if not _auth.verify_pin(old_pin):
                return JSONResponse({"error": "Current PIN is incorrect."}, status_code=403)

        salt, hashed = _auth.set_pin(new_pin)
        update_env("PIN_SALT", salt)
        update_env("PIN_HASH", hashed)

        # Reload env so the in-process check picks up the new values immediately
        from helm.web_routes.app import reload_env
        reload_env()

        return JSONResponse({"ok": True})
    except Exception as exc:
        logger.error("set-pin error: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/auth/status")
async def auth_status():
    """Return whether a PIN is configured (used by the setup wizard)."""
    return JSONResponse({"pin_set": _auth.pin_is_set()})
