"""
helm/web_routes/history_routes.py — History list, search, export, delete, rename endpoints.
"""

import asyncio
import json
import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

import helm.state as _st
from helm.config import CHAT_LOG_DIR, HISTORY_ID_RE, logger
from helm.history import (
    is_valid_history_id, load_chat_names, rebuild_hist_cache_sync,
    save_chat_name, get_history_messages,
)


router = APIRouter()


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------

@router.get("/history")
async def history_list(force: bool = False):
    """Return history session list."""
    if force:
        sessions = await asyncio.get_event_loop().run_in_executor(None, rebuild_hist_cache_sync)
        return JSONResponse(sessions)
    age = time.time() - _st.hist_cache_ts
    if age > 15 or not _st.hist_cache_ts:
        asyncio.get_event_loop().run_in_executor(None, rebuild_hist_cache_sync)
    return JSONResponse(_st.hist_cache)


@router.get("/history/search")
async def history_search(q: str = ""):
    """Full-text search across all chat log files."""
    q = q.strip()
    if len(q) < 2:
        return JSONResponse([])

    lq = q.lower()
    names = load_chat_names()
    results: list[dict] = []

    if not CHAT_LOG_DIR.exists():
        return JSONResponse([])

    log_files = sorted(
        [f for f in CHAT_LOG_DIR.glob("*.jsonl") if HISTORY_ID_RE.fullmatch(f.stem)],
        reverse=True,
    )

    for log_file in log_files:
        date_str = log_file.stem
        snippet = ""
        match_count = 0
        last_ai = ""
        last_ts = None

        try:
            for raw_line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    rec = json.loads(raw_line)
                except Exception:
                    continue
                if rec.get("type") != "message":
                    if rec.get("ai"):
                        last_ai = rec["ai"]
                    continue
                content: str = rec.get("content", "")
                if rec.get("ai"):
                    last_ai = rec["ai"]
                if rec.get("ts"):
                    last_ts = rec["ts"]
                idx = content.lower().find(lq)
                if idx != -1:
                    match_count += 1
                    if not snippet:
                        start = max(0, idx - 60)
                        end   = min(len(content), idx + len(q) + 60)
                        excerpt = content[start:end].replace("\n", " ").strip()
                        if start > 0:
                            excerpt = "..." + excerpt
                        if end < len(content):
                            excerpt = excerpt + "..."
                        snippet = excerpt
        except Exception:
            continue

        if match_count > 0:
            results.append({
                "date": date_str,
                "name": names.get(date_str, ""),
                "snippet": snippet,
                "match_count": match_count,
                "ai": last_ai,
                "ts": last_ts,
            })
            if len(results) >= 20:
                break

    return JSONResponse(results)


@router.get("/history/{date}")
async def history_get(date: str):
    """Return all messages for a given date or path ID."""
    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)
    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    messages = []
    last_cwd = None
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("type") == "cwd":
                last_cwd = rec["path"]
            elif rec.get("type") == "message":
                messages.append(rec)
        except Exception:
            pass
    return JSONResponse({"messages": messages, "cwd": last_cwd})


@router.get("/history/{date}/resume")
async def history_resume(date: str):
    """Return context prefix for resuming a session."""
    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)

    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)

    messages = []
    try:
        for line in log_file.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                if rec.get("role") in ("user", "assistant"):
                    messages.append(rec)
            except Exception:
                continue
    except Exception:
        pass

    if not messages:
        return JSONResponse({"context": ""})

    turns = messages[-10:]
    lines_ctx = []
    for m in turns:
        role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
        body = (m.get("content") or "")[:300]
        if len(m.get("content", "")) > 300:
            body += "..."
        lines_ctx.append(f"{role}: {body}")

    label = load_chat_names().get(date) or date
    context_prefix = (
        f"[Previous conversation — {label}]\n"
        + "\n".join(lines_ctx)
        + "\n[End context]\n\n"
    )
    return JSONResponse({"context": context_prefix})


