"""xAI Grok Build CLI integration (grok)."""

import pathlib
import sys

KEY   = "grok"
NAME  = "Grok"
EMOJI = "🅧"
COLOR = "#e5e7eb"   # light grey, xAI's monochrome

# The prompt goes on the command line, which Windows caps at 32,767 characters.
# A longer prompt (a review with a big diff) is written to a file Grok is told to read.
_MAX_ARG_PROMPT = 24_000


def _prompt_file(prompt: str) -> pathlib.Path:
    import tempfile
    import time
    import uuid
    folder = pathlib.Path(tempfile.gettempdir()) / "rapr-grok-prompts"
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
    """grok [flags] -p "<prompt>": headless mode runs one prompt with its tools, prints the
    answer and exits. --always-approve so it doesn't stop to ask with nobody there to
    answer; --no-auto-update so a run never waits on an update check."""
    import os
    import shlex
    _ext = ".cmd" if sys.platform == "win32" else ""
    # GROK_ARGS overrides the flags if xAI renames them.
    _default = "--always-approve --no-auto-update --output-format plain"
    cmd = [f"grok{_ext}"] + shlex.split(os.environ.get("GROK_ARGS", _default))
    if model:
        cmd.extend(["--model", model])
    if len(prompt) > _MAX_ARG_PROMPT:
        path = _prompt_file(prompt)
        prompt = (f"The full request is in the file {path} (too long to pass directly). "
                  "Read that whole file first, then do exactly what it asks. "
                  "Don't mention the file in your answer.")
    return cmd + ["-p", prompt]


STDIN_PROMPT = False  # the prompt is the -p argument

ENV_VARS   = []   # Grok signs in with `grok login`
SETUP_HINT = "Install Grok Build (see docs.x.ai/build), then sign in with: grok login"

# Catalog (Settings → AI Integrations)
ABOUT   = "xAI's coding agent. Sign in with `grok login`."
INSTALL = ""
DOCS    = "https://docs.x.ai/build/cli/headless-scripting"
