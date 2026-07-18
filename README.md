# TEMSPEST STATION

Simulador interativo temático **Ghost Angolano / TTEMSPESTT** — um "ecossistema de agentes"
que trabalham para gerar **$2 biliões**, inspirado no formato de estações sci-fi
(estilo Station Commander / Space Haven) visto em vídeos de AI agent ecosystems.

## O que é
- Uma **estação** com salas modulares. A primeira sala é a **"Sala dos Criadores"**
  (os "escravos do Ghost") — onde agentes forjam conteúdo (gravar snipes, editar
  clutches, subir shorts, analisar trends).
- Cada agente tem nível, XP, produtividade e clips forjados; sobe de nível sozinho.
- Engine de simulação acumula views + $ até ao objetivo de **$2,000,000,000**.
- Salas 2 (Edição) e 3 (Negócios Angola) desbloqueiam por conquista de capital.

## Como abrir
Apenas abre `index.html` no browser (duplo-clique). Não precisa de servidor.

1. Clica em **▶ Iniciar estação**
2. Sobe a **Velocidade** (até 1000x) para ver o capital subir
3. **+ Recrutar criador** adiciona agentes à Sala 1
4. **📺 Carregar clip** reproduz um vídeo de teste no ecrã da Sala 1

## Estrutura
```
index.html                      # o simulador (estação + salas + HUD + log)
TTEMSPESTT_brand_bible.md       # guia de marca TTEMSPESTT
TTEMSPESTT_pack_generator.html  # gerador de pacotes de publicação (Ghost Ops Terminal)
TTEMSPESTT_instagram_setup.md   # setup de publicação automática via Meta Graph API
ttemspept_publisher.py          # script de publicação Instagram (Reels) a pedido
clips/                          # vídeos de teste (NÃO comitados — ver clips/README.md)
```

## Roadmap
- [ ] Tornar os $ realistas (views × RPM Angola / Tier-1)
- [ ] Implementar Sala 2 (Edição) com mecânica real
- [ ] Implementar Sala 3 (Negócios Angola / Agente de Planos)
- [ ] Agentes de IA reais a correr tarefas
- [ ] Polish visual (bandeira Angola, skull Ghost, sons)

---
*TTEMSPESTT™ — Ghost Angolano · construído com Agent Migs · 2026*
