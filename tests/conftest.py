"""Fixtures shared by the tests in this folder."""
from core_harness import rapr  # noqa: F401  (a RAPR to send messages through)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _mcp_usage_in_tmp(tmp_path, monkeypatch):
    """AIs run in tests count toward a throwaway usage file, not ~/.config/rapr (helm/mcp_usage.py)."""
    monkeypatch.setenv("RAPR_MCP_USAGE_FILE", str(tmp_path / "mcp-usage.json"))
