#!/usr/bin/env python3
"""Aplica o HUD vertical (assets/hud_vertical.png) a todos os shorts em clips/*/short_*.mp4.
Gera os ficheiros finais em clips_shorts_hud/ mantendo o nome original.
"""
import os, subprocess, glob

BASE = os.path.dirname(__file__)
HUD = os.path.join(BASE, "assets", "hud_vertical.png")
OUT = os.path.join(BASE, "clips_shorts_hud")
os.makedirs(OUT, exist_ok=True)

shorts = sorted(glob.glob(os.path.join(BASE, "clips", "**", "short_*.mp4"), recursive=True))
print("Shorts encontrados:", len(shorts))
ok = 0
for i, sp in enumerate(shorts, 1):
    name = os.path.basename(sp)
    dst = os.path.join(OUT, name)
    cmd = ["ffmpeg", "-y", "-i", sp, "-i", HUD, "-filter_complex", "overlay=0:0",
           "-c:a", "copy", "-crf", "20", "-preset", "fast", "-shortest", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(dst):
        ok += 1
        print(f"  [{i}/{len(shorts)}] {name} -> OK")
    else:
        print(f"  [{i}/{len(shorts)}] {name} -> FALHOU")
        print(r.stderr[-300:])
print(f"\nGerados: {ok}/{len(shorts)} em {OUT}")
