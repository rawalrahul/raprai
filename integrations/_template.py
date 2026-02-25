"""
AI CLI Integration Template
===========================
Copy this file to  integrations/<your_ai_name>.py  and fill in the sections below.
That's it — the bot auto-discovers every *.py file in this folder at startup.

Quick steps:
  1. cp integrations/_template.py integrations/mygpt.py
  2. Edit KEY, NAME, EMOJI, COLOR and build_command() below.
  3. Restart the bot.  Your new AI appears in Telegram buttons and the web UI.

No other file needs to be touched.
"""

import sys

# ── REQUIRED ──────────────────────────────────────────────────────────────────

KEY  = "mygpt"       # Unique slug — lowercase, no spaces, no special chars.
                     # Used internally and in Telegram callback_data.

NAME = "MyGPT"       # Human-readable display name shown in buttons and messages.

EMOJI = "⭐"          # Single emoji shown on the button (keep it one char).

# ── Command builder (REQUIRED) ────────────────────────────────────────────────

def build_command(prompt: str) -> list[str]:
    """
    Return the shell command that runs your AI CLI with `prompt` as input.

    Examples:
        ["mygpt", "--prompt", prompt]
        ["python", "-m", "mygpt", prompt]
        ["mygpt.cmd", "--full-auto", "--query", prompt]   # Windows .cmd wrapper
    """
    _ext = ".cmd" if sys.platform == "win32" else ""
    return [f"mygpt{_ext}", "--prompt", prompt]

# ── OPTIONAL ──────────────────────────────────────────────────────────────────

# Hex color used in the web UI for the AI indicator dot and active-state border.
# Pick something distinct from existing AIs so it's easy to tell apart at a glance.
COLOR = "#8b5cf6"          # purple — change to whatever fits your AI

# Environment variables this integration needs.
# Shown in the /status output so the user knows what to set in .env.
ENV_VARS: list[str] = ["MYGPT_API_KEY"]

# One-liner shown when ENV_VARS are missing or when the user asks for setup help.
SETUP_HINT: str = (
    "Install: pip install mygpt-cli  |  "
    "Set MYGPT_API_KEY=your_key_here in .env"
)
