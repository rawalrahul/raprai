import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from helm.paths import HELM_DIR

DEMOS_DIR = HELM_DIR / "demos"
RAW_DIR = DEMOS_DIR / "raw"
PROCESSED_DIR = DEMOS_DIR / "processed"
LIBRARY_FILE = DEMOS_DIR / "library.json"


def _validate_id(demo_id: str) -> None:
    if not demo_id.isalnum() or len(demo_id) > 32:
        raise ValueError(f"Invalid demo_id: {demo_id!r}")


def _ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def create_demo(source_filename: str) -> dict:
    _ensure_dirs()
    demo_id = uuid.uuid4().hex[:12]
    title = Path(source_filename).stem.replace(" ", "_")
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


def delete_demo(demo_id: str) -> None:
    _validate_id(demo_id)
    for d in (RAW_DIR / demo_id, PROCESSED_DIR / demo_id):
        if d.exists():
            shutil.rmtree(d)
    _remove_from_library(demo_id)


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
    library = [d for d in list_demos() if d["demo_id"] != demo_id]
    if LIBRARY_FILE.exists():
        LIBRARY_FILE.write_text(
            json.dumps(library, indent=2, ensure_ascii=False), encoding="utf-8"
        )
