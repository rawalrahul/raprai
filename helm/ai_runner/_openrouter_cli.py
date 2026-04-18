"""Standalone OpenRouter API runner called as subprocess by the integration.

Usage (from build_command):
    python -m helm.ai_runner._openrouter_cli --model <model> < prompt.txt

Reads the prompt from stdin, calls OpenRouter chat completions API,
prints the assistant reply to stdout.

Requires OPENROUTER_API_KEY in environment.
"""

import json
import os
import sys
import urllib.error
import urllib.request

_API_URL = "https://openrouter.ai/api/v1/chat/completions"
_DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"
_TIMEOUT = 120  # seconds


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("(error: OPENROUTER_API_KEY not set — add it in Settings → API Keys)",
              file=sys.stderr)
        sys.exit(1)

    # Parse --model flag
    model = _DEFAULT_MODEL
    args = sys.argv[1:]
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model = args[idx + 1]

    prompt = sys.stdin.read().strip()
    if not prompt:
        print("(error: empty prompt)", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        _API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://raprai.local",
            "X-Title": "RAPR AI Agent",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", err_body)
        except Exception:
            msg = err_body
        print(f"(error: OpenRouter {exc.code} — {msg})", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"(error: OpenRouter request failed — {exc})", file=sys.stderr)
        sys.exit(1)

    try:
        reply = body["choices"][0]["message"]["content"]
        print(reply)
    except (KeyError, IndexError) as exc:
        print(f"(error: unexpected OpenRouter response — {exc}: {body})", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
