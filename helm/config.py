"""
helm/config.py — All constants, environment variables, and logging setup.

Import this first; every other module depends on it.
"""

import logging
import os
import pathlib
import re
import sys

from dotenv import load_dotenv

# In bundled mode, .env lives next to the .exe (not inside the bundle)
from helm.paths import user_data_dir as _udd, is_bundled as _is_bundled
_env_path = _udd() / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
elif not _is_bundled():
    load_dotenv()  # dev mode fallback: search from cwd
# When bundled with no .env, skip — setup wizard will create it

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("helm")

# Suppress httpx INFO logs (they leak Telegram bot tokens in URLs)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Telegram / auth
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_IDS: set[int] = set(
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
)

# ---------------------------------------------------------------------------
# Terminal / AI timeouts
# ---------------------------------------------------------------------------
# All values are in seconds.  0 = unlimited where applicable.
# Override via environment variables (e.g. in .env).
#
# OUTPUT_IDLE_TIMEOUT  – how long to wait after the last output chunk before
#                         declaring the subprocess "done" (shell / terminal mode)
# OUTPUT_MAX_WAIT      – hard ceiling on total shell/terminal wait
# OUTPUT_NO_RESPONSE   – how long to wait before first output appears
# CLAUDE_TIMEOUT       – Claude CLI subprocess timeout (0 = unlimited)

IDLE_TIMEOUT        = float(os.environ.get("OUTPUT_IDLE_TIMEOUT", "30"))   # was 1.5
MAX_WAIT            = float(os.environ.get("OUTPUT_MAX_WAIT",      "600"))  # was 60  (10 min)
NO_OUTPUT_TIMEOUT   = float(os.environ.get("OUTPUT_NO_RESPONSE",   "120"))  # was 5   (2 min)
CLAUDE_TIMEOUT      = float(os.environ.get("CLAUDE_TIMEOUT",       "0"))    # 0 = unlimited
# INTEGRATION_TIMEOUT – max seconds for non-Claude AI subprocesses (Gemini, Codex, …).
#                       These are single-turn CLIs so a 3-min ceiling is ample.
#                       Prevents infinite hang when an invalid --model causes the
#                       CLI to enter an interactive picker (no terminal attached).
INTEGRATION_TIMEOUT = float(os.environ.get("INTEGRATION_TIMEOUT", "180"))  # 3 min

# ---------------------------------------------------------------------------
# Paths / server
# ---------------------------------------------------------------------------

_DEFAULT_CWD = os.environ.get("SESSION_CWD", os.getcwd())
WEB_PORT     = int(os.environ.get("WEB_PORT", "8000"))
WEB_HOST     = os.environ.get("WEB_HOST", "127.0.0.1")
# In bundled mode, chat_logs/ lives next to the .exe for persistence
_chat_log_env = os.environ.get("CHAT_LOG_DIR", "")
if _chat_log_env:
    CHAT_LOG_DIR = pathlib.Path(_chat_log_env)
else:
    CHAT_LOG_DIR = _udd() / "chat_logs"

# ---------------------------------------------------------------------------
# PIN auth (values populated by helm/auth.py after first setup)
# PIN_SALT and PIN_HASH are written to .env by the setup wizard / /auth/set-pin
# SESSION_DAYS controls how long a login cookie is valid
# PIN_MAX_ATTEMPTS / PIN_LOCKOUT_SECS control brute-force protection
# ---------------------------------------------------------------------------
# (No constants needed here — auth.py reads these directly from os.environ)

# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------

USAGE_PERIOD_SECONDS = max(
    3600,
    int(float(os.environ.get("USAGE_RESET_HOURS", "24")) * 3600),
)

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

_CMD_EXT = ".cmd" if sys.platform == "win32" else ""

# Regex helpers (used in multiple modules)
ANSI_ESCAPE    = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][AB012]|\x1b.")
HISTORY_ID_RE  = re.compile(r"^\d{4}-\d{2}-\d{2}$|^p_[a-f0-9]{12}$")

BROWSE_PAGE_SIZE = 8

# Croniter availability flag (populated once in scheduler.py)
try:
    from croniter import croniter as _Croniter
    CRONITER_OK = True
except ImportError:
    _Croniter = None        # type: ignore[assignment]
    CRONITER_OK = False
