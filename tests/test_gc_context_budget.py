"""Group chats: how much each member may see (helm/groupchat_context/budget.py)."""
import helm.state as _st
from helm.groupchat_context import budget


def _m(ai, model=None):
    return {"id": "m", "ai": ai, "model": model}


def test_online_ais_default_to_200k(env, monkeypatch):
    monkeypatch.delenv("GROUP_CONTEXT_TOKENS", raising=False)
    _st.integrations["codex"] = {"stdin_prompt": True}
    _st.integrations["mystery"] = {"stdin_prompt": True}
    for ai in ("claude", "codex", "mystery"):
        assert budget.budget_tokens(_m(ai)) == 200_000


def test_the_setting_is_used_as_set_and_read_live(env, monkeypatch):
    _st.integrations["codex"] = {"stdin_prompt": True}
    monkeypatch.setenv("GROUP_CONTEXT_TOKENS", "1000000")
    assert budget.budget_tokens(_m("claude")) == 1_000_000      # not cut to 80% of a 1M guess
    assert budget.budget_tokens(_m("codex")) == 1_000_000
    monkeypatch.setenv("GROUP_CONTEXT_TOKENS", "2,500,000")        # windows keep growing
    assert budget.budget_tokens(_m("claude")) == 2_500_000
    monkeypatch.setenv("GROUP_CONTEXT_TOKENS", "120000")           # lower is the user's call too
    assert budget.budget_tokens(_m("claude")) == 120_000
    for bad in ("lots", "-5", "10"):                               # nonsense → the default
        monkeypatch.setenv("GROUP_CONTEXT_TOKENS", bad)
        assert budget.budget_tokens(_m("claude")) == 200_000


def test_a_window_the_user_set_for_an_ai_caps_the_setting(env, monkeypatch):
    monkeypatch.setenv("GROUP_CONTEXT_TOKENS", "1000000")
    monkeypatch.setenv("CONTEXT_WINDOW_CLAUDE", "500000")
    assert budget.budget_tokens(_m("claude")) == int(500_000 * budget.WINDOW_HEADROOM)
    monkeypatch.setenv("CONTEXT_WINDOW_CLAUDE", "4000000")
    assert budget.budget_tokens(_m("claude")) == 1_000_000


def test_offline_models_get_a_share_of_their_window(env, monkeypatch):
    _st.integrations["claude_ollama"] = {"stdin_prompt": True}
    _st.integrations["ollama"] = {"stdin_prompt": True}
    assert budget.is_offline(_m("claude_ollama")) and budget.is_offline(_m("ollama"))
    small = budget.budget_tokens(_m("claude_ollama"))
    assert small == int(budget.OFFLINE_DEFAULT_WINDOW * 0.5)
    monkeypatch.setenv("GROUP_CONTEXT_TOKENS", "1000000")           # online setting: no effect here
    assert budget.budget_tokens(_m("claude_ollama")) == small
    monkeypatch.setenv("GROUP_CONTEXT_OFFLINE_SHARE", "25")         # percent, as Settings saves it
    assert budget.budget_tokens(_m("claude_ollama")) == 8_000
    monkeypatch.setenv("GROUP_CONTEXT_OFFLINE_SHARE", "0.75")
    assert budget.budget_tokens(_m("claude_ollama")) == 24_000
    monkeypatch.delenv("GROUP_CONTEXT_OFFLINE_SHARE")
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
