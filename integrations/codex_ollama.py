"""Codex running on a local Ollama model (free, offline): `codex exec --oss`.

Checked against Codex 0.162.1: --oss --local-provider ollama talks to Ollama
(CODEX_OSS_BASE_URL overrides the address), pulls the model if it's missing,
and reads the prompt from stdin. No OpenAI sign-in is needed or sent.
"""

import os
import shutil

KEY   = "codex_ollama"
NAME  = "Codex (Ollama)"
EMOJI = "🦙"
COLOR = "#10a37f"

_DEFAULT_MODEL = "gpt-oss:20b"   # Codex's own default for --oss


def _model(model: str | None) -> str:
    if model:
        return model
    try:
        import helm.state as _st
        return _st.default_models.get(KEY) or os.environ.get("CODEX_OLLAMA_MODEL") or _DEFAULT_MODEL
    except Exception:
        return os.environ.get("CODEX_OLLAMA_MODEL") or _DEFAULT_MODEL


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    return [shutil.which("codex") or "codex", "exec", "--oss", "--local-provider", "ollama",
            "--skip-git-repo-check", "--sandbox", "workspace-write", "-m", _model(model)]


def _process_env() -> dict:
    host = os.environ.get("OLLAMA_HOST", "").strip()
    if not host:
        return {}
    if not host.startswith("http"):
        host = "http://" + host
    return {"CODEX_OSS_BASE_URL": host.rstrip("/") + "/v1"}


STDIN_PROMPT = True
ENV_VARS: list[str] = []
PROCESS_ENV = _process_env()
SETUP_HINT = ("Needs Codex and Ollama running. Codex downloads the model on first use "
              "(default gpt-oss:20b, about 13 GB). Pick another with /model.")

# Catalog (Settings → AI Integrations)
ABOUT   = "Codex on a free local model through Ollama. Needs a strong computer."
INSTALL = "npm install -g @openai/codex"
DOCS    = "https://github.com/openai/codex"
