#!/usr/bin/env python3
"""
TEMSPEST STATION — Backend de RESULTADOS REAIS
Deixa de ser simulador: os agentes recebem informacao, produzem resultados,
e os ganhos/percas reais sao carregados numa base de dados SQLite (finance.db).

Tabelas:
  ledger      -> cada entrada financeira (ganho/perca) com origem, agente, valor, momento
  info_feed   -> informacao carregada para os agentes processarem
  results     -> resultados produzidos pelos agentes (clips, posts, planos)
  snapshots   -> capital acumulado ao longo do tempo (contagem real)

Endpoints principais:
  POST /api/entry        -> carrega ganho/perca (valor, tipo, origem, nota)
  GET  /api/balance      -> capital real, total ganho, total perca
  POST /api/info         -> carrega informacao para os agentes
  GET  /api/info         -> lista informacao pendente
  POST /api/result       -> agente produz um resultado (link/descricao/valor)
  GET  /api/state        -> estado completo para o simulador/painel
  POST /api/notify       -> (mantido) agente terminou -> pede validacao
  GET  /api/decisions    -> simulador faz poll das tuas acoes
  POST /api/decide       -> telemovel aprova/rejeita
  /                      -> pagina web de aprovacao + carregamento de ganhos
"""
import json, os, sqlite3, threading, time, datetime

try:
    for line in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

from flask import Flask, request, jsonify, Response

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "finance.db")

WHATSAPP_NUMBER = os.environ.get("TTEMSPEST_WHATSAPP", "244XXXxxxxxxx")
KZ_PER_USD = float(os.environ.get("KZ_PER_USD", "850"))

app = Flask(__name__)
_lock = threading.Lock()


def db():
    cx = sqlite3.connect(DB)
    cx.row_factory = sqlite3.Row
    return cx


def init_db():
    cx = db()
    cx.executescript("""
    CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        kind TEXT,          -- 'ganho' | 'perca'
        amount REAL,
        origin TEXT,        -- 'YouTube' | 'TikTok' | 'Instagram' | 'Sponsor' | 'Outro'
        agent TEXT,
        note TEXT
    );
    CREATE TABLE IF NOT EXISTS info_feed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        text TEXT,
        status TEXT DEFAULT 'pendente'   -- 'pendente' | 'processado'
    );
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        agent TEXT,
        room TEXT,
        kind TEXT,         -- 'clip' | 'post' | 'plano' | 'outro'
        title TEXT,
        link TEXT,
        value REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        capital REAL
    );
    """)
    cx.commit()
    cx.close()


init_db()


def balance():
    cx = db()
    row = cx.execute("SELECT COALESCE(SUM(CASE WHEN kind='ganho' THEN amount ELSE -amount END),0) AS bal, "
                     "COALESCE(SUM(CASE WHEN kind='ganho' THEN amount ELSE 0 END),0) AS g, "
                     "COALESCE(SUM(CASE WHEN kind='perca' THEN amount ELSE 0 END),0) AS p FROM ledger").fetchone()
    cx.close()
    return {"capital": row["bal"], "ganho": row["g"], "perca": row["p"]}


def send_whatsapp(text):
    try:
        import pywhatkit
        num = WHATSAPP_NUMBER
        if num and not num.startswith("244XXX"):
            pywhatkit.sendwhatmsg_instantly(f"+{num}", text, wait_time=8, tab_close=True)
            return True
    except Exception as e:
        print("WhatsApp falhou:", e)
    return False


# ---------- FINANCEIRO ----------
@app.route("/api/entry", methods=["POST"])
def entry():
    d = request.get_json(force=True)
    kind = d.get("kind", "ganho")
    amount = float(d.get("amount", 0))
    origin = d.get("origin", "Outro")
    agent = d.get("agent", "-")
    note = d.get("note", "")
    if kind not in ("ganho", "perca") or amount <= 0:
        return jsonify({"ok": False, "reason": "kind invalido ou amount<=0"}), 400
    currency = (d.get("currency") or "USD").upper()
    original = amount
    if currency == "KZ":
        amount = round(amount / KZ_PER_USD, 2)
    with _lock:
        cx = db()
        cx.execute("INSERT INTO ledger(kind,amount,origin,agent,note) VALUES(?,?,?,?,?)",
                   (kind, amount, origin, agent, note))
        cx.commit()
        cx.close()
        b = balance()
        cx = db()
        cx.execute("INSERT INTO snapshots(capital) VALUES(?)", (b["capital"],))
        cx.commit()
        cx.close()
    conv = f" ({original:.2f} {currency} -> {amount:.2f} USD)" if currency == "KZ" else ""
    print(f"ENTRY {kind} {amount} ({origin}) -> capital {b['capital']}{conv}")
    return jsonify({"ok": True, **b})


@app.route("/api/balance", methods=["GET"])
def get_balance():
    return jsonify(balance())

@app.route("/api/rate", methods=["GET"])
def get_rate():
    return jsonify({"kz_per_usd": KZ_PER_USD, "usd_per_kz": 1/KZ_PER_USD})


# ---------- INFO -> AGENTES -> RESULTADOS ----------
@app.route("/api/info", methods=["POST"])
def add_info():
    d = request.get_json(force=True)
    text = (d.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "reason": "texto vazio"}), 400
    cx = db()
    cx.execute("INSERT INTO info_feed(text) VALUES(?)", (text,))
    cx.commit()
    cx.close()
    print("INFO recebida:", text[:60])
    return jsonify({"ok": True})


