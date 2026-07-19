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

# === PASTAS DA ESTACAO (filesystem local, sem web upload) ===
ESTACAO = os.path.join(BASE, "estacao")
SALAS = {
    "sala_criacao":   {"num": "R1", "name": "SALA DE CRIACAO",   "path": os.path.join(ESTACAO, "sala_criacao")},
    "sala_edicao":    {"num": "R2", "name": "SALA DE EDICAO",    "path": os.path.join(ESTACAO, "sala_edicao")},
    "sala_negocios":  {"num": "R3", "name": "SALA DE NEGOCIOS",  "path": os.path.join(ESTACAO, "sala_negocios")},
    "sala_financeira":{"num": "R4", "name": "GESTORES FINANCEIROS", "path": os.path.join(ESTACAO, "sala_financeira")},
    "sala_publicidade":{"num": "R5", "name": "ESTUDIO PUBLICITARIO", "path": os.path.join(ESTACAO, "sala_publicidade")},
}
IDEIAS_DIR = os.path.join(ESTACAO, "ideias_negocio")

# subpastas da Sala de Negocios
NEG_ANALISE = os.path.join(SALAS["sala_negocios"]["path"], "documentos_analise")
NEG_CRIADOS = os.path.join(SALAS["sala_negocios"]["path"], "documentos_criados")
# subpastas da Sala de Publicidade (R5)
PUB_BRIEF = os.path.join(SALAS["sala_publicidade"]["path"], "briefings")
PUB_ADS   = os.path.join(SALAS["sala_publicidade"]["path"], "publicidades")
PUB_APROV = os.path.join(SALAS["sala_publicidade"]["path"], "aprovacao_cliente")

def ensure_estacao():
    os.makedirs(IDEIAS_DIR, exist_ok=True)
    os.makedirs(NEG_ANALISE, exist_ok=True)
    os.makedirs(NEG_CRIADOS, exist_ok=True)
    os.makedirs(PUB_BRIEF, exist_ok=True)
    os.makedirs(PUB_ADS, exist_ok=True)
    os.makedirs(PUB_APROV, exist_ok=True)
    for s in SALAS.values():
        os.makedirs(s["path"], exist_ok=True)
    # README em cada sala a explicar o que vai la
    hints = {
        "sala_criacao":   "Aqui a Sala de Criacao vai buscar referencias de clips/shorts/hashtags. Coloca aqui: estilos, exemplos, briefings de edicao.",
        "sala_edicao":    "Aqui a Sala de Edicao vai buscar referencias de cor, som, thumbnails. Coloca aqui: LUTs, audio refs, estilos de thumb.",
        "sala_negocios":  "Sala de Negocios: documentos_analise/ (coloca AQUI os docs para analisar) + documentos_criados/ (os planos de negocio gerados ficam aqui).",
        "sala_financeira":"A Sala de Gestores Financeiros vai buscar aqui relatorios de capital/contabilidade. O backend escreve aqui os resumos de balanco.",
        "sala_publicidade":"Estudio Publicitario: briefings/ (pedidos de clientes) + publicidades/ (2 versoes geradas por cliente) + aprovacao_cliente/ (aguarda OK do cliente).",
    }
    for key, s in SALAS.items():
        readme = os.path.join(s["path"], "README.txt")
        if not os.path.exists(readme):
            with open(readme, "w", encoding="utf-8") as f:
                f.write(hints.get(key, ""))
ensure_estacao()

def slugify(txt):
    import re
    t = re.sub(r'[^a-z0-9]+', '-', txt.lower()).strip('-')
    return (t or "ideia")[:60]

