"""Group chats: how much each member may see (helm/groupchat_context/budget.py)."""
import helm.state as _st
from helm.groupchat_context import budget


def _m(ai, model=None):
    return {"id": "m", "ai": ai, "model": model}


def test_online_ais_get_at_least_200k(env, monkeypatch):
    _st.integrations["codex"] = {"stdin_prompt": True}
    _st.integrations["mystery"] = {"stdin_prompt": True}
    assert budget.budget_tokens(_m("claude")) >= 200_000
    assert budget.budget_tokens(_m("codex")) >= 200_000
    assert budget.budget_tokens(_m("mystery")) >= 200_000   # unknown online AI: assume 1M window
    monkeypatch.setattr(budget, "ONLINE_TOKENS", 400_000)
    assert budget.budget_tokens(_m("claude")) == 400_000


def test_floor_cant_be_configured_lower():
    import importlib
    import os
    old = os.environ.get("GROUP_CONTEXT_TOKENS")
    os.environ["GROUP_CONTEXT_TOKENS"] = "50000"
    try:
        assert importlib.reload(budget).ONLINE_TOKENS == 200_000
    finally:
        if old is None:
            os.environ.pop("GROUP_CONTEXT_TOKENS")
        else:
            os.environ["GROUP_CONTEXT_TOKENS"] = old
        importlib.reload(budget)


def test_offline_models_get_a_share_of_their_window(env, monkeypatch):
    _st.integrations["claude_ollama"] = {"stdin_prompt": True}
    _st.integrations["ollama"] = {"stdin_prompt": True}
    assert budget.is_offline(_m("claude_ollama")) and budget.is_offline(_m("ollama"))
    small = budget.budget_tokens(_m("claude_ollama"))
    assert small == int(budget.OFFLINE_DEFAULT_WINDOW * budget.OFFLINE_SHARE)
    # A known model's window is used; an env override wins over everything.
    assert budget.budget_tokens(_m("ollama", "mistral:7b")) == 16_000
    monkeypatch.setenv("CONTEXT_WINDOW_OLLAMA", "8000")
    assert budget.budget_tokens(_m("ollama", "mistral:7b")) == 4000


def test_online_service_with_a_small_window_stays_inside_it(env):
    _st.integrations["groq"] = {"stdin_prompt": True}
    assert budget.budget_tokens(_m("groq")) == int(128_000 * budget.WINDOW_HEADROOM)


def test_command_line_prompts_are_capped_by_the_os(env, monkeypatch):
    _st.integrations["argvai"] = {"stdin_prompt": False}
    monkeypatch.setattr(budget, "ARGV_MAX_CHARS_POSIX", 8000)
    monkeypatch.setattr(budget, "ARGV_MAX_CHARS_WINDOWS", 8000)
    assert budget.budget_tokens(_m("argvai")) == 2000
