"""Local OpenAI-compatible server integration.

Works with local LLM servers that expose an OpenAI-compatible REST API,
including LM Studio, Jan.ai, llama.cpp server, Oobabooga, and Koboldcpp.
Configure the server URL and model from Settings > LLM Provider Setup; users
should not edit .env manually. No API key is required for typical local use.
"""

import os
import sys

KEY = "local_ai"
NAME = "Local AI"
EMOJI = "🏠"
COLOR = "#06b6d4"

_DEFAULT_URL = "http://localhost:1234"
_DEFAULT_MODEL = "local-model"


def _server_url() -> str:
    return os.environ.get("LOCAL_AI_URL", _DEFAULT_URL).rstrip("/")


def _model() -> str:
    try:
        import helm.state as _st
        dm = _st.default_models.get("local_ai", "")
        if dm:
            return dm
    except Exception:
        pass
    return os.environ.get("LOCAL_AI_MODEL", _DEFAULT_MODEL).strip()


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    cmd = [
        sys.executable, "-m", "helm.ai_runner._openai_compat_cli",
        "--base-url", _server_url() + "/v1",
        "--model", model or _model(),
        "--timeout", "180",
    ]
    if os.environ.get("LOCAL_AI_API_KEY", "").strip():
        cmd.extend(["--api-key-env", "LOCAL_AI_API_KEY"])
    return cmd


STDIN_PROMPT = True
ENV_VARS = []  # key is optional — most local servers need no auth
SETUP_HINT = (
    "Set the Local AI URL and model in Settings > LLM Provider Setup. "
    "LM Studio commonly uses http://localhost:1234; Jan.ai commonly uses "
    "http://localhost:1337; llama.cpp commonly uses http://localhost:8080. "
    "Set LOCAL_AI_API_KEY if your server requires authentication."
)
