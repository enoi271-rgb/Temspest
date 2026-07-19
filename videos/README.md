# TEMSPEST — ESTRUTURA DE VÍDEOS

Organização pronta para publicação em massa (YouTube Shorts / TikTok / Instagram Reels).

```
videos/
├── clips/          # Todos os clips extraídos das 4 fontes (short_/clutch_/reel_)
│   ├── cod_main/   # Call of Duty (fonte 1) — Warzone Angola
│   ├── cod_2/      # Call of Duty (fonte 2) — Clutch
│   ├── cod_3/      # Call of Duty (fonte 3) — Montage
│   └── ghost/      # Ghost Angolano
├── shorts/         # 42 Shorts VERTICAIS (9:16) COM HUD TEMSPEST — prontos p/ publicar
└── completos/      # 4 vídeos completos originais (prontos a publicar)
    ├── cod_main_completo.mp4
    ├── cod_2_completo.mp4
    ├── cod_3_completo.mp4
    └── ghost_completo.mp4
```

## Como publicar
1. **Shorts**: `videos/shorts/` → 42 vídeos 1080×1920, 30s, com HUD TEMSPEST.
   Usa `publicar_shorts.md` (na raiz) para títulos + hashtags + legendas.
2. **Clips**: `videos/clips/` → cortes por categoria (short_/clutch_/reel_).
3. **Completos**: `videos/completos/` → vídeos longos prontos para YouTube/TikTok.

## Regenerar HUD nos shorts
```bash
./.venv/bin/python apply_hud_shorts.py
```

## Notas
- Todos os shorts: 1080×1920, ≤60s (formato Shorts/Reels).
- HUD: `assets/hud_vertical.png` (identidade TEMSPEST).
- Vídeos pesados estão no `.gitignore` (locais, não vão ao GitHub).
