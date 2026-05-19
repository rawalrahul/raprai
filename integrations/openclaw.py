"""
OpenClaw direct integration - run openclaw CLI without the NemoClaw sandbox.

OpenClaw manages its own auth (OAuth, API keys, etc.) — configure it with:
  openclaw auth login       # OAuth for Claude.ai Pro / Max
  openclaw config set key ANTHROPIC_API_KEY <key>   # direct API key
  openclaw config set key OPENAI_API_KEY <key>       # GPT models
  ... and so on for any provider openclaw supports

This integration just calls the installed openclaw binary.  No API keys need
to be set in RAPR AI — auth lives entirely inside openclaw's own config.

Install: npm install -g @openclaw/cli

Compared to NemoClaw (sandboxed):
  + No sandbox overhead — ~500ms faster per call
  + Works natively from the host PATH
  - No Landlock/seccomp isolation (openclaw runs with your user permissions)

Set OPENCLAW_AGENT to use a different agent profile (default: "main").
Set OPENCLAW_MODEL to pin a model (e.g. "claude-opus-4-7", "gpt-4o").
"""

import os

# ── Identity ─────────────────────────────────────────────────────────────────

KEY   = "openclaw"
NAME  = "OpenClaw"
EMOJI = "🐾"
COLOR = "#f59e0b"   # amber

# Prompt is passed as a direct argv value. subprocess.Popen receives an argv
# list, so shell quoting is not involved.
STDIN_PROMPT = False

# ── Helpers ──────────────────────────────────────────────────────────────────

def _agent() -> str:
    return os.environ.get("OPENCLAW_AGENT", "main").strip() or "main"


def _model_args(model: str | None) -> list[str]:
    m = (model or os.environ.get("OPENCLAW_MODEL", "")).strip()
    return ["--model", m] if m else []


# ── Command builder ──────────────────────────────────────────────────────────

def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """
    Build a direct host command for openclaw.

    Strategy:
      - Prompt is passed as --message in the argv list.
      - No shell wrapper is used.
      - No WSL bridge is used; that belongs to the NemoClaw integration.
      - openclaw must be installed on the host PATH.
    """
    agent = _agent()
    # OPENCLAW_LOCAL_FLAG: set to "" to drop --local if openclaw removes it.
    local_flag = os.environ.get("OPENCLAW_LOCAL_FLAG", "--local").strip()
    cmd = ["openclaw", "agent", "--agent", agent]
    if local_flag:
        cmd.append(local_flag)
    cmd += ["--message", prompt, *_model_args(model)]
    return cmd


# ── Metadata ─────────────────────────────────────────────────────────────────

# No RAPR AI env vars needed — openclaw stores its own credentials.
ENV_VARS: list[str] = ["OPENCLAW_AGENT", "OPENCLAW_MODEL", "OPENCLAW_LOCAL_FLAG"]

SETUP_HINT: str = (
    "Install openclaw: npm install -g @openclaw/cli  |  "
    "Authenticate: openclaw auth login (OAuth) or openclaw config set key ANTHROPIC_API_KEY <key>  |  "
    "Make sure openclaw is available on the host PATH  |  "
    "Set OPENCLAW_AGENT=<name> to use a different agent profile  |  "
    "Set OPENCLAW_MODEL=<model> to pin a specific model"
)
