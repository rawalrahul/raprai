"""
helm/ai_runner — AI subprocess runner and core message processor.

This package splits the original ai_runner.py module into organized sub-modules:
  - core.py — process_message, run_ai_popen, kill_session_proc
  - claude.py — build_claude_cmd
  - ollama.py — Ollama agent loop, tools, and helpers
  - doc_generators.py — PowerPoint, PDF, and Word document generators
  - helpers.py — Telegram notifications and CWD management

All public functions are re-exported here for backward compatibility.
Existing code using `from helm.ai_runner import X` continues to work; the names load
on first use (see _WHERE below).
"""

# Each name loads its sub-module on first use, so a light caller (the MCP server
# building a Claude command) doesn't pull in the web server and Telegram.
_WHERE = {
    # Core subprocess runner
    "run_ai_popen": "core", "_run_ai_popen": "core",
    "kill_session_proc": "core", "_kill_session_proc": "core",
    "process_message": "core", "_process_message": "core",
    # Claude-specific
    "build_claude_cmd": "claude", "_build_claude_cmd": "claude",
    # Ollama REST API agent and tools
    "ollama_model_supports_tools": "ollama", "_OLLAMA_URL": "ollama",
    "_ollama_system_prompt": "ollama", "_run_ollama_agent": "ollama",
    "_OLLAMA_TOOLS": "ollama_tools", "_execute_ollama_tool": "ollama_tools",
    "_parse_content_tool_calls": "ollama_tools",
    # Document code generators
    "_generate_pptx_code": "doc_generators", "_generate_pdf_code": "doc_generators",
    "_generate_docx_code": "doc_generators",
    # Helpers: Telegram and CWD
    "forward_to_telegram": "helpers", "_forward_to_telegram": "helpers",
    "tg_update_focus": "helpers", "_tg_update_focus": "helpers",
    "tg_progress_notify": "helpers", "_tg_progress_notify": "helpers",
    "change_cwd": "helpers", "_change_cwd": "helpers",
}


def __getattr__(name):
    mod = _WHERE.get(name)
    if mod is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    value = getattr(importlib.import_module(f".{mod}", __name__), name)
    globals()[name] = value
    return value


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
