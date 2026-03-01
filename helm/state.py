"""
helm/state.py — All mutable global state for the Helm HQ process.

Every other module imports this module object and accesses variables via
``import helm.state as _st; _st.focused_id = ...`` so that scalar rebindings
are visible across the whole application.

Rules:
  • Mutable containers (dict / list / set) can also be imported directly
    because mutations propagate through the shared object reference.
  • Scalar rebindings (str / int / float / None) MUST be done via the module:
      _st.focused_id = "s1"    ✓
      from helm.state import focused_id; focused_id = "s1"   ✗  (creates local copy)
"""

import time
from typing import Optional, TYPE_CHECKING

from helm.config import _DEFAULT_CWD, ALLOWED_USER_IDS, USAGE_PERIOD_SECONDS

if TYPE_CHECKING:
    from telegram.ext import Application

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

sessions: dict[str, dict] = {}       # sid -> session_dict
focused_id: Optional[str] = None     # which session Telegram/Web are talking to
session_counter: int = 0             # incremented for each new session

# ---------------------------------------------------------------------------
# CWD tracking
# ---------------------------------------------------------------------------

last_cwd: str = _DEFAULT_CWD         # persists even when no session is focused

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

# For private bot DMs, chat_id == user_id; pre-init from ALLOWED_USER_IDS so
# web-initiated responses are forwarded to Telegram even before the user
# sends their first Telegram message.
telegram_chat_id: Optional[int] = next(iter(ALLOWED_USER_IDS), None)
telegram_app: Optional["Application"] = None   # set in startup._main()

pending_tg_context: Optional[str] = None       # injected into next Telegram msg after /resume
tg_browse_state: dict = {}                      # user_id -> {path, dirs, page}

# ---------------------------------------------------------------------------
# WebSocket clients & in-memory chat history
# ---------------------------------------------------------------------------

ws_clients: set = set()
chat_history: list[dict] = []        # recent msgs replayed to new WS clients

# ---------------------------------------------------------------------------
# AI integration plugins (populated by integrations.load_integrations())
# ---------------------------------------------------------------------------

integrations: dict = {}

# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------

usage_period_start: float = time.time()
usage_stats: dict[str, dict] = {}    # ai_key -> counters for current period
usage_exact: dict[str, dict] = {}    # ai_key -> exact-ish CLI parsed usage info

# ---------------------------------------------------------------------------
# Scheduled tasks
# ---------------------------------------------------------------------------

scheduled_tasks: dict[str, dict] = {}
sched_counter: int = 0

# ---------------------------------------------------------------------------
# History cache (populated by history.rebuild_hist_cache_sync)
# ---------------------------------------------------------------------------

hist_cache: list = []
hist_cache_ts: float = 0.0
