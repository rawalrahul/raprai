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

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("helm")

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

IDLE_TIMEOUT        = float(os.environ.get("OUTPUT_IDLE_TIMEOUT", "1.5"))
MAX_WAIT            = float(os.environ.get("OUTPUT_MAX_WAIT", "60"))
NO_OUTPUT_TIMEOUT   = float(os.environ.get("OUTPUT_NO_RESPONSE", "5"))
CLAUDE_TIMEOUT      = float(os.environ.get("CLAUDE_TIMEOUT", "0"))  # 0 = unlimited

# ---------------------------------------------------------------------------
# Paths / server
# ---------------------------------------------------------------------------

_DEFAULT_CWD = os.environ.get("SESSION_CWD", os.getcwd())
WEB_PORT     = int(os.environ.get("WEB_PORT", "8000"))
WEB_HOST     = os.environ.get("WEB_HOST", "127.0.0.1")
CHAT_LOG_DIR = pathlib.Path(os.environ.get("CHAT_LOG_DIR", "chat_logs"))

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
