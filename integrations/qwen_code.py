"""Qwen Code — Alibaba's open-source coding agent (a Gemini CLI fork).

Checked against qwen 0.25.0: run without a prompt argument and with input piped
in, it answers once and exits; --yolo approves tool use; -m picks the model.
Qwen's free OAuth sign-in was discontinued, so it needs an API key: e.g.
OPENAI_API_KEY + OPENAI_BASE_URL + OPENAI_MODEL with QWEN_AUTH_TYPE=openai
(or DASHSCOPE_API_KEY), or settings made in its own config.
"""

import os
import shutil

KEY   = "qwen_code"
NAME  = "Qwen Code"
EMOJI = "🐉"
COLOR = "#615ced"


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    cmd = [shutil.which("qwen") or "qwen", "--yolo"]
    auth = os.environ.get("QWEN_AUTH_TYPE", "").strip()
    if auth:
        cmd.extend(["--auth-type", auth])
    if model:
        cmd.extend(["-m", model])
    return cmd


STDIN_PROMPT = True
ENV_VARS: list[str] = []
PROCESS_ENV = {"QWEN_CODE_SUPPRESS_YOLO_WARNING": "1"}
SETUP_HINT = ("Install: npm install -g @qwen-code/qwen-code@latest (Node 22+)  |  Needs an API key: "
              "set QWEN_AUTH_TYPE=openai with OPENAI_API_KEY, OPENAI_BASE_URL and OPENAI_MODEL")

# Catalog (Settings → AI Integrations)
ABOUT   = "Alibaba's open-source coding agent. Works with any OpenAI-compatible API key, including Ollama."
INSTALL = "npm install -g @qwen-code/qwen-code@latest"
DOCS    = "https://github.com/QwenLM/qwen-code"
