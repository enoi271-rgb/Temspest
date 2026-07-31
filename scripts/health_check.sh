#!/bin/bash
# health_check.sh — TEMSPEST AI OS
# Verifica, em segundos, se a estação está de pé — sem abrir o browser.

echo "🔍 TEMSPEST AI OS — Health Check"
echo "================================="

# 1. Servidor local (porta 5050)
if curl -s -o /dev/null -w "" --max-time 3 http://127.0.0.1:5050/station; then
    echo "✅ Servidor local (5050): A RESPONDER"
else
    echo "❌ Servidor local (5050): SEM RESPOSTA"
fi

# 2. Event Bus — confirma que o ficheiro existe e mostra o último evento
EVENTBUS="$HOME/TEMSPEST_STATION/estacao/event_bus.jsonl"
if [ -f "$EVENTBUS" ]; then
    N=$(wc -l < "$EVENTBUS" | tr -d ' ')
    echo "✅ Event Bus: $N evento(s) registado(s)"
    echo "   Último: $(tail -1 "$EVENTBUS" 2>/dev/null | cut -c1-90)..."
else
    echo "⚠️  Event Bus: ainda sem eventos (ficheiro não existe)"
fi

# 3. Tunnel Cloudflare (lê o ficheiro que o próprio projeto já mantém)
TUNNEL_FILE="$HOME/TEMSPEST_STATION/tunnel_url.txt"
if [ -f "$TUNNEL_FILE" ]; then
    URL=$(cat "$TUNNEL_FILE")
    if curl -s -o /dev/null -w "" --max-time 5 "$URL/station"; then
        echo "✅ Tunnel público: A RESPONDER — $URL"
    else
        echo "⚠️  Tunnel público: URL existe mas não responde — $URL"
    fi
else
    echo "❌ Tunnel público: ficheiro tunnel_url.txt não encontrado"
fi

# 4. Razão financeiro real — só confirma que a base de dados existe e tem tamanho > 0
DB="$HOME/TEMSPEST_STATION/finance.db"
if [ -f "$DB" ] && [ -s "$DB" ]; then
    echo "✅ Razão financeiro (finance.db): presente ($(du -h "$DB" | cut -f1))"
else
    echo "❌ Razão financeiro (finance.db): em falta ou vazio"
fi

echo "================================="
echo "Feito às $(date '+%H:%M:%S')"
