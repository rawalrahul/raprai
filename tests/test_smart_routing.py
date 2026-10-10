"""Auto: pick the cheapest capable AI, respecting budgets and the user's choice."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from helm import smart_routing as sr

INSTALLED = ["claude", "codex", "gemini", "ollama"]


def test_short_question_goes_to_free_local_model():
    d = sr.decide("what time is it in Tokyo?", INSTALLED)
    assert d.ai == "ollama" and "free" in d.reason
    assert d.fallbacks[0] == "gemini"


def test_multi_step_coding_goes_to_strongest():
    text = ("refactor the auth module and then update every test that uses it, "
            "also fix the failing migration")
    d = sr.decide(text, INSTALLED)
    assert d.ai == "claude"
    assert sr.is_hard(d.task_type, d.complexity)


def test_over_budget_ai_is_skipped():
    d = sr.decide("what time is it in Tokyo?", INSTALLED, allowed=lambda ai: ai != "ollama")
    assert d.ai == "gemini"
    assert "ollama" not in d.fallbacks


def test_user_choice_wins_when_usable():
    d = sr.decide("what time is it?", INSTALLED, preferred="codex")
    assert d.ai == "codex" and d.reason == "you chose codex"


def test_user_choice_ignored_when_over_budget():
    d = sr.decide("what time is it?", INSTALLED, preferred="codex",
                  allowed=lambda ai: ai != "codex")
    assert d.ai != "codex"


def test_nothing_available_is_explained():
    d = sr.decide("hi", [], allowed=lambda ai: True)
    assert d.ai is None and "no AI" in d.reason
    d = sr.decide("hi", ["claude"], allowed=lambda ai: False)
    assert d.ai is None


def test_unknown_ai_is_used_only_last():
    d = sr.decide("what time is it?", ["mystery", "gemini"])
    assert d.ai == "gemini"
    assert d.fallbacks == ["mystery"]


def test_duplicates_are_ignored():
    d = sr.decide("what time is it?", ["ollama", "ollama", "gemini"])
    assert d.ai == "ollama" and d.fallbacks == ["gemini"]
