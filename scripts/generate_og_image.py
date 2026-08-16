#!/usr/bin/env python3
"""Generate docs/assets/og-image.png for Open Graph. Run: python scripts/generate_og_image.py"""
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow required: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets" / "og-image.png"
ICON = ROOT / "assets" / "icon.png"

WIDTH, HEIGHT = 1200, 630
BG = (11, 20, 26)
TEXT = (233, 237, 239)
SUBTEXT = (174, 186, 193)
GREEN = (0, 168, 132)


def _font(size: int, bold: bool = False):
    names = ["segoeui.ttf", "Segoe UI.ttf", "arial.ttf"]
    if bold:
        names = ["segoeuib.ttf", "Segoe UI Bold.ttf", "arialbd.ttf"] + names
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG[0] + (0 - BG[0]) * t * 0.3)
        g = int(BG[1] + (40 - BG[1]) * t * 0.3)
        b = int(BG[2] + (50 - BG[2]) * t * 0.3)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    icon = Image.open(ICON).convert("RGBA")
    icon_size = 180
    icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    ix = 72
    iy = (HEIGHT - icon_size) // 2
    img.paste(icon, (ix, iy), icon)

    title_font = _font(56, bold=True)
    sub_font = _font(28)
    badge_font = _font(22)

    tx = ix + icon_size + 48
    draw.text((tx, 200), "S3MANAGER", fill=TEXT, font=title_font)
    draw.text(
        (tx, 270),
        "DigitalOcean Spaces için masaüstü dosya yöneticisi",
        fill=SUBTEXT,
        font=sub_font,
    )

    badge_w, badge_h = 120, 36
    bx, by = tx, 340
    draw.rounded_rectangle(
        (bx, by, bx + badge_w, by + badge_h),
        radius=18,
        fill=GREEN,
    )
    draw.text((bx + 18, by + 6), "v0.0.8", fill=TEXT, font=badge_font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"Created {OUT}")


if __name__ == "__main__":
    main()
