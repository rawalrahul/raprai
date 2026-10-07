"""Convert Kelvin sticker PNGs to Telegram-ready 512x512 WEBP files,
and pack desktop-Kelvin frames into one sprite strip per mood.

Run after scripts/render_kelvin_assets.cjs:
    python scripts/png_to_webp.py
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

KELVIN_DIR = Path(__file__).resolve().parent.parent / "frontend2" / "assets" / "kelvin"

for png in sorted(KELVIN_DIR.glob("sticker-*.png")):
    img = Image.open(png).convert("RGBA")
    img.thumbnail((512, 512))
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.paste(img, ((512 - img.width) // 2, (512 - img.height) // 2), img)
    out = png.with_suffix(".webp")
    canvas.save(out, "WEBP", quality=90, method=6)
    png.unlink()
    print(f"{out.name}: {out.stat().st_size // 1024} KB")

for frames_file in sorted(KELVIN_DIR.glob("pet-*.frames.json")):
    frames = [Image.open(io.BytesIO(base64.b64decode(b))).convert("RGBA") for b in json.loads(frames_file.read_text())]
    w, h = frames[0].size
    strip = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        strip.paste(fr, (i * w, 0))
    out = KELVIN_DIR / frames_file.name.replace(".frames.json", ".png")
    strip.save(out, optimize=True)
    frames_file.unlink()
    print(f"{out.name}: {len(frames)} frames, {out.stat().st_size // 1024} KB")
