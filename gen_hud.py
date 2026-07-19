#!/usr/bin/env python3
"""Gera HUD vertical (1080x1920) transparente para Shorts: nome TEMSPEST + cantos + mira + barras."""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.join(os.path.dirname(__file__), "assets", "hud_vertical.png")
W, H = 1080, 1920
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

GREEN = (143, 179, 90, 230)
AMBER = (217, 154, 62, 230)
LIGHT = (231, 228, 214, 235)
FAINT = (154, 156, 140, 180)

def font(sz, bold=False):
    # fallback monospace/Teko-like
    cands = [
        "/System/Library/Fonts/Supplemental/Teko-Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Teko-Regular.ttf",
        "/Library/Fonts/Teko-Bold.ttf" if bold else "/Library/Fonts/Teko-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for c in cands:
        if os.path.exists(c):
            return ImageFont.truetype(c, sz)
    return ImageFont.load_default()

# vinheta inferior (gradiente simples)
for y in range(H):
    a = int(120 * (y / H) ** 2)  # mais opaco embaixo
    if a > 0:
        d.line([(0, y), (W, y)], fill=(0, 0, 0, min(a, 90)))

# cantos HUD
lw = 6
c = 60
for (x0, y0, dx, dy) in [  # (start, direction)
    (60, 200, 1, 1), (W - 60, 200, -1, 1),
    (60, H - 200, 1, -1), (W - 60, H - 200, -1, -1),
]:
    L = 110
    if dx > 0 and dy > 0:      # sup-esq
        d.line([(x0, y0 + L), (x0, y0), (x0 + L, y0)], fill=GREEN, width=lw)
    elif dx < 0 and dy > 0:    # sup-dir
        d.line([(x0, y0 + L), (x0, y0), (x0 - L, y0)], fill=GREEN, width=lw)
    elif dx > 0 and dy < 0:    # inf-esq
        d.line([(x0, y0 - L), (x0, y0), (x0 + L, y0)], fill=GREEN, width=lw)
    else:                      # inf-dir
        d.line([(x0, y0 - L), (x0, y0), (x0 - L, y0)], fill=GREEN, width=lw)

# barra lateral esq (status) — cheia + meio
d.rectangle([72, 240, 80, H - 240], fill=(143, 179, 90, 90))
d.rectangle([72, 240, 80, 240 + (H - 480) // 2], fill=GREEN)

# mira central
cx, cy = W // 2, H // 2
d.line([(cx, cy - 80), (cx, cy - 30)], fill=GREEN, width=3)
d.line([(cx, cy + 30), (cx, cy + 80)], fill=GREEN, width=3)
d.line([(cx - 80, cy), (cx - 30, cy)], fill=GREEN, width=3)
d.line([(cx + 30, cy), (cx + 80, cy)], fill=GREEN, width=3)
d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], outline=GREEN, width=3)

# NOME TEMSPEST
ft = font(160, bold=True)
tb = d.textbbox((0, 0), "TEMSPEST", font=ft)
tw = tb[2] - tb[0]
# glow
d.text(((W - tw) // 2 + 3, 250 + 3), "TEMSPEST", font=ft, fill=GREEN)
d.text(((W - tw) // 2, 250), "TEMSPEST", font=ft, fill=LIGHT)
fs = font(36)
d.text((W // 2, 320), "GHOST ANGOLANO", font=fs, fill=GREEN, anchor="mm")

# HUD inferior (texto)
fb = font(34, bold=True)
d.text((100, H - 250), "[ STATUS: LIVE ]", font=fb, fill=LIGHT)
d.text((100, H - 205), "RPM    ▮▮▮▯▯", font=fb, fill=GREEN)
d.text((100, H - 160), "MORALE ▮▮▮▮▯", font=fb, fill=AMBER)
fh = font(28)
d.text((W // 2, H - 95), "#TTEMSPESTT  #WarzoneAngola", font=fh, fill=FAINT, anchor="mm")

img.save(OUT)
print("HUD gerado:", OUT, img.size)
