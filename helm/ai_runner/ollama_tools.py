"""
helm/ai_runner/ollama_tools.py — The tools a local Ollama model can call: the fixed
list, MCP server tools, running a call, and reading calls written as plain text.

The agent loop that uses them is in ollama.py.
"""

import asyncio
import json
import pathlib
import re
import subprocess
import sys

from helm.config import logger
from helm.subprocess_utils import hidden_kwargs

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
            "name": "execute_shell",
            "description": (
                "Run a shell/terminal command in the user's working directory. "
                "Use for CLI tools like npx, npm, pip, git, playwright-cli, opencli, "
                "cli-anything, curl, and any other command-line programs. "
                "Returns stdout and stderr. Prefer this over execute_python when "
                "the task involves running CLI commands or tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "The shell command to execute (e.g. 'npx @playwright/cli open https://example.com', "
                            "'opencli hackernews top --limit 5', 'npm install -g package-name')"
                        ),
                    },
                },
                "required": ["command"],
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

    # Add Computer Use tools when enabled — schemas already in OpenAI format
    # (Ollama uses the same shape for function calling).
    from helm.builtin_tools import is_computer_use_enabled, COMPUTER_USE_TOOLS
    if is_computer_use_enabled():
        for t in COMPUTER_USE_TOOLS:
            tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["desc"],
                    "parameters": t["schema"],
                },
            })
        logger.debug("Ollama tools: added %d computer_use tools", len(COMPUTER_USE_TOOLS))

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
                **hidden_kwargs(),
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if result.returncode != 0:
                return f"Exit {result.returncode}:\n{err}\n{out}".strip()
            return out or "✓ executed (no output)"

        elif name == "execute_shell":
            command = args.get("command", "")
            if not command:
                return "Error: 'command' is required."
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True, text=True, timeout=600, cwd=cwd,
                shell=True,
                **hidden_kwargs(),
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if result.returncode != 0:
                return f"Exit {result.returncode}:\n{err}\n{out}".strip()
            return out or "✓ command executed (no output)"

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
            from helm.skill_creation import create_skill
            from helm.skills import get_user_skills_dir
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
                **hidden_kwargs(),
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
                **hidden_kwargs(),
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
                **hidden_kwargs(),
            )
            if result.returncode != 0:
                return f"Error creating document:\n{result.stderr.strip()}"
            fpath = pathlib.Path(cwd) / filename
            size  = fpath.stat().st_size if fpath.exists() else 0
            return f"✓ Created {filename} ({size:,} bytes) with {len(sections)} sections. Saved to: {fpath}"

        # Route Computer Use tools through the shared builtin dispatcher.
        from helm.builtin_tools import is_builtin_tool, execute_builtin_tool
        if is_builtin_tool(name):
            return await execute_builtin_tool(name, args, cwd)

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

    Handles all common formats (tried in order):
      1. [tool_name] {"arg": "val"}       (bracket pseudo-call notation)
      2. {"name": "fn", "arguments": {...}}
      3. [{"name": "fn", "arguments": {...}}, ...]
      4. ```json\n{...}\n```
      5. <tool_call>{...}</tool_call>
      6. ```bash\n<command>\n```           (bash code blocks → execute_shell)

    Returns a list of synthetic tool-call dicts matching the shape our agent
    loop already expects:  [{"function": {"name": ..., "arguments": ...}}, ...]
    """
    if not content:
        return []

    text = content.strip()

    # ── 1. Try [tool_name] {...} pattern ──
    # Models often output:  [execute_shell] {"command": "npx ..."}
    bracket_calls = re.findall(
        r'\[(\w+)\]\s*\{([^}]+)\}', content, re.DOTALL,
    )
    if bracket_calls:
        result = []
        for tool_name, json_body in bracket_calls:
            try:
                args = json.loads("{" + json_body + "}")
            except (json.JSONDecodeError, ValueError):
                continue
            result.append({"function": {"name": tool_name, "arguments": args}})
        if result:
            return result

    # ── 2. Try structured JSON formats ──

    # Strip markdown code fences (json / tool_call only, NOT bash)
    fence = re.search(r'```(?:json|tool_call)?\s*(\[.*?\]|\{.*?\})\s*```',
                      text, re.DOTALL)
    if fence:
        text = fence.group(1)

    # Strip XML-style tool_call tags
    xml = re.search(r'<tool_call>\s*(\{.*?\}|\[.*?\])\s*</tool_call>',
                    text, re.DOTALL)
    if xml:
        text = xml.group(1)

    parsed = None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

    if parsed is not None:
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list):
            result = []
            for item in parsed:
                if not isinstance(item, dict) or "name" not in item:
                    continue
                args = item.get("arguments") or item.get("parameters") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                result.append({"function": {"name": item["name"], "arguments": args}})
            if result:
                return result

    # ── 3. Final fallback: detect ```bash / ```shell code blocks ──
    # Many models output shell commands as markdown code blocks instead of
    # calling execute_shell.  Convert them automatically.
    bash_blocks = re.findall(
        r'```(?:bash|shell|sh|cmd|powershell|terminal|console)\s*\n(.+?)```',
        content, re.DOTALL,
    )
    if bash_blocks:
        return [
            {"function": {"name": "execute_shell",
                          "arguments": {"command": cmd.strip()}}}
            for cmd in bash_blocks
            if cmd.strip()
        ]

    return []