WHATSAPP_NUMBER = os.environ.get("TTEMSPEST_WHATSAPP", "244XXXxxxxxxx")
KZ_PER_USD = float(os.environ.get("KZ_PER_USD", "850"))  # 1 USD em Kwanza
IG_TOKEN = os.environ.get("IG_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")
YT_API_KEY = os.environ.get("YT_API_KEY", "")

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
    CREATE TABLE IF NOT EXISTS platform_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        platform TEXT,
        video_id TEXT,
        title TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        url TEXT,
        hashtags TEXT
    );
    CREATE TABLE IF NOT EXISTS hashtag_stats (
        tag TEXT PRIMARY KEY,
        total_views INTEGER DEFAULT 0,
        posts INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS business_docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        filename TEXT,
        tipo TEXT,
        texto TEXT
    );
    CREATE TABLE IF NOT EXISTS business_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT DEFAULT (datetime('now')),
        idea TEXT,
        plano TEXT,
        autor TEXT,
        meta_receita REAL DEFAULT 0,
        prazo_meses INTEGER DEFAULT 0
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
<div style="background:#1a140c;border:1px solid #8fb35a;color:#8fb35a;padding:8px 12px;margin-bottom:12px;font-size:13px;border-radius:4px;">
  👉 ABRE A <b>ESTACAO COMPLETA</b> (simulador + carregar documentos + planos):
  <a href="/station" style="color:#e7e4d6;">http://192.168.1.71:5050/station</a>
  &nbsp;|&nbsp; ou <a href="http://localhost:5050/station" style="color:#e7e4d6;">http://localhost:5050/station</a>
</div>
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


