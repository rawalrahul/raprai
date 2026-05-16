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
    council = _st.councils.get(council_id)
    if not council:
        return

    council["status"] = "running"
    await broadcast_council("council_created", {"council": council})

    try:
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
                council["messages"].append(
                    make_council_message("system", decision.get("summary", ""))
                )
                _archive_council(council)
                await broadcast_council("council_completed", {"council": council})
                return

            # Step 2: Participant streams response
            ai_name = decision.get("next")
            participant = _find_participant(council, ai_name)
            if not participant:
                # fallback: pick first participant
                participant = council["participants"][0]

            chunks = []
            async for chunk in _runner.stream_council_response(
                session_id=participant["session_id"],
                topic=council["topic"],
                transcript=build_transcript(council["messages"]),
                moderator_prompt=decision.get("prompt", "Share your thoughts."),
                participant_name=participant["name"],
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
            council["rounds"] += 1
            await broadcast_council("council_message", {
                "council_id": council_id,
                "message": msg,
            })

        # Exhausted max rounds
        if council["status"] == "running":
            council["status"] = "stopped"
            await broadcast_council("council_stopped", {"council_id": council_id})

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
