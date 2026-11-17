#!/usr/bin/env python3
"""Generate the self-contained, installable THE VAULT app icons."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("website")
OUT.mkdir(parents=True, exist_ok=True)
GOLD = "#d1a95b"
BG = "#0b0d13"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def make(size, filename):
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)
    m = round(size * .105)
    d.rounded_rectangle((m, m, size-m, size-m), radius=size//7,
                        outline=GOLD, width=max(3, size//44))
    try:
        f = ImageFont.truetype(FONT, size=int(size*.51))
    except OSError:
        f = ImageFont.load_default()
    box = d.textbbox((0, 0), "V", font=f)
    x = (size - (box[2]-box[0]))/2-box[0]
    y = (size - (box[3]-box[1]))/2-box[1] - size*.025
    d.text((x,y), "V", fill=GOLD, font=f)
    im.save(OUT / filename, optimize=True)

make(192, "icon-192.png")
make(512, "icon-512.png")
make(180, "apple-touch-icon.png")
print("Created three installable app icons")
