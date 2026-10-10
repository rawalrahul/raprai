"""Open Interpreter integration.

Open Interpreter has no "--message" option, and its "--stdin" mode reads only
one line. So RAPR runs Open Interpreter's own Python and hands it the whole
prompt through its Python API. If that Python can't be found, it falls back to
"interpreter --stdin", which only reads the prompt's first line.
"""

import os
import pathlib
import shutil
import sys

KEY   = "interpreter"
NAME  = "Open Interpreter"
EMOJI = "🖥️"
COLOR = "#8b5cf6"  # purple

# Runs inside Open Interpreter's Python: argv[1] = model ("" = its default),
# argv[2] = "1" to run code without asking. The prompt comes on stdin.
_RUNNER = (
    "import sys\n"
    "from interpreter import interpreter as oi\n"
    "if sys.argv[1]: oi.llm.model = sys.argv[1]\n"
    "oi.auto_run = sys.argv[2] == '1'\n"
    "msgs = oi.chat(sys.stdin.read(), display=False)\n"
    "print('\\n\\n'.join(m.get('content', '') for m in msgs or []\n"
    "      if m.get('role') == 'assistant' and m.get('type') == 'message'))\n"
)


def _interpreter_python() -> str | None:
    """The Python that Open Interpreter is installed in (next to its launcher)."""
    exe = shutil.which("interpreter")
    if not exe:
        return None
    path = pathlib.Path(exe)
    if sys.platform == "win32":
        # venv: Scripts\\python.exe; plain install: Scripts\\..\\python.exe
        for cand in (path.parent / "python.exe", path.parent.parent / "python.exe"):
            if cand.exists():
                return str(cand)
        return None
    try:
        first = path.resolve().read_bytes()[:300].split(b"\n", 1)[0].decode()
    except OSError:
        return None
    if first.startswith("#!"):
        py = first[2:].strip().split()[0] if first[2:].strip() else ""
        if py and os.path.isabs(py) and os.path.exists(py):
            return py
    return None


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    auto = os.environ.get("INTERPRETER_AUTO_FLAG", "--auto_run").strip()
    py = _interpreter_python()
    if py:
        return [py, "-c", _RUNNER, model or "", "1" if auto else "0"]
    _ext = ".exe" if sys.platform == "win32" else ""
    cmd = [f"interpreter{_ext}"]
    if model:
        cmd.extend(["--model", model])
    if auto:
        cmd.append(auto)
    cmd.append("--stdin")
    return cmd


STDIN_PROMPT = True
ENV_VARS: list[str] = ["INTERPRETER_AUTO_FLAG"]
SETUP_HINT: str = (
    "Install: pip install open-interpreter  |  "
    "Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env  |  "
    "Local models: interpreter --local"
)
