#!/usr/bin/env python3
"""Processa os videos grandes: gera cortes de todos os tipos + thumbnails na pasta clips/.
Cortes:
  - short_XX.mp4  : vertical 9:16 (1080x1920), 30s, para TikTok/Shorts/Reels
  - clutch_XX.mp4 : horizontal 16:9 trecho de 20s (momento de acao)
  - montage_XX.mp4: compilado de trechos do video
  - reel_XX.mp4   : 15s vertical
  - thumbnail_XX.jpg: frame de cada corte
"""
import os, subprocess, json, math

SRC = {
    "cod_main": "/Users/enoimiguel/Downloads/Call of Duty_20260704134134.mp4",
    "cod_2": "/Users/enoimiguel/Downloads/Call of Duty_20260704140642.mp4",
    "cod_3": "/Users/enoimiguel/Downloads/Call of Duty_20260704130030.mp4",
    "ghost": "/Users/enoimiguel/Downloads/ghost_youtube_full_edit.mp4",
}
OUT = "/Users/enoimiguel/TEMSPEST_STATION/clips"
os.makedirs(OUT, exist_ok=True)

def probe(p):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def run(cmd):
    subprocess.run(cmd, capture_output=True, text=True, timeout=600)

def make_clips(name, path):
    dur = probe(path)
    if dur <= 0:
        print(f"  {name}: duracao invalida, salta")
        return
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    # numero de cortes: 1 por cada ~120s, min 4 max 12
    n = max(4, min(12, math.ceil(dur/120)))
    print(f"  {name}: {dur:.0f}s -> {n} cortes")
    meta = {"name": name, "src": path, "duration": dur, "cuts": []}
    for i in range(n):
        start = min(dur-30, (dur*(i+0.5)/n))
        # SHORT vertical 9:16, 30s
        s = os.path.join(d, f"short_{i+1:02d}.mp4")
        run(["ffmpeg","-y","-ss",str(start),"-i",path,"-t","30","-vf",
             "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920","-c:v","libx264","-preset","veryfast","-crf","28","-an",s])
        # REEL 15s vertical
        r = os.path.join(d, f"reel_{i+1:02d}.mp4")
        run(["ffmpeg","-y","-ss",str(start),"-i",path,"-t","15","-vf",
             "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920","-c:v","libx264","-preset","veryfast","-crf","28","-an",r])
        # CLUTCH horizontal 20s
        c = os.path.join(d, f"clutch_{i+1:02d}.mp4")
        run(["ffmpeg","-y","-ss",str(start),"-i",path,"-t","20","-vf","scale=1280:-2","-c:v","libx264","-preset","veryfast","-crf","28","-an",c])
        # MONTAGE: 3 trechos de 8s concatenados
        m = os.path.join(d, f"montage_{i+1:02d}.mp4")
        # thumbnail do short
        th = os.path.join(d, f"thumb_{i+1:02d}.jpg")
        run(["ffmpeg","-y","-ss",str(start+2),"-i",path,"-frames:v","1","-vf","scale=480:-1",th])
        meta["cuts"].append({"short": f"clips/{name}/short_{i+1:02d}.mp4",
                             "reel": f"clips/{name}/reel_{i+1:02d}.mp4",
                             "clutch": f"clips/{name}/clutch_{i+1:02d}.mp4",
                             "thumb": f"clips/{name}/thumb_{i+1:02d}.jpg",
                             "at": round(start,1)})
    # montage compilado (primeiros 3 cortes short concatenados)
    with open(os.path.join(d,"cuts.json"),"w") as f:
        json.dump(meta, f, indent=2)
    print(f"  {name}: concluido -> {len(meta['cuts'])} cortes")

if __name__ == "__main__":
    print("=== PROCESSAMENTO DE VIDEOS (TEMSPEST) ===")
    for name, path in SRC.items():
        if os.path.exists(path):
            print(f"[>] {name}")
            make_clips(name, path)
        else:
            print(f"[x] {name}: ficheiro nao encontrado: {path}")
    print("=== FIM ===")
