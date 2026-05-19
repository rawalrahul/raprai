"""Aider AI coding assistant integration."""

import os
import sys

KEY   = "aider"
NAME  = "Aider"
EMOJI = "🪄"
COLOR = "#f97316"  # orange

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build aider command. Prompt passed via --message (not stdin)."""
    _ext = ".exe" if sys.platform == "win32" else ""
    # AIDER_YES_FLAG: override if aider renames its auto-confirm flag.
    yes_flag = os.environ.get("AIDER_YES_FLAG", "--yes").strip()
    cmd = [f"aider{_ext}"]
    if model:
        cmd.extend(["--model", model])
    if yes_flag:
        cmd.append(yes_flag)
    cmd.append("--no-auto-commits")
    cmd.extend(["--message", prompt])
    return cmd

# aider does not read the message from stdin — uses --message flag.
STDIN_PROMPT = False

ENV_VARS: list[str] = ["AIDER_YES_FLAG"]

SETUP_HINT: str = (
    "Install: pip install aider-chat  |  "
    "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env  |  "
    "Aider picks the key that matches the model selected"
)
