"""
helm/ai_runner/claude.py — Claude-specific logic.

Covers: build_claude_cmd and related utilities.
"""


def build_claude_cmd(prompt: str, has_history: bool,
                     model: str | None = None) -> list[str]:
    """Build the command-line arguments to invoke the Claude CLI."""
    cmd = ["claude"]
    if model:
        cmd.extend(["--model", model])
    if has_history:
        cmd.append("--continue")
    cmd.extend(["-p", prompt])
    return cmd


_build_claude_cmd = build_claude_cmd  # legacy alias
