"""Google Gemini CLI integration."""

import sys

KEY   = "gemini"
NAME  = "Gemini"
EMOJI = "✨"
COLOR = "#3b82f6"   # blue

def build_command(prompt: str) -> list[str]:
    _ext = ".cmd" if sys.platform == "win32" else ""
    return [f"gemini{_ext}", "-p", prompt, "--yolo"]

ENV_VARS   = []   # API key is optional — Gemini CLI handles auth internally
SETUP_HINT = "Install: npm install -g @google/gemini-cli"
