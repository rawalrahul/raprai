"""
helm/builtin_tools.py — Shared built-in tool execution for all AI runners.

Exposes document generation tools (create_presentation, create_pdf,
create_document) that were previously Ollama-only. These can now be
called from any AI via the agent_loop or HTTP /mcp/call endpoint.

Also exposes the optional Computer Use tool surface (mouse/keyboard/window
control) when the COMPUTER_USE env flag is enabled. All computer tools
serialize through a single asyncio lock so concurrent agent_loop dispatch
cannot interleave keystrokes or clicks.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import subprocess
import sys

from helm.config import logger

# ---------------------------------------------------------------------------
# Module init: per-monitor DPI awareness on Windows.
# Without this, pyautogui reports logical (scaled) coordinates and every
# click lands off-target on Win11's default 125-150% display scaling.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        # Older Windows, already set by parent process, or shcore unavailable
        pass


# Names of built-in tools
BUILTIN_TOOL_NAMES = {"create_presentation", "create_pdf", "create_document"}

# Short descriptions for prompt injection
BUILTIN_TOOL_DOCS = (
    "- create_presentation: Create .pptx. Args: filename, title, subtitle, theme(dark/corporate/light/forest), "
    "slides(array of {type,title,bullets/content}). Types: content,two_column,stat,section,timeline,comparison,quote,cards,table,closing\n"
    "- create_pdf: Create .pdf. Args: filename, title, subtitle, sections(array of {heading,body})\n"
    "- create_document: Create .docx. Args: filename, title, sections(array of {heading,body})\n"
)


# ---------------------------------------------------------------------------
# Computer Use tool surface
# ---------------------------------------------------------------------------
def is_computer_use_enabled() -> bool:
    """True when the COMPUTER_USE env flag is set to a truthy value."""
    return os.environ.get("COMPUTER_USE", "false").lower() == "true"


# Serialization lock — agent_loop dispatches tools via asyncio.gather,
# so two concurrent pyautogui calls would interleave input events.
_COMPUTER_LOCK = asyncio.Lock()

# Single source of truth: descriptions for Tier 1 prompt injection AND
# JSON schemas for Tier 2 native function calling.
COMPUTER_USE_TOOLS = [
    {"name": "computer_screenshot",
     "desc": "Capture screen. Args: region? [x,y,w,h]. Returns saved PNG path.",
     "schema": {"type": "object", "properties": {
         "region": {"type": "array", "items": {"type": "integer"},
                    "minItems": 4, "maxItems": 4},
     }, "required": []}},
    {"name": "computer_click",
     "desc": "Click at coords. Args: x, y, button?(left|right|middle), clicks?(int)",
     "schema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
         "button": {"type": "string", "enum": ["left", "right", "middle"]},
         "clicks": {"type": "integer", "minimum": 1},
     }, "required": ["x", "y"]}},
    {"name": "computer_double_click",
     "desc": "Double-click. Args: x, y",
     "schema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
     }, "required": ["x", "y"]}},
    {"name": "computer_right_click",
     "desc": "Right-click. Args: x, y",
     "schema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
     }, "required": ["x", "y"]}},
    {"name": "computer_move",
     "desc": "Move mouse. Args: x, y",
     "schema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
     }, "required": ["x", "y"]}},
    {"name": "computer_type",
     "desc": "Type text at focus. Args: text, interval?(seconds per char)",
     "schema": {"type": "object", "properties": {
         "text": {"type": "string"},
         "interval": {"type": "number", "minimum": 0},
     }, "required": ["text"]}},
    {"name": "computer_key",
     "desc": "Press key/hotkey. Args: keys (e.g. 'ctrl+c', 'enter', 'alt+tab')",
     "schema": {"type": "object", "properties": {
         "keys": {"type": "string"},
     }, "required": ["keys"]}},
    {"name": "computer_scroll",
     "desc": "Scroll at position. Args: x, y, amount (negative=down)",
     "schema": {"type": "object", "properties": {
         "x": {"type": "integer"}, "y": {"type": "integer"},
         "amount": {"type": "integer"},
     }, "required": ["amount"]}},
    {"name": "computer_get_windows",
     "desc": "List visible windows. Returns JSON array of {title,left,top,width,height}",
     "schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "computer_focus_window",
     "desc": "Bring window to foreground by title substring. Args: title",
     "schema": {"type": "object", "properties": {
         "title": {"type": "string"},
     }, "required": ["title"]}},
    {"name": "computer_resize_window",
     "desc": "Move + resize window. Args: title, x, y, w, h",
     "schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "x": {"type": "integer"}, "y": {"type": "integer"},
         "w": {"type": "integer"}, "h": {"type": "integer"},
     }, "required": ["title", "x", "y", "w", "h"]}},
    {"name": "computer_open_app",
     "desc": "Launch app by name (resolved via PATH) or absolute path. Args: path",
     "schema": {"type": "object", "properties": {
         "path": {"type": "string"},
     }, "required": ["path"]}},
    {"name": "computer_get_cursor",
     "desc": "Get mouse position. Returns {x,y}",
     "schema": {"type": "object", "properties": {}, "required": []}},

    # ── Tier 3: pywinauto semantic Win32 control ──────────────────────
    {"name": "computer_get_window_tree",
     "desc": ("Win32 accessibility tree for a window (semantic, no vision). "
              "Args: title (substring), max_depth?(default 4). "
              "Returns JSON of {name,type,auto_id,rect,children}."),
     "schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "max_depth": {"type": "integer", "minimum": 1, "maximum": 8},
     }, "required": ["title"]}},
    {"name": "computer_click_control",
     "desc": ("Click a control by accessibility name/auto_id (semantic, no pixels). "
              "Args: title, name?, auto_id?, control_type?, double?"),
     "schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "name": {"type": "string"},
         "auto_id": {"type": "string"},
         "control_type": {"type": "string"},
         "double": {"type": "boolean"},
     }, "required": ["title"]}},
    {"name": "computer_type_in_control",
     "desc": ("Type text into a named control (focuses + sets text). "
              "Args: title, text, name?, auto_id?, control_type?"),
     "schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "text": {"type": "string"},
         "name": {"type": "string"},
         "auto_id": {"type": "string"},
         "control_type": {"type": "string"},
     }, "required": ["title", "text"]}},
    {"name": "computer_get_control_value",
     "desc": ("Read text/value of a named control. "
              "Args: title, name?, auto_id?, control_type?"),
     "schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "name": {"type": "string"},
         "auto_id": {"type": "string"},
         "control_type": {"type": "string"},
     }, "required": ["title"]}},

    # ── OmniParser: vision element detection (opt-in) ─────────────────
    {"name": "computer_parse_screen",
     "desc": ("Detect UI elements on screen (OmniParser YOLO+Florence). "
              "Returns JSON list of {bbox,center,label,conf}. "
              "Args: conf?(0..1, default 0.25), max_elements?(default 60). "
              "Requires OMNIPARSER_ENABLED=true and ML deps installed."),
     "schema": {"type": "object", "properties": {
         "conf": {"type": "number", "minimum": 0, "maximum": 1},
         "max_elements": {"type": "integer", "minimum": 1, "maximum": 200},
     }, "required": []}},
]

_COMPUTER_TOOL_NAMES = {t["name"] for t in COMPUTER_USE_TOOLS}


def get_computer_use_tool_descriptions() -> str:
    """Render computer tool list as a text block for prompt injection."""
    return "".join(f"- {t['name']}: {t['desc']}\n" for t in COMPUTER_USE_TOOLS)


def is_builtin_tool(name: str) -> bool:
    """Check if a tool name is a built-in tool."""
    if name in BUILTIN_TOOL_NAMES:
        return True
    if is_computer_use_enabled() and name in _COMPUTER_TOOL_NAMES:
        return True
    return False


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
    elif name in _COMPUTER_TOOL_NAMES:
        if not is_computer_use_enabled():
            return "Error: Computer Use is disabled. Enable it in Settings."
        return await _exec_computer(name, args, cwd)
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


# ---------------------------------------------------------------------------
# Computer Use executor
# ---------------------------------------------------------------------------
async def _exec_computer(name: str, args: dict, cwd: str) -> str:
    """Run a computer tool under the global serialization lock.

    pyautogui calls are blocking; offload to a thread so the event loop
    stays responsive. The lock prevents two parallel agent tool calls
    from interleaving mouse/keyboard input.
    """
    async with _COMPUTER_LOCK:
        return await asyncio.to_thread(_run_computer_sync, name, args, cwd)


def _run_computer_sync(name: str, args: dict, cwd: str) -> str:
    """Synchronous dispatcher. Lazy imports keep startup fast when disabled."""
    import datetime
    import json

    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
    except Exception as e:
        return f"Error: pyautogui import failed: {e}"

    try:
        if name == "computer_screenshot":
            import mss
            shots_dir = pathlib.Path(cwd) / ".rapr_screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            out = shots_dir / f"screenshot_{ts}.png"
            with mss.mss() as sct:
                region = args.get("region")
                if region and len(region) == 4:
                    x, y, w, h = region
                    mon = {"left": x, "top": y, "width": w, "height": h}
                else:
                    mon = sct.monitors[1]  # primary monitor
                img = sct.grab(mon)
                mss.tools.to_png(img.rgb, img.size, output=str(out))
            return (f"Screenshot saved: {out} "
                    f"(size {out.stat().st_size} bytes, {img.size[0]}x{img.size[1]})")

        if name == "computer_click":
            x, y = int(args["x"]), int(args["y"])
            button = args.get("button", "left")
            clicks = int(args.get("clicks", 1))
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return f"Clicked ({x},{y}) button={button} clicks={clicks}"

        if name == "computer_double_click":
            x, y = int(args["x"]), int(args["y"])
            pyautogui.doubleClick(x=x, y=y)
            return f"Double-clicked ({x},{y})"

        if name == "computer_right_click":
            x, y = int(args["x"]), int(args["y"])
            pyautogui.rightClick(x=x, y=y)
            return f"Right-clicked ({x},{y})"

        if name == "computer_move":
            x, y = int(args["x"]), int(args["y"])
            pyautogui.moveTo(x, y, duration=0.2)
            return f"Moved to ({x},{y})"

        if name == "computer_type":
            text = str(args.get("text", ""))
            interval = float(args.get("interval", 0.01))
            if text.isascii():
                pyautogui.write(text, interval=interval)
            else:
                # Unicode fallback: clipboard paste keeps emoji / non-ASCII intact.
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
            return f"Typed {len(text)} chars"

        if name == "computer_key":
            keys = str(args["keys"]).strip()
            parts = [k.strip() for k in keys.split("+") if k.strip()]
            if len(parts) == 1:
                pyautogui.press(parts[0])
            else:
                pyautogui.hotkey(*parts)
            return f"Pressed: {keys}"

        if name == "computer_scroll":
            x = int(args.get("x", pyautogui.position().x))
            y = int(args.get("y", pyautogui.position().y))
            amount = int(args["amount"])
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.scroll(amount)
            return f"Scrolled {amount} at ({x},{y})"

        if name == "computer_get_windows":
            import pygetwindow as gw
            wins = []
            for w in gw.getAllWindows():
                if not w.title:
                    continue
                wins.append({"title": w.title, "left": w.left, "top": w.top,
                             "width": w.width, "height": w.height})
            return json.dumps(wins[:50])  # cap to prevent prompt bloat

        if name == "computer_focus_window":
            import pygetwindow as gw
            title = str(args["title"])
            matches = gw.getWindowsWithTitle(title)
            if not matches:
                return f"Error: no window matching '{title}'"
            w = matches[0]
            try:
                if w.isMinimized:
                    w.restore()
                w.activate()
            except Exception as e:
                # Win32 sometimes denies activate(); fall back to minimize+restore
                try:
                    w.minimize()
                    w.restore()
                except Exception:
                    return f"Error focusing '{w.title}': {e}"
            return f"Focused: {w.title}"

        if name == "computer_resize_window":
            import pygetwindow as gw
            title = str(args["title"])
            matches = gw.getWindowsWithTitle(title)
            if not matches:
                return f"Error: no window matching '{title}'"
            w = matches[0]
            w.moveTo(int(args["x"]), int(args["y"]))
            w.resizeTo(int(args["w"]), int(args["h"]))
            return (f"Resized '{w.title}' to ({args['x']},{args['y']}) "
                    f"{args['w']}x{args['h']}")

        if name == "computer_open_app":
            import shutil
            raw = str(args["path"]).strip()
            # shell=False + shutil.which() — AI-provided strings cannot inject
            # shell metacharacters (`&`, `|`, `;`, backticks).
            resolved = shutil.which(raw) or raw
            if (not pathlib.Path(resolved).is_absolute()
                    and not shutil.which(resolved)):
                return f"Error: app '{raw}' not found on PATH and not an absolute path"
            proc = subprocess.Popen([resolved], shell=False)
            return f"Launched: {resolved} (pid={proc.pid})"

        if name == "computer_get_cursor":
            p = pyautogui.position()
            return json.dumps({"x": p.x, "y": p.y})

        # ── Tier 3: pywinauto semantic control ────────────────────────
        if name == "computer_get_window_tree":
            from helm.computer_runners import pywinauto_tools
            return pywinauto_tools.get_window_tree(args)
        if name == "computer_click_control":
            from helm.computer_runners import pywinauto_tools
            return pywinauto_tools.click_control(args)
        if name == "computer_type_in_control":
            from helm.computer_runners import pywinauto_tools
            return pywinauto_tools.type_in_control(args)
        if name == "computer_get_control_value":
            from helm.computer_runners import pywinauto_tools
            return pywinauto_tools.get_control_value(args)

        # ── OmniParser: vision-driven element detection ───────────────
        if name == "computer_parse_screen":
            from helm.computer_runners import omniparser
            return omniparser.parse_screen(args)

        return f"Error: unknown computer tool '{name}'"

    except pyautogui.FailSafeException:
        return ("Error: PyAutoGUI fail-safe triggered (mouse moved to corner). "
                "Operation aborted.")
    except KeyError as e:
        return f"Error: missing required argument {e}"
    except Exception as e:
        logger.exception("computer tool '%s' failed", name)
        return f"Error: {type(e).__name__}: {e}"
