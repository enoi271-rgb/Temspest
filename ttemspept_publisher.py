#!/usr/bin/env python3
"""
TTEMSPESTT — Instagram Publisher (Meta Graph API)
Publica Reels/Vídeo/Carrossel no Instagram @duna_peps a pedido do utilizador.

USO:
  Reel/Vídeo:
    python3 ttemspept_publisher.py --video clip.mp4 --caption "legenda..." --hashtags "#TTEMSPESTT #GhostAngolano"

  Carrossel (1+ imagens):
    python3 ttemspept_publisher.py --image f1.jpg --image f2.jpg --caption "legenda..." --hashtags "#TTEMSPESTT"

PRÉ-REQUISITOS:
  - Ficheiro ~/.hermes/ttemspept_ig_token.json com {"access_token": "...", "ig_user_id": "..."}
  - Conta IG Business ligada a uma Facebook Page
  - Biblioteca 'requests' instalada (pip install requests)
"""
import json, os, sys, time, argparse
try:
    import requests
except ImportError:
    sys.exit("FALTA a biblioteca 'requests'. Instala com: pip install requests")

CONFIG_PATH = os.path.expanduser("~/.hermes/ttemspept_ig_token.json")
API = "https://graph.facebook.com/v21.0"

def load_cfg():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(f"FALTA token: cria {CONFIG_PATH} com {{\"access_token\",\"ig_user_id\"}}")
    with open(CONFIG_PATH) as f:
        return json.load(f)

def clean_caption(caption, hashtags):
    cap = (caption or "").strip()
    ht = (hashtags or "").strip()
    if ht:
        cap = (cap + "\n\n" + ht).strip()
    return cap

def _api(method, path, **kw):
    url = f"{API}/{path}"
    r = requests.request(method, url, **kw)
    try:
        return r.json()
    except ValueError:
        return {"error": {"message": r.text, "code": r.status_code}}

def _poll_container(ig_id, tok, container_id):
    for _ in range(30):  # até ~150s
        s = _api("GET", f"{container_id}?fields=status_code,error_message", params={"access_token": tok})
        code = s.get("status_code")
        if code == "FINISHED":
            return True
        if code == "ERROR":
            raise RuntimeError(f"Container falhou: {s.get('error_message')}")
        time.sleep(5)
    raise RuntimeError("Timeout a esperar que o container ficasse pronto (FINISHED).")

def publish_reel(video_path, caption):
    if not os.path.exists(video_path):
        return f"ERRO: vídeo não encontrado: {video_path}"
    cfg = load_cfg()
    tok = cfg["access_token"]
    ig_id = cfg["ig_user_id"]

    # 1. Criar container (upload binário)
    with open(video_path, "rb") as f:
        resp = _api("POST", f"{ig_id}/media",
                    data={"media_type": "REEL", "caption": caption, "access_token": tok},
                    files={"video": f})
    if "id" not in resp:
        return f"ERRO ao criar container: {resp}"
    container_id = resp["id"]

    # 2. Poll até FINISHED
    try:
        _poll_container(ig_id, tok, container_id)
    except RuntimeError as e:
        return f"ERRO: {e}"

    # 3. Publicar
    pub = _api("POST", f"{ig_id}/media_publish",
               data={"creation_id": container_id, "access_token": tok})
    return pub

def publish_carousel(image_paths, caption):
    for p in image_paths:
        if not os.path.exists(p):
            return f"ERRO: imagem não encontrada: {p}"
    cfg = load_cfg()
    tok = cfg["access_token"]
    ig_id = cfg["ig_user_id"]

    children = []
    for p in image_paths:
        with open(p, "rb") as f:
            resp = _api("POST", f"{ig_id}/media",
                        data={"media_type": "IMAGE", "is_carousel_item": "true", "access_token": tok},
                        files={"image": f})
        if "id" not in resp:
            return f"ERRO ao criar item do carrossel: {resp}"
        children.append(resp["id"])

    # Container do carrossel
    resp = _api("POST", f"{ig_id}/media",
                data={"media_type": "CAROUSEL", "caption": caption,
                      "children": ",".join(children), "access_token": tok})
    if "id" not in resp:
        return f"ERRO ao criar container do carrossel: {resp}"
    container_id = resp["id"]

    try:
        _poll_container(ig_id, tok, container_id)
    except RuntimeError as e:
        return f"ERRO: {e}"

    pub = _api("POST", f"{ig_id}/media_publish",
               data={"creation_id": container_id, "access_token": tok})
    return pub

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Publica no Instagram @duna_peps (TTEMSPESTT).")
    p.add_argument("--video", help="caminho do vídeo (Reel)")
    p.add_argument("--image", action="append", default=[], help="caminho de imagem (repete p/ carrossel)")
    p.add_argument("--caption", default="")
    p.add_argument("--hashtags", default="")
    a = p.parse_args()

    cap = clean_caption(a.caption, a.hashtags)

    if a.video:
        print("A publicar Reel...", flush=True)
        print(publish_reel(a.video, cap))
    elif a.image:
        print("A publicar Carrossel...", flush=True)
        print(publish_carousel(a.image, cap))
    else:
        sys.exit("Especifica --video <ficheiro> ou --image <ficheiro> (podes repetir --image).")
