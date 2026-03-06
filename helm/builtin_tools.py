"""
helm/builtin_tools.py — Shared built-in tool execution for all AI runners.

Exposes document generation tools (create_presentation, create_pdf,
create_document) that were previously Ollama-only. These can now be
called from any AI via the agent_loop or HTTP /mcp/call endpoint.
"""

from __future__ import annotations

import asyncio
import pathlib
import subprocess
import sys

from helm.config import logger

# Names of built-in tools
BUILTIN_TOOL_NAMES = {"create_presentation", "create_pdf", "create_document"}

# Short descriptions for prompt injection
BUILTIN_TOOL_DOCS = (
    "- create_presentation: Create .pptx. Args: filename, title, subtitle, theme(dark/corporate/light/forest), "
    "slides(array of {type,title,bullets/content}). Types: content,two_column,stat,section,timeline,comparison,quote,cards,table,closing\n"
    "- create_pdf: Create .pdf. Args: filename, title, subtitle, sections(array of {heading,body})\n"
    "- create_document: Create .docx. Args: filename, title, sections(array of {heading,body})\n"
)


def is_builtin_tool(name: str) -> bool:
    """Check if a tool name is a built-in tool."""
    return name in BUILTIN_TOOL_NAMES


async def execute_builtin_tool(name: str, args: dict, cwd: str) -> str:
    """Execute a built-in tool and return the result string.

    Raises ValueError if tool name is unknown.
    """
    if name == "create_presentation":
        return await _exec_presentation(args, cwd)
    elif name == "create_pdf":
        return await _exec_pdf(args, cwd)
    elif name == "create_document":
        return await _exec_document(args, cwd)
    else:
        raise ValueError(f"Unknown built-in tool: {name}")


async def _exec_presentation(args: dict, cwd: str) -> str:
    from helm.ai_runner.doc_generators import _generate_pptx_code

    filename = args.get("filename", "Presentation.pptx")
    if not filename.endswith(".pptx"):
        filename += ".pptx"
    title = args.get("title", "Presentation")
    subtitle = args.get("subtitle", "")
    theme = args.get("theme", "dark")
    slides = args.get("slides", [])
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
    size = fpath.stat().st_size if fpath.exists() else 0
    return (
        f"✓ Created {filename} ({size:,} bytes) with {len(slides)+1} slides. "
        f"Saved to: {fpath}"
    )


async def _exec_pdf(args: dict, cwd: str) -> str:
    from helm.ai_runner.doc_generators import _generate_pdf_code

    filename = args.get("filename", "Document.pdf")
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    title = args.get("title", "Document")
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
    size = fpath.stat().st_size if fpath.exists() else 0
    return f"✓ Created {filename} ({size:,} bytes) with {len(sections)} sections. Saved to: {fpath}"


async def _exec_document(args: dict, cwd: str) -> str:
    from helm.ai_runner.doc_generators import _generate_docx_code

    filename = args.get("filename", "Document.docx")
    if not filename.endswith(".docx"):
        filename += ".docx"
    title = args.get("title", "Document")
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
    size = fpath.stat().st_size if fpath.exists() else 0
    return f"✓ Created {filename} ({size:,} bytes) with {len(sections)} sections. Saved to: {fpath}"
