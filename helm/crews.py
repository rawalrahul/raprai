"""
helm/crews.py — Ready-made AI crews: a group chat with a job for each member.

A crew is a group chat where every AI has a role, for example "Writer" and
"Reviewer". The role is added to that member's prompt, so it knows what to do
in the room. Pick a crew, choose which open AI sessions to use, and RAPR
assigns each role to one of them (preferring the AI a role suits best).
"""

from __future__ import annotations

from typing import Optional

CREWS = [
    {
        "id": "code-review",
        "name": "Code review",
        "about": "Review a change before it's merged: one writes or explains the code, one reviews it, one checks the tests.",
        "roles": [
            {"name": "Author", "prefers": ["claude", "codex"],
             "prompt": "You explain and write the code change. Keep changes small and say what you changed."},
            {"name": "Reviewer", "prefers": ["codex", "claude", "gemini"],
             "prompt": "You review the change for bugs, risky edges and style. Point to exact lines. Don't rewrite everything."},
            {"name": "Tester", "prefers": ["gemini", "ollama", "claude"],
             "prompt": "You think about tests: what's covered, what's missing, and the exact test to add."},
        ],
    },
    {
        "id": "research",
        "name": "Research",
        "about": "Look into a question from several angles and agree on an answer.",
        "roles": [
            {"name": "Researcher", "prefers": ["gemini", "claude"],
             "prompt": "You gather the facts and the main options. Say what you're sure of and what you're not."},
            {"name": "Skeptic", "prefers": ["claude", "codex"],
             "prompt": "You challenge the claims: what could be wrong, what's missing, what would change the answer."},
            {"name": "Summariser", "prefers": ["ollama", "gemini"],
             "prompt": "You wait for the others, then give a short summary with a recommendation and its main risk."},
        ],
    },
    {
        "id": "launch",
        "name": "Launch",
        "about": "Get a product or feature ready to ship: the copy, the plan and the risks.",
        "roles": [
            {"name": "Copywriter", "prefers": ["claude", "gemini"],
             "prompt": "You write the announcement and the short description in plain, friendly language."},
            {"name": "Planner", "prefers": ["codex", "claude"],
             "prompt": "You turn the goal into a checklist with owners and dates."},
            {"name": "Risk checker", "prefers": ["gemini", "ollama"],
             "prompt": "You list what could go wrong at launch and how to notice it early."},
        ],
    },
    {
        "id": "debate-to-decision",
        "name": "Debate to decision",
        "about": "Two AIs argue for and against a choice; a third decides.",
        "roles": [
            {"name": "For", "prefers": ["claude", "gemini"],
             "prompt": "You argue for the option the user is considering, with the strongest honest case."},
            {"name": "Against", "prefers": ["codex", "ollama", "gemini"],
             "prompt": "You argue against it, with the strongest honest case."},
            {"name": "Judge", "prefers": ["claude", "codex"],
             "prompt": "You read both sides and give a decision in three sentences: the choice, why, and what would change your mind."},
        ],
    },
]


def get(crew_id: str) -> Optional[dict]:
    return next((c for c in CREWS if c["id"] == crew_id), None)


def assign(crew: dict, sessions: list[dict]) -> list[tuple[dict, dict]]:
    """Give each role a different session, preferring its suited AI.

    sessions: [{"id", "ai", ...}] (AI sessions only). Raises ValueError if
    there are fewer sessions than roles.
    """
    roles = crew["roles"]
    if len(sessions) < len(roles):
        raise ValueError(f"the {crew['name']} crew needs {len(roles)} AI sessions, you picked {len(sessions)}")
    free = list(sessions)
    pairs = []
    for role in roles:
        best = None
        for pref in role["prefers"]:
            best = next((s for s in free if s.get("ai") == pref), None)
            if best:
                break
        if best is None:
            best = free[0]
        free.remove(best)
        pairs.append((role, best))
    return pairs


def public(crew: dict) -> dict:
    return {"id": crew["id"], "name": crew["name"], "about": crew["about"],
            "roles": [{"name": r["name"], "prefers": r["prefers"]} for r in crew["roles"]]}
