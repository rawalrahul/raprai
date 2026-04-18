"""File I/O node executor."""

import os


async def execute_file_node(node: dict, context: str) -> str:
    """Execute read/write/append/parse operations for a file node."""
    op = node.get("file_op", "read")
    path = node.get("file_path", "").strip()
    if not path:
        return "Error: file node requires file_path"

    if op == "read":
        return _read_text(path)
    if op == "write":
        return _write_text(path, node.get("task", "").strip() or context, "w")
    if op == "append":
        return _write_text(path, node.get("task", "").strip() or context, "a")
    if op == "parse_pdf":
        return _parse_pdf(path)
    if op == "parse_docx":
        return _parse_docx(path)
    return f"Error: unknown file_op '{op}'"


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: file not found - {path}"
    except Exception as exc:
        return f"Error reading file: {exc}"


def _write_text(path: str, content: str, mode: str) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        return f"OK: wrote {len(content)} chars to {path}"
    except Exception as exc:
        return f"Error writing file: {exc}"


def _parse_pdf(path: str) -> str:
    try:
        from pdfminer.high_level import extract_text
        return extract_text(path).strip() or "(empty PDF)"
    except ImportError:
        return "Error: pdfminer.six not installed - run: pip install pdfminer.six"
    except Exception as exc:
        return f"Error parsing PDF: {exc}"


def _parse_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines) or "(empty DOCX)"
    except ImportError:
        return "Error: python-docx not installed - run: pip install python-docx"
    except Exception as exc:
        return f"Error parsing DOCX: {exc}"
