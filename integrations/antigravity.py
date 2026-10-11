"""Google Antigravity CLI integration (agy). Google stopped the Gemini CLI for personal
accounts in June 2026; agy is its replacement."""

import os
import pathlib
import sys

KEY   = "antigravity"
NAME  = "Antigravity"
EMOJI = "🪐"
COLOR = "#8b5cf6"   # purple — distinct from Gemini's blue


def _agy_exe() -> str:
    """Resolve the agy binary: PATH first, then %LOCALAPPDATA%\\Antigravity\\agy.exe on Windows."""
    import shutil
    found = shutil.which("agy")
    if found:
        return found
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            candidate = pathlib.Path(local_app) / "Antigravity" / "agy.exe"
            if candidate.exists():
                return str(candidate)
    return "agy"


# agy doesn't read the prompt from stdin, so it goes on the command line, which
# Windows caps at 32,767 characters. A longer prompt is written to a file that
# agy is told to read (its folder is added to agy's workspace with --add-dir).
_MAX_ARG_PROMPT = 24_000


def _prompt_file(prompt: str) -> pathlib.Path:
    import tempfile
    import time
    import uuid
    folder = pathlib.Path(tempfile.gettempdir()) / "rapr-agy-prompts"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("prompt-*.md"):          # tidy up earlier runs
        try:
            if time.time() - old.stat().st_mtime > 6 * 3600:
                old.unlink()
        except OSError:
            pass
    path = folder / f"prompt-{uuid.uuid4().hex[:12]}.md"
    path.write_text(prompt, encoding="utf-8")
    return path


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """agy -p "<prompt>" [--model M] --dangerously-skip-permissions

    Print mode runs one prompt and exits. --dangerously-skip-permissions is
    needed because headless mode can't ask for tool approvals (it denies them).
    Override via AGY_APPROVAL_FLAG (set to "" to omit).
    """
    cmd = [_agy_exe()]
    if len(prompt) > _MAX_ARG_PROMPT:
        path = _prompt_file(prompt)
        cmd += ["--add-dir", str(path.parent)]
        prompt = (f"The full request is in the file {path} (too long to pass directly). "
                  "Read that whole file first, then do exactly what it asks. "
                  "Don't mention the file in your answer.")
    cmd += ["-p", prompt]
    if model:
        cmd.extend(["--model", model])
    approval_flag = os.environ.get("AGY_APPROVAL_FLAG", "--dangerously-skip-permissions")
    if approval_flag:
        cmd.append(approval_flag)
    return cmd


STDIN_PROMPT = False  # agy doesn't read stdin in print mode; the prompt is the -p argument

ENV_VARS   = []       # auth handled by agy itself (Google sign-in)
SETUP_HINT = ("Install Antigravity CLI (agy), Google's replacement for the Gemini CLI: "
              "see antigravity.google/docs/cli-using, then sign in by running agy once.")
