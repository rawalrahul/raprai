"""helm/council/moderator.py — Moderator AI prompt builders + JSON response parsing."""

import json
import re

from helm.config import logger
from .models import build_transcript


def _extract_json(text: str) -> str:
    """Extract first JSON object from text."""
    match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text


async def get_next_turn(council: dict) -> dict:
    """Ask moderator AI who speaks next. Returns decision dict."""
    from . import runner as _runner

    participants_str = ", ".join(
        f"{p['name']} ({p['ai']})" for p in council["participants"]
    )
    transcript = build_transcript(council["messages"])

    prompt = f"""You are the moderator of an AI council debate.

Topic: {council['topic']}
Participants: {participants_str}

Full conversation so far:
{transcript}

Your job:
1. Pick which participant should speak next.
2. Give them a focused question or angle to address (1-2 sentences).
3. Decide if consensus has been reached (participants broadly agree, all key angles covered).

Reply ONLY in this JSON format:
{{"next": "<ai_name>", "prompt": "<question for them>", "consensus": false, "summary": null}}

If consensus reached:
{{"next": null, "prompt": null, "consensus": true, "summary": "<2-3 paragraph synthesis>"}}"""

    response = await _runner.run_moderator(council["moderator_session_id"], prompt)

    try:
        return json.loads(_extract_json(response))
    except Exception:
        # Fallback: round-robin, no consensus
        used = [m["participant_ai"] for m in council["messages"] if m["role"] == "participant"]
        candidates = [p for p in council["participants"] if p["ai"] not in used[-1:]]
        next_p = (candidates or council["participants"])[0]
        return {
            "next": next_p["ai"],
            "prompt": "Share your perspective on the topic.",
            "consensus": False,
            "summary": None,
        }
