"""Google Antigravity CLI integration (agy — successor to Gemini CLI, launched Google I/O 2026)."""

import os
import pathlib
import sys

KEY   = "antigravity"
NAME  = "Antigravity"
EMOJI = "🪐"
COLOR = "#8b5cf6"   # purple — distinct from Gemini's blue


def _agy_exe() -> str:
    """Resolve the agy binary. On Windows checks %LOCALAPPDATA%\\Antigravity\\agy.exe first."""
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            candidate = pathlib.Path(local_app) / "Antigravity" / "agy.exe"
            if candidate.exists():
                return str(candidate)
    return "agy"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Build command args for Antigravity CLI. Prompt is piped via stdin.

    --dangerously-skip-permissions is required for headless subprocess use;
    without it agy blocks waiting for interactive tool approvals.
    Override via AGY_APPROVAL_FLAG env var (e.g. set to "" to omit entirely,
    or to a stricter flag if a future agy release adds one).
    """
    cmd = [_agy_exe()]
    if model:
        cmd.extend(["--model", model])
    approval_flag = os.environ.get("AGY_APPROVAL_FLAG", "--dangerously-skip-permissions")
    if approval_flag:
        cmd.append(approval_flag)
    return cmd


STDIN_PROMPT = True   # signals ai_runner to pipe prompt via stdin

ENV_VARS   = []       # auth handled internally (Google account or GEMINI_API_KEY)
SETUP_HINT = "Install Antigravity CLI: see antigravity.google/docs/cli-using"