@router.delete("/history/{date}")
async def history_delete(date: str):
    """Delete the log file for a given ID."""
    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)
    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    try:
        log_file.unlink()
        save_chat_name(date, "")  # remove custom name entry if any
        _st.hist_cache_ts = 0    # invalidate cache
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/history/{date}/rename")
@router.patch("/history/{date}/name")
async def history_rename(date: str, request: Request):
    """Set or clear a custom display name for a chat session ID."""
    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    log_file = CHAT_LOG_DIR / f"{date}.jsonl"
    if not log_file.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    save_chat_name(date, name)
    _st.hist_cache_ts = 0  # invalidate cache
    return JSONResponse({"ok": True, "name": name})


@router.get("/history/{hid}/export")
async def history_export(hid: str, format: str = "md"):
    """Export chat history in Markdown, text, or JSON format.

    Args:
        hid: History ID (date or path ID)
        format: Export format — 'md' (default), 'txt', or 'json'
    """
    if not is_valid_history_id(hid):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)

    # Get the AI name from cache or infer from messages
    ai_name = "AI"
    for sess in _st.hist_cache:
        if sess.get("date") == hid:
            ai_name = sess.get("ai") or "AI"
            break

    messages = get_history_messages(hid)
    if not messages and not CHAT_LOG_DIR.joinpath(f"{hid}.jsonl").exists():
        return JSONResponse({"error": "Not found"}, status_code=404)

    if format == "json":
        # Raw JSON export
        content = json.dumps(messages, ensure_ascii=False, indent=2)
        media_type = "application/json"
        filename = f"chat_{hid}.json"
    elif format == "txt":
        # Plain text format
        lines = []
        for msg in messages:
            role = "User" if msg.get("role") == "user" else msg.get("ai") or ai_name
            content_text = msg.get("content", "").strip()
            lines.append(f"[{role}]: {content_text}\n")
        content = "\n".join(lines)
        media_type = "text/plain"
        filename = f"chat_{hid}.txt"
    else:
        # Markdown format (default)
        lines = []
        for msg in messages:
            if msg.get("role") == "user":
                lines.append(f"## User\n\n{msg.get('content', '')}\n\n")
            else:
                role_name = msg.get("ai") or ai_name
                lines.append(f"## Assistant ({role_name})\n\n{msg.get('content', '')}\n\n---\n\n")
        content = "".join(lines)
        media_type = "text/markdown"
        filename = f"chat_{hid}.md"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ---------------------------------------------------------------------------
# Session Templates
# ---------------------------------------------------------------------------

@router.get("/templates")
async def list_templates():
    """Return list of saved session templates."""
    templates_file = CHAT_LOG_DIR / "templates.json"
    if not templates_file.exists():
        return JSONResponse([])
    try:
        templates = json.loads(templates_file.read_text(encoding="utf-8"))
        return JSONResponse(list(templates.values()) if isinstance(templates, dict) else templates)
    except Exception as e:
        logger.warning("Failed to load templates: %s", e)
        return JSONResponse([])


@router.post("/templates")
async def create_template(request: Request):
    """Save a new session template."""
    from helm.history import ts
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
        if not name:
            return JSONResponse({"error": "Template name is required"}, status_code=400)

        template = {
            "name": name,
            "ai": body.get("ai", ""),
            "cwd": body.get("cwd", ""),
            "model": body.get("model", ""),
            "prompt": body.get("prompt", ""),
            "timestamp": ts(),
        }

        CHAT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        templates_file = CHAT_LOG_DIR / "templates.json"
        templates = {}
        if templates_file.exists():
            try:
                templates = json.loads(templates_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        templates[name] = template
        templates_file.write_text(json.dumps(templates, ensure_ascii=False, indent=2), encoding="utf-8")
        return JSONResponse({"ok": True, "template": template})
    except Exception as e:
        logger.error("Failed to save template: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/templates/{name}")
async def delete_template(name: str):
    """Delete a saved template."""
    if not name or "/" in name or "\\" in name:
        return JSONResponse({"error": "Invalid template name"}, status_code=400)

    try:
        templates_file = CHAT_LOG_DIR / "templates.json"
        if not templates_file.exists():
            return JSONResponse({"error": "Not found"}, status_code=404)

        templates = json.loads(templates_file.read_text(encoding="utf-8"))
        if name not in templates:
            return JSONResponse({"error": "Not found"}, status_code=404)

        del templates[name]
        templates_file.write_text(json.dumps(templates, ensure_ascii=False, indent=2), encoding="utf-8")
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error("Failed to delete template: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
