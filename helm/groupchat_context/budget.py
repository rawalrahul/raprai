"""
How much of the group chat each member may see, in estimated tokens.

  • Online AIs (Claude, Codex, Gemini, Copilot…): most have 1M-token windows,
    so a member sees up to GROUP_CONTEXT_TOKENS (default and floor 200K) —
    never more than WINDOW_HEADROOM of a window known to be smaller.
  • Offline models (Ollama, Claude/Codex on Ollama, LM Studio…): their windows
    are small, so they get OFFLINE_SHARE of the window.
  • A prompt that must go on the command line (not stdin) is also capped by
    the OS command-line limit.

The budget is a ceiling: a short chat is sent as it is.
"""

from __future__ import annotations

import os

from helm.groupchat_context.text import CHARS_PER_TOKEN

ONLINE_MIN_TOKENS = 200_000
ONLINE_TOKENS = max(int(os.environ.get("GROUP_CONTEXT_TOKENS", "200000")), ONLINE_MIN_TOKENS)
OFFLINE_SHARE = float(os.environ.get("GROUP_CONTEXT_OFFLINE_SHARE", "0.5"))
OFFLINE_DEFAULT_WINDOW = 32_000       # what RAPR asks local models to be run with
UNKNOWN_ONLINE_WINDOW = 1_000_000
WINDOW_HEADROOM = 0.8                 # leave room for the AI's own system prompt and reply
MIN_TOKENS = 2_000
ARGV_MAX_CHARS_WINDOWS = 7_000        # cmd.exe caps a whole command line at 8191 chars
ARGV_MAX_CHARS_POSIX = 100_000        # Linux caps one argument at 128 KiB

OFFLINE_AIS = {"ollama", "claude_ollama", "codex_ollama", "local_openai", "lmstudio"}
# Online services whose models are known to have smaller windows.
SMALL_ONLINE_WINDOWS = {"groq": 128_000, "github_models": 128_000}


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
    return _DEFAULT_WINDOWS.get(ai) or UNKNOWN_ONLINE_WINDOW


def prompt_via_stdin(member: dict) -> bool:
    """True when a long prompt reaches this member's CLI over stdin, not argv."""
    if member.get("ai") == "claude":
        return True
    import helm.state as _st
    info = _st.integrations.get(member.get("ai") or "") or {}
    return bool(info.get("stdin_prompt"))


def budget_tokens(member: dict) -> int:
    win = window(member)
    if is_offline(member):
        budget = int(win * OFFLINE_SHARE)
    else:
        budget = min(ONLINE_TOKENS, int(win * WINDOW_HEADROOM))
    budget = max(budget, MIN_TOKENS)
    if not prompt_via_stdin(member):
        argv_max = ARGV_MAX_CHARS_WINDOWS if os.name == "nt" else ARGV_MAX_CHARS_POSIX
        budget = min(budget, argv_max // CHARS_PER_TOKEN)
    return budget
