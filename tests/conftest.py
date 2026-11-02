"""Fixtures shared by the tests in this folder."""
from core_harness import rapr  # noqa: F401  (a RAPR to send messages through)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _mcp_usage_in_tmp(tmp_path, monkeypatch):
    """AIs run in tests count toward a throwaway usage file, not ~/.config/rapr (helm/mcp_usage.py)."""
    monkeypatch.setenv("RAPR_MCP_USAGE_FILE", str(tmp_path / "mcp-usage.json"))
    monkeypatch.setenv("RAPR_USAGE_READERS", "0")   # no asking real AI accounts for their usage
    monkeypatch.setenv("RAPR_CONFIG_DIR", str(tmp_path / "rapr-config"))   # no real RAPR Bridge
    # Run from a VS Code terminal or not, the tests see the same: not under VS Code.
    for var in ("TERM_PROGRAM", "CLAUDE_CODE_ENTRYPOINT", "VSCODE_PID", "VSCODE_IPC_HOOK",
                "VSCODE_IPC_HOOK_CLI", "VSCODE_AGENT_FOLDER", "VSCODE_CWD"):
        monkeypatch.delenv(var, raising=False)
