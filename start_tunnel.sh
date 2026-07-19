#!/bin/bash
# TEMSPEST STATION — Tunnel público (Cloudflare quick tunnel, sem conta)
# Liga o servidor local :5050 a um URL público (funciona atrás de qualquer router/NAT).
set -e
cd "$(dirname "$0")"
LOG=cloudflared.log
PIDF=cloudflared.pid

start() {
  if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
    echo "Tunnel já a correr: $(cat tunnel_url.txt 2>/dev/null)"
    exit 0
  fi
  echo "A iniciar tunnel Cloudflare para localhost:5050 ..."
  # quick tunnel: -url http://localhost:5050
  nohup cloudflared tunnel --url http://localhost:5050 > "$LOG" 2>&1 &
  echo $! > "$PIDF"
  # espera o URL aparecer no log (linha com trycloudflare.com)
  for i in $(seq 1 30); do
    sleep 1
    URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
    if [ -n "$URL" ]; then
      echo "$URL" > tunnel_url.txt
      echo "TUNNEL PRONTO: $URL"
      echo "Abrir a Station de qualquer lugar: $URL/station"
      exit 0
    fi
  done
  echo "Falhou a obter URL (vê $LOG)."
  exit 1
}

stop() {
  if [ -f "$PIDF" ]; then kill "$(cat "$PIDF")" 2>/dev/null || true; rm -f "$PIDF"; fi
  pkill -f "cloudflared tunnel" 2>/dev/null || true
  rm -f tunnel_url.txt
  echo "Tunnel parado."
}

case "$1" in
  stop) stop;;
  *) start;;
esac
