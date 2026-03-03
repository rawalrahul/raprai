"""OpenAI Codex CLI integration."""

import sys

KEY   = "codex"
NAME  = "Codex"
EMOJI = "💻"
COLOR = "#22c55e"   # green

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build command args WITHOUT the prompt — prompt is piped via stdin
    to avoid Windows cmd.exe 8 KB command-line length limits."""
    _ext = ".cmd" if sys.platform == "win32" else ""
    cmd = [f"codex{_ext}", "exec", "--skip-git-repo-check", "--full-auto"]
    if model:
        cmd.extend(["--model", model])
    # Prompt is passed via stdin by the caller (run_ai_popen stdin_text)
    return cmd

STDIN_PROMPT = True  # signals ai_runner to pipe prompt via stdin

ENV_VARS   = []   # API key is optional — Codex CLI handles auth internally
SETUP_HINT = "Install: npm install -g @openai/codex"
