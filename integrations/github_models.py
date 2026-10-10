"""GitHub Models integration — OpenAI-compatible inference via GitHub token.

Uses the GitHub Models API (models.github.ai) with your GitHub Personal Access
Token. Model IDs are "publisher/name": openai/gpt-4o-mini, openai/gpt-4.1,
meta/Llama-3.3-70B-Instruct, microsoft/Phi-4, mistral-ai/Mistral-Large-2411, etc.

Setup: Settings > LLM Provider Setup → enter a fine-grained GitHub PAT with the
"Models: read" permission (a free account gives generous rate limits).
"""

import sys

KEY = "github_models"
NAME = "GitHub Models"
EMOJI = "🐙"
COLOR = "#238636"

# The old endpoint, models.inference.ai.azure.com, was retired and no longer resolves.
_BASE_URL = "https://models.github.ai/inference"
_DEFAULT_MODEL = "openai/gpt-4o-mini"

# Short names used before 2.0.1 → current catalog IDs.
_LEGACY_MODELS = {
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "Meta-Llama-3.1-70B-Instruct": "meta/Meta-Llama-3.1-70B-Instruct",
    "Phi-4": "microsoft/Phi-4",
    "Mistral-large": "mistral-ai/Mistral-Large-2411",
}


def _model_id(model: str | None) -> str:
    if not model:
        return _DEFAULT_MODEL
    return _LEGACY_MODELS.get(model, model)


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    return [
        sys.executable, "-m", "helm.ai_runner._openai_compat_cli",
        "--base-url", _BASE_URL,
        "--model", _model_id(model),
        "--api-key-env", "GITHUB_TOKEN",
    ]


STDIN_PROMPT = True
ENV_VARS = ["GITHUB_TOKEN"]
SETUP_HINT = (
    "Create a fine-grained GitHub token at github.com/settings/personal-access-tokens "
    "with the \"Models: read\" permission. "
    "Save it as GITHUB_TOKEN in Settings > LLM Provider Setup. "
    "Models: openai/gpt-4o-mini, openai/gpt-4.1, meta/Llama-3.3-70B-Instruct, microsoft/Phi-4."
)
