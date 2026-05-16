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


async def judge_round(council: dict, round_messages: list) -> dict:
    """Ask moderator to judge the completed round. Returns {winner_ai, reasoning}."""
    from . import runner as _runner

    participants_str = ", ".join(
        f"{p['name']} ({p['ai']})" for p in council["participants"]
    )
    round_transcript = "\n\n".join(
        f"[{m['participant_name']} ({m['participant_ai']})]: {m['content']}"
        for m in round_messages if m["role"] == "participant"
    )

    prompt = f"""You are the moderator of an AI council debate.

Topic: {council['topic']}
Participants: {participants_str}

This round's arguments:
{round_transcript}

Judge this round. Evaluate each participant's argument and declare the winner.

Your judgment must:
1. Briefly note what each participant argued
2. Explain what made the winner's argument stronger (specific claims, evidence, logic)
3. Note any weaknesses in the losing arguments

Reply ONLY in this JSON format:
{{"winner": "<ai_name>", "reasoning": "<3-5 sentence detailed judgment explaining what each participant argued, why the winner's case was stronger, and what the others missed or got wrong>"}}"""

    response = await _runner.run_moderator(council["moderator_session_id"], prompt)

    try:
        return json.loads(_extract_json(response))
    except Exception:
        return {"winner": council["participants"][0]["ai"], "reasoning": "Round judged by default."}


async def declare_overall_winner(council: dict) -> dict:
    """Ask moderator to declare the overall winner with full reasoning."""
    from . import runner as _runner

    participants_str = ", ".join(
        f"{p['name']} ({p['ai']})" for p in council["participants"]
    )
    scores_str = ", ".join(
        f"{p['name']}: {council['scores'].get(p['ai'], 0)} round win(s)"
        for p in council["participants"]
    )
    round_summaries = "\n".join(
        f"Round {r['round']}: {r['winner_name']} won — {r['reasoning']}"
        for r in council.get("round_results", [])
    )

    prompt = f"""You are the moderator of an AI council debate that has just concluded.

Topic: {council['topic']}
Participants: {participants_str}
Final scores: {scores_str}

Round-by-round results:
{round_summaries}

Declare the overall winner and provide a comprehensive final judgment.

Your verdict must:
1. State who won and by what margin
2. Explain what argumentation style, specific points, or reasoning gave them the edge
3. Acknowledge the strongest counter-arguments from the losing side
4. State what the debate ultimately resolved or left open

Reply ONLY in this JSON format:
{{"winner": "<ai_name>", "verdict": "<comprehensive 4-6 sentence final verdict covering the above points>"}}"""

    response = await _runner.run_moderator(council["moderator_session_id"], prompt)

    try:
        data = json.loads(_extract_json(response))
        return {"winner": data.get("winner", ""), "verdict": data.get("verdict", data.get("reasoning", ""))}
    except Exception:
        scores = council.get("scores", {})
        best = max(scores, key=lambda k: scores[k]) if scores else ""
        return {"winner": best, "verdict": "Overall winner declared by score."}


async def update_context_summary(council: dict, round_messages: list) -> str:
    """After a round completes, ask moderator to update the rolling debate summary."""
    from . import runner as _runner

    participants_str = ", ".join(
        f"{p['name']} ({p['ai']})" for p in council["participants"]
    )
    round_transcript = "\n\n".join(
        f"[{m['participant_name']}]: {m['content']}"
        for m in round_messages if m["role"] == "participant"
    )
    existing = council.get("context_summary", "")
    prior_block = f"Prior summary:\n{existing}\n\n" if existing else ""

    prompt = f"""You are moderating an AI council debate.

Topic: {council['topic']}
Participants: {participants_str}

{prior_block}This round's arguments:
{round_transcript}

Write a concise updated summary (4-6 sentences) covering ALL key positions, evidence, and points of contention raised across all rounds so far.
Write ONLY the summary text — no labels, no JSON."""

    response = await _runner.run_moderator(council["moderator_session_id"], prompt)
    return response.strip() or existing


async def get_next_turn(council: dict) -> dict:
    """Ask moderator AI who speaks next. Returns decision dict."""
    from . import runner as _runner

    participants_str = ", ".join(
        f"{p['name']} ({p['ai']})" for p in council["participants"]
    )

    # Use rolling summary + last round verbatim to keep prompt bounded
    context_summary = council.get("context_summary", "")
    n = len(council["participants"])
    recent_msgs = [m for m in council["messages"]
                   if m["role"] in ("participant", "moderator")][-max(n * 2, 6):]
    recent_transcript = build_transcript(recent_msgs)

    summary_block = f"Debate summary so far:\n{context_summary}\n\n" if context_summary else ""

    prompt = f"""You are the moderator of an AI council debate.

Topic: {council['topic']}
Participants: {participants_str}

{summary_block}Most recent exchanges:
{recent_transcript}

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
