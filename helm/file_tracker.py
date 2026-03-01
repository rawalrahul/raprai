"""
helm/file_tracker.py — File change detection, Telegram file sender, session summaries.

Covers: snapshot_dir, diff_snapshots, fmt_duration_short, display_change_path,
        merge_session_changes, emit_session_end_summary, git_diff_stat,
        git_is_repo, send_file_to_telegram, handle_diff, handle_new_files.
"""

import asyncio
import pathlib
import subprocess
import time
from typing import Optional

import helm.state as _st
from helm.config import WEB_PORT, logger
from helm.broadcast import push_message
from helm.session_mgr import session_cwd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Extensions we auto-send to Telegram after an AI command creates them
_PHOTO_EXT   = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_VIDEO_EXT   = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
_GIF_EXT     = {".gif"}
_DOC_EXT     = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc",
    ".xlsx", ".xls", ".csv",
    ".html", ".htm",
    ".zip", ".tar", ".gz",
    ".txt", ".md",
}
_ALL_SENDABLE = _PHOTO_EXT | _VIDEO_EXT | _GIF_EXT | _DOC_EXT

# Max file size to auto-send (50 MB — Telegram bot limit for most types)
_MAX_SEND_BYTES = 50 * 1024 * 1024

# Directories we never recurse into when snapshotting (avoid walking huge trees)
_SKIP_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".env", "dist", "build", ".next", ".nuxt", ".cache",
    ".tox", ".mypy_cache", ".pytest_cache", "target",
})


# ---------------------------------------------------------------------------
# Snapshot & diff
# ---------------------------------------------------------------------------

def snapshot_dir(cwd: str) -> dict[str, tuple[int, float]]:
    """Return {abs_path: (size_bytes, mtime)} for files in cwd (2 levels deep)."""
    result: dict[str, tuple[int, float]] = {}
    try:
        base = pathlib.Path(cwd)
        for entry in base.iterdir():
            if entry.is_file():
                try:
                    st = entry.stat()
                    result[str(entry)] = (st.st_size, st.st_mtime)
                except Exception:
                    pass
            elif entry.is_dir() and entry.name not in _SKIP_DIRS:
                try:
                    for child in entry.iterdir():
                        if child.is_file():
                            try:
                                st = child.stat()
                                result[str(child)] = (st.st_size, st.st_mtime)
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass
    return result


_snapshot_dir = snapshot_dir  # legacy alias


def diff_snapshots(before: dict, after: dict) -> dict:
    """Compare two snapshots; return {new, modified, deleted} path lists."""
    b = set(before)
    a = set(after)
    return {
        "new":      sorted(a - b),
        "modified": sorted(p for p in b & a if before[p] != after[p]),
        "deleted":  sorted(b - a),
    }


_diff_snapshots = diff_snapshots  # legacy alias


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_duration_short(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


_fmt_duration_short = fmt_duration_short  # legacy alias


def display_change_path(filepath: str, cwd: str) -> str:
    """Return a stable, user-friendly path label for change summaries."""
    try:
        p = pathlib.Path(filepath).resolve()
        base = pathlib.Path(cwd).resolve()
        return p.relative_to(base).as_posix()
    except Exception:
        try:
            return pathlib.Path(filepath).name
        except Exception:
            return str(filepath)


_display_change_path = display_change_path  # legacy alias


# ---------------------------------------------------------------------------
# Session change accumulation
# ---------------------------------------------------------------------------

def merge_session_changes(sess: dict, diff: dict, cwd: str) -> None:
    """Accumulate per-task file changes into in-memory session summary buckets."""
    buckets = sess.setdefault("changes", {"new": [], "modified": [], "deleted": []})
    for key in ("new", "modified", "deleted"):
        cur = buckets.setdefault(key, [])
        seen = set(cur)
        for fp in diff.get(key, []):
            name = display_change_path(fp, cwd)
            if name in seen:
                continue
            cur.append(name)
            seen.add(name)


_merge_session_changes = merge_session_changes  # legacy alias


async def emit_session_end_summary(sess: dict, ended_as: str, source: str) -> None:
    """Send end-of-session summary to chat + Telegram (without persisting metadata)."""
    now = time.time()
    started = float(sess.get("session_started") or sess.get("created") or now)
    total_session = max(0.0, now - started)
    total_task = float(sess.get("total_task_seconds") or 0.0)
    if sess.get("busy") and sess.get("task_start"):
        total_task += max(0.0, now - float(sess["task_start"]))
    task_count = int(sess.get("task_count") or 0)

    changes = sess.get("changes") or {}
    new_files = changes.get("new", [])
    mod_files = changes.get("modified", [])
    del_files = changes.get("deleted", [])

    lines = [
        f"\U0001F4CA Session {ended_as}: {sess['name']}",
        f"\u23F1 Session duration: {fmt_duration_short(total_session)}",
        f"\U0001F9E0 Task time: {fmt_duration_short(total_task)} across {task_count} task(s)",
        f"\U0001F4C1 Changes: +{len(new_files)}  ~{len(mod_files)}  -{len(del_files)}",
    ]

    def _add_block(title: str, items: list[str], icon: str):
        if not items:
            return
        lines.append(f"{icon} {title}:")
        for p in items[:8]:
            lines.append(f"  - {p}")
        if len(items) > 8:
            lines.append(f"  - ... and {len(items) - 8} more")

    _add_block("Created", new_files, "\u2705")
    _add_block("Modified", mod_files, "\u270F\uFE0F")
    _add_block("Deleted", del_files, "\U0001F5D1\uFE0F")

    summary = "\n".join(lines)
    await push_message("system", summary, source=source, session_id=sess.get("id"))

    if _st.telegram_app and _st.telegram_chat_id:
        try:
            await _st.telegram_app.bot.send_message(chat_id=_st.telegram_chat_id, text=summary)
        except Exception as e:
            logger.warning("Session summary Telegram notify failed: %s", e)


_emit_session_end_summary = emit_session_end_summary  # legacy alias


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git_diff_stat(cwd: str) -> Optional[str]:
    """Run `git diff --stat` in cwd. Returns None if not a git repo or no diff."""
    try:
        r = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=cwd, capture_output=True, text=True, timeout=10,
        )
        out = r.stdout.strip()
        return out if out else None
    except Exception:
        return None


