"""OpenRouter integration — 200+ models via a single API key.

Setup:
  1. Get a free API key at https://openrouter.ai/keys
  2. Add  OPENROUTER_API_KEY=sk-or-...  to your .env file
  3. Restart RAPR AI — OpenRouter appears in the AI selector automatically.

In the Agent Builder, select "OpenRouter" as the node AI and enter
a model string in the Model field, e.g.:
  anthropic/claude-sonnet-4-5
  openai/gpt-4o
  google/gemini-2.0-flash-001
  meta-llama/llama-3.3-70b-instruct
  mistralai/mistral-large-2411
  deepseek/deepseek-chat-v3-0324

Full model list: https://openrouter.ai/models
"""

import sys

KEY   = "openrouter"
NAME  = "OpenRouter"
EMOJI = "🌐"
COLOR = "#8b5cf6"   # violet


def build_command(prompt: str, model: str | None = None, **kwargs) -> list[str]:
    """Call the OpenRouter API via the bundled Python runner.

    Prompt is piped via stdin (STDIN_PROMPT = True).
    Model comes from node["ai"] after resolve_ai_spec strips the "openrouter/" prefix.
    """
    cmd = [sys.executable, "-m", "helm.ai_runner._openrouter_cli"]
    if model:
        cmd.extend(["--model", model])
    return cmd


STDIN_PROMPT = True

ENV_VARS = ["OPENROUTER_API_KEY"]

SETUP_HINT = (
    "Get a free API key at https://openrouter.ai/keys  |  "
    "Add OPENROUTER_API_KEY=sk-or-... to .env  |  "
    "200+ models: Claude, GPT-4o, Gemini, Llama, Mistral, DeepSeek and more"
)
