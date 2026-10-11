"""OpenAI Codex CLI integration."""

import sys

KEY   = "codex"
NAME  = "Codex"
EMOJI = "💻"
COLOR = "#22c55e"   # green

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build command args WITHOUT the prompt — prompt is piped via stdin
    to avoid Windows cmd.exe 8 KB command-line length limits."""
    import os, shlex
    _ext = ".cmd" if sys.platform == "win32" else ""
    # CODEX_AUTO_ARGS overrides the full base args (subcommand + flags) if OpenAI
    # restructures the CLI invocation. Codex 0.16x removed --full-auto; "--sandbox
    # workspace-write" is what it meant (edit files in the project, no prompts in exec),
    # and older versions accept it too.
    _default = "exec --skip-git-repo-check --sandbox workspace-write"
    _base = shlex.split(os.environ.get("CODEX_AUTO_ARGS", _default))
    cmd = [f"codex{_ext}"] + _base
    if model:
        cmd.extend(["--model", model])
    return cmd

STDIN_PROMPT = True  # signals ai_runner to pipe prompt via stdin

ENV_VARS   = []   # API key is optional — Codex CLI handles auth internally
SETUP_HINT = "Install: npm install -g @openai/codex"
