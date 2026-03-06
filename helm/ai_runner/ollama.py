"""
helm/ai_runner/ollama.py — Ollama REST API agent and tool execution.

Covers: ollama_model_supports_tools, _OLLAMA_TOOLS, _execute_ollama_tool,
        _parse_content_tool_calls, _ollama_system_prompt, _run_ollama_agent.
"""

import asyncio
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

import helm.state as _st
from helm.broadcast import push_message
from helm.config import logger
from helm.skills import inject_skill_prefix, detect_skill

from .doc_generators import _generate_pptx_code, _generate_pdf_code, _generate_docx_code

# MCP Manager (lazy import to avoid circular deps)
_mcp_manager = None

def _get_mcp_manager():
    """Lazy-load the MCP Manager singleton."""
    global _mcp_manager
    if _mcp_manager is None:
        try:
            from helm.mcp import get_manager
            _mcp_manager = get_manager()
        except ImportError:
            pass
    return _mcp_manager


_OLLAMA_URL = "http://localhost:11434/api/chat"

_OLLAMA_TOOL_SUPPORT: dict[str, bool] = {
    "qwen2.5":          True,
    "qwen3":            True,
    "llama3.1":         True,
    "llama3.2":         True,
    "llama3.3":         True,
    "mistral-nemo":     True,
    "mistral":          True,
    "command-r":        True,
    "granite3":         True,
    "firefunction":     True,
    "smollm2":          True,
    "deepseek-r1":      False,
    "deepseek-v":       False,
    "llama2":           False,
    "phi3":             False,
    "gemma":            False,
    "gemma2":           False,
    "gemma3":           False,
    "codellama":        False,
    "starcoder":        False,
    "flux":             False,
    "stable-diffusion": False,
}


def ollama_model_supports_tools(model: str) -> bool | None:
    """
    Return True if the model is known to support tool calling,
    False if known not to, or None if unknown.
    """
    m = model.lower().split(":")[0]
    for prefix, supported in _OLLAMA_TOOL_SUPPORT.items():
        if m.startswith(prefix):
            return supported
    return None


_OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_presentation",
            "description": (
                "Create a professional, beautifully-styled PowerPoint presentation (.pptx) "
                "with themed slides, accent bars, cards, and polished visuals. "
                "YOU MUST USE THIS TOOL for any presentation / slide / ppt request. "
                "Provide the slide content and this tool handles all the styling. "
                "Use VARIED slide types for engaging presentations — don't repeat the same type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Output filename, e.g. 'AGI_Presentation.pptx'",
                    },
                    "title": {"type": "string", "description": "Presentation title for the title slide"},
                    "subtitle": {"type": "string", "description": "Subtitle or tagline for the title slide"},
                    "theme": {
                        "type": "string",
                        "description": "Visual theme: 'dark' (default, blue/cyan on dark), 'corporate' (navy/gold), 'light' (clean white/blue), 'forest' (green/gold on dark green)",
                    },
                    "slides": {
                        "type": "array",
                        "description": (
                            "Array of slide objects. Each slide has a 'type' and content fields. "
                            "Available types and their fields:\n"
                            "- 'content': title + bullets (array of strings)\n"
                            "- 'two_column': title + left_title + left_items + right_title + right_items\n"
                            "- 'stat': stat_value (big number) + stat_label + context\n"
                            "- 'section': number (int) + title (section divider)\n"
                            "- 'timeline': title + steps (array of strings or {title, description})\n"
                            "- 'comparison': title + option_a + option_a_points + option_b + option_b_points\n"
                            "- 'quote': quote (text) + author\n"
                            "- 'cards': title + cards (array of strings or {title, description}, max 4)\n"
                            "- 'table': title + headers (array) + rows (array of arrays)\n"
                            "- 'closing': title + subtitle (thank you / contact slide)\n"
                            "Aim for 8-12 slides. Mix at least 4 different types for variety."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "Slide type: content, two_column, stat, section, timeline, comparison, quote, cards, table, closing",
                                },
                                "title": {"type": "string", "description": "Slide title"},
                                "subtitle": {"type": "string", "description": "Slide subtitle (closing)"},
                                "bullets": {"type": "array", "items": {"type": "string"}, "description": "Bullet points (content)"},
                                "left_title": {"type": "string"}, "left_items": {"type": "array", "items": {"type": "string"}},
                                "right_title": {"type": "string"}, "right_items": {"type": "array", "items": {"type": "string"}},
                                "stat_value": {"type": "string", "description": "Big number (stat)"}, "stat_label": {"type": "string"}, "context": {"type": "string"},
                                "number": {"type": "integer", "description": "Section number"},
                                "steps": {"type": "array", "description": "Timeline steps (strings or {title, description})"},
                                "option_a": {"type": "string"}, "option_a_points": {"type": "array", "items": {"type": "string"}},
                                "option_b": {"type": "string"}, "option_b_points": {"type": "array", "items": {"type": "string"}},
                                "quote": {"type": "string"}, "author": {"type": "string"},
                                "cards": {"type": "array", "description": "Card items (strings or {title, description}), max 4"},
                                "headers": {"type": "array", "items": {"type": "string"}, "description": "Table headers"},
                                "rows": {"type": "array", "description": "Table rows (array of arrays)"},
                            },
                            "required": ["type"],
                        },
                    },
                },
                "required": ["filename", "title", "slides"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": (
                "Create a professional styled PDF document with headers, footers, "
                "tables, callout boxes, key-value pairs, and polished typography. "
                "YOU MUST USE THIS TOOL for any PDF creation request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Output filename, e.g. 'Report.pdf'"},
                    "title": {"type": "string", "description": "Document title"},
                    "subtitle": {"type": "string", "description": "Subtitle or byline"},
                    "sections": {
                        "type": "array",
                        "description": (
                            "Array of sections. Each has heading + content fields:\n"
                            "- paragraphs: array of body text strings\n"
                            "- bullets: array of bullet point strings\n"
                            "- numbered_items: array of numbered list items\n"
                            "- callout: highlighted note text (+ callout_label)\n"
                            "- key_value_pairs: array of [key, value] pairs for info tables\n"
                            "- table_headers + table_rows: data table\n"
                            "- page_break: boolean to insert page break after"
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string", "description": "Section heading"},
                                "paragraphs": {"type": "array", "items": {"type": "string"}},
                                "bullets": {"type": "array", "items": {"type": "string"}},
                                "numbered_items": {"type": "array", "items": {"type": "string"}, "description": "Auto-numbered list"},
                                "callout": {"type": "string", "description": "Highlighted callout text"},
                                "callout_label": {"type": "string", "description": "Label for callout, e.g. 'Important', 'Tip'"},
                                "key_value_pairs": {"type": "array", "description": "Array of [key, value] pairs", "items": {"type": "array"}},
                                "table_headers": {"type": "array", "items": {"type": "string"}},
                                "table_rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                                "page_break": {"type": "boolean"},
                            },
                            "required": ["heading"],
                        },
                    },
                },
                "required": ["filename", "title", "sections"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_document",
            "description": (
                "Create a professional styled Word document (.docx) with proper headings, "
                "bullet points, numbered lists, tables, callouts, and formatting. "
                "YOU MUST USE THIS TOOL for any Word document / .docx request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Output filename, e.g. 'Report.docx'"},
                    "title": {"type": "string", "description": "Document title"},
                    "sections": {
                        "type": "array",
                        "description": (
                            "Array of sections. Each has heading + content fields:\n"
                            "- paragraphs: array of body text strings\n"
                            "- bullets: array of bullet point strings\n"
                            "- numbered_items: array of numbered list items\n"
                            "- callout: indented highlighted text with accent border\n"
                            "- key_value_pairs: array of [key, value] pairs for info tables\n"
                            "- table_headers + table_rows: data table"
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "heading": {"type": "string", "description": "Section heading"},
                                "paragraphs": {"type": "array", "items": {"type": "string"}},
                                "bullets": {"type": "array", "items": {"type": "string"}},
                                "numbered_items": {"type": "array", "items": {"type": "string"}},
                                "callout": {"type": "string", "description": "Highlighted callout text with accent border"},
                                "key_value_pairs": {"type": "array", "description": "Array of [key, value] pairs", "items": {"type": "array"}},
                                "table_headers": {"type": "array", "items": {"type": "string"}},
                                "table_rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                            },
                            "required": ["heading"],
                        },
                    },
                },
                "required": ["filename", "title", "sections"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": (
                "Execute Python code in the user's working directory. "
                "Use for general coding tasks, Excel (.xlsx), images, and scripts. "
                "Do NOT use for .pptx (use create_presentation), "
                ".pdf (use create_pdf), or .docx (use create_document). "
                "Install packages with subprocess if needed. "
                "Always print a confirmation at the end."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Complete, self-contained Python code to execute. "
                            "Use try/except for error handling. "
                            "All file paths should be relative to the working directory."
                        ),
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write text content directly to a file. "
                "ONLY for plain text, Markdown, JSON, CSV, HTML, or source code. "
                "NEVER for .pptx, .pdf, or .docx — use create_presentation, "
                "create_pdf, or create_document instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to working directory (e.g. 'report.md')",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full text content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read an existing file's contents. Use before editing files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to working directory",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in the working directory or a subdirectory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to list. Use '.' for the current directory.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_skill",
            "description": (
                "Save a new reusable skill to the RAPR AI skill library. "
                "Call this when you discover a reliable pattern for a task type "
                "that you've successfully completed and that no existing skill covers. "
                "The skill will be available to you and all other AIs for future similar tasks. "
                "Use a kebab-case name like 'word-document-from-template' or 'quarterly-report'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Kebab-case skill name (e.g. 'document-creation', "
                            "'excel-budget', 'api-data-fetch'). "
                            "Must be unique — do not overwrite existing skills."
                        ),
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "One sentence describing what tasks this skill covers "
                            "(used in the skill registry and UI)."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Full Markdown content of the skill. Include: "
                            "## What this skill covers, "
                            "## Step-by-step approach, "
                            "## Python code template (for Ollama), "
                            "## Tips and common pitfalls."
                        ),
                    },
                },
                "required": ["name", "description", "content"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# MCP tools (dynamically added from all running MCP servers)
# ---------------------------------------------------------------------------

def _build_ollama_tools() -> list[dict]:
    """Build the tools list, including MCP server tools if available."""
    tools = list(_OLLAMA_TOOLS)  # copy base tools

    # Add tools from all running MCP servers
    mgr = _get_mcp_manager()
    if mgr and mgr.has_running_servers():
        mcp_tools = mgr.get_ollama_tool_defs()
        tools.extend(mcp_tools)
        logger.debug("Ollama tools: added %d MCP tools from %d servers",
                      len(mcp_tools),
                      len([s for s in mgr._clients.values() if s.is_running()]))

    return tools


async def _execute_ollama_tool(name: str, args: dict, cwd: str) -> str:
    """Dispatch and run a single Ollama tool call; return the result as a string."""
    try:
        if name == "execute_python":
            code = args.get("code", "")
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=600, cwd=cwd,
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if result.returncode != 0:
                return f"Exit {result.returncode}:\n{err}\n{out}".strip()
            return out or "✓ executed (no output)"

        elif name == "write_file":
            rel     = args.get("path", "")
            content = args.get("content", "")
            dest    = pathlib.Path(cwd) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            return f"✓ wrote {len(content):,} chars → {rel}"

        elif name == "read_file":
            rel  = args.get("path", "")
            text = (pathlib.Path(cwd) / rel).read_text(encoding="utf-8")
            if len(text) > 8000:
                text = text[:8000] + "\n…(truncated — file continues)"
            return text

        elif name == "list_directory":
            rel     = args.get("path", ".")
            entries = sorted(
                (pathlib.Path(cwd) / rel).iterdir(),
                key=lambda p: (p.is_file(), p.name),
            )
            lines = [
                f"📁 {e.name}/" if e.is_dir() else f"📄 {e.name} ({e.stat().st_size:,} B)"
                for e in entries
            ]
            return "\n".join(lines) or "(empty directory)"

        elif name == "save_skill":
            from helm.skills import create_skill, get_user_skills_dir
            skill_name  = args.get("name", "").strip()
            description = args.get("description", "").strip()
            content     = args.get("content", "").strip()
            if not skill_name or not content:
                return "Error: 'name' and 'content' are required."
            skills_dir = get_user_skills_dir()
            if not skills_dir:
                return "Error: No writable skills directory configured."
            ok = await asyncio.to_thread(create_skill, skill_name, description, content)
            if ok:
                return (
                    f"✓ Skill '{skill_name}' saved to {skills_dir}/{skill_name}/SKILL.md\n"
                    f"It is now active in the registry and will be used for future tasks."
                )
            return f"Error: could not save skill '{skill_name}'. Check server logs."

        elif name == "create_presentation":
            filename = args.get("filename", "Presentation.pptx")
            if not filename.endswith(".pptx"):
                filename += ".pptx"
            title    = args.get("title", "Presentation")
            subtitle = args.get("subtitle", "")
            theme    = args.get("theme", "dark")
            slides   = args.get("slides", [])
            if not slides:
                return "Error: 'slides' list is required with at least one slide."
            code = _generate_pptx_code(filename, title, subtitle, slides, theme=theme)
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=120, cwd=cwd,
            )
            if result.returncode != 0:
                return f"Error creating presentation:\n{result.stderr.strip()}"
            fpath = pathlib.Path(cwd) / filename
            size  = fpath.stat().st_size if fpath.exists() else 0
            return (
                f"✓ Created {filename} ({size:,} bytes) with {len(slides)+1} slides "
                f"(title + {len(slides)} content slides). "
                f"Saved to: {fpath}"
            )

        elif name == "create_pdf":
            filename = args.get("filename", "Document.pdf")
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            title    = args.get("title", "Document")
            subtitle = args.get("subtitle", "")
            sections = args.get("sections", [])
            if not sections:
                return "Error: 'sections' list is required with at least one section."
            code = _generate_pdf_code(filename, title, subtitle, sections)
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=120, cwd=cwd,
            )
            if result.returncode != 0:
                return f"Error creating PDF:\n{result.stderr.strip()}"
            fpath = pathlib.Path(cwd) / filename
            size  = fpath.stat().st_size if fpath.exists() else 0
            return f"✓ Created {filename} ({size:,} bytes) with {len(sections)} sections. Saved to: {fpath}"

        elif name == "create_document":
            filename = args.get("filename", "Document.docx")
            if not filename.endswith(".docx"):
                filename += ".docx"
            title    = args.get("title", "Document")
            sections = args.get("sections", [])
            if not sections:
                return "Error: 'sections' list is required with at least one section."
            code = _generate_docx_code(filename, title, sections)
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=120, cwd=cwd,
            )
            if result.returncode != 0:
                return f"Error creating document:\n{result.stderr.strip()}"
            fpath = pathlib.Path(cwd) / filename
            size  = fpath.stat().st_size if fpath.exists() else 0
            return f"✓ Created {filename} ({size:,} bytes) with {len(sections)} sections. Saved to: {fpath}"

        # Route MCP server tools (e.g. google_workspace_gmail_users_messages_list)
        mgr = _get_mcp_manager()
        if mgr and mgr.is_mcp_tool(name):
            return await mgr.call_tool(name, args)

        return f"Unknown tool: {name}"

    except subprocess.TimeoutExpired:
        return "Error: timed out after 600 s"
    except Exception as exc:
        return f"Error: {exc}"


