"""Factory Droid — coding agent from Factory.

Checked against droid 0.238.0: `droid exec` runs one prompt and exits, reading
it from stdin. It is read-only by default; --auto low|medium|high allows edits
(medium: also installs, builds and local git). -m picks the model.
"""

import os
import shutil

KEY   = "droid"
NAME  = "Droid"
EMOJI = "🤖"
COLOR = "#6366f1"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    cmd = [shutil.which("droid") or "droid", "exec"]
    level = os.environ.get("DROID_AUTO_LEVEL", "medium").strip()
    if level:
        cmd.extend(["--auto", level])
    if model:
        cmd.extend(["-m", model])
    return cmd


STDIN_PROMPT = True
ENV_VARS: list[str] = []
SETUP_HINT = ("Install: npm install -g @factory/cli  |  Auth: set FACTORY_API_KEY (from app.factory.ai)  |  "
              "Edits allowed via --auto medium; set DROID_AUTO_LEVEL=low for file edits only")

# Catalog (Settings → AI Integrations)
ABOUT   = "Factory's coding agent. Needs a Factory account (FACTORY_API_KEY)."
INSTALL = "npm install -g @factory/cli"
DOCS    = "https://www.npmjs.com/package/@factory/cli"
