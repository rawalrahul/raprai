"""
Ollama local AI integration — runs any model installed via `ollama pull`.

Setup:
  1. Install Ollama: https://ollama.com/download
  2. Pull a model:  ollama pull qwen3:4b
  3. Set OLLAMA_MODEL=qwen3:4b in .env  (optional — defaults to qwen3:4b)
  4. Restart Helm HQ — Ollama appears in the AI selector automatically.

No API key required. Works fully offline.

Installed models on this machine (from `ollama list`):
  deepseek-r1:8b     — reasoning / long-form analysis
  qwen3:4b           — fast general-purpose chat (default)
  qwen2.5-coder:7b   — code generation and review
"""

import os
import sys

# ── Identity ─────────────────────────────────────────────────────────────────

KEY   = "ollama"
NAME  = "Ollama"
EMOJI = "🦙"
COLOR = "#10b981"   # emerald green — matches Ollama brand

# ── Model selection ───────────────────────────────────────────────────────────

def _model() -> str:
    """Return the model name from .env, or fall back to the sensible default."""
    return os.environ.get("OLLAMA_MODEL", "qwen3:4b").strip()

# ── Command builder ───────────────────────────────────────────────────────────

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """
    Run a single non-interactive Ollama query and return the output.

    `ollama run MODEL "prompt"` exits automatically after generating the response,
    which matches Helm HQ's one-shot subprocess model.

    Args:
        prompt: The user prompt to send to the model.
        model:  Override the model for this call (e.g. "deepseek-r1:8b").
                Falls back to OLLAMA_MODEL env var or the built-in default.
    """
    chosen = (model or _model()).strip()
    return ["ollama", "run", chosen, "--nowordwrap", prompt]

# ── Metadata ──────────────────────────────────────────────────────────────────

# No API key needed — Ollama is fully local.
ENV_VARS: list[str] = []

SETUP_HINT: str = (
    "Install Ollama from https://ollama.com/download  |  "
    "Pull a model: ollama pull qwen3:4b  |  "
    "Set OLLAMA_MODEL=model-name in .env to switch models  |  "
    "Available models: deepseek-r1:8b  qwen3:4b  qwen2.5-coder:7b"
)
