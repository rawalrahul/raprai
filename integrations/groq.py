"""Groq API integration - ultra-fast inference.

Groq runs open-source models (Llama, Gemma, Mixtral, DeepSeek) on custom LPU
hardware. Setup is done from Settings > LLM Provider Setup; users should not
edit .env manually.
"""

import sys

KEY = "groq"
NAME = "Groq"
EMOJI = "⚡"
COLOR = "#f97316"

_BASE_URL = "https://api.groq.com/openai/v1"
_DEFAULT_MODEL = "openai/gpt-oss-120b"   # Llama 3.x models were retired in Aug 2026


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    return [
        sys.executable, "-m", "helm.ai_runner._openai_compat_cli",
        "--base-url", _BASE_URL,
        "--model", model or _DEFAULT_MODEL,
        "--api-key-env", "GROQ_API_KEY",
    ]


STDIN_PROMPT = True
ENV_VARS = ["GROQ_API_KEY"]
SETUP_HINT = (
    "Save your Groq API key in Settings > LLM Provider Setup. "
    "Popular models: openai/gpt-oss-120b, openai/gpt-oss-20b (faster). "
    "Current list: console.groq.com/docs/models"
)