_git_diff_stat = git_diff_stat  # legacy alias


def git_is_repo(cwd: str) -> bool:
    """Return True if cwd is inside a git repository."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


_git_is_repo = git_is_repo  # legacy alias


# ---------------------------------------------------------------------------
# Telegram file sender
# ---------------------------------------------------------------------------

async def send_file_to_telegram(filepath: str, source: str = "web"):
    """Send a newly-created file to Telegram as the appropriate media type."""
    if not (_st.telegram_app and _st.telegram_chat_id):
        return

    path = pathlib.Path(filepath)
    ext  = path.suffix.lower()

    try:
        size = path.stat().st_size
    except Exception:
        return
    if size == 0 or size > _MAX_SEND_BYTES:
        logger.info("Skipping large/empty file: %s (%d bytes)", path.name, size)
        return

    # Build a relative URL path so files inside subdirs work correctly
    try:
        rel_posix = path.resolve().relative_to(pathlib.Path(session_cwd()).resolve()).as_posix()
    except ValueError:
        rel_posix = path.name
    local_url = f"http://localhost:{WEB_PORT}/files/{rel_posix}"
    display   = str(pathlib.Path(rel_posix))
    caption   = f"📌 {display}\n🔗 {local_url}"

    try:
        with open(filepath, "rb") as fh:
            bot = _st.telegram_app.bot
            if ext in _PHOTO_EXT:
                await bot.send_photo(chat_id=_st.telegram_chat_id, photo=fh, caption=caption)
            elif ext in _VIDEO_EXT:
                await bot.send_video(chat_id=_st.telegram_chat_id, video=fh, caption=caption)
            elif ext in _GIF_EXT:
                await bot.send_animation(chat_id=_st.telegram_chat_id, animation=fh, caption=caption)
            else:
                await bot.send_document(chat_id=_st.telegram_chat_id, document=fh, caption=caption)
        logger.info("Sent file to Telegram: %s", path.name)
    except Exception as e:
        logger.warning("Could not send %s to Telegram: %s", path.name, e)


_send_file_to_telegram = send_file_to_telegram  # legacy alias


# ---------------------------------------------------------------------------
# Main diff handler
# ---------------------------------------------------------------------------

async def handle_diff(before: dict, after: dict, source: str, cwd: str,
                      session_id: Optional[str] = None):
    """Diff snapshots -> notify web chat + Telegram about new, modified, deleted files."""
    diff = diff_snapshots(before, after)
    if session_id and session_id in _st.sessions:
        merge_session_changes(_st.sessions[session_id], diff, cwd)

    # --- New files ---
    for filepath in diff["new"]:
        path = pathlib.Path(filepath)
        ext  = path.suffix.lower()
        if ext not in _ALL_SENDABLE:
            continue
        local_url = f"http://localhost:{WEB_PORT}/files/{path.name}"
        try:
            size_kb = path.stat().st_size // 1024
        except Exception:
            size_kb = 0
        await push_message(
            "system",
            f"📌 New file: {path.name} ({size_kb} KB)  ->  {local_url}",
            source=source,
            session_id=session_id
        )
        await send_file_to_telegram(filepath, source)

    # --- Modified files ---
    if diff["modified"]:
        git_stat = await asyncio.to_thread(git_diff_stat, cwd) if git_is_repo(cwd) else None
        if git_stat:
            summary = f"📝 Changes:\n```\n{git_stat[:1400]}\n```"
        else:
            lines = [f"📝 Modified {len(diff['modified'])} file(s):"]
            for fp in diff["modified"][:12]:
                p = pathlib.Path(fp)
                old_sz, _ = before[fp]
                new_sz, _ = after[fp]
                delta     = new_sz - old_sz
                lines.append(f"  📝 {p.name}  ({delta:+,} B)")
            if len(diff["modified"]) > 12:
                lines.append(f"  ... and {len(diff['modified']) - 12} more")
            summary = "\n".join(lines)

        await push_message("system", summary, source=source, session_id=session_id)

        if _st.telegram_app and _st.telegram_chat_id:
            tg_text = git_stat or "\n".join(
                f"📝 {pathlib.Path(fp).name}" for fp in diff["modified"][:10]
            )
            try:
                await _st.telegram_app.bot.send_message(
                    chat_id=_st.telegram_chat_id,
                    text=f"📝 *Changes:*\n```\n{tg_text[:1400]}\n```",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning("Diff Telegram notify failed: %s", e)

    # --- Deleted files ---
    if diff["deleted"]:
        names = ", ".join(pathlib.Path(fp).name for fp in diff["deleted"][:6])
        if len(diff["deleted"]) > 6:
            names += f" +{len(diff['deleted']) - 6} more"
        await push_message("system", f"🗑️ Deleted: {names}", source=source, session_id=session_id)


_handle_diff = handle_diff  # legacy alias


# Keep old name as alias so any external callers don't break
async def handle_new_files(before, after, source: str):
    cwd = session_cwd()
    # Support both old set[str] and new dict[str, tuple] snapshots
    if isinstance(before, set):
        before = {p: (0, 0.0) for p in before}
        after  = {p: (0, 0.0) for p in after}
    await handle_diff(before, after, source, cwd)


_handle_new_files = handle_new_files  # legacy alias
