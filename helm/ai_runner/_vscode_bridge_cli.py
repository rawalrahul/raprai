"""GitHub Copilot through the RAPR Bridge in VS Code (helm/vscode_bridge), as an agent.

Run as a subprocess by integrations/copilot_vscode.py, like the other API helpers here, in
the folder Copilot should work in:

    RAPR_AGENT_MODE=edit+run python -m helm.ai_runner._vscode_bridge_cli [--model gpt-4.1]

Reads the task from stdin, lets Copilot work on it with the tools RAPR_AGENT_MODE allows
(read, edit, edit+run; read when unset: see helm/vscode_bridge/agent.py) and prints its
answer. On failure prints "(error: ...)" to stderr, with what to do, and exits 1.
"""

import os
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
    from helm.vscode_bridge import agent
    mode = os.environ.get("RAPR_AGENT_MODE", "").strip() or agent.READ
    try:
        answer = agent.run(prompt, os.getcwd(), mode, model, log=lambda line: print(line, file=sys.stderr))
    except vscode_bridge.BridgeError as exc:
        print(f"(error: {exc})", file=sys.stderr)
        sys.exit(1)
    if not answer.strip():
        print("(error: Copilot answered with nothing)", file=sys.stderr)
        sys.exit(1)
    print(answer)


if __name__ == "__main__":
    main()
