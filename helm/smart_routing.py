"""
helm/smart_routing.py — "Auto": pick the AI for a task.

You don't have to choose. RAPR classifies the task and picks the cheapest AI
that can handle it, skipping any AI that is over its budget or not installed:

  • easy tasks (short, chat, questions, summaries)  → local/free first
    (Ollama on your PC, then the cheaper cloud AIs)
  • hard tasks (multi-step, pipelines, coding and computer use) → the strongest
    coding AIs first (Claude Code, then Codex, then the others)

The decision comes with a reason ("short question → Ollama, free"), and an
ordered fallback list so a failed or blocked AI can be replaced automatically.

This module decides only. It doesn't run anything, so it can be tested with
fake budgets and fake availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from helm.learning.classifier import classify_task, complexity_score

# Relative cost tiers: lower is cheaper. Unknown AIs count as "premium" so they
# are used only when nothing cheaper is available.
COST_TIER = {
    "ollama": 0,        # runs on the user's machine: free
    "gemini": 1,        # free tier / low cost API
    "groq": 1,
    "openrouter": 2,
    "github_models": 2,
    "codex": 3,
    "openai": 3,
    "claude": 4,
    "cursor": 4,
}
CAPABILITY_TIER = {        # higher is more capable for hard coding work
    "claude": 4, "codex": 3, "cursor": 3, "gemini": 3, "openai": 3,
    "openrouter": 2, "groq": 2, "github_models": 2, "ollama": 1,
}
HARD_TYPES = {"computer_use", "agent_build"}   # plus any "code.*" type, see is_hard
HARD_COMPLEXITY = 4


@dataclass
class Decision:
    ai: Optional[str]
    reason: str
    task_type: str
    complexity: int
    fallbacks: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ai": self.ai, "reason": self.reason, "task_type": self.task_type,
                "complexity": self.complexity, "fallbacks": self.fallbacks}


def is_hard(task_type: str, complexity: int) -> bool:
    """Coding, computer use and agent building are hard; so is anything long or multi-step."""
    return (task_type in HARD_TYPES or task_type.startswith("code.")
            or complexity >= HARD_COMPLEXITY)


def _ranked(ais: Iterable[str], hard: bool) -> list[str]:
    if hard:
        return sorted(ais, key=lambda a: (-CAPABILITY_TIER.get(a, 2), COST_TIER.get(a, 5), a))
    return sorted(ais, key=lambda a: (COST_TIER.get(a, 5), -CAPABILITY_TIER.get(a, 2), a))


def decide(text: str, available: Iterable[str],
           allowed: Callable[[str], bool] = lambda ai: True,
           preferred: Optional[str] = None) -> Decision:
    """Choose an AI for `text`.

    available: AIs installed/connected on this machine.
    allowed:   budget check per AI (False = over cap or blocked).
    preferred: the user's pick, if they set one; it wins when usable.
    """
    task_type = classify_task(text)
    complexity = complexity_score(text)
    hard = is_hard(task_type, complexity)
    installed = [a for a in dict.fromkeys(available) if a]

    if preferred and preferred in installed and allowed(preferred):
        return Decision(preferred, f"you chose {preferred}", task_type, complexity,
                        [a for a in _ranked(installed, hard) if a != preferred and allowed(a)])

    usable = [a for a in installed if allowed(a)]
    if not usable:
        blocked = ", ".join(installed) or "none installed"
        return Decision(None, f"no AI can take this right now ({blocked})", task_type, complexity)

    order = _ranked(usable, hard)
    chosen = order[0]
    if hard:
        why = "coding or multi-step task" if task_type.startswith("code.") or complexity >= HARD_COMPLEXITY else "complex task"
    else:
        why = "short or simple task"
    cost = "free" if COST_TIER.get(chosen, 5) == 0 else "uses your plan or API budget"
    reason = f"{why} → {chosen} ({cost})"
    return Decision(chosen, reason, task_type, complexity, order[1:])


def available_from_state() -> list[str]:
    """AIs that are installed and not stopped, from the live app state."""
    import helm.state as _st
    installed = {s["ai"] for s in _st.sessions.values() if s.get("ai") and s.get("status") != "stopped"}
    installed.update(k for k in _st.integrations.keys())
    return sorted(installed)


def allowed_from_budget(ai: str) -> bool:
    try:
        from helm.web_routes.usage_routes import check_budget
        return bool(check_budget(ai).get("allowed", True))
    except Exception:
        return True
