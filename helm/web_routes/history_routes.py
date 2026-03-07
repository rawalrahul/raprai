"""
helm/web_routes/history_routes.py — History list, search, export, delete, rename endpoints.

All data is now read from/written to the SQLite database via helm/db.py.
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
    """Full-text search across all chat messages in the database."""
    from helm.db import get_db

    q = q.strip()
    if len(q) < 2:
        return JSONResponse([])

    db = get_db()
    names = load_chat_names()
    results: list[dict] = []

    try:
        # Try FTS5 first (if migration v2 succeeded)
        try:
            fts_rows = db.execute(
                """SELECT history_id, snippet(messages_fts, 0, '', '', '...', 30) as snippet
                   FROM messages_fts
                   WHERE content MATCH ?
                   ORDER BY rank
                   LIMIT 20""",
                (q,),
            ).fetchall()

            seen_hids = set()
            for row in fts_rows:
                hid = row["history_id"]
                if hid in seen_hids:
                    continue
                seen_hids.add(hid)

                # Get additional metadata
                meta = db.execute(
                    """SELECT ai, ts FROM messages
                       WHERE history_id = ? AND type = 'message'
                       ORDER BY id DESC LIMIT 1""",
                    (hid,),
                ).fetchone()

                count_row = db.execute(
                    """SELECT COUNT(*) as cnt FROM messages_fts
                       WHERE history_id = ? AND content MATCH ?""",
                    (hid, q),
                ).fetchone()

                results.append({
                    "date": hid,
                    "name": names.get(hid, ""),
                    "snippet": row["snippet"],
                    "match_count": count_row["cnt"] if count_row else 1,
                    "ai": meta["ai"] if meta else "",
                    "ts": meta["ts"] if meta else None,
                })

            return JSONResponse(results)

        except Exception:
            # FTS5 not available — fall back to LIKE search
            pass

        # Fallback: LIKE search
        lq = f"%{q}%"
        rows = db.execute(
            """SELECT DISTINCT history_id FROM messages
               WHERE type = 'message' AND content LIKE ?
               LIMIT 20""",
            (lq,),
        ).fetchall()

        for row in rows:
            hid = row["history_id"]

            # Get a snippet
            snippet_row = db.execute(
                """SELECT content FROM messages
                   WHERE history_id = ? AND type = 'message' AND content LIKE ?
                   LIMIT 1""",
                (hid, lq),
            ).fetchone()
            snippet = ""
            if snippet_row and snippet_row["content"]:
                content = snippet_row["content"]
                idx = content.lower().find(q.lower())
                if idx >= 0:
                    start = max(0, idx - 60)
                    end = min(len(content), idx + len(q) + 60)
                    excerpt = content[start:end].replace("\n", " ").strip()
                    if start > 0:
                        excerpt = "..." + excerpt
                    if end < len(content):
                        excerpt = excerpt + "..."
                    snippet = excerpt

            # Count matches
            count_row = db.execute(
                """SELECT COUNT(*) as cnt FROM messages
                   WHERE history_id = ? AND type = 'message' AND content LIKE ?""",
                (hid, lq),
            ).fetchone()

            # Last AI and ts
            meta = db.execute(
                """SELECT ai, ts FROM messages
                   WHERE history_id = ? AND type = 'message'
                   ORDER BY id DESC LIMIT 1""",
                (hid,),
            ).fetchone()

            results.append({
                "date": hid,
                "name": names.get(hid, ""),
                "snippet": snippet,
                "match_count": count_row["cnt"] if count_row else 1,
                "ai": meta["ai"] if meta else "",
                "ts": meta["ts"] if meta else None,
            })

        return JSONResponse(results)

    except Exception as e:
        logger.warning("History search error: %s", e)
        return JSONResponse([])


@router.get("/history/{date}")
async def history_get(date: str):
    """Return all messages for a given date or path ID."""
    from helm.db import get_db

    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)

    db = get_db()

    # Check if this history_id exists
    exists = db.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE history_id = ?", (date,)
    ).fetchone()
    if not exists or exists["cnt"] == 0:
        return JSONResponse({"error": "Not found"}, status_code=404)

    messages = get_history_messages(date)

    # Get last CWD and AI
    last_cwd = None
    cwd_row = db.execute(
        """SELECT path FROM messages
           WHERE history_id = ? AND type = 'cwd' AND path IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (date,),
    ).fetchone()
    if cwd_row:
        last_cwd = cwd_row["path"]

    last_ai = ""
    ai_row = db.execute(
        """SELECT ai FROM messages
           WHERE history_id = ? AND type = 'message' AND ai IS NOT NULL
           ORDER BY id DESC LIMIT 1""",
        (date,),
    ).fetchone()
    if ai_row:
        last_ai = ai_row["ai"] or ""

    return JSONResponse({"messages": messages, "cwd": last_cwd, "ai": last_ai})


