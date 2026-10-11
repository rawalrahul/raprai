"""Claude Code running on a local Ollama model (free, offline).

Ollama (0.14+) speaks Anthropic's Messages API, so Claude Code can use a local
model: ANTHROPIC_BASE_URL points at Ollama and --model names an Ollama model.
Checked against Claude Code 2.1.296: `claude -p` reads the prompt from stdin and
sends it to ANTHROPIC_BASE_URL with the given model.

Claude Code may send the user's own Claude sign-in token with each request, so
RAPR only ever points it at Ollama on this computer (127.0.0.1), never at a
remote OLLAMA_HOST: the token can't leave the machine.
"""

import json
import os
import pathlib
import re
import shutil
import tempfile

KEY   = "claude_ollama"
NAME  = "Claude Code (Ollama)"
EMOJI = "🦙"
COLOR = "#d97757"

_DEFAULT_MODEL = "qwen3-coder"
_LOCAL_OLLAMA = "http://127.0.0.1:11434"


def _local_port() -> str:
    """Port of a local OLLAMA_HOST (e.g. "127.0.0.1:11500"); remote hosts are ignored."""
    host = os.environ.get("OLLAMA_HOST", "").strip().replace("http://", "").replace("https://", "")
    name, _, port = host.partition(":")
    if name in ("", "127.0.0.1", "localhost", "0.0.0.0") and port.isdigit():
        return port
    return "11434"


def _model(model: str | None) -> str:
    if model:
        return model
    try:
        import helm.state as _st
        return _st.default_models.get(KEY) or os.environ.get("CLAUDE_OLLAMA_MODEL") or _DEFAULT_MODEL
    except Exception:
        return os.environ.get("CLAUDE_OLLAMA_MODEL") or _DEFAULT_MODEL


def _settings_file(model: str) -> str:
    """Claude Code also calls its "haiku/sonnet/opus" models in the background;
    map them all to the chosen Ollama model (a file, so Windows quoting can't mangle JSON)."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", model)
    path = pathlib.Path(tempfile.gettempdir()) / "rapr-claude-ollama" / f"{safe}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    env = {f"ANTHROPIC_DEFAULT_{tier}_MODEL": model for tier in ("HAIKU", "SONNET", "OPUS")}
    path.write_text(json.dumps({"env": env}), encoding="utf-8")
    return str(path)


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    m = _model(model)
    return [shutil.which("claude") or "claude", "-p", "--model", m,
            "--dangerously-skip-permissions", "--output-format", "text",
            "--settings", _settings_file(m)]


STDIN_PROMPT = True
ENV_VARS: list[str] = []
PROCESS_ENV = {
    "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{_local_port()}",
    "ANTHROPIC_AUTH_TOKEN": "ollama",
    "ANTHROPIC_API_KEY": "",
}
SETUP_HINT = ("Needs Claude Code and Ollama 0.14+ running on this computer, with a coding model "
              "pulled (e.g. ollama pull qwen3-coder). Pick the model with /model. Local models "
              "are slower and weaker than Claude; give them a 32K+ context.")

# Catalog (Settings → AI Integrations)
ABOUT   = "Claude Code on a free local model through Ollama. Needs a strong computer."
INSTALL = "ollama pull qwen3-coder"
DOCS    = "https://ollama.com/blog/claude"
