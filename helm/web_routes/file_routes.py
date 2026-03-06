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

    # Deep-sanitise: make sure no secrets leak in any field or log line
    from helm.security import sanitize_diagnostics
    diag = sanitize_diagnostics(diag)

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
    from helm.security import validate_upload, MAX_UPLOAD_SIZE

    filename = file.filename or f"upload_{int(_time.time())}"

    # Read data with size limit enforcement
    try:
        data = await file.read()
    except Exception as exc:
        return JSONResponse({"error": f"Failed to read upload: {exc}"}, status_code=400)

    # Validate file type and size
    error = validate_upload(filename, len(data))
    if error:
        return JSONResponse({"error": error}, status_code=400)

    if len(data) > MAX_UPLOAD_SIZE:
        return JSONResponse(
            {"error": f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB."},
            status_code=413,
        )

    sid = _st.focused_id
    sess = _st.sessions.get(sid) if sid else None
    cwd = sess.get("cwd", _DEFAULT_CWD) if sess else _DEFAULT_CWD

    # Sanitize filename — prevent path traversal
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name.startswith("."):
        safe_name = f"upload_{int(_time.time())}"
    save_path = os.path.join(cwd, safe_name)

    # Prevent writing outside CWD
    resolved = os.path.realpath(save_path)
    if not resolved.startswith(os.path.realpath(cwd)):
        return JSONResponse({"error": "Invalid upload path"}, status_code=400)

    try:
        with open(save_path, "wb") as f:
            f.write(data)
        return JSONResponse({"filename": safe_name, "path": save_path, "size": len(data)})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
