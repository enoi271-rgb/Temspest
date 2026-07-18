#!/usr/bin/env python3
"""
TTEMSPESTT — Instagram Publisher (Meta Graph API)
Publica Reels/Vídeo/Carrossel no Instagram @duna_peps a pedido do utilizador.

USO:
  python3 ttemspept_publisher.py --video clip.mp4 --caption "legenda..." --hashtags "#TTEMSPESTT #GhostAngolano"

PRÉ-REQUISITOS:
  - Ficheiro ~/.hermes/ttemspept_ig_token.json com {"access_token": "...", "ig_user_id": "..."}
  - Conta IG Business ligada a uma Facebook Page
"""
import json, os, sys, argparse, urllib.parse, urllib.request

CONFIG_PATH = os.path.expanduser("~/.hermes/ttemspept_ig_token.json")
API = "https://graph.facebook.com/v21.0"

def load_cfg():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"FALTA token: cria {CONFIG_PATH} com {{'access_token','ig_user_id'}}")
    with open(CONFIG_PATH) as f:
        return json.load(f)

def api(method, path, data=None, files=None):
    url = f"{API}/{path}"
    headers = {}
    if files:
        import requests
        r = requests.request(method, url, data=data, files=files, headers=headers)
        return r.json()
    if data:
        data = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        return json.load(e)

def publish_reel(video_path, caption):
    cfg = load_cfg()
    tok = cfg["access_token"]
    ig_id = cfg["ig_user_id"]

    # 1. Upload do vídeo (container)
    with open(video_path, "rb") as f:
        import requests
        r = requests.post(f"{API}/{ig_id}/media",
            data={"media_type":"REEL","video_url":None,"caption":caption,"access_token":tok},
            files={"video":f})
    resp = r.json()
    if "id" not in resp:
        return f"ERRO ao criar container: {resp}"
    container_id = resp["id"]

    # 2. Poll até estar pronto
    import time
    for _ in range(20):
        s = api("GET", f"{container_id}?fields=status_code&access_token={tok}")
        if s.get("status_code") == "FINISHED":
            break
        time.sleep(5)

    # 3. Publicar
    pub = api("POST", f"{ig_id}/media_publish", {"creation_id": container_id, "access_token": tok})
    return pub

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--caption", default="")
    p.add_argument("--hashtags", default="")
    a = p.parse_args()
    cap = a.caption + "\n\n" + a.hashtags
    print(publish_reel(a.video, cap))
