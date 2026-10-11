"""GitHub Copilot CLI.

Checked against copilot 1.0.95: with the prompt piped in (no -p) it answers once
and exits (with -p, piped input is ignored, so RAPR doesn't use -p);
--allow-all-tools is required headless; -s prints only the answer.
"""

import os
import shutil

KEY   = "copilot"
NAME  = "Copilot CLI"
EMOJI = "✈️"
COLOR = "#8957e5"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    cmd = [shutil.which("copilot") or "copilot"]
    allow = os.environ.get("COPILOT_ALLOW_FLAG", "--allow-all-tools").strip()
    if allow:
        cmd.append(allow)
    cmd += ["-s", "--no-auto-update"]
    if model:
        cmd.extend(["--model", model])
    return cmd


STDIN_PROMPT = True
ENV_VARS: list[str] = []
SETUP_HINT = ("Install: npm install -g @github/copilot  |  Sign in: copilot login "
              "(or set COPILOT_GITHUB_TOKEN)  |  Needs a GitHub Copilot plan")

# Catalog (Settings → AI Integrations)
ABOUT   = "GitHub Copilot's coding agent. Sign in with your GitHub account and Copilot plan."
INSTALL = "npm install -g @github/copilot"
DOCS    = "https://www.npmjs.com/package/@github/copilot"
