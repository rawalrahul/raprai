"""OpenCode (sst/opencode) — open-source coding agent, any model provider.

Checked against opencode 1.19.0: `opencode run` runs one prompt and exits,
reading it from stdin; --auto approves tool use; -m picks provider/model.
"""

import os
import shutil

KEY   = "opencode"
NAME  = "OpenCode"
EMOJI = "🖥️"
COLOR = "#f97316"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    cmd = [shutil.which("opencode") or "opencode", "run"]
    if model:
        cmd.extend(["-m", model])          # provider/model, e.g. anthropic/claude-sonnet-4-6
    auto = os.environ.get("OPENCODE_AUTO_FLAG", "--auto").strip()
    if auto:
        cmd.append(auto)
    return cmd


STDIN_PROMPT = True
ENV_VARS: list[str] = []
SETUP_HINT = ("Install: npm install -g opencode-ai  |  Sign in to a provider: opencode auth login  |  "
              "Model format: provider/model (e.g. ollama/qwen3-coder)")

# Catalog (Settings → AI Integrations)
ABOUT   = "Open-source coding agent that works with many model providers, including Ollama."
INSTALL = "npm install -g opencode-ai"
DOCS    = "https://opencode.ai/docs"
