"""GitHub Models integration — OpenAI-compatible inference via GitHub token.

Uses the GitHub Models API (Azure-backed) with your GitHub Personal Access Token.
Supports gpt-4o, gpt-4o-mini, Meta-Llama-3.1-70B-Instruct, Phi-4, Mistral, etc.

Setup: Settings > LLM Provider Setup → enter a GitHub PAT with no special scopes
(a free account gives generous rate limits).
"""

import sys

KEY = "github_models"
NAME = "GitHub Models"
EMOJI = "🐙"
COLOR = "#238636"

_BASE_URL = "https://models.inference.ai.azure.com"
_DEFAULT_MODEL = "gpt-4o-mini"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    return [
        sys.executable, "-m", "helm.ai_runner._openai_compat_cli",
        "--base-url", _BASE_URL,
        "--model", model or _DEFAULT_MODEL,
        "--api-key-env", "GITHUB_TOKEN",
    ]


STDIN_PROMPT = True
ENV_VARS = ["GITHUB_TOKEN"]
SETUP_HINT = (
    "Create a GitHub Personal Access Token at github.com/settings/tokens (no scopes needed). "
    "Save it as GITHUB_TOKEN in Settings > LLM Provider Setup. "
    "Available models: gpt-4o, gpt-4o-mini, Meta-Llama-3.1-70B-Instruct, Phi-4, Mistral-large."
)
