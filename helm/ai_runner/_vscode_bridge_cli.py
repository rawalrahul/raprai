"""Ask GitHub Copilot through the RAPR Bridge in VS Code (helm/vscode_bridge).

Run as a subprocess by integrations/copilot_vscode.py, like the other API helpers here:

    python -m helm.ai_runner._vscode_bridge_cli [--model gpt-4.1]

Reads the prompt from stdin and prints Copilot's answer. On failure prints "(error: ...)"
to stderr, with what to do, and exits 1.
"""

import sys

from helm.ai_runner._openai_compat_cli import _use_utf8


def main() -> None:
    _use_utf8()
    args = sys.argv[1:]
    model = args[args.index("--model") + 1] if "--model" in args and args.index("--model") + 1 < len(args) else None
    prompt = sys.stdin.read()
    if not prompt.strip():
        print("(error: empty prompt)", file=sys.stderr)
        sys.exit(1)
    from helm import vscode_bridge
    try:
        answer = vscode_bridge.ask(prompt, model)
    except vscode_bridge.BridgeError as exc:
        print(f"(error: {exc})", file=sys.stderr)
        sys.exit(1)
    if not answer.strip():
        print("(error: Copilot answered with nothing)", file=sys.stderr)
        sys.exit(1)
    print(answer)


if __name__ == "__main__":
    main()
