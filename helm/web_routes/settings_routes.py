"""
helm/web_routes/settings_routes.py — Settings GET/POST, model discovery endpoints, webhook.
"""

import asyncio
import json
import os
import pathlib
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.session_mgr import make_session
from helm.ai_runner import process_message
from .app import update_env, _SETTINGS_KEYS
from .helpers import _fetch_claude_models, _fetch_ollama_models, _fetch_openai_models, _fetch_gemini_models


router = APIRouter()


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_settings():
    """Return the current value of each editable setting."""
    from dotenv import dotenv_values
    import helm.auth as _auth

    env_path = pathlib.Path(".env")
    saved = dotenv_values(env_path) if env_path.exists() else {}
    data = {}
    for key in _SETTINGS_KEYS:
        # Prefer the live os.environ value (reflects any in-process overrides),
        # falling back to the raw .env file value.
        data[key] = os.environ.get(key, saved.get(key, ""))
    # Also surface whether a PIN is currently set
    data["pin_is_set"] = _auth.pin_is_set()
    return JSONResponse(data)


@router.post("/settings")
async def save_settings(request: Request):
    """Persist one or more safe settings to .env and reload the environment."""
    body = await request.json()
    saved = []
    skipped = []
    for key, value in body.items():
        if key not in _SETTINGS_KEYS:
            skipped.append(key)
            continue
        update_env(key, str(value).strip())
        os.environ[key] = str(value).strip()
        saved.append(key)
    # Reload dotenv so any module that reads os.environ gets fresh values
    from dotenv import load_dotenv
    load_dotenv(override=True)
    return JSONResponse({"saved": saved, "skipped": skipped})


# ---------------------------------------------------------------------------
# Model Discovery API
# ---------------------------------------------------------------------------

@router.get("/integrations/models")
async def integration_models():
    """
    Discover available models from all configured AI integrations.
    Runs model fetchers in background threads to avoid blocking the event loop.
    Results are cached to avoid re-fetching on every request.
    """
    def _gather():
        info = {
            "updated_at": str(pathlib.Path.cwd()),
            "status": "partial",
            "models": {},
        }

        try:
            info["models"]["ollama"] = _fetch_ollama_models()
        except Exception as e:
            info["models"]["ollama"] = []
            info.setdefault("errors", {})["ollama"] = str(e)

        try:
            info["models"]["claude"] = _fetch_claude_models()
        except Exception as e:
            info["models"]["claude"] = []
            info.setdefault("errors", {})["claude"] = str(e)

        try:
            info["models"]["codex"] = _fetch_openai_models()
        except Exception as e:
            info["models"]["codex"] = []
            info.setdefault("errors", {})["codex"] = str(e)

        try:
            info["models"]["gemini"] = _fetch_gemini_models()
        except Exception as e:
            info["models"]["gemini"] = []
            info.setdefault("errors", {})["gemini"] = str(e)

        return info

    result = await asyncio.to_thread(_gather)
    return JSONResponse(result)


@router.get("/integrations/models/debug")
async def integration_models_debug():
    """
    Debug endpoint: run each model fetcher individually and return raw results
    (including errors) for each one.  Useful for diagnosing API failures.
    """

    def _gather_debug():
        info = {
            "ollama":  {"models": [], "error": None},
            "claude":  {"models": [], "error": None},
            "gemini":  {"models": [], "error": None},
            "codex":   {"models": [], "error": None},
        }

        try:
            info["ollama"]["models"] = _fetch_ollama_models()
        except Exception as e:
            info["ollama"]["error"] = str(e)

        try:
            info["claude"]["models"] = _fetch_claude_models()
        except Exception as e:
            info["claude"]["error"] = str(e)

        try:
            info["gemini"]["models"] = _fetch_gemini_models()
        except Exception as e:
            info["gemini"]["error"] = str(e)

        try:
            info["codex"]["models"] = _fetch_openai_models()
        except Exception as e:
            info["codex"]["error"] = str(e)

        return info

    result = await asyncio.to_thread(_gather_debug)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Webhook / Zapier Integration
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def webhook_endpoint(request: Request):
    """
    Accept webhook requests from external services (Zapier, IFTTT, etc).

    Request body:
    {
      "prompt": "...",
      "ai": "claude|gemini|shell",
      "cwd": "/optional/path",
      "token": "webhook_token"
    }
    """
    webhook_token = os.environ.get("WEBHOOK_TOKEN", "").strip()

    # If no token is set, reject all webhook requests
    if not webhook_token:
        return JSONResponse(
            {"error": "Webhook not configured. Set WEBHOOK_TOKEN in settings."},
            status_code=403
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Validate token
    provided_token = (body.get("token") or "").strip()
    if provided_token != webhook_token:
        return JSONResponse({"error": "Invalid token"}, status_code=403)

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    ai_key = (body.get("ai") or "").strip() or None
    cwd = (body.get("cwd") or "").strip() or None
    model = (body.get("model") or "").strip() or None

    try:
        # Create ephemeral session for the webhook request
        sess = make_session(ai_key, cwd=cwd, model=model)
        response = await process_message(prompt, source="webhook", session_id=sess["id"])

        return JSONResponse({
            "ok": True,
            "response": response,
            "session_id": sess["id"],
            "ai": sess.get("ai", "shell"),
        })
    except Exception as e:
        logger.error("Webhook processing error: %s", e)
        return JSONResponse(
            {"error": f"Processing failed: {str(e)}"},
            status_code=500
        )