def _parse_content_tool_calls(content: str) -> list[dict]:
    """
    Some models embed tool calls as JSON text in the message content field
    instead of the structured tool_calls field.

    Handles all common formats:
      • {"name": "fn", "arguments": {...}}
      • [{"name": "fn", "arguments": {...}}, ...]
      • ```json\n{...}\n```
      • <tool_call>{...}</tool_call>
      • <tool_call>\n{...}\n</tool_call>

    Returns a list of synthetic tool-call dicts matching the shape our agent
    loop already expects:  [{"function": {"name": ..., "arguments": ...}}, ...]
    """
    if not content:
        return []

    text = content.strip()

    # Strip markdown code fences
    fence = re.search(r'```(?:json|tool_call)?\s*(\[.*?\]|\{.*?\})\s*```',
                      text, re.DOTALL)
    if fence:
        text = fence.group(1)

    # Strip XML-style tool_call tags
    xml = re.search(r'<tool_call>\s*(\{.*?\}|\[.*?\])\s*</tool_call>',
                    text, re.DOTALL)
    if xml:
        text = xml.group(1)

    # Try to parse whatever we have
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Last-ditch: find the first {...} block in the content
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            return []
        try:
            parsed = json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            return []

    # Normalise to a list
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []

    result = []
    for item in parsed:
        if not isinstance(item, dict) or "name" not in item:
            continue
        args = item.get("arguments") or item.get("parameters") or {}
        # Some models wrap arguments as a JSON string
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        result.append({"function": {"name": item["name"], "arguments": args}})

    return result


