"""
helm/ai_runner/claude.py — Claude-specific logic.

Covers: build_claude_cmd, parse_claude_json_output, and related utilities.
"""

import json
import re


def build_claude_cmd(prompt: str, has_history: bool,
                     model: str | None = None,
                     auto_approve: bool = False) -> list[str]:
    """Build the command-line arguments to invoke the Claude CLI.

    Uses --output-format json to get structured output including token counts.
    auto_approve: if True, adds --dangerously-skip-permissions so Claude
                  won't pause for file/command approvals (required for
                  non-interactive pipeline steps and background sessions).
    """
    cmd = ["claude"]
    if model:
        cmd.extend(["--model", model])
    if has_history:
        cmd.append("--continue")
    if auto_approve:
        cmd.append("--dangerously-skip-permissions")
    cmd.extend(["--output-format", "json", "-p", prompt])
    return cmd


def parse_claude_json_output(raw: str) -> dict:
    """Parse Claude CLI JSON output to extract text and token counts.

    Claude CLI with --output-format json returns:
    {
      "type": "result",
      "result": "the text response",
      "cost_usd": 0.012,
      "duration_ms": 3500,
      "is_error": false,
      "num_turns": 1,
      "session_id": "...",
      "total_cost_usd": 0.05,
      "usage": {
        "input_tokens": 1234,
        "output_tokens": 567
      }
    }

    Returns dict with: text, input_tokens, output_tokens, cost_usd, is_json
    """
    if not raw or not raw.strip():
        return {"text": raw or "(no output)", "input_tokens": None,
                "output_tokens": None, "cost_usd": None, "is_json": False}

    text = raw.strip()

    # Try parsing as JSON
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON — might be plain text (older CLI version or error)
        # Try to find a JSON object containing "result"
        m = re.search(r'\{[^{}]*"result"[^{}]*\}', text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {"text": text, "input_tokens": None,
                        "output_tokens": None, "cost_usd": None, "is_json": False}
        else:
            return {"text": text, "input_tokens": None,
                    "output_tokens": None, "cost_usd": None, "is_json": False}

    if not isinstance(data, dict):
        return {"text": text, "input_tokens": None,
                "output_tokens": None, "cost_usd": None, "is_json": False}

    # Extract the response text
    result_text = data.get("result", "")
    if not result_text and data.get("is_error"):
        result_text = data.get("error", text)

    # Extract token counts
    usage = data.get("usage", {})
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")

    # Extract cost
    cost_usd = data.get("cost_usd")

    return {
        "text": result_text or "(no output)",
        "input_tokens": int(input_tokens) if input_tokens is not None else None,
        "output_tokens": int(output_tokens) if output_tokens is not None else None,
        "cost_usd": float(cost_usd) if cost_usd is not None else None,
        "is_json": True,
    }


_build_claude_cmd = build_claude_cmd  # legacy alias
