import json
import os
import shutil
import stat
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from helm.config import logger
from helm.paths import HELM_DIR

DEMOS_DIR = HELM_DIR / "demos"
RAW_DIR = DEMOS_DIR / "raw"
PROCESSED_DIR = DEMOS_DIR / "processed"
LIBRARY_FILE = DEMOS_DIR / "library.json"

_library_lock = threading.Lock()


def _validate_id(demo_id: str) -> None:
    if not demo_id.isalnum() or len(demo_id) > 32:
        raise ValueError(f"Invalid demo_id: {demo_id!r}")


def _ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def create_demo(source_filename: str) -> dict:
    _ensure_dirs()
    demo_id = uuid.uuid4().hex[:12]
    title = Path(Path(source_filename).stem.replace(" ", "_")).name
    meta = {
        "demo_id": demo_id,
        "title": title,
        "status": "uploading",
        "duration_s": None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "source_filename": source_filename,
        "analysis_ai": None,
        "file_uri": None,
        "gemini_file_name": None,
        "file_uri_expires_at": None,
        "playbook_path": None,
        "error_message": None,
    }
    (RAW_DIR / demo_id).mkdir(parents=True, exist_ok=True)
    (PROCESSED_DIR / demo_id).mkdir(parents=True, exist_ok=True)
    _write_meta(demo_id, meta)
    _update_library(demo_id, meta)
    return meta


def get_demo(demo_id: str) -> dict | None:
    _validate_id(demo_id)
    meta = _read_meta(demo_id)
    if meta is None:
        return None
    return {**meta, "actions": _read_actions(demo_id)}


def update_meta(demo_id: str, updates: dict) -> dict:
    _validate_id(demo_id)
    meta = _read_meta(demo_id)
    if meta is None:
        raise KeyError(f"demo_id not found: {demo_id}")
    meta.update(updates)
    _write_meta(demo_id, meta)
    _update_library(demo_id, meta)
    return meta


def _on_rm_error(func, path, exc_info):
    """rmtree onerror: clear read-only / locked attrs and retry (Windows-friendly)."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception:
        pass  # leave to outer retry/cleanup


def _rmtree_with_retry(path: Path, attempts: int = 4, delay: float = 0.3) -> bool:
    """Try rmtree several times; return True if directory is gone."""
    for i in range(attempts):
        try:
            shutil.rmtree(path, onerror=_on_rm_error)
            if not path.exists():
                return True
        except Exception as exc:
            logger.warning("rmtree attempt %d failed for %s: %s", i + 1, path, exc)
        time.sleep(delay)
    return not path.exists()


def delete_demo(demo_id: str) -> None:
    _validate_id(demo_id)
    # Always remove library entry first so the UI reflects the deletion even
    # if a file handle (e.g. open by analysis subprocess) blocks rmtree.
    _remove_from_library(demo_id)
    stuck: list[str] = []
    for d in (RAW_DIR / demo_id, PROCESSED_DIR / demo_id):
        if d.exists() and not _rmtree_with_retry(d):
            stuck.append(str(d))
    if stuck:
        logger.warning("delete_demo %s: removed from library but files still locked: %s",
                       demo_id, stuck)


def list_demos() -> list:
    if not LIBRARY_FILE.exists():
        return []
    try:
        return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def get_video_path(demo_id: str) -> Path | None:
    _validate_id(demo_id)
    for ext in ("mp4", "mov", "webm", "mkv", "avi"):
        p = RAW_DIR / demo_id / f"video.{ext}"
        if p.exists():
            return p
    return None


def get_frames_dir(demo_id: str) -> Path:
    _validate_id(demo_id)
    d = PROCESSED_DIR / demo_id / "frames"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_actions(demo_id: str, actions: list) -> None:
    _validate_id(demo_id)
    path = PROCESSED_DIR / demo_id / "actions.json"
    path.write_text(json.dumps(actions, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_meta(demo_id: str) -> dict | None:
    path = RAW_DIR / demo_id / "meta.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_meta(demo_id: str, meta: dict) -> None:
    (RAW_DIR / demo_id).mkdir(parents=True, exist_ok=True)
    (RAW_DIR / demo_id / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _read_actions(demo_id: str) -> list | None:
    path = PROCESSED_DIR / demo_id / "actions.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _update_library(demo_id: str, meta: dict) -> None:
    with _library_lock:
        library = list_demos()
        entry = {
            "demo_id": demo_id,
            "title": meta.get("title"),
            "status": meta.get("status"),
            "duration_s": meta.get("duration_s"),
            "uploaded_at": meta.get("uploaded_at"),
        }
        idx = next((i for i, d in enumerate(library) if d["demo_id"] == demo_id), None)
        if idx is not None:
            library[idx] = entry
        else:
            library.insert(0, entry)
        LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        LIBRARY_FILE.write_text(json.dumps(library, indent=2, ensure_ascii=False), encoding="utf-8")


def _remove_from_library(demo_id: str) -> None:
    with _library_lock:
        library = [d for d in list_demos() if d["demo_id"] != demo_id]
        if LIBRARY_FILE.exists():
            LIBRARY_FILE.write_text(
                json.dumps(library, indent=2, ensure_ascii=False), encoding="utf-8"
            )