@app.route("/station")
def station_page():
    # serve o simulador completo (com backend ativo: upload, ideia, ganhos, analytics)
    try:
        with open(os.path.join(BASE, "index.html"), encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/html")
    except Exception as e:
        return Response("<h1>index.html nao encontrado: %s</h1>" % e, mimetype="text/html")

# ---------- VIEWS REAIS (YouTube / TikTok / Instagram) ----------
import urllib.request, json as _json

def store_video(platform, video_id, title, views, likes, url, hashtags):
    with _lock:
        cx = db()
        cx.execute("INSERT INTO platform_views(platform,video_id,title,views,likes,url,hashtags) VALUES(?,?,?,?,?,?,?)",
                   (platform, video_id, title, views, likes, url, hashtags))
        # atualiza hashtag_stats
        for t in (hashtags or "").split():
            t = t.strip()
            if not t: continue
            row = cx.execute("SELECT * FROM hashtag_stats WHERE tag=?", (t,)).fetchone()
            if row:
                cx.execute("UPDATE hashtag_stats SET total_views=total_views+?, posts=posts+1 WHERE tag=?", (views, t))
            else:
                cx.execute("INSERT INTO hashtag_stats(tag,total_views,posts) VALUES(?,?,1)", (t, views))
        cx.commit(); cx.close()

@app.route("/api/views/manual", methods=["POST"])
def views_manual():
    d = request.get_json(force=True)
    store_video(d.get("platform","Outro"), d.get("video_id","-"), d.get("title",""),
                int(d.get("views",0)), int(d.get("likes",0)), d.get("url",""), d.get("hashtags",""))
    return jsonify({"ok": True})

@app.route("/api/ig/sync", methods=["POST"])
def ig_sync():
    if not IG_TOKEN or not IG_USER_ID:
        return jsonify({"ok": False, "reason": "IG_TOKEN/IG_USER_ID em falta no .env"}), 400
    try:
        url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media?fields=id,caption,media_type,media_url,permalink,like_count,views&access_token={IG_TOKEN}"
        req = urllib.request.urlopen(url, timeout=20)
        data = _json.load(req)
        for m in data.get("data", []):
            cap = m.get("caption") or ""
            tags = " ".join([w for w in cap.split() if w.startswith("#")])
            store_video("Instagram", m.get("id"), (cap[:60] or "post"),
                        int(m.get("views") or m.get("like_count") or 0),
                        int(m.get("like_count") or 0), m.get("permalink",""), tags)
        return jsonify({"ok": True, "synced": len(data.get("data", []))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/yt/sync", methods=["POST"])
def yt_sync():
    if not YT_API_KEY:
        return jsonify({"ok": False, "reason": "YT_API_KEY em falta no .env"}), 400
    # requer channel_id no body; busca videos recentes do canal
    ch = (request.get_json(force=True) or {}).get("channel_id") or request.args.get("channel_id")
    if not ch: return jsonify({"ok": False, "reason": "channel_id necessario"}), 400
    try:
        # lista de uploads
        u = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={ch}&key={YT_API_KEY}"
        cd = _json.load(urllib.request.urlopen(u, timeout=20))
        upl = cd["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=20&playlistId={upl}&key={YT_API_KEY}"
        ids = [i["contentDetails"]["videoId"] for i in _json.load(urllib.request.urlopen(pl, timeout=20))["items"]]
        vurl = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={','.join(ids)}&key={YT_API_KEY}"
        for v in _json.load(urllib.request.urlopen(vurl, timeout=20))["items"]:
            sn = v["snippet"]; st = v.get("statistics", {})
            tags = " ".join(sn.get("tags", [])[:10])
            store_video("YouTube", v["id"], sn.get("title",""), int(st.get("viewCount",0)),
                        int(st.get("likeCount",0)), f"https://youtu.be/{v['id']}", tags)
        return jsonify({"ok": True, "synced": len(ids)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/analytics", methods=["GET"])
def analytics():
    cx = db()
    total = cx.execute("SELECT COALESCE(SUM(views),0) FROM platform_views").fetchone()[0]
    by_plat = cx.execute("SELECT platform, COALESCE(SUM(views),0) views, COUNT(*) n FROM platform_views GROUP BY platform ORDER BY views DESC").fetchall()
    top_v = cx.execute("SELECT platform,title,views,url FROM platform_views ORDER BY views DESC LIMIT 8").fetchall()
    top_h = cx.execute("SELECT tag,total_views,posts FROM hashtag_stats ORDER BY total_views DESC LIMIT 10").fetchall()
    cx.close()
    return jsonify({
        "total_views": total,
        "by_platform": [dict(r) for r in by_plat],
        "top_videos": [dict(r) for r in top_v],
        "top_hashtags": [dict(r) for r in top_h],
    })

@app.route("/analytics")
def analytics_page():
    try:
        a = analytics().get_json()
    except Exception:
        a = {"total_views":0,"by_platform":[],"top_videos":[],"top_hashtags":[]}
    plat = "".join(f'<div style="border:1px solid #3d4530;padding:6px 10px;margin:4px 0;font-size:13px;">'
                   f'<b style="color:#8fb35a">{p["platform"]}</b>: {p["views"]:,} views · {p["n"]} videos</div>' for p in a["by_platform"])
    tv = "".join(f'<div style="border:1px solid #3d4530;padding:6px 10px;margin:4px 0;font-size:12px;">'
                 f'{t["platform"]} · <b>{t["views"]:,}</b> views<br><a href="{t["url"]}" style="color:#9a9c8c;font-size:10px">{t["title"]}</a></div>' for t in a["top_videos"])
    th = "".join(f'<div style="font-size:12px;padding:2px 0;">{h["tag"]} — <b>{h["total_views"]:,}</b> views ({h["posts"]} posts)</div>' for h in a["top_hashtags"])
    html = f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TEMSPEST // Analytics</title>
<style>body{{background:#0a0c08;color:#e7e4d6;font-family:monospace;padding:16px;}} h1{{color:#8fb35a;}} h3{{color:#8fb35a;}}</style></head>
<body>
<h1>TEMSPEST // ANALYTICS (views reais)</h1>
<div style="font-size:28px;color:#8fb35a;margin:8px 0;">{a['total_views']:,} views totais</div>
<h3>Por plataforma</h3>{plat or '<p style="color:#5f6355">Sem dados. Usa /api/views/manual ou sincroniza IG/YT.</p>'}
<h3>Videos mais assistidos</h3>{tv or '<p style="color:#5f6355">Nenhum.</p>'}
<h3>Hashtags que atraem (por views)</h3>{th or '<p style="color:#5f6355">Nenhuma.</p>'}
<p style="color:#9a9c8c;font-size:11px;margin-top:14px;">Os clips guardados estao em clips/ (ver no simulador / repositorio). Planos de negocio em negocios/.</p>
</body></html>"""
    return Response(html, mimetype="text/html")

# ---------- SALA DE NEGOCIO: upload PDF/Word + plano de consultoria ----------
import os as _os
from werkzeug.utils import secure_filename

def ler_doc(path, ext):
    # tenta extrair texto; fallback nome
    try:
        if ext in (".pdf",):
            try:
                from pdfminer.high_level import extract_text
                return extract_text(path)[:8000]
            except Exception:
                return "(PDF sem extrator — instala pdfminer.six)"
        if ext in (".docx", ".doc"):
            try:
                import docx
                d = docx.Document(path)
                return "\n".join([pp.text for pp in d.paragraphs])[:8000]
            except Exception:
                return "(DOCX sem extrator — instala python-docx)"
        if ext in (".txt", ".md"):
            return open(path, encoding="utf-8", errors="ignore").read()[:8000]
    except Exception as e:
        return "(erro a ler: %s)" % e
    return ""

def gen_plan(idea, docs_text):
    # Plano de consultoria "15 anos de experiencia" — estruturado, offline
    autor = "STRATEGIST"
    meta = 50000.0
    prazo = 12
    idea_u = (idea or "ideia sem nome").strip().capitalize()
    doc_ctx = (docs_text or "")[:1500]
    plano = []
    plano.append("PLANO DE NEGOCIO — %s" % idea_u)
    plano.append("Elaborado pela Sala de Negocios (TTEMSPESTT) com criterio de consultoria senior.\n")
    plano.append("1. RESUMO EXECUTIVO")
    plano.append("  %s e uma oportunidade de negocio em Angola com trajecto de receita recorrente. " % idea_u)
    plano.append("Posicionamento: marca forte de gaming/creator economy. Meta conservadora ano 1: %s USD; trajecto a 12 meses." % int(meta))
    plano.append("\n2. ANALISE DE MERCADO")
    plano.append("  Mercado angolano: 35M habitantes, penetracao movel >70%, creator economy em fase inicial (pouca concorrencia qualificada).")
    plano.append("  Diferencial: ecossistema de agentes automaticos a produzir conteudo 24/7. Risco baixo de saturação a curto prazo.")
    if doc_ctx:
        plano.append("  Contexto dos teus documentos carregados: %s" % doc_ctx[:600].replace("\n"," "))
    plano.append("\n3. MODELO DE RECEITA")
    plano.append("  Fontes: AdSense/RPM + sponsors locais + affiliatos + TikTok Shop + eventos ao vivo.")
    plano.append("  Estimativa conservadora ano 1: %s USD (não inclui escala de canal). Margem operacional alvo: 60%%." % int(meta))
    plano.append("\n4. OPERACOES")
    plano.append("  Sala de Criacao (4 estacoes) produz clips/shorts/reels diarios. Sala de Edicao eleva qualidade/RPM.")
    plano.append("  Sala de Negocios gere funil, parcerias eroadmap. Tudo orquestrado pela sala E (Hermes).")
    plano.append("\n5. RISCO E MITIGACAO")
    plano.append("  Volatilidade Kz -> contabilizar em USD (taxa 850 Kz/USD). Plataformas mudam -> diversificar 4 canais.")
    plano.append("  Burnout -> agentes com morale + movimento. Concentracao de sponsor -> funil multiplas fontes.")
    plano.append("\n6. ROADMAP (%s meses)" % prazo)
    plano.append("  Fase 1 (0-3m): lancar operacao, 50 clips, 1 sponsor. Fase 2 (3-9m): 200 clips/mes + TikTok Shop.")
    plano.append("  Fase 3 (9-24m): equipa 20+ agentes, parceria internacional, $1M. Fase 4 (24m+): dominio gaming Angola.")
    plano.append("\n7. KPIs VISIVEIS")
    plano.append("  Views totais (YouTube/TikTok/Instagram), capital real (finance.db), clips/mes, RPM, retencao >45%%, CTR thumb >8%%.")
    plano.append("\nRESULTADO ESPERADO (visivel): %s USD em 12 meses, escalavel para o objetivo de $2B." % int(meta))
    return "\n".join(plano), autor, meta, prazo

@app.route("/api/doc/upload", methods=["POST"])
def doc_upload():
    f = request.files.get("file")
    if not f: return jsonify({"ok": False, "reason": "sem ficheiro"}), 400
    fn = secure_filename(f.filename)
    ext = _os.path.splitext(fn)[1].lower()
    if ext not in (".pdf", ".docx", ".doc", ".txt", ".md"):
        return jsonify({"ok": False, "reason": "formato nao suportado (usa PDF/Word/txt)"}), 400
    tmp = _os.path.join(BASE, "uploads")
    _os.makedirs(tmp, exist_ok=True)
    path = _os.path.join(tmp, fn)
    f.save(path)
    texto = ler_doc(path, ext)
    with _lock:
        cx = db()
        cx.execute("INSERT INTO business_docs(filename,tipo,texto) VALUES(?,?,?)", (fn, ext, texto))
        cx.commit(); cx.close()
    # alimenta os agentes
    fetch_notify = False
    try:
        import requests
        requests.post("http://127.0.0.1:%s/api/info" % int(os.environ.get("PORT",5050)),
                        json={"text": "Documento carregado: %s. Usa como base para planos." % fn}, timeout=3)
    except Exception:
        pass
    return jsonify({"ok": True, "filename": fn, "chars": len(texto)})

@app.route("/api/idea", methods=["POST"])
def idea():
    d = request.get_json(force=True) or {}
    idea_txt = d.get("idea", "")
    if not idea_txt.strip(): return jsonify({"ok": False, "reason": "ideia vazia"}), 400
    # junta contexto dos docs carregados
    cx = db(); docs = cx.execute("SELECT texto FROM business_docs ORDER BY id DESC LIMIT 3").fetchall(); cx.close()
    ctx = "\n".join([r[0] for r in docs])
    plano, autor, meta, prazo = gen_plan(idea_txt, ctx)
    with _lock:
        cx = db()
        cx.execute("INSERT INTO business_plans(idea,plano,autor,meta_receita,prazo_meses) VALUES(?,?,?,?,?)",
                   (idea_txt, plano, autor, meta, prazo))
        cx.commit(); cx.close()
    # === ESCREVE FICHEIRO REAL NAS PASTAS (sem web upload) ===
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(idea_txt)
    fname = "%s__%s.md" % (ts, slug)
    # 1) documento na pasta de ideias de negocio
    ideia_path = os.path.join(IDEIAS_DIR, fname)
    with open(ideia_path, "w", encoding="utf-8") as f:
        f.write("# IDEIA DE NEGOCIO — %s\n\n" % idea_txt.strip())
        f.write("> Gerado pela Sala de Negocios (TTEMSPESTT) — %s\n\n" % ts)
        f.write(plano)
        f.write("\n\n---\n*Documento produzido automaticamente. Pasta: estacao/ideias_negocio/%s*\n" % fname)
    # 2) contexto tambem vai para a sala de negocios (agentes vao buscar la)
    neg_path = os.path.join(SALAS["sala_negocios"]["path"], fname)
    with open(neg_path, "w", encoding="utf-8") as f:
        f.write("# CONTEXTO DE IDEIA — %s\n\n" % idea_txt.strip())
        f.write(plano)
    return jsonify({"ok": True, "autor": autor, "meta_usd": meta, "prazo": prazo,
                    "file": fname, "path": ideia_path})

@app.route("/api/estacao", methods=["GET"])
def estacao():
    out = {}
    for key, s in SALAS.items():
        files = []
        for fn in sorted(os.listdir(s["path"])):
            fp = os.path.join(s["path"], fn)
            if os.path.isfile(fp):
                files.append({"name": fn, "size": os.path.getsize(fp)})
        out[key] = {"num": s["num"], "name": s["name"], "files": files}
    ideias = []
    for fn in sorted(os.listdir(IDEIAS_DIR)):
        fp = os.path.join(IDEIAS_DIR, fn)
        if os.path.isfile(fp):
            ideias.append({"name": fn, "size": os.path.getsize(fp)})
    out["ideias_negocio"] = ideias
    return jsonify(out)

@app.route("/api/business", methods=["GET"])
def business():
    cx = db()
    docs = cx.execute("SELECT id,filename,tipo FROM business_docs ORDER BY id DESC LIMIT 10").fetchall()
    plans = cx.execute("SELECT id,idea,autor,meta_receita,prazo_meses,ts FROM business_plans ORDER BY id DESC LIMIT 10").fetchall()
    cx.close()
    return jsonify({
        "docs": [dict(r) for r in docs],
        "plans": [dict(r) for r in plans],
    })

@app.route("/api/ad/brief", methods=["POST"])
def ad_brief():
    d = request.get_json(force=True) or {}
    cliente = (d.get("cliente") or "cliente").strip() or "cliente"
    pedido = (d.get("pedido") or "").strip()
    if not pedido:
        return jsonify({"ok": False, "reason": "pedido vazio"}), 400
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(cliente)
    # guarda o briefing do cliente (entrada)
    brief_path = os.path.join(PUB_BRIEF, "%s__%s.txt" % (ts, slug))
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write("CLIENTE: %s\nPEDIDO: %s\nDATA: %s\n" % (cliente, pedido, ts))
    # gera 2 versoes de publicidade/thumbnail (copy + concepto)
    versoes = []
    for v in (1, 2):
        vtext = gen_ad(cliente, pedido, v)
        fname = "%s__%s__v%d.md" % (ts, slug, v)
        vpath = os.path.join(PUB_ADS, fname)
        with open(vpath, "w", encoding="utf-8") as f:
            f.write("# PUBLICIDADE v%d — %s\n\n" % (v, cliente))
            f.write("> Gerado pelo Estudio Publicitario (TTEMSPESTT) — %s\n\n" % ts)
            f.write(vtext)
            f.write("\n\n---\n*Aguarda aprovacao do cliente. Pasta: estacao/sala_publicidade/publicidades/%s*\n" % fname)
        versoes.append({"versao": v, "file": fname, "texto": vtext})
    # ficheiro de aprovacao (estado: pendente)
    apr_path = os.path.join(PUB_APROV, "%s__%s.json" % (ts, slug))
    with open(apr_path, "w", encoding="utf-8") as f:
        json.dump({"cliente": cliente, "pedido": pedido, "ts": ts, "status": "pendente",
                   "versoes": [vv["file"] for vv in versoes]}, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True, "cliente": cliente, "brief": os.path.basename(brief_path),
                    "versoes": [vv["file"] for vv in versoes], "status": "pendente"})

@app.route("/api/ad/approve", methods=["POST"])
def ad_approve():
    d = request.get_json(force=True) or {}
    ts = d.get("ts"); slug = d.get("slug"); versao = int(d.get("versao", 1))
    if not ts or not slug:
        return jsonify({"ok": False, "reason": "faltam ts/slug"}), 400
    apr_path = os.path.join(PUB_APROV, "%s__%s.json" % (ts, slug))
    if not os.path.exists(apr_path):
        return jsonify({"ok": False, "reason": "pedido nao encontrado"}), 404
    data = json.load(open(apr_path, encoding="utf-8"))
    data["status"] = "aprovado"
    data["versao_aprovada"] = versao
    json.dump(data, open(apr_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # regista o resultado (permite avancar projetos)
    try:
        with _lock:
            cx = db()
            cx.execute("INSERT INTO results(agente,tipo,descricao,valor,ts) VALUES(?,?,?,?,?)",
                       ("ESTUDIO_PUB", "publicidade", "Cliente %s aprovou v%d" % (data["cliente"], versao), 0, ts))
            cx.commit(); cx.close()
    except Exception:
        pass
    return jsonify({"ok": True, "cliente": data["cliente"], "versao_aprovada": versao, "status": "aprovado"})

def gen_ad(cliente, pedido, v):
    # gera copy de publicidade (2 versoes distintas) — tom consultor/publicitario
    if v == 1:
        tom = "emocional/impacto"
        head = "Sente a adrenalina. Seja a marca que todos lembram."
    else:
        tom = "racional/beneficio"
        head = "Resultados que falam por si. A tua marca, no proximo nivel."
    L = []
    L.append("VERSAO %d (%s)" % (v, tom))
    L.append("HEADLINE: %s" % head)
    L.append("CLIENTE: %s" % cliente)
    L.append("PEDIDO: %s" % pedido)
    L.append("COPY (30s):")
    L.append("  [%s] %s — conteudo criado pela TEMSPEST para %s. Thumbnail: contraste alto,")
    L.append("  logo do cliente a direita, CTA 'Sabe mais' em baixo. Formato 1080x1920 (Reels/Shorts).")
    L.append("THUMBNAIL: fundo escuro + 1 elemento da marca + texto curto (<=4 pal.).")
    L.append("CTA: 'Fala connosco' / 'Ver campanha'.")
    L.append("ENTREGA: 2 conceptos (este e a v%d) para aprovacao do cliente." % (2 if v == 1 else 1))
    return "\n".join(L)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"TEMSPEST backend (resultados reais) em http://localhost:{port}")
    print(f"WhatsApp numero alvo: {WHATSAPP_NUMBER}")
    app.run(host="0.0.0.0", port=port, debug=False)
