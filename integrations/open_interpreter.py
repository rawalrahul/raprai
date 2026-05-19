"""Open Interpreter integration."""

import os
import sys

KEY   = "interpreter"
NAME  = "Open Interpreter"
EMOJI = "🖥️"
COLOR = "#8b5cf6"  # purple

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build Open Interpreter command. Prompt passed via --message flag."""
    _ext = ".exe" if sys.platform == "win32" else ""
    # INTERPRETER_AUTO_FLAG: override if Open Interpreter renames --auto_run.
    auto_flag = os.environ.get("INTERPRETER_AUTO_FLAG", "--auto_run").strip()
    cmd = [f"interpreter{_ext}"]
    if model:
        cmd.extend(["--model", model])
    if auto_flag:
        cmd.append(auto_flag)
    cmd.extend(["--message", prompt])
    return cmd

STDIN_PROMPT = False

ENV_VARS: list[str] = ["INTERPRETER_AUTO_FLAG"]

SETUP_HINT: str = (
    "Install: pip install open-interpreter  |  "
    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env  |  "
    "Local models: interpreter --local"
)
