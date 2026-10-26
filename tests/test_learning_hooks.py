"""What the learning system records after a task (helm/learning/hooks.py)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import helm.learning.analyzer as analyzer
import helm.learning.cross_ai as cross_ai
from helm.learning.hooks import task_finished


def _finish(monkeypatch, sess, output_ok=True):
    queued, compared = [], []
    monkeypatch.setattr(analyzer, "enqueue", queued.append)
    monkeypatch.setattr(analyzer, "drain_queue", lambda: asyncio.sleep(0))
    monkeypatch.setattr(cross_ai, "record_task", compared.append)

    async def run():
        task_finished(None, {"task_type": "code", "task_fingerprint": "fp"}, text="fix it",
                      ai="claude", sess=sess, sid="s1", output="done", success=output_ok,
                      elapsed=2.0, tok_in=None, tok_out=None)
    asyncio.run(run())
    return queued, compared


def test_a_task_is_queued_for_analysis_and_comparison(monkeypatch):
    queued, compared = _finish(monkeypatch, {"model": "opus"}, output_ok=False)
    assert queued == compared
    assert queued[0]["task_type"] == "code" and queued[0]["ai_model_version"] == "opus"
    assert queued[0]["success"] is False and queued[0]["success_confidence"] == 0.3


def test_a_background_look_teaches_nothing(monkeypatch):
    queued, compared = _finish(monkeypatch, {"read_only": True})
    assert queued == [] and compared == []
