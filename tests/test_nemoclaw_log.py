"""NemoClaw's debug log stays small.

Both NemoClaw modules wrote every WSL command and its output to one file at
DEBUG level, through two handlers, with no limit.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_one_capped_log_for_both_modules(tmp_path, monkeypatch):
    monkeypatch.setenv("RAPR_DATA_DIR", str(tmp_path))
    parent = logging.getLogger("nemoclaw")
    for h in list(parent.handlers):
        parent.removeHandler(h)
    from helm.nemoclaw_log import nemoclaw_logger
    bridge, integration = nemoclaw_logger("bridge"), nemoclaw_logger("integration")
    assert len(parent.handlers) == 1
    for _ in range(3000):
        bridge.debug("x" * 1000)
        integration.debug("y" * 1000)
    parent.handlers[0].close()
    files = sorted(p.name for p in tmp_path.glob("nemoclaw_debug.log*"))
    assert files == ["nemoclaw_debug.log", "nemoclaw_debug.log.1"]
    assert all(p.stat().st_size <= 1_100_000 for p in tmp_path.glob("nemoclaw_debug.log*"))
    for h in list(parent.handlers):
        parent.removeHandler(h)
