# Clips de teste (vídeos)

Coloca aqui os teus vídeos de teste para reproduzir na **Sala 1** do TEMSPEST STATION.

## Como usar
1. Copia o teu vídeo para esta pasta, ex.:
   - `clips/teste_full.mp4`  (o teu `Call of Duty_20260704134134.mp4`)
2. No simulador (index.html), clica em **"📺 Carregar clip"** e seleciona o ficheiro.
   - OU aponta o caminho em `clips/manifest.json`:
     ```json
     { "default_clip": "clips/teste_full.mp4", "title": "Ghost Angolano — Teste Completo" }
     ```

## Nota de tamanho
Os vídeos são grandes (o teu de teste tem ~551MB). **NÃO são comitados ao git**
— estão no `.gitignore`. O simulador reproduz a partir do teu disco local.

## Vídeo de teste atual
- `Call of Duty_20260704134134.mp4` (551MB) — gameplay Warzone completo, usado para teste de playback/edição.