@router.get("/history/{date}/resume")
async def history_resume(date: str):
    """Return context prefix for resuming a session.

    Uses stored conversation summaries when available (much richer context
    from prior compactions), falling back to the last 10 raw messages.
    """
    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)

    messages = get_history_messages(date)
    if not messages:
        return JSONResponse({"context": ""})

    label = load_chat_names().get(date) or date

    # Try stored summaries first (persisted during context compaction)
    from helm.context_manager import load_summaries_from_db
    summaries = load_summaries_from_db(date)

    if summaries:
        # Use summaries + last 5 recent messages for best resume quality
        summary_block = "\n\n".join(summaries)
        turns = [m for m in messages if m.get("role") in ("user", "assistant")][-5:]
        recent_lines = []
        for m in turns:
            role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
            body = (m.get("content") or "")[:300]
            if len(m.get("content", "")) > 300:
                body += "..."
            recent_lines.append(f"{role}: {body}")

        context_prefix = (
            f"[Previous conversation — {label}]\n"
            f"[Conversation Summary]\n{summary_block}\n"
            f"[Recent Messages]\n" + "\n".join(recent_lines)
            + "\n[End context]\n\n"
        )
    else:
        # Fallback: last 10 raw messages
        turns = [m for m in messages if m.get("role") in ("user", "assistant")][-10:]
        lines_ctx = []
        for m in turns:
            role = "User" if m["role"] == "user" else (m.get("ai") or "AI").title()
            body = (m.get("content") or "")[:300]
            if len(m.get("content", "")) > 300:
                body += "..."
            lines_ctx.append(f"{role}: {body}")

        context_prefix = (
            f"[Previous conversation — {label}]\n"
            + "\n".join(lines_ctx)
            + "\n[End context]\n\n"
        )

    return JSONResponse({"context": context_prefix})


@router.delete("/history/{date}")
async def history_delete(date: str):
    """Delete all records for a given history ID."""
    from helm.db import get_db

    if not is_valid_history_id(date):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)

    db = get_db()

    # Check exists
    exists = db.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE history_id = ?", (date,)
    ).fetchone()
    if not exists or exists["cnt"] == 0:
        return JSONResponse({"error": "Not found"}, status_code=404)

    try:
        db.execute("DELETE FROM messages WHERE history_id = ?", (date,))
        db.commit()
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

    from helm.db import get_db
    db = get_db()
    exists = db.execute(
        "SELECT COUNT(*) as cnt FROM messages WHERE history_id = ?", (date,)
    ).fetchone()
    if not exists or exists["cnt"] == 0:
        return JSONResponse({"error": "Not found"}, status_code=404)

    save_chat_name(date, name)
    _st.hist_cache_ts = 0  # invalidate cache
    return JSONResponse({"ok": True, "name": name})


@router.get("/history/{hid}/export")
async def history_export(hid: str, format: str = "md"):
    """Export chat history in Markdown, text, or JSON format."""
    if not is_valid_history_id(hid):
        return JSONResponse({"error": "Invalid ID format."}, status_code=400)

    # Get the AI name from cache or infer from messages
    ai_name = "AI"
    for sess in _st.hist_cache:
        if sess.get("date") == hid:
            ai_name = sess.get("ai") or "AI"
            break

    messages = get_history_messages(hid)
    if not messages:
        return JSONResponse({"error": "Not found"}, status_code=404)

    if format == "json":
        content = json.dumps(messages, ensure_ascii=False, indent=2)
        media_type = "application/json"
        filename = f"chat_{hid}.json"
    elif format == "txt":
        lines = []
        for msg in messages:
            role = "User" if msg.get("role") == "user" else msg.get("ai") or ai_name
            content_text = msg.get("content", "").strip()
            lines.append(f"[{role}]: {content_text}\n")
        content = "\n".join(lines)
        media_type = "text/plain"
        filename = f"chat_{hid}.txt"
    else:
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
# Session Templates (SQLite-backed)
# ---------------------------------------------------------------------------

@router.get("/templates")
async def list_templates():
    """Return list of saved session templates."""
    from helm.db import get_db
    try:
        db = get_db()
        rows = db.execute("SELECT * FROM session_templates ORDER BY timestamp DESC").fetchall()
        templates = []
        for row in rows:
            templates.append({
                "name": row["name"],
                "ai": row["ai"],
                "cwd": row["cwd"],
                "model": row["model"],
                "prompt": row["prompt"],
                "timestamp": row["timestamp"],
            })
        return JSONResponse(templates)
    except Exception as e:
        logger.warning("Failed to load templates: %s", e)
        return JSONResponse([])


@router.post("/templates")
async def create_template(request: Request):
    """Save a new session template."""
    from helm.db import get_db
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

        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO session_templates
               (name, ai, cwd, model, prompt, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                template["name"], template["ai"], template["cwd"],
                template["model"], template["prompt"], template["timestamp"],
            ),
        )
        db.commit()
        return JSONResponse({"ok": True, "template": template})
    except Exception as e:
        logger.error("Failed to save template: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/templates/{name}")
async def delete_template(name: str):
    """Delete a saved template."""
    if not name or "/" in name or "\\" in name:
        return JSONResponse({"error": "Invalid template name"}, status_code=400)

    from helm.db import get_db
    try:
        db = get_db()
        row = db.execute("SELECT name FROM session_templates WHERE name = ?", (name,)).fetchone()
        if not row:
            return JSONResponse({"error": "Not found"}, status_code=404)
        db.execute("DELETE FROM session_templates WHERE name = ?", (name,))
        db.commit()
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error("Failed to delete template: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
