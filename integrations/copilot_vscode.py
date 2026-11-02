"""GitHub Copilot through VS Code's own sign-in, by way of the RAPR Bridge extension.

VS Code's Copilot has no command-line tool RAPR can run and keeps its sign-in inside VS Code,
so RAPR asks it through a small extension (helm/vscode_bridge, vscode-bridge/ in the repo)
that uses VS Code's language model API with your permission. It answers questions (reviews,
plans, second opinions); it doesn't edit files, and it works while VS Code is open.

Shown only where GitHub Copilot Chat is installed in VS Code (or the bridge is), ready only
while the bridge answers, so nothing changes for anyone else.
"""

import sys

KEY   = "copilot_vscode"
NAME  = "Copilot (VS Code)"
EMOJI = "🪁"
COLOR = "#8957e5"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    cmd = [sys.executable, "-m", "helm.ai_runner._vscode_bridge_cli"]
    if model:
        cmd += ["--model", model]
    return cmd


def SHOW() -> bool:
    from helm import vscode_bridge
    return vscode_bridge.copilot_in_vscode() or vscode_bridge.installed() or vscode_bridge.read_info() is not None


def READY() -> bool:
    from helm import vscode_bridge
    return vscode_bridge.healthy()


# Answers questions; can't edit files (RAPR refuses it for roles that must).
ANSWERS_ONLY = True
STDIN_PROMPT = True
ENV_VARS: list[str] = []
SETUP_HINT = ("Needs GitHub Copilot Chat signed in, in VS Code, and the RAPR Bridge extension: ask your AI to "
              "\"connect Copilot from VS Code\" (RAPR's connect_vscode_copilot tool), then in VS Code run "
              "\"RAPR: Connect Copilot\" and press Allow.")

# Catalog (Settings → AI Integrations)
ABOUT   = "GitHub Copilot, using your VS Code sign-in through the RAPR Bridge extension. Answers questions; no file edits."
INSTALL = ""
DOCS    = "https://github.com/rawalrahul/raprai/blob/main/docs/guide.md#copilot-from-vs-code"
