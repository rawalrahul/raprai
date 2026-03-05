"""
helm/web_routes/ — FastAPI app and route handlers (modularized).

This package replaces the monolithic web_routes.py file with organized sub-modules:
- app.py — FastAPI app creation, CORS, middleware, health endpoint
- auth_routes.py — Login, logout, PIN setup, setup wizard routes
- session_routes.py — Session browser, integration status, model discovery
- chat_ws.py — WebSocket endpoint, web command dispatcher
- history_routes.py — History list, search, export, rename endpoints
- settings_routes.py — Settings CRUD, model endpoints, webhook
- file_routes.py — Generated files, diagnostics export
- helpers.py — Model fetching utilities

The `app` object is importable as: `from helm.web_routes import app`
"""

from .app import app
from .auth_routes import router as auth_router
from .session_routes import router as session_router
from .chat_ws import router as chat_ws_router
from .history_routes import router as history_router
from .settings_routes import router as settings_router
from .file_routes import router as file_router
from .voice_routes import router as voice_router
from .usage_routes import router as usage_router
from .pipeline_routes import router as pipeline_router
from .approval_routes import router as approval_router
from .plugins_routes import router as plugins_router
from .context_routes import router as context_router

# Include all routers in the app
app.include_router(auth_router)
app.include_router(session_router)
app.include_router(chat_ws_router)
app.include_router(history_router)
app.include_router(settings_router)
app.include_router(file_router)
app.include_router(voice_router)
app.include_router(usage_router)
app.include_router(pipeline_router)
app.include_router(approval_router)
app.include_router(plugins_router)
app.include_router(context_router)

# Re-export model fetchers so they can be imported as: from helm.web_routes import _fetch_claude_models
from .helpers import (
    _fetch_claude_models, _fetch_ollama_models,
    _fetch_gemini_models, _fetch_openai_models,
)

# Re-export app so it can be imported as: from helm.web_routes import app
__all__ = [
    "app",
    "_fetch_claude_models", "_fetch_ollama_models",
    "_fetch_gemini_models", "_fetch_openai_models",
]
