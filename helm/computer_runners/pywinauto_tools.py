"""
helm/computer_runners/pywinauto_tools.py — Tier 3 semantic Win32 control.

Uses pywinauto's UI Automation backend to drive native Windows apps via
their accessibility tree instead of screenshot + coordinate guessing.

Why bother:
- ~10x faster: no vision round-trip per action.
- Far cheaper: no image tokens to the model.
- More reliable: clicks resolve by control name/automation_id, not pixel.

When it fails (custom-canvas apps, games, web inside an unrecognized
WebView host) fall back to the pyautogui pixel path in Tier 1.

All functions accept ``title`` as a substring match against the
top-level window title. They are synchronous; callers must wrap them
in ``asyncio.to_thread`` (see builtin_tools._run_computer_sync).
"""

from __future__ import annotations

import json
import sys


def _require_windows() -> str | None:
    """Return an error string if pywinauto cannot run here, else None."""
    if sys.platform != "win32":
        return "Error: pywinauto tools are Windows-only"
    return None


def _connect(title: str):
    """Locate the top-level window by title substring (UIA backend)."""
    from pywinauto import Application
    app = Application(backend="uia").connect(title_re=f".*{title}.*", timeout=3)
    win = app.window(title_re=f".*{title}.*")
    win.wait("exists", timeout=2)
    return win


def _control_info(ctrl, depth: int = 0, max_depth: int = 4) -> dict:
    """Compact one control + children for tree dumps. Max depth caps token bloat."""
    try:
        name = ctrl.element_info.name or ""
        ctype = ctrl.element_info.control_type or ""
        auto_id = ctrl.element_info.automation_id or ""
        rect = ctrl.element_info.rectangle
        info = {
            "name": name[:80],
            "type": ctype,
            "auto_id": auto_id[:60],
            "rect": [rect.left, rect.top, rect.right, rect.bottom],
        }
        if depth < max_depth:
            children = []
            for child in ctrl.children()[:25]:  # cap fan-out
                children.append(_control_info(child, depth + 1, max_depth))
            if children:
                info["children"] = children
        return info
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _find_control(win, name: str | None, auto_id: str | None, control_type: str | None):
    """Locate a descendant control. Prefer auto_id, fall back to name + type."""
    kwargs: dict = {}
    if auto_id:
        kwargs["auto_id"] = auto_id
    if name:
        kwargs["title"] = name
    if control_type:
        kwargs["control_type"] = control_type
    if not kwargs:
        raise ValueError("Need at least one of: name, auto_id, control_type")
    ctrl = win.descendants(**kwargs)
    if not ctrl:
        # fall back to relaxed title_re search
        if name:
            ctrl = win.descendants(title_re=f".*{name}.*")
    if not ctrl:
        raise LookupError(
            f"No control found matching name={name!r} auto_id={auto_id!r} type={control_type!r}"
        )
    return ctrl[0]


# ---------------------------------------------------------------------------
# Tool implementations — sync, called from _run_computer_sync.
# ---------------------------------------------------------------------------

def get_window_tree(args: dict) -> str:
    err = _require_windows()
    if err:
        return err
    title = str(args.get("title", "")).strip()
    if not title:
        return "Error: 'title' required"
    max_depth = int(args.get("max_depth", 4))
    try:
        win = _connect(title)
        tree = _control_info(win, depth=0, max_depth=max_depth)
        return json.dumps(tree)
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def click_control(args: dict) -> str:
    err = _require_windows()
    if err:
        return err
    title = str(args.get("title", "")).strip()
    if not title:
        return "Error: 'title' required"
    name = args.get("name")
    auto_id = args.get("auto_id")
    control_type = args.get("control_type")
    double = bool(args.get("double", False))
    try:
        win = _connect(title)
        ctrl = _find_control(win, name, auto_id, control_type)
        if double:
            ctrl.double_click_input()
        else:
            ctrl.click_input()
        return f"Clicked control: name={name!r} auto_id={auto_id!r} type={control_type!r}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def type_in_control(args: dict) -> str:
    err = _require_windows()
    if err:
        return err
    title = str(args.get("title", "")).strip()
    text = str(args.get("text", ""))
    if not title or not text:
        return "Error: 'title' and 'text' required"
    name = args.get("name")
    auto_id = args.get("auto_id")
    control_type = args.get("control_type")
    try:
        win = _connect(title)
        ctrl = _find_control(win, name, auto_id, control_type)
        ctrl.set_focus()
        # set_edit_text exists on Edit controls; fall back to type_keys.
        if hasattr(ctrl, "set_edit_text"):
            try:
                ctrl.set_edit_text(text)
                return f"Set text on control ({len(text)} chars)"
            except Exception:
                pass
        ctrl.type_keys(text, with_spaces=True, pause=0.01)
        return f"Typed into control ({len(text)} chars)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def get_control_value(args: dict) -> str:
    err = _require_windows()
    if err:
        return err
    title = str(args.get("title", "")).strip()
    if not title:
        return "Error: 'title' required"
    name = args.get("name")
    auto_id = args.get("auto_id")
    control_type = args.get("control_type")
    try:
        win = _connect(title)
        ctrl = _find_control(win, name, auto_id, control_type)
        # Try the most common property aggregators in order.
        for getter in ("window_text", "get_value", "legacy_properties"):
            fn = getattr(ctrl, getter, None)
            if fn:
                try:
                    val = fn()
                    return json.dumps({"getter": getter, "value": str(val)})
                except Exception:
                    continue
        return json.dumps({"getter": "none", "value": ""})
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
