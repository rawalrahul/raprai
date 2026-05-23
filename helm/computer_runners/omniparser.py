"""
helm/computer_runners/omniparser.py — Element-detection screen parser.

Wraps Microsoft OmniParser v2: YOLOv8 icon detector + Florence-2 captioner.
Returns a list of labeled screen elements with bounding boxes so the
calling model can click by semantic label instead of guessing pixels.

Opt-in: gated by ``OMNIPARSER_ENABLED=true`` plus the heavy ML deps
(torch, transformers, ultralytics) being importable. Without those the
tool returns a clean error string — never crashes the agent loop.

Weights are downloaded on first use into
``{user_data_dir}/omniparser_weights`` (a few hundred MB).
"""

from __future__ import annotations

import json
import os
import pathlib
import threading


_MODEL_LOCK = threading.Lock()
_MODELS: dict = {"yolo": None, "caption_processor": None, "caption_model": None}

# HuggingFace repo / files for OmniParser v2.
_REPO_ID = "microsoft/OmniParser-v2.0"
_YOLO_FILE = "icon_detect/model.pt"
_CAPTION_DIR = "icon_caption_florence"


def _weights_root() -> pathlib.Path:
    """Cache directory for downloaded weights."""
    base = os.environ.get("OMNIPARSER_WEIGHTS_DIR")
    if base:
        return pathlib.Path(base)
    # Fall back to user data dir if available, else cwd-relative.
    try:
        from helm.config import user_data_dir
        return pathlib.Path(user_data_dir()) / "omniparser_weights"
    except Exception:
        return pathlib.Path.cwd() / "omniparser_weights"


def is_enabled() -> bool:
    return os.environ.get("OMNIPARSER_ENABLED", "false").lower() == "true"


def _load_models() -> str | None:
    """Lazy-load YOLO + Florence on first use. Return error string on failure."""
    if all(_MODELS[k] is not None for k in _MODELS):
        return None
    with _MODEL_LOCK:
        if all(_MODELS[k] is not None for k in _MODELS):
            return None
        try:
            from huggingface_hub import hf_hub_download, snapshot_download
            from ultralytics import YOLO
            from transformers import AutoModelForCausalLM, AutoProcessor
            import torch
        except ImportError as e:
            return (
                "Error: OmniParser deps not installed. "
                "Install: pip install torch torchvision ultralytics "
                f"transformers huggingface_hub einops ({e})"
            )

        cache_dir = _weights_root()
        cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            yolo_path = hf_hub_download(
                repo_id=_REPO_ID, filename=_YOLO_FILE,
                cache_dir=str(cache_dir),
            )
            caption_path = snapshot_download(
                repo_id=_REPO_ID, allow_patterns=[f"{_CAPTION_DIR}/*"],
                cache_dir=str(cache_dir),
            )
            caption_root = pathlib.Path(caption_path) / _CAPTION_DIR
        except Exception as e:
            return f"Error: weight download failed: {type(e).__name__}: {e}"

        try:
            _MODELS["yolo"] = YOLO(yolo_path)
            _MODELS["caption_processor"] = AutoProcessor.from_pretrained(
                str(caption_root), trust_remote_code=True,
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _MODELS["caption_model"] = AutoModelForCausalLM.from_pretrained(
                str(caption_root),
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                trust_remote_code=True,
            ).to(device)
            _MODELS["device"] = device
        except Exception as e:
            # Reset partial state so a retry can try again.
            for k in _MODELS:
                _MODELS[k] = None
            return f"Error: model load failed: {type(e).__name__}: {e}"

    return None


def _grab_pil():
    """Capture primary monitor as a PIL.Image (RGB)."""
    import mss
    from PIL import Image
    with mss.mss() as sct:
        mon = sct.monitors[1]
        raw = sct.grab(mon)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def _caption_crop(img) -> str:
    """Run Florence-2 caption on a single PIL crop. Returns string."""
    import torch
    proc = _MODELS["caption_processor"]
    model = _MODELS["caption_model"]
    device = _MODELS["device"]
    prompt = "<CAPTION>"
    inputs = proc(text=prompt, images=img, return_tensors="pt").to(device)
    if device == "cuda":
        inputs = {k: (v.half() if v.dtype == torch.float32 else v) for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=30,
            num_beams=1,
            do_sample=False,
        )
    text = proc.batch_decode(out, skip_special_tokens=True)[0]
    return text.strip()


def parse_screen(args: dict) -> str:
    """Return JSON list of {bbox, center, label} for detected UI elements."""
    if not is_enabled():
        return "Error: OmniParser is disabled. Set OMNIPARSER_ENABLED=true."

    err = _load_models()
    if err:
        return err

    try:
        conf = float(args.get("conf", 0.25))
        max_elements = int(args.get("max_elements", 60))
        img = _grab_pil()
        yolo = _MODELS["yolo"]
        results = yolo(img, conf=conf, verbose=False)
        elements = []
        if not results:
            return json.dumps([])
        boxes = results[0].boxes
        if boxes is None:
            return json.dumps([])
        # xyxy in original image coords.
        coords = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        # Sort by confidence, take top N.
        order = confs.argsort()[::-1][:max_elements]
        for idx in order:
            x1, y1, x2, y2 = [int(v) for v in coords[idx]]
            crop = img.crop((x1, y1, x2, y2))
            try:
                label = _caption_crop(crop)
            except Exception as e:
                label = f"(caption failed: {type(e).__name__})"
            elements.append({
                "bbox": [x1, y1, x2, y2],
                "center": [(x1 + x2) // 2, (y1 + y2) // 2],
                "conf": float(confs[idx]),
                "label": label[:120],
            })
        return json.dumps(elements)
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
