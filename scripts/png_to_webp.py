"""Convert Kelvin sticker PNGs to Telegram-ready 512x512 WEBP files.

Run after scripts/render_kelvin_assets.cjs:
    python scripts/png_to_webp.py
"""
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
