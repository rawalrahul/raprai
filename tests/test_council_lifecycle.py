"""Council status: one rule for ending it, and why it stopped.

"stopped" meant the person stopped it, it errored, or it ran out of rounds, with no
way to tell. The stop endpoint could turn a completed council into "stopped", a late
consensus could overwrite the person's stop, and a stop that came before the loop
started was overwritten with "running".
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.state as _st
from helm.council import executor as ex


def test_end_council_only_ends_it_once():
    c = {"status": "running"}
    assert ex.end_council(c, "stopped", "user")
    assert (c["status"], c["stop_reason"]) == ("stopped", "user")
    assert not ex.end_council(c, "completed", "")      # late consensus
    assert c["status"] == "stopped"

    done = {"status": "completed"}
    assert not ex.end_council(done, "stopped", "user")
    assert done["status"] == "completed" and "stop_reason" not in done


def test_stop_before_start_is_kept(monkeypatch):
    async def quiet(*a, **k):
        return None
    monkeypatch.setattr(ex, "broadcast_council", quiet)
    c = {"id": "c-early", "status": "pending"}
    monkeypatch.setitem(_st.councils, "c-early", c)
    assert ex.end_council(c, "stopped", "user")
    asyncio.run(ex.run_council("c-early"))
    assert c["status"] == "stopped"