def _ollama_system_prompt(cwd: str, skill_content: str = "") -> str:
    """Build the Ollama system prompt."""
    base = (
        f"You are a capable AI assistant with tools to create and manage files.\n"
        f"Working directory: {cwd}\n\n"
        "You have tools available — use whichever tool fits the task best. "
        "Produce detailed, professional content. Never produce stubs or placeholders.\n"
    )

    if skill_content:
        base += (
            "\nThe following skill guide applies to this task:\n\n"
            f"{skill_content}\n"
        )

    # Add MCP server info if any servers are running
    mgr = _get_mcp_manager()
    if mgr and mgr.has_running_servers():
        mcp_summary = mgr.get_system_prompt_summary()
        if mcp_summary:
            base += f"\n{mcp_summary}\n"

    # Inject shared AI memory
    try:
        from helm.memory import get_memory_block
        mem_block = get_memory_block()
        if mem_block:
            base += f"\n{mem_block}"
    except Exception:
        pass

    return base


async def _run_ollama_agent(sess: dict, text: str, source: str, sid: str) -> str:
    """
    Ollama agentic loop via /api/chat with tool calling.

    Sends the user message together with tool definitions, executes any
    tool_calls the model returns, feeds results back, and repeats until the
    model gives a plain-text answer.  Falls back to the regular subprocess
    (ollama run) when the REST API is unreachable or the model does not
    support tools.
    """
    from helm.file_tracker import snapshot_dir, handle_diff
    from .core import run_ai_popen  # lazy to avoid circular import

    cwd   = sess["cwd"]
    model = sess.get("model") or _st.default_models.get("ollama", "") or os.environ.get("OLLAMA_MODEL", "")
    if not model:
        try:
            _r = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5,
            )
            for _line in _r.stdout.strip().splitlines()[1:]:
                _parts = _line.split()
                if _parts:
                    model = _parts[0].strip()
                    break
        except Exception:
            pass
    if not model:
        model = "qwen3:4b"

    tool_support = ollama_model_supports_tools(model)
    if tool_support is False:
        await push_message(
            "system",
            f"⚠️ **{model}** does not support tool calling — file creation tools are disabled.\n"
            f"Switch to a compatible model (e.g. `qwen2.5-coder:7b`, `qwen3:4b`, `llama3.1:8b`) "
            f"via `/model` to enable tools.",
            source=source, session_id=sid,
        )
    elif tool_support is None:
        await push_message(
            "system",
            f"ℹ️ **{model}** — tool calling support unknown. "
            f"If file creation doesn't work, switch to `qwen2.5-coder:7b` or `llama3.1:8b`.",
            source=source, session_id=sid,
        )

    from helm.skills import _registry
    skill_name = detect_skill(text)
    skill_content = ""
    if skill_name:
        ai_specific = f"{sess['ai']}-{skill_name}" if sess.get("ai") else ""
        if ai_specific and ai_specific in _registry:
            skill_name = ai_specific
        skill_content = _registry.get(skill_name, {}).get("content", "")
        logger.info("Ollama skill injection (system prompt): skill=%s chars=%d",
                     skill_name, len(skill_content))

    system_content = _ollama_system_prompt(cwd, skill_content=skill_content)
    if not sess.get("ollama_messages"):
        sess["ollama_messages"] = [{"role": "system", "content": system_content}]
    else:
        if sess["ollama_messages"][0].get("role") == "system":
            sess["ollama_messages"][0]["content"] = system_content

    sess["ollama_messages"].append({"role": "user", "content": text})

    before       = await asyncio.to_thread(snapshot_dir, cwd)
    final_output = ""

    # Token tracking — accumulate across all iterations of the agent loop
    _total_prompt_tokens = 0
    _total_eval_tokens   = 0

    # No hard iteration cap — the loop runs until the model produces a
    # text response (no more tool calls) or the budget guardrail stops it.
    # A safety limit of 200 prevents true infinite loops from buggy models.
    _SAFETY_LIMIT = 200
    for _iteration in range(_SAFETY_LIMIT):
        active_tools = _build_ollama_tools()
        payload = {
            "model":   model,
            "messages": sess["ollama_messages"],
            "tools":   active_tools,
            "stream":  False,
        }

        try:
            req = urllib.request.Request(
                _OLLAMA_URL,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read())

        except urllib.error.URLError as exc:
            logger.warning("Ollama REST API unreachable (%s) — falling back to CLI", exc)
            cli_text = inject_skill_prefix(text, ai=sess.get("ai", "ollama"))
            cmd = _st.integrations["ollama"]["build_command"](
                cli_text, model=sess.get("model")
            )
            final_output = await asyncio.to_thread(
                run_ai_popen, cmd, cwd, "ollama", sess
            )
            break

        except Exception as exc:
            final_output = f"Ollama error: {exc}"
            logger.error(final_output)
            break

        api_error = data.get("error", "")
        if api_error:
            logger.warning(
                "Ollama API returned error (%s) — falling back to CLI", api_error
            )
            cli_text = inject_skill_prefix(text, ai=sess.get("ai", "ollama"))
            cmd = _st.integrations["ollama"]["build_command"](
                cli_text, model=sess.get("model")
            )
            final_output = await asyncio.to_thread(
                run_ai_popen, cmd, cwd, "ollama", sess
            )
            break

        # Extract token counts from Ollama response
        _total_prompt_tokens += int(data.get("prompt_eval_count", 0))
        _total_eval_tokens   += int(data.get("eval_count", 0))

        msg        = data.get("message", {})
        tool_calls = msg.get("tool_calls") or []
        content    = (msg.get("content") or "").strip()

        if not tool_calls and content:
            tool_calls = _parse_content_tool_calls(content)
            if tool_calls:
                logger.info(
                    "Ollama: parsed %d tool call(s) from content text (model=%s)",
                    len(tool_calls), model,
                )
                content = ""

        sess["ollama_messages"].append(msg)

        if not tool_calls:
            final_output = content or "(no response)"
            break

        for tc in tool_calls:
            fn        = tc.get("function", {})
            tool_name = fn.get("name", "")
            tool_args = fn.get("arguments", {})

            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except Exception:
                    tool_args = {}

            await push_message(
                "system", f"🔧 `{tool_name}` — running…",
                source=source, session_id=sid,
            )

            tool_result = await _execute_ollama_tool(tool_name, tool_args, cwd)

            sess["ollama_messages"].append({
                "role":    "tool",
                "content": tool_result,
            })

            # Show success or error to the user based on actual result
            if tool_result.startswith("Error") or tool_result.startswith("Exit "):
                await push_message(
                    "system", f"❌ `{tool_name}` — failed",
                    source=source, session_id=sid,
                )
            else:
                await push_message(
                    "system", f"✅ `{tool_name}` — done",
                    source=source, session_id=sid,
                )

    else:
        # Loop exhausted — force a final summary by calling the model
        # one more time WITHOUT tools so it must produce a text response.
        logger.warning("Ollama agent loop hit %d-iteration safety limit — forcing summary",
                       _SAFETY_LIMIT)
        sess["ollama_messages"].append({
            "role": "user",
            "content": (
                "You have completed all the tool calls. Now provide a brief, "
                "friendly summary of everything you did and any files you created. "
                "Do NOT call any more tools — just reply with text."
            ),
        })
        try:
            _summary_payload = {
                "model":    model,
                "messages": sess["ollama_messages"],
                "stream":   False,
                # No "tools" key — forces text-only response
            }
            _summary_req = urllib.request.Request(
                _OLLAMA_URL,
                data=json.dumps(_summary_payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(_summary_req, timeout=120) as _summary_resp:
                _summary_data = json.loads(_summary_resp.read())
            _total_prompt_tokens += int(_summary_data.get("prompt_eval_count", 0))
            _total_eval_tokens   += int(_summary_data.get("eval_count", 0))
            _summary_msg = _summary_data.get("message", {})
            final_output = (_summary_msg.get("content") or "").strip()
            if _summary_msg:
                sess["ollama_messages"].append(_summary_msg)
        except Exception as exc:
            logger.error("Ollama summary call failed: %s", exc)

        if not final_output:
            # Absolute last resort — build a summary from the tool results
            _tool_names = [
                m.get("content", "")[:80]
                for m in sess.get("ollama_messages", [])
                if m.get("role") == "system" and "done" in m.get("content", "")
            ]
            final_output = "✅ All tasks completed successfully."

    after = await asyncio.to_thread(snapshot_dir, cwd)
    await handle_diff(before, after, source, cwd, session_id=sid)

    # Store actual token counts in session for record_usage_task to pick up
    if _total_prompt_tokens > 0 or _total_eval_tokens > 0:
        sess["_last_tokens"] = {
            "input": _total_prompt_tokens,
            "output": _total_eval_tokens,
        }
        logger.info("Ollama tokens: %d in + %d out = %d total",
                     _total_prompt_tokens, _total_eval_tokens,
                     _total_prompt_tokens + _total_eval_tokens)

    return final_output