@app.route("/api/info", methods=["GET"])
def get_info():
    cx = db()
    rows = cx.execute("SELECT * FROM info_feed ORDER BY id DESC LIMIT 50").fetchall()
    cx.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/result", methods=["POST"])
def add_result():
    d = request.get_json(force=True)
    cx = db()
    cx.execute("INSERT INTO results(agent,room,kind,title,link,value) VALUES(?,?,?,?,?,?)",
               (d.get("agent", "-"), d.get("room", "?"), d.get("kind", "outro"),
                d.get("title", ""), d.get("link", ""), float(d.get("value", 0))))
    cx.commit()
    cx.close()
    print("RESULT:", d.get("title"))
    return jsonify({"ok": True})


@app.route("/api/state", methods=["GET"])
def state():
    cx = db()
    b = balance()
    info = cx.execute("SELECT COUNT(*) c FROM info_feed WHERE status='pendente'").fetchone()["c"]
    results = cx.execute("SELECT COUNT(*) c FROM results").fetchone()["c"]
    cx.close()
    return jsonify({"balance": b, "info_pendente": info, "results": results})


# ---------- APROVACAO (mantido do simulador) ----------
PENDING = []


@app.route("/api/notify", methods=["POST"])
def notify():
    item = request.get_json(force=True)
    PENDING.append(item)
    send_whatsapp(f"TEMSPEST: {item.get('name')} terminou {item.get('kind')} — responde 'sim {item.get('id')}'")
    print("NOTIFY:", item.get("name"))
    return jsonify({"ok": True})


@app.route("/api/decisions", methods=["GET"])
def decisions():
    return jsonify(get_decisions())


DECISIONS = []


def get_decisions():
    out = DECISIONS[:]
    DECISIONS.clear()
    return out


@app.route("/api/decide", methods=["POST"])
def decide():
    d = request.get_json(force=True)
    global PENDING
    PENDING = [p for p in PENDING if p.get("id") != d.get("id")]
    DECISIONS.append({"id": d.get("id"), "action": d.get("action")})
    print("DECIDE:", d.get("id"), d.get("action"))
    return jsonify({"ok": True})


@app.route("/api/queue", methods=["GET"])
def queue():
    return jsonify(PENDING)


# ---------- PAGINA WEB (telemovel + carregamento) ----------
@app.route("/", methods=["GET"])
def page():
    b = balance()
    cx = db()
    recent = cx.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT 15").fetchall()
    rows = "".join(
        f'<div style="border:1px solid #3d4530;background:#12150f;padding:6px 10px;margin:4px 0;border-radius:3px;font-size:12px;">'
        f'<b style="color:{"#8fb35a" if r["kind"]=="ganho" else "#c04a34"}">{r["kind"].upper()}</b> '
        f'{r["amount"]:.2f} € · {r["origin"]} · {r["agent"]}<br>'
        f'<span style="color:#9a9c8c;font-size:10px">{r["ts"]} · {r["note"] or ""}</span></div>'
        for r in recent
    )
    cx.close()
    html = f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TEMSPEST // Resultados Reais</title>
<style>body{{background:#0a0c08;color:#e7e4d6;font-family:monospace;padding:16px;}} h1{{color:#8fb35a;margin:0;}}
.cap{{font-size:28px;color:#8fb35a;margin:8px 0;}} .lbl{{color:#9a9c8c;font-size:11px;}}
input,select,textarea,button{{font-family:monospace;font-size:13px;padding:8px;margin:4px 0;width:100%;box-sizing:border-box;border-radius:4px;border:1px solid #3d4530;background:#12150f;color:#e7e4d6;}}
button{{background:#4d5f37;color:#eef4e2;border:1px solid #8fb35a;cursor:pointer;}}</style>
<script>
function post(u,obj){{fetch(u,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(obj)}}).then(()=>location.reload());}}
setInterval(()=>location.reload(),7000);
</script></head>
<body>
<h1>TEMSPEST // RESULTADOS REAIS</h1>
<div class="lbl">CAPITAL ATUAL (contagem real)</div>
<div class="cap">{b['capital']:.2f} €</div>
<div class="lbl">Ganho total: {b['ganho']:.2f} € · Perda total: {b['perca']:.2f} €</div>

<h3 style="color:#8fb35a">+ Carregar GANHO / PERCA</h3>
<form onsubmit="event.preventDefault();post('/api/entry',{{kind:document.getElementById('k').value,amount:parseFloat(document.getElementById('a').value),origin:document.getElementById('o').value,agent:document.getElementById('ag').value,note:document.getElementById('n').value}});">
<select id="k"><option value="ganho">GANHO</option><option value="perca">PERCA</option></select>
<input id="a" type="number" step="0.01" placeholder="Valor (€)">
<input id="o" placeholder="Origem (YouTube/TikTok/Instagram/Sponsor/Outro)">
<input id="ag" placeholder="Agente (ex: VECTOR)">
<input id="n" placeholder="Nota (opcional)">
<button>Registar</button></form>

<h3 style="color:#8fb35a">+ Informacao para os agentes</h3>
<form onsubmit="event.preventDefault();post('/api/info',{{text:document.getElementById('it').value}});">
<textarea id="it" placeholder="Cola aqui a informacao / briefing / dados..."></textarea>
<button>Enviar aos agentes</button></form>

<h3 style="color:#8fb35a">Ultimas entradas</h3>
{rows or '<p style="color:#5f6355">Sem registos ainda.</p>'}
</body></html>"""
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"TEMSPEST backend (resultados reais) em http://localhost:{port}")
    print(f"WhatsApp numero alvo: {WHATSAPP_NUMBER}")
    app.run(host="0.0.0.0", port=port, debug=False)
