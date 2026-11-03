"""
How much of the group chat each member may see, in estimated tokens.

  • Online AIs (Claude, Codex, Gemini, Copilot…): up to GROUP_CONTEXT_TOKENS,
    the user's setting (Settings → Group chats; default 200K). It is used as
    set, so raising it to 1M or more takes effect as windows grow. Only a
    window known to be smaller caps it: one the user set for that AI
    (CONTEXT_WINDOW_<AI>) or a service with a fixed smaller window (Groq…).
  • Offline models (Ollama, Claude/Codex on Ollama, LM Studio…): their windows
    are small, so they get GROUP_CONTEXT_OFFLINE_SHARE (default 50%) of it.
  Both settings are read on every prompt, so a change applies on the next reply.
  • A prompt that must go on the command line (not stdin) is also capped by
    the OS command-line limit.

The budget is a ceiling: a short chat is sent as it is.
"""

from __future__ import annotations

import os

from helm.groupchat_context.text import CHARS_PER_TOKEN

DEFAULT_ONLINE_TOKENS = 200_000
DEFAULT_OFFLINE_SHARE = 0.5
OFFLINE_DEFAULT_WINDOW = 32_000       # what RAPR asks local models to be run with
WINDOW_HEADROOM = 0.8                 # leave room for the AI's own system prompt and reply
MIN_TOKENS = 2_000
ARGV_MAX_CHARS_WINDOWS = 7_000        # cmd.exe caps a whole command line at 8191 chars
ARGV_MAX_CHARS_POSIX = 100_000        # Linux caps one argument at 128 KiB

OFFLINE_AIS = {"ollama", "claude_ollama", "codex_ollama", "local_openai", "lmstudio"}
# Online services whose models are known to have smaller windows.
SMALL_ONLINE_WINDOWS = {"groq": 128_000, "github_models": 128_000}


def online_tokens() -> int:
    """The user's setting for online AIs (GROUP_CONTEXT_TOKENS), read live."""
    raw = os.environ.get("GROUP_CONTEXT_TOKENS", "").strip().replace(",", "").replace("_", "")
    try:
        value = int(float(raw)) if raw else DEFAULT_ONLINE_TOKENS
    except ValueError:
        return DEFAULT_ONLINE_TOKENS
    return value if value >= MIN_TOKENS else DEFAULT_ONLINE_TOKENS


def offline_share() -> float:
    """Share of an offline model's window (GROUP_CONTEXT_OFFLINE_SHARE: 0.5 or 50)."""
    raw = os.environ.get("GROUP_CONTEXT_OFFLINE_SHARE", "").strip().rstrip("%")
    try:
        value = float(raw) if raw else DEFAULT_OFFLINE_SHARE
    except ValueError:
        return DEFAULT_OFFLINE_SHARE
    if value > 1:
        value /= 100
    return value if 0 < value <= 1 else DEFAULT_OFFLINE_SHARE


def is_offline(member: dict) -> bool:
    ai = (member.get("ai") or "").lower()
    return ai in OFFLINE_AIS or ai.endswith("_ollama")


def _env_window(ai: str) -> int:
    raw = os.environ.get(f"CONTEXT_WINDOW_{ai.upper()}", "").strip()
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


def window(member: dict) -> int:
    """Best guess at the member's context window, in tokens."""
    ai = (member.get("ai") or "").lower()
    model = (member.get("model") or "").lower().split(":")[0]
    explicit = _env_window(ai)
    if explicit:
        return explicit
    try:
        from helm.context_manager import _DEFAULT_WINDOWS
    except Exception:
        _DEFAULT_WINDOWS = {}
    if model and model in _DEFAULT_WINDOWS:
        return _DEFAULT_WINDOWS[model]
    if is_offline(member):
        return OFFLINE_DEFAULT_WINDOW
    if ai in SMALL_ONLINE_WINDOWS:
        return SMALL_ONLINE_WINDOWS[ai]
    return _DEFAULT_WINDOWS.get(ai) or online_tokens()


def prompt_via_stdin(member: dict) -> bool:
    """True when a long prompt reaches this member's CLI over stdin, not argv."""
    if member.get("ai") == "claude":
        return True
    import helm.state as _st
    info = _st.integrations.get(member.get("ai") or "") or {}
    return bool(info.get("stdin_prompt"))


def known_smaller_window(member: dict) -> int:
    """An online AI's window when it is known for sure (set by the user, or a
    service with a fixed small window), else 0: the setting is used as is."""
    ai = (member.get("ai") or "").lower()
    return _env_window(ai) or SMALL_ONLINE_WINDOWS.get(ai, 0)


def budget_tokens(member: dict) -> int:
    if is_offline(member):
        budget = int(window(member) * offline_share())
    else:
        budget = online_tokens()
        known = known_smaller_window(member)
        if known:
            budget = min(budget, int(known * WINDOW_HEADROOM))
    budget = max(budget, MIN_TOKENS)
    if not prompt_via_stdin(member):
        argv_max = ARGV_MAX_CHARS_WINDOWS if os.name == "nt" else ARGV_MAX_CHARS_POSIX
        budget = min(budget, argv_max // CHARS_PER_TOKEN)
    return budget
