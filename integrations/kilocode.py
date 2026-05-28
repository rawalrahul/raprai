"""Kilo Code CLI integration (kilo — open-source AI coding agent, 500+ models)."""

import os
import sys

KEY   = "kilocode"
NAME  = "Kilo Code"
EMOJI = "⚡"
COLOR = "#eab308"   # yellow


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build command for Kilo Code CLI autonomous mode.

    Binary: kilo  (npm install -g @kilocode/cli)
    'kilo run --auto' reads the prompt from stdin when no positional arg is given.
    --model accepts provider/model-id format: e.g. anthropic/claude-sonnet-4-6

    Override autonomous flag via KILO_AUTO_FLAG env var (set to "" to disable).
    """
    _ext = ".cmd" if sys.platform == "win32" else ""
    cmd = [f"kilo{_ext}", "run"]
    if model:
        cmd.extend(["--model", model])
    auto_flag = os.environ.get("KILO_AUTO_FLAG", "--auto")
    if auto_flag:
        cmd.append(auto_flag)
    return cmd


STDIN_PROMPT = True   # prompt piped via stdin (kilo run --auto reads stdin when no positional arg)

ENV_VARS   = []       # model-agnostic — set ANTHROPIC_API_KEY / OPENAI_API_KEY / etc per model
SETUP_HINT = (
    "Install: npm install -g @kilocode/cli  |  "
    "Set API key for your model provider (e.g. ANTHROPIC_API_KEY)  |  "
    "Model format: provider/model-id (e.g. anthropic/claude-sonnet-4-6)"
)
