"""
helm/web_routes/file_routes.py — Generated files listing, diagnostics export.
"""

import json
import os
import pathlib
import platform
import subprocess as _sub
import sys as _sys
import time as _time
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse, Response

import helm.state as _st
from helm.history import ts
from .app import _find_cli


router = APIRouter()


# ---------------------------------------------------------------------------
# Generated Files / Output Manager
# ---------------------------------------------------------------------------

@router.get("/generated-files")
async def list_generated_files():
    """Return the list of AI-generated files across all sessions."""
    result = []
    for f in reversed(_st.generated_files):  # newest first
        entry = dict(f)
        entry["age"] = _time.time() - entry.get("ts", 0)
        # Check if file still exists
        entry["exists"] = pathlib.Path(entry["path"]).exists()
        result.append(entry)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Bug Reporting & Diagnostics Export
# ---------------------------------------------------------------------------

@router.get("/diagnostics")
async def diagnostics_export():
    """Bundle system info, recent logs, session state into a downloadable JSON."""
    diag: dict = {
        "generated_at": ts(),
        "system": {
            "os": platform.platform(),
            "python": _sys.version,
            "machine": platform.machine(),
        },
        "server": {
            "web_port": int(os.environ.get("WEB_PORT", "8000")),
            "web_host": os.environ.get("WEB_HOST", "127.0.0.1"),
            "uptime_seconds": round(_time.time() - _st.usage_period_start),
        },
        "sessions": {
            "count": len(_st.sessions),
            "focused_id": _st.focused_id,
            "details": [],
        },
        "integrations": [],
        "recent_errors": [],
    }

    # Session info (no message content)
    for sid, sess in _st.sessions.items():
        diag["sessions"]["details"].append({
            "id": sid,
            "name": sess.get("name", ""),
            "ai": sess.get("ai", ""),
            "model": sess.get("model", ""),
            "status": sess.get("status", ""),
            "cwd": sess.get("cwd", ""),
            "busy": sess.get("busy", False),
            "task_count": sess.get("task_count", 0),
        })

    # Integration status (no secrets)
    for key, info in _st.integrations.items():
        diag["integrations"].append({
            "key": key,
            "name": info.get("name", key),
            "cli_found": bool(_find_cli(key)),
        })

    # CLI versions
    for cli_name in ("claude", "gemini", "codex", "ollama"):
        try:
            r = _sub.run([cli_name, "--version"], capture_output=True, text=True, timeout=5)
            diag["system"][f"{cli_name}_version"] = r.stdout.strip()[:100] or r.stderr.strip()[:100]
        except Exception:
            diag["system"][f"{cli_name}_version"] = "not found"

    # Recent log entries (last 100 lines from Python logger)
    import logging
    for handler in logging.getLogger("helm").handlers:
        if hasattr(handler, "baseFilename"):
            try:
                with open(handler.baseFilename, "r") as f:
                    lines = f.readlines()
                    diag["recent_logs"] = [l.rstrip() for l in lines[-100:]]
            except Exception:
                pass

    # Sanitise: make sure no secrets leak
    for key in ("TELEGRAM_BOT_TOKEN", "PIN_HASH", "PIN_SALT", "WEBHOOK_TOKEN",
                "GEMINI_API_KEY", "OPENAI_API_KEY"):
        diag.pop(key, None)

    payload = json.dumps(diag, indent=2, default=str)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="helm_diagnostics_{ts()[:10]}.json"'
        },
    )


# ---------------------------------------------------------------------------
# File Upload — save attachment to the focused session's CWD
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Save an uploaded file to the active session's CWD."""
    from helm.config import _DEFAULT_CWD

    sid = _st.focused_id
    sess = _st.sessions.get(sid) if sid else None
    cwd = sess.get("cwd", _DEFAULT_CWD) if sess else _DEFAULT_CWD

    filename = file.filename or f"upload_{int(_time.time())}"
    save_path = os.path.join(cwd, filename)

    try:
        data = await file.read()
        with open(save_path, "wb") as f:
            f.write(data)
        return JSONResponse({"filename": filename, "path": save_path, "size": len(data)})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
