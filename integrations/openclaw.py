"""
OpenClaw direct integration — run openclaw CLI without the NemoClaw sandbox.

OpenClaw manages its own auth (OAuth, API keys, etc.) — configure it with:
  openclaw auth login       # OAuth for Claude.ai Pro / Max
  openclaw config set key ANTHROPIC_API_KEY <key>   # direct API key
  openclaw config set key OPENAI_API_KEY <key>       # GPT models
  ... and so on for any provider openclaw supports

This integration just calls the installed openclaw binary.  No API keys need
to be set in RAPR AI — auth lives entirely inside openclaw's own config.

Windows users: openclaw must be installed inside WSL2.
  Install: npm install -g @openclaw/cli   (run inside WSL terminal)
Linux/Mac: npm install -g @openclaw/cli

Compared to NemoClaw (sandboxed):
  + No sandbox overhead — ~500ms faster per call
  + Works natively on Linux and Mac
  - No Landlock/seccomp isolation (openclaw runs with your user permissions)

Set OPENCLAW_AGENT to use a different agent profile (default: "main").
Set OPENCLAW_MODEL to pin a model (e.g. "claude-opus-4-7", "gpt-4o").
"""

import os
import sys

# ── Identity ─────────────────────────────────────────────────────────────────

KEY   = "openclaw"
NAME  = "OpenClaw"
EMOJI = "🐾"
COLOR = "#f59e0b"   # amber

# Prompt is piped via stdin — avoids Windows command-line length limits and
# lets the WSL shell wrapper read it cleanly without argument quoting issues.
STDIN_PROMPT = True

# ── Helpers ──────────────────────────────────────────────────────────────────

def _agent() -> str:
    return os.environ.get("OPENCLAW_AGENT", "main").strip() or "main"


def _model_flag(model: str | None) -> str:
    m = (model or os.environ.get("OPENCLAW_MODEL", "")).strip()
    return f" --model {m}" if m else ""


# ── Command builder ──────────────────────────────────────────────────────────

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """
    Build a command that pipes the prompt (via stdin) into openclaw.

    Strategy:
      - Prompt arrives via stdin (STDIN_PROMPT = True).
      - A bash wrapper reads stdin, base64-encodes it, then passes the decoded
        text as --message to openclaw.  Base64 avoids all shell quoting issues
        regardless of what characters the prompt contains.
      - Windows: routed through wsl.exe (openclaw must live inside WSL2).
      - Linux/Mac: bash called directly (openclaw must be in PATH).
    """
    agent = _agent()
    mflag = _model_flag(model)

    shell_script = (
        f'export PATH="$HOME/.local/bin:$PATH" && '
        f'B64=$(cat | base64 -w0) && '
        f'openclaw agent --agent {agent} --local'
        f' --message "$(echo $B64 | base64 -d)"{mflag}'
    )

    if sys.platform == "win32":
        return ["wsl.exe", "-e", "bash", "-lc", shell_script]
    else:
        return ["bash", "-lc", shell_script]


# ── Metadata ─────────────────────────────────────────────────────────────────

# No RAPR AI env vars needed — openclaw stores its own credentials.
ENV_VARS: list[str] = []

SETUP_HINT: str = (
    "Install openclaw: npm install -g @openclaw/cli  |  "
    "Authenticate: openclaw auth login (OAuth) or openclaw config set key ANTHROPIC_API_KEY <key>  |  "
    "Windows: run both commands inside WSL2  |  "
    "Set OPENCLAW_AGENT=<name> to use a different agent profile  |  "
    "Set OPENCLAW_MODEL=<model> to pin a specific model"
)
