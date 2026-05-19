"""Amazon Q Developer CLI integration."""

import os

KEY   = "amazon_q"
NAME  = "Amazon Q"
EMOJI = "🔶"
COLOR = "#ff9900"  # AWS orange

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build Amazon Q command. Prompt piped via stdin."""
    # AMAZON_Q_TRUST_FLAG: override if Amazon renames the tool-trust flag.
    trust_flag = os.environ.get("AMAZON_Q_TRUST_FLAG", "--trust-all-tools").strip()
    cmd = ["q", "chat"]
    if trust_flag:
        cmd.append(trust_flag)
    return cmd

# q chat reads prompt from stdin when piped non-interactively.
STDIN_PROMPT = True

ENV_VARS: list[str] = ["AMAZON_Q_TRUST_FLAG"]

SETUP_HINT: str = (
    "Install Amazon Q CLI: https://docs.aws.amazon.com/amazonq/  |  "
    "Auth: q login (free AWS Builder ID — no credit card)  |  "
    "No API key needed — Amazon Q handles auth internally"
)
