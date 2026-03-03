"""
helm/ai_runner — AI subprocess runner and core message processor.

This package splits the original ai_runner.py module into organized sub-modules:
  - core.py — process_message, run_ai_popen, kill_session_proc
  - claude.py — build_claude_cmd
  - ollama.py — Ollama agent loop, tools, and helpers
  - doc_generators.py — PowerPoint, PDF, and Word document generators
  - helpers.py — Telegram notifications and CWD management

All public functions are re-exported here for backward compatibility.
Existing code using `from helm.ai_runner import X` continues to work.
"""

# Core subprocess runner
from .core import (
    run_ai_popen,
    _run_ai_popen,
    kill_session_proc,
    _kill_session_proc,
    process_message,
    _process_message,
)

# Claude-specific
from .claude import (
    build_claude_cmd,
    _build_claude_cmd,
)

# Ollama REST API agent and tools
from .ollama import (
    ollama_model_supports_tools,
    _OLLAMA_TOOLS,
    _OLLAMA_URL,
    _execute_ollama_tool,
    _parse_content_tool_calls,
    _ollama_system_prompt,
    _run_ollama_agent,
)

# Document code generators
from .doc_generators import (
    _generate_pptx_code,
    _generate_pdf_code,
    _generate_docx_code,
)

# Helpers: Telegram and CWD
from .helpers import (
    forward_to_telegram,
    _forward_to_telegram,
    tg_update_focus,
    _tg_update_focus,
    tg_progress_notify,
    _tg_progress_notify,
    change_cwd,
    _change_cwd,
)


__all__ = [
    # Core
    "run_ai_popen",
    "_run_ai_popen",
    "kill_session_proc",
    "_kill_session_proc",
    "process_message",
    "_process_message",
    # Claude
    "build_claude_cmd",
    "_build_claude_cmd",
    # Ollama
    "ollama_model_supports_tools",
    "_OLLAMA_TOOLS",
    "_OLLAMA_URL",
    "_execute_ollama_tool",
    "_parse_content_tool_calls",
    "_ollama_system_prompt",
    "_run_ollama_agent",
    # Document generators
    "_generate_pptx_code",
    "_generate_pdf_code",
    "_generate_docx_code",
    # Helpers
    "forward_to_telegram",
    "_forward_to_telegram",
    "tg_update_focus",
    "_tg_update_focus",
    "tg_progress_notify",
    "_tg_progress_notify",
    "change_cwd",
    "_change_cwd",
]
