"""helm/council/executor.py — Async council loop."""

import asyncio

import helm.state as _st
from helm.broadcast import broadcast
from helm.config import logger
from helm.history import ts
from .models import make_council_message, build_transcript
from . import moderator as _moderator
from . import runner as _runner


async def broadcast_council(event_type: str, data: dict):
    await broadcast({"type": event_type, **data})


def _find_participant(council: dict, ai_name: str) -> dict | None:
    for p in council["participants"]:
        if p["ai"] == ai_name:
            return p
    return None


async def run_council(council_id: str):
    """Main council loop. Launched as asyncio.create_task()."""
    try:
        council = _st.councils.get(council_id)
        if not council:
            logger.error("council %s not found in state", council_id)
            return

        council["status"] = "running"
        await broadcast_council("council_created", {"council": council})
    except Exception as exc:
        logger.error("council startup error for %s: %s", council_id, exc, exc_info=True)
        return

    try:
        n_participants = len(council["participants"])
        total_turns = 0  # each participant speaking once = 1 turn

        while council["rounds"] < council["max_rounds"]:
            if council["status"] == "stopped":
                await broadcast_council("council_stopped", {"council_id": council_id})
                return

            # Step 1: Moderator decides next speaker
            try:
                decision = await _moderator.get_next_turn(council)
            except Exception as exc:
                logger.error("council moderator error: %s", exc)
                council["status"] = "stopped"
                await broadcast_council("council_stopped", {"council_id": council_id})
                return

            if decision.get("prompt"):
                mod_msg = make_council_message("moderator", decision.get("prompt", ""))
                council["messages"].append(mod_msg)
            await broadcast_council("council_moderator", {
                "council_id": council_id,
                "next_participant": decision.get("next"),
                "moderator_prompt": decision.get("prompt"),
                "consensus": decision.get("consensus", False),
            })

            if decision.get("consensus"):
                council["status"] = "completed"
                council["consensus_summary"] = decision.get("summary", "")
                council["completed_at"] = ts()
                rounds_done = council["rounds"]
                max_rounds = council["max_rounds"]
                early = rounds_done < max_rounds
                notice = (
                    f"Consensus reached after {rounds_done} of {max_rounds} rounds — debate concluded early.\n\n"
                    if early else ""
                )
                council["early_consensus"] = early
                council["messages"].append(
                    make_council_message("system", notice + decision.get("summary", ""))
                )
                _archive_council(council)
                await broadcast_council("council_completed", {
                    "council": council,
                    "early_consensus": early,
                    "rounds_done": rounds_done,
                    "max_rounds": max_rounds,
                })
                return

            # Step 2: Participant streams response
            ai_name = decision.get("next")
            participant = _find_participant(council, ai_name)
            if not participant:
                participant = council["participants"][total_turns % n_participants]

            # Build context: rolling summary + last round verbatim (bounds prompt size)
            n_p = len(council["participants"])
            recent_msgs = [m for m in council["messages"]
                           if m["role"] in ("participant", "moderator")][-max(n_p * 2, 6):]
            recent_transcript = build_transcript(recent_msgs)

            chunks = []
            async for chunk in _runner.stream_council_response(
                session_id=participant["session_id"],
                topic=council["topic"],
                transcript=recent_transcript,
                moderator_prompt=decision.get("prompt", "Share your thoughts."),
                participant_name=participant["name"],
                context_summary=council.get("context_summary", ""),
            ):
                chunks.append(chunk)
                await broadcast_council("council_stream", {
                    "council_id": council_id,
                    "participant_ai": participant["ai"],
                    "chunk": chunk,
                })

            full_response = "".join(chunks)
            msg = make_council_message("participant", full_response, participant)
            council["messages"].append(msg)
            total_turns += 1

            await broadcast_council("council_message", {
                "council_id": council_id,
                "message": msg,
            })

            # Round completes when every participant has spoken once
            if total_turns % n_participants == 0:
                round_num = council["rounds"] + 1
                round_msgs = [m for m in council["messages"]
                              if m["role"] == "participant"][-n_participants:]

                try:
                    judgment = await _moderator.judge_round(council, round_msgs)
                except Exception as exc:
                    logger.warning("council judge error round %d: %s", round_num, exc)
                    judgment = {"winner": council["participants"][0]["ai"], "reasoning": "Judging failed."}

                winner_ai = judgment.get("winner", "")
                reasoning = judgment.get("reasoning", "")
                winner_p = _find_participant(council, winner_ai) or council["participants"][0]

                if winner_ai in council["scores"]:
                    council["scores"][winner_ai] += 1

                result = {
                    "round": round_num,
                    "winner_ai": winner_p["ai"],
                    "winner_name": winner_p["name"],
                    "reasoning": reasoning,
                }
                council["round_results"].append(result)
                verdict_text = f"Round {round_num} winner: {winner_p['name']} — {reasoning}"
                council["messages"].append(make_council_message("system", verdict_text))

                council["rounds"] += 1

                # Update rolling summary so future prompts stay bounded
                try:
                    council["context_summary"] = await _moderator.update_context_summary(
                        council, round_msgs
                    )
                except Exception as exc:
                    logger.warning("council summary update error round %d: %s", round_num, exc)

                await broadcast_council("council_round_result", {
                    "council_id": council_id,
                    "result": result,
                    "scores": council["scores"],
                })

        # Exhausted max rounds — declare overall winner
        if council["status"] == "running":
            council["status"] = "stopped"
            try:
                final = await _moderator.declare_overall_winner(council)
                winner_ai = final.get("winner", "")
                verdict = final.get("verdict", "")
                winner_p = _find_participant(council, winner_ai) or council["participants"][0]
                council["overall_winner"] = {
                    "ai": winner_p["ai"],
                    "name": winner_p["name"],
                    "score": council["scores"].get(winner_p["ai"], 0),
                    "total_rounds": council["rounds"],
                    "verdict": verdict,
                }
                council["messages"].append(
                    make_council_message("system", f"FINAL VERDICT: {winner_p['name']} wins. {verdict}")
                )
            except Exception as exc:
                logger.warning("council overall winner error: %s", exc)
                if council["scores"]:
                    winner_ai = max(council["scores"], key=lambda k: council["scores"][k])
                    winner_p = _find_participant(council, winner_ai) or council["participants"][0]
                    council["overall_winner"] = {
                        "ai": winner_p["ai"], "name": winner_p["name"],
                        "score": council["scores"].get(winner_ai, 0),
                        "total_rounds": council["rounds"], "verdict": "",
                    }
            await broadcast_council("council_stopped", {"council_id": council_id, "council": council})

    except asyncio.CancelledError:
        council["status"] = "stopped"
        await broadcast_council("council_stopped", {"council_id": council_id})
    except Exception as exc:
        logger.error("council executor error: %s", exc, exc_info=True)
        council["status"] = "stopped"
        await broadcast_council("council_stopped", {"council_id": council_id})


def _archive_council(council: dict):
    """Move completed council to history, keeping last 10."""
    _st.council_history.append(council)
    if len(_st.council_history) > 10:
        _st.council_history.pop(0)
