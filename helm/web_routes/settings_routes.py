"""
helm/web_routes/settings_routes.py — Settings GET/POST, model discovery endpoints.
"""

import asyncio
import json
import os
import pathlib
import shlex
import urllib.error
import urllib.request
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import helm.state as _st
from helm.config import logger
from helm.paths import user_data_dir
from .app import update_env, _SETTINGS_KEYS
from .helpers import _fetch_claude_models, _fetch_ollama_models, _fetch_openai_models, _fetch_gemini_models


router = APIRouter()


_KNOWN_OPENROUTER_MODELS = [
    "anthropic/claude-sonnet-4-5",
    "openai/gpt-4o",
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-large-2411",
    "deepseek/deepseek-chat-v3-0324",
]

_KNOWN_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "deepseek-r1-distill-llama-70b",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


def _clear_backend_availability_cache(*keys: str) -> None:
    """Clear cached provider availability after settings/API keys change."""
    try:
        from helm.ai_runner.core import _availability_cache
        for key in keys:
            _availability_cache.pop(key, None)
    except Exception:
        pass


def _split_integration_command(command: str) -> list[str]:
    return [p.strip('"') for p in shlex.split(command or "", posix=False) if p.strip()]


def _command_arg(parts: list[str], flag: str) -> str:
    try:
        idx = parts.index(flag)
    except ValueError:
        return ""
    return parts[idx + 1] if idx + 1 < len(parts) else ""


def _fetch_openai_compat_models(base_url: str, api_key: str = "", timeout: int = 5) -> list[str]:
    """Fetch model ids from an OpenAI-compatible /models endpoint."""
    if not base_url:
        return []
    url = base_url.rstrip("/") + "/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    data = body.get("data", body if isinstance(body, list) else [])
    models = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            models.append(str(item["id"]))
        elif isinstance(item, str):
            models.append(item)
    return sorted(set(models))


def _custom_openai_models(entry: dict) -> list[str]:
    command = entry.get("command", "")
    if "_openai_compat_cli" not in command:
        return []
    parts = _split_integration_command(command)
    base_url = _command_arg(parts, "--base-url")
    api_key = _command_arg(parts, "--api-key")
    api_key_env = _command_arg(parts, "--api-key-env")
    if not api_key and api_key_env:
        api_key = os.environ.get(api_key_env, "")
    return _fetch_openai_compat_models(base_url, api_key=api_key)


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_settings():
    """Return the current value of each editable setting."""
    from dotenv import dotenv_values
    import helm.auth as _auth

    env_path = user_data_dir() / ".env"
    saved = dotenv_values(env_path) if env_path.exists() else {}
    data = {}
    for key in _SETTINGS_KEYS:
        # Prefer the live os.environ value (reflects any in-process overrides),
        # falling back to the raw .env file value.
        data[key] = os.environ.get(key, saved.get(key, ""))
    # Return all CONTEXT_WINDOW_* overrides (dynamic — any AI key)
    for k, v in {**saved, **os.environ}.items():
        if k.startswith("CONTEXT_WINDOW_") and v:
            data[k] = v
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
        if key not in _SETTINGS_KEYS and not key.startswith("CONTEXT_WINDOW_"):
            skipped.append(key)
            continue
        update_env(key, str(value).strip())
        os.environ[key] = str(value).strip()
        saved.append(key)
    # Reload dotenv so any module that reads os.environ gets fresh values
    from helm.web_routes.app import reload_env
    reload_env()
    _clear_backend_availability_cache("local_ai")
    return JSONResponse({"saved": saved, "skipped": skipped})


# ---------------------------------------------------------------------------
# Default Models per AI
# ---------------------------------------------------------------------------

@router.get("/settings/default-models")
async def get_default_models():
    """Return configured default models for each AI."""
    return JSONResponse({"default_models": dict(_st.default_models)})


