"""OpenRouter integration - many hosted models through one API key.

Setup is done from Settings > LLM Provider Setup; users should not edit .env
manually. In Agent Builder, select OpenRouter and optionally set a model such
as anthropic/claude-sonnet-4-6, openai/gpt-4o, or google/gemini-2.0-flash-001.
"""

import sys

KEY = "openrouter"
NAME = "OpenRouter"
EMOJI = "🌐"
COLOR = "#8b5cf6"

_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    return [
        sys.executable, "-m", "helm.ai_runner._openai_compat_cli",
        "--base-url", _BASE_URL,
        "--model", model or _DEFAULT_MODEL,
        "--api-key-env", "OPENROUTER_API_KEY",
    ]


STDIN_PROMPT = True
ENV_VARS = ["OPENROUTER_API_KEY"]
SETUP_HINT = (
    "Save your OpenRouter API key in Settings > LLM Provider Setup. "
    "Supports Claude, GPT, Gemini, Llama, Mistral, DeepSeek, and more."
)
