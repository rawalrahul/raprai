"""Google Gemini CLI integration."""

import sys

KEY   = "gemini"
NAME  = "Gemini"
EMOJI = "✨"
COLOR = "#3b82f6"   # blue

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build command args WITHOUT the prompt — prompt is piped via stdin
    to avoid Windows cmd.exe 8 KB command-line length limits."""
    _ext = ".cmd" if sys.platform == "win32" else ""
    cmd = [f"gemini{_ext}"]
    if model:
        cmd.extend(["--model", model])
    # Prompt is passed via stdin by the caller (run_ai_popen stdin_text)
    # Using --yolo without -p: Gemini CLI reads from stdin when piped.
    cmd.append("--yolo")
    return cmd

STDIN_PROMPT = True  # signals ai_runner to pipe prompt via stdin

ENV_VARS   = []   # API key is optional — Gemini CLI handles auth internally
SETUP_HINT = "Install: npm install -g @google/gemini-cli"
