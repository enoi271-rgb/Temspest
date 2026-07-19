#!/usr/bin/env python3
"""Aplica o HUD vertical (assets/hud_vertical.png) a todos os shorts em videos/clips/*/short_*.mp4.
Gera os ficheiros finais em videos/shorts/ com nome unico (fonte_nome).
"""
import os, subprocess, glob

BASE = os.path.dirname(__file__)
HUD = os.path.join(BASE, "assets", "hud_vertical.png")
SRC = os.path.join(BASE, "videos", "clips")
OUT = os.path.join(BASE, "videos", "shorts")
os.makedirs(OUT, exist_ok=True)

shorts = sorted(glob.glob(os.path.join(SRC, "**", "short_*.mp4"), recursive=True))
print("Shorts encontrados:", len(shorts))
ok = 0
for i, sp in enumerate(shorts, 1):
    fonte = os.path.basename(os.path.dirname(sp))  # ex: cod_main
    name = os.path.basename(sp)                     # ex: short_01.mp4
    dst = os.path.join(OUT, f"{fonte}_{name}")      # ex: cod_main_short_01.mp4
    cmd = ["ffmpeg", "-y", "-i", sp, "-i", HUD, "-filter_complex", "overlay=0:0",
           "-c:a", "copy", "-crf", "20", "-preset", "fast", "-shortest", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and os.path.exists(dst):
        ok += 1
        print(f"  [{i}/{len(shorts)}] {os.path.basename(dst)} -> OK")
    else:
        print(f"  [{i}/{len(shorts)}] {os.path.basename(dst)} -> FALHOU")
        print(r.stderr[-300:])
print(f"\nGerados: {ok}/{len(shorts)} em {OUT}")
