"""Generic OpenAI-compatible API runner.

Called as a subprocess by any integration that speaks the OpenAI chat
completions API format — OpenRouter, Groq, LM Studio, Jan.ai, Together AI,
Fireworks AI, llama.cpp server, Oobabooga, Koboldcpp, custom endpoints, etc.

Usage:
    python -m helm.ai_runner._openai_compat_cli \
        --base-url https://api.groq.com/openai/v1 \
        --model llama-3.3-70b-versatile \
        --api-key gsk_... \
        [--timeout 120]

Reads the prompt from stdin. Prints the assistant reply to stdout.
API key is optional for local servers (pass "" or omit).
"""

import json
import os
import sys
import urllib.error
import urllib.request

_DEFAULT_TIMEOUT = 120


def main() -> None:
    args = sys.argv[1:]

    def _arg(flag: str, default: str = "") -> str:
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        return default

    base_url = _arg("--base-url").rstrip("/")
    model    = _arg("--model")
    api_key  = _arg("--api-key")
    api_key_env = _arg("--api-key-env")
    if not api_key and api_key_env:
        api_key = os.environ.get(api_key_env, "").strip()
        if not api_key:
            print(
                f"(error: {api_key_env} is not set — configure it in Settings > LLM Provider Setup)",
                file=sys.stderr,
            )
            sys.exit(1)
    timeout  = int(_arg("--timeout", str(_DEFAULT_TIMEOUT)))

    if not base_url:
        print("(error: --base-url is required)", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("(error: --model is required)", file=sys.stderr)
        sys.exit(1)

    prompt = sys.stdin.read().strip()
    if not prompt:
        print("(error: empty prompt)", file=sys.stderr)
        sys.exit(1)

    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = "https://raprai.local"
        headers["X-Title"]      = "RAPR AI Agent"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(err_body).get("error", {})
            msg = msg.get("message", err_body) if isinstance(msg, dict) else str(msg)
        except Exception:
            msg = err_body
        print(f"(error: API {exc.code} — {msg})", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"(error: request failed — {exc})", file=sys.stderr)
        sys.exit(1)

    try:
        reply = body["choices"][0]["message"]["content"]
        print(reply)
    except (KeyError, IndexError) as exc:
        print(f"(error: unexpected response — {exc}: {body})", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
