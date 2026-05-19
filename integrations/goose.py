"""Goose AI agent integration (by Block)."""

import os
import shlex

KEY   = "goose"
NAME  = "Goose"
EMOJI = "🪿"
COLOR = "#6366f1"  # indigo

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build Goose command for non-interactive single-shot execution."""
    # GOOSE_RUN_ARGS: override if Block restructures the run subcommand or flags.
    _default = "run --text"
    run_args = shlex.split(os.environ.get("GOOSE_RUN_ARGS", _default))
    cmd = ["goose"] + run_args + [prompt]
    return cmd

STDIN_PROMPT = False

ENV_VARS: list[str] = ["GOOSE_RUN_ARGS"]

SETUP_HINT: str = (
    "Install Goose: https://block.github.io/goose/docs/getting-started/installation  |  "
    "Configure provider: goose configure  |  "
    "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
)
