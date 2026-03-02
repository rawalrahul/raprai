"""Google Gemini CLI integration."""

import sys

KEY   = "gemini"
NAME  = "Gemini"
EMOJI = "✨"
COLOR = "#3b82f6"   # blue

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    _ext = ".cmd" if sys.platform == "win32" else ""
    cmd = [f"gemini{_ext}"]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(["-p", prompt, "--yolo"])
    return cmd

ENV_VARS   = []   # API key is optional — Gemini CLI handles auth internally
SETUP_HINT = "Install: npm install -g @google/gemini-cli"
