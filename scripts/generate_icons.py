#!/usr/bin/env python3
"""Generate placeholder S3MANAGER icons (png, ico). Run: python scripts/generate_icons.py"""
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit("Pillow required: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SIZE = 256


def draw_icon() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (18, 18, 18, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((24, 24, 232, 232), radius=32, fill=(37, 211, 102, 255))
    try:
        font = ImageFont.truetype("arial.ttf", 72)
    except OSError:
        font = ImageFont.load_default()
    draw.text((72, 88), "S3", fill=(18, 18, 18, 255), font=font)
    return img


def main():
    ASSETS.mkdir(exist_ok=True)
    icon = draw_icon()
    icon.save(ASSETS / "icon.png")
    icon.save(ASSETS / "icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print(f"Created {ASSETS / 'icon.png'} and {ASSETS / 'icon.ico'}")


if __name__ == "__main__":
    main()