@router.post("/settings/default-models")
async def save_default_models(request: Request):
    """Save default models per AI. Body: {ai_key: model_name, ...}
    Empty string or null removes the default for that AI.
    """
    body = await request.json()
    updated = []

    # Only allow setting defaults for REST-API AIs (ollama + integrations)
    # CLI/OAuth AIs (claude, gemini, codex) don't expose reliable model lists.
    _cli_ais = {"claude", "gemini", "codex"}

    for ai_key, model_name in body.items():
        if ai_key in _cli_ais:
            continue  # skip CLI-based OAuth AIs
        model_name = (model_name or "").strip()
        if model_name:
            _st.default_models[ai_key] = model_name
            # Also persist to .env as DEFAULT_MODEL_{AI}
            env_key = f"DEFAULT_MODEL_{ai_key.upper()}"
            update_env(env_key, model_name)
            os.environ[env_key] = model_name
        else:
            _st.default_models.pop(ai_key, None)
            # Clear from .env
            env_key = f"DEFAULT_MODEL_{ai_key.upper()}"
            update_env(env_key, "")
            os.environ.pop(env_key, None)
        updated.append(ai_key)

    return JSONResponse({"ok": True, "updated": updated})


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
            info["models"]["claude"] = []
        except Exception as e:
            info["models"]["claude"] = []
            info.setdefault("errors", {})["claude"] = str(e)

        try:
            info["models"]["codex"] = []
        except Exception as e:
            info["models"]["codex"] = []
            info.setdefault("errors", {})["codex"] = str(e)

        try:
            info["models"]["gemini"] = []
        except Exception as e:
            info["models"]["gemini"] = []
            info.setdefault("errors", {})["gemini"] = str(e)

        try:
            fetched = _fetch_openai_compat_models(
                "https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            )
            info["models"]["openrouter"] = fetched or _KNOWN_OPENROUTER_MODELS
        except Exception as e:
            info["models"]["openrouter"] = _KNOWN_OPENROUTER_MODELS
            info.setdefault("errors", {})["openrouter"] = str(e)

        try:
            fetched = _fetch_openai_compat_models(
                "https://api.groq.com/openai/v1",
                api_key=os.environ.get("GROQ_API_KEY", ""),
            )
            info["models"]["groq"] = fetched or _KNOWN_GROQ_MODELS
        except Exception as e:
            info["models"]["groq"] = _KNOWN_GROQ_MODELS
            info.setdefault("errors", {})["groq"] = str(e)

        try:
            local_url = os.environ.get("LOCAL_AI_URL", "http://localhost:1234").rstrip("/") + "/v1"
            info["models"]["local_ai"] = _fetch_openai_compat_models(local_url)
        except Exception as e:
            info["models"]["local_ai"] = []
            info.setdefault("errors", {})["local_ai"] = str(e)

        try:
            from helm.integrations import list_custom
            for entry in list_custom():
                key = entry.get("key")
                if key and key not in info["models"]:
                    info["models"][key] = _custom_openai_models(entry)
        except Exception as e:
            info.setdefault("errors", {})["custom"] = str(e)

        info["status"] = "ok"

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
            info["claude"]["error"] = "Model discovery disabled for OAuth CLI"
        except Exception as e:
            info["claude"]["error"] = str(e)

        try:
            info["gemini"]["error"] = "Model discovery disabled for OAuth CLI"
        except Exception as e:
            info["gemini"]["error"] = str(e)

        try:
            info["codex"]["error"] = "Model discovery disabled for OAuth CLI"
        except Exception as e:
            info["codex"]["error"] = str(e)

        return info

    result = await asyncio.to_thread(_gather_debug)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# API Key Management (vault-secured)
# ---------------------------------------------------------------------------

@router.post("/settings/api-keys")
async def save_api_key(request: Request):
    """Save a core API key through the encrypted vault.

    Body: ``{"env_key": "GROQ_API_KEY", "value": "gsk_..."}``

    The key is encrypted via Fernet and stored in the SQLite token_vault.
    The ``.env`` file receives a ``vault-managed`` placeholder so the
    actual secret is never stored in plaintext on disk.
    """
    from helm.security import VAULT_ELIGIBLE_KEYS
    from helm.token_vault import store_token

    body = await request.json()
    env_key = body.get("env_key", "").strip()
    value = body.get("value", "").strip()

    if not env_key or not value:
        return JSONResponse({"ok": False, "error": "env_key and value are required"}, status_code=400)

    if env_key not in VAULT_ELIGIBLE_KEYS:
        return JSONResponse(
            {"ok": False, "error": f"Unknown or non-secret key: {env_key}"},
            status_code=400,
        )

    # Store encrypted in vault + set in os.environ for runtime
    store_token(env_key, value)
    # Replace .env entry with placeholder
    update_env(env_key, "vault-managed")
    os.environ[env_key] = value
    if env_key == "GROQ_API_KEY":
        _clear_backend_availability_cache("groq")
    elif env_key == "OPENROUTER_API_KEY":
        _clear_backend_availability_cache("openrouter")
    elif env_key == "GITHUB_TOKEN":
        _clear_backend_availability_cache("github_models")

    logger.info("API key saved via vault: %s", env_key)
    return JSONResponse({"ok": True, "env_key": env_key})


@router.delete("/settings/api-keys/{env_key}")
async def delete_api_key(env_key: str):
    """Remove a stored API key from the vault."""
    from helm.security import VAULT_ELIGIBLE_KEYS
    from helm.token_vault import delete_token

    if env_key not in VAULT_ELIGIBLE_KEYS:
        return JSONResponse(
            {"ok": False, "error": f"Unknown or non-secret key: {env_key}"},
            status_code=400,
        )

    delete_token(env_key)
    update_env(env_key, "")
    os.environ.pop(env_key, None)
    if env_key == "GROQ_API_KEY":
        _clear_backend_availability_cache("groq")
    elif env_key == "OPENROUTER_API_KEY":
        _clear_backend_availability_cache("openrouter")
    elif env_key == "GITHUB_TOKEN":
        _clear_backend_availability_cache("github_models")
    logger.info("API key removed from vault: %s", env_key)
    return JSONResponse({"ok": True, "env_key": env_key})


@router.get("/settings/api-keys")
async def list_api_keys():
    """List which API keys are configured (names only, not values).

    Returns a dict mapping env_key → bool (True if a value exists in the
    vault or os.environ, False if unconfigured).
    """
    from helm.security import VAULT_ELIGIBLE_KEYS, redact_env_value

    status = {}
    for key in sorted(VAULT_ELIGIBLE_KEYS):
        val = os.environ.get(key, "")
        if val and val != "vault-managed":
            status[key] = {"configured": True, "preview": redact_env_value(key, val)}
        elif val == "vault-managed":
            status[key] = {"configured": True, "preview": "vault-managed"}
        else:
            status[key] = {"configured": False, "preview": ""}

    return JSONResponse(status)


# ---------------------------------------------------------------------------
# User prefs — lightweight server-side key/value store for UI state that
# must survive localStorage resets (e.g. Electron profile wipes, port changes)
# ---------------------------------------------------------------------------

def _prefs_file() -> pathlib.Path:
    return user_data_dir() / "user_prefs.json"

def _load_prefs() -> dict:
    try:
        return json.loads(_prefs_file().read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_prefs(prefs: dict) -> None:
    _prefs_file().write_text(json.dumps(prefs, indent=2), encoding="utf-8")


@router.get("/prefs")
async def get_prefs():
    """Return persisted user preferences."""
    return JSONResponse(await asyncio.to_thread(_load_prefs))


@router.post("/prefs")
async def set_prefs(request: Request):
    """Merge supplied key/value pairs into persisted user preferences."""
    updates = await request.json()
    if not isinstance(updates, dict):
        return JSONResponse({"error": "expected object"}, status_code=400)
    def _merge():
        prefs = _load_prefs()
        prefs.update(updates)
        _save_prefs(prefs)
        return prefs
    result = await asyncio.to_thread(_merge)
    return JSONResponse(result)
