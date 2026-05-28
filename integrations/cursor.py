"""Cursor Agent CLI integration (headless AI coding agent)."""

import os
import sys

KEY   = "cursor"
NAME  = "Cursor"
EMOJI = "🖱️"
COLOR = "#a855f7"   # purple


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build command for Cursor Agent CLI headless mode.

    Binary defaults to "agent" (installed by curl https://cursor.com/install).
    Override via CURSOR_CLI_BIN env var if it conflicts with another "agent" in PATH.

    -p / --print: non-interactive print mode (headless/scripting).
    --force: auto-approve file changes without confirmation (required for headless).
    Override approval flag via CURSOR_APPROVAL_FLAG (e.g. set to "--yolo" or "").

    Requires CURSOR_API_KEY for authentication.
    """
    _bin = os.environ.get("CURSOR_CLI_BIN", "agent")
    if sys.platform == "win32" and not os.path.isabs(_bin) and "." not in _bin:
        # Try .cmd wrapper first (npm-distributed), then plain
        import shutil
        if shutil.which(_bin + ".cmd"):
            _bin = _bin + ".cmd"
    cmd = [_bin, "-p"]
    if model:
        cmd.extend(["-m", model])
    approval_flag = os.environ.get("CURSOR_APPROVAL_FLAG", "--force")
    if approval_flag:
        cmd.append(approval_flag)
    cmd.append(prompt)
    return cmd


STDIN_PROMPT = False  # prompt is passed as positional arg

ENV_VARS   = ["CURSOR_API_KEY"]
SETUP_HINT = (
    "Install Cursor CLI: curl https://cursor.com/install -fsSL | bash  |  "
    "Set CURSOR_API_KEY env var  |  "
    "If 'agent' conflicts, set CURSOR_CLI_BIN to the full path"
)
