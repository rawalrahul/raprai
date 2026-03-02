"""OpenAI Codex CLI integration."""

import sys

KEY   = "codex"
NAME  = "Codex"
EMOJI = "💻"
COLOR = "#22c55e"   # green

def build_command(prompt: str) -> list[str]:
    _ext = ".cmd" if sys.platform == "win32" else ""
    return [f"codex{_ext}", "exec", "--skip-git-repo-check", "--full-auto", prompt]

ENV_VARS   = []   # API key is optional — Codex CLI handles auth internally
SETUP_HINT = "Install: npm install -g @openai/codex"
