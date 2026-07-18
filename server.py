#!/usr/bin/env python3
"""
TEMSPEST STATION — Bridge WhatsApp + Aprovacao
Servidor leve que:
  - recebe POST /api/notify do simulador (agente terminou -> pede validacao)
  - envia a notificacao para o teu WhatsApp (pywhatkit / WhatsApp Web)
  - guarda fila em queue.json
  - GET /api/decisions  -> simulador faz poll das tuas acoes
  - GET /              -> pagina web simples p/ aprovar do telemovel
  - POST /api/decide   -> o telemovel (ou WhatsApp) envia approve/reject

Requer: pip install flask pywhatkit
WhatsApp: o pywhatkit abre o WhatsApp Web no browser e envia a mensagem.
"""
import json, os, threading, time, webbrowser

try:
    for line in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')):
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            k,v=line.split('=',1); os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass
from flask import Flask, request, jsonify, Response

BASE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(BASE, "queue.json")

# === CONFIGURA O TEU NUMERO AQUI (formato internacional, sem +) ===
WHATSAPP_NUMBER = os.environ.get("TTEMSPEST_WHATSAPP", "244XXXxxxxxxx")  # ex: 244923000000

app = Flask(__name__)

def load():
    if os.path.exists(QUEUE):
        try: return json.load(open(QUEUE))
        except: pass
    return {"pending": [], "decisions": []}

def save(d):
    json.dump(d, open(QUEUE, "w"), indent=2)

DATA = load()
DATA.setdefault("pending", [])
DATA.setdefault("decisions", [])
_lock = threading.Lock()

def send_whatsapp(text):
    """Envia mensagem via WhatsApp Web (pywhatkit). Falha silenciosa se nao instalado."""
    try:
        import pywhatkit
        num = WHATSAPP_NUMBER
        if num and not num.startswith("244XXX"):
            pywhatkit.sendwhatmsg_instantly(f"+{num}", text, wait_time=8, tab_close=True)
            return True
    except Exception as e:
        print("WhatsApp send falhou (pywhatkit nao instalado ou numero nao configurado):", e)
    return False

@app.route("/api/notify", methods=["POST"])
def notify():
    item = request.get_json(force=True)
    with _lock:
        DATA["pending"].append(item)
        save(DATA)
    msg = f"TEMSPEST: {item.get('name')} ({item.get('room')}/{item.get('role')}) terminou {item.get('kind')} — {item.get('result')}. Responde 'sim {id}' ou 'nao {id}' no WhatsApp, ou abre o link de aprovacao.".format(id=item.get('id'))
    send_whatsapp(msg)
    print("NOTIFY:", item.get("name"), "-> WhatsApp")
    return jsonify({"ok": True})

@app.route("/api/decisions", methods=["GET"])
def decisions():
    with _lock:
        d = DATA["decisions"]
        DATA["decisions"] = []  # consumir
        save(DATA)
    return jsonify(d)

@app.route("/api/decide", methods=["POST"])
def decide():
    d = request.get_json(force=True)
    with _lock:
        # remover da pendencia
        DATA["pending"] = [p for p in DATA["pending"] if p.get("id") != d.get("id")]
        DATA["decisions"].append({"id": d.get("id"), "action": d.get("action")})
        save(DATA)
    print("DECIDE:", d.get("id"), d.get("action"))
    return jsonify({"ok": True})

@app.route("/api/queue", methods=["GET"])
def queue():
    with _lock:
        return jsonify(DATA["pending"])

@app.route("/", methods=["GET"])
def page():
    with _lock:
        pend = DATA["pending"]
    cards = "".join(
        f'<div style="border:1px solid #3d4530;background:#12150f;padding:12px;margin:8px 0;border-radius:4px;">'
        f'<b>{p.get("name")}</b> ({p.get("room")}/{p.get("role")})<br>'
        f'{p.get("kind")} — {p.get("result")}<br>'
        f'<button onclick="dec(\'{p.get("id")}\',\'approve\')" style="background:#4d5f37;color:#eef4e2;border:1px solid #8fb35a;padding:6px 12px;margin:6px 6px 0 0;border-radius:3px;">✓ Validar</button>'
        f'<button onclick="dec(\'{p.get("id")}\',\'reject\')" style="background:transparent;color:#c04a34;border:1px solid #c04a34;padding:6px 12px;margin-top:6px;border-radius:3px;">✗ Rejeitar</button>'
        f'</div>'
        for p in pend
    ) or '<p style="color:#5f6355">Sem nada a aprovar.</p>'
    html = f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TEMSPEST — Aprovacao</title>
<style>body{{background:#0a0c08;color:#e7e4d6;font-family:monospace;padding:16px;}} h1{{color:#8fb35a;}}</style>
<script>
function dec(id,a){{fetch('/api/decide',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id,action:a}})}}).then(()=>location.reload());}}
setInterval(()=>location.reload(),5000);
</script></head>
<body><h1>TEMSPEST // Aprovacao (telemovel)</h1>
<p style="color:#9a9c8c;font-size:12px">Aprova os agentes do simulador. Atualiza sozinho.</p>
{cards}</body></html>"""
    return Response(html, mimetype="text/html")

@app.route("/incoming", methods=["GET", "POST"])
def incoming():
    """Recebe comandos via WhatsApp (ex: 'sim ID' / 'nao ID').
    Integra com o teu numero ou com um bot. Aqui aceitamos POST simples."""
    txt = ""
    if request.method == "POST":
        txt = (request.get_json(force=True) or {}).get("text", "")
    else:
        txt = request.args.get("text", "")
    import re
    m = re.match(r"(sim|nao|sim|yes|no)\s+(\w+)", txt.strip().lower())
    if m:
        action = "approve" if m.group(1) in ("sim", "yes") else "reject"
        pid = m.group(2)
        with _lock:
            item = next((p for p in DATA["pending"] if p.get("id") == pid), None)
            if item:
                DATA["pending"] = [p for p in DATA["pending"] if p.get("id") != pid]
                DATA["decisions"].append({"id": pid, "action": action})
                save(DATA)
                return jsonify({"ok": True, "action": action})
        return jsonify({"ok": False, "reason": "id nao encontrado"})
    return jsonify({"ok": False, "hint": "envia: sim ID  ou  nao ID"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"TEMSPEST bridge em http://localhost:{port}  (abre no telemovel via o teu IP/rede)")
    print(f"WhatsApp numero alvo: {WHATSAPP_NUMBER}")
    app.run(host="0.0.0.0", port=port, debug=False)
