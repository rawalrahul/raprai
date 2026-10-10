"""Amazon Q Developer CLI integration (now Kiro CLI: kiro-cli, with q kept as an alias).

Headless use needs --no-interactive and the prompt as an argument; without them
it opens an interactive chat and treats stdin only as extra context.
"""

import os
import shutil

KEY   = "amazon_q"
NAME  = "Amazon Q"
EMOJI = "🔶"
COLOR = "#ff9900"  # AWS orange

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build Amazon Q / Kiro command. Prompt passed as the last argument."""
    # AMAZON_Q_TRUST_FLAG: override if Amazon renames the tool-trust flag.
    trust_flag = os.environ.get("AMAZON_Q_TRUST_FLAG", "--trust-all-tools").strip()
    exe = "kiro-cli" if shutil.which("kiro-cli") or not shutil.which("q") else "q"
    cmd = [exe, "chat", "--no-interactive"]
    if trust_flag:
        cmd.append(trust_flag)
    cmd.append(prompt)
    return cmd

# q chat reads prompt from stdin when piped non-interactively.
STDIN_PROMPT = False

ENV_VARS: list[str] = ["AMAZON_Q_TRUST_FLAG"]

SETUP_HINT: str = (
    "Install Kiro CLI (formerly Amazon Q CLI): https://kiro.dev/docs/cli/  |  "
    "Auth: kiro-cli login (free AWS Builder ID — no credit card)  |  "
    "No API key needed — Amazon Q handles auth internally"
)
