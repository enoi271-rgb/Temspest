# MANUAL DE GESTAO — TEMSPEST STATION
> Ghost Angolano / TTEMSPESTT · Warzone PC·Console
> Documento para uso eterno. Mantem-te no controlo do ecossistema.
> (Futuro: podes clonar este manual para a tua esposa — ver secao 9.)

---

## 1. O QUE E
TEMSPEST STATION e um **ecossistema de salas** (cada sala = uma nave) onde **agentes autonomos** trabalham 24/7 rumo a **$2B**.
- O simulador (frontend `index.html`) corre no teu Mac como **servidor persistente** (arranca sozinho no login).
- Um **tunnel publico** (Cloudflare) deixa-te aceder de qualquer router / telemovel.
- Um **Menu Bar app** (icone 💀) liga/desliga tudo.
- Os **valores reais** (capital, views, documentos) vivem numa base SQLite (`finance.db`) + pastas em `estacao/secretaria/`.

## 2. COMO ACEDER
| Onde | URL |
|---|---|
| Mac local | `http://localhost:5050/station` |
| Rede local (telemovel no mesmo WiFi) | `http://192.168.1.71:5050/station` |
| **De qualquer lugar** (tunnel) | ler `tunnel_url.txt` ou abrir o Menu Bar 💀 → mostra o link |
| Pagina publica (estatica, sem backend) | `https://enoi271-rgb.github.io/Temspest/` |

> O URL do tunnel muda se o processo reiniciar. O ficheiro `tunnel_url.txt` esta sempre atualizado. Se nao abrir: `bash ~/TEMSPEST_STATION/start_tunnel.sh start`

## 3. ESTRUTURA DAS SALAS
| Sala | Nome | Funcao | Agentes (2 base) |
|---|---|---|---|
| R1 | Criacao | Redes, shorts, cortes, hashtags, textos; **prepara hype de kills** | EDITOR, COPYWRITER |
| R2 | Negocios Angola | Gerar receita de negocio; planos p/ aprovar | STRATEGIST, RESEARCHER |
| R3 | Edicao | Elevar qualidade / RPM | SOUND, RETOUCH, COLORIST |
| R4 | Gestores Financeiros | Contabilizar capital real, ganhos/percas, projetar 2B | CFO, TREASURER |
| R5 | Estudio Publicitario | Thumbnails + anuncios p/ clientes (2 versoes, aguarda aprovacao) | COPY_AD, CLIENT_MGR, ART_DIR, THUMB_MAKER |
| R6 | Web & Presenca | Sites/landing, gestao de contas, presenca em todas as redes | SOCIAL_MGR, AUTOMATOR, BRAND_STRAT |
| R7 | Atendimento & Clientes | Interacoes, reclamacoes, criticas, melhoria | SUPPORT, INSIGHT, SENTIMENT |
| R8 | Relaxe | Nave separada: bar + snooker + sofas; agentes descansam se morale < 28% | — |
| E (HUB) | Mae | Hermes (supervisor) garante que todos trabalham | HERMES |

**Auto-arranque:** ao abrir, o ecossistema fica **ATIVO** sozinho (sem clicar "Ativar"). O botao "ATIVAR" fica desativado.

## 4. BACKEND — ENDPOINTS REAIS (Flask :5050)
Alimentas o sistema por aqui (o simulador chama-os):

| Endpoint | Para que serve |
|---|---|
| `POST /api/entry` | Registar ganho/perca manual (capital real) |
| `GET /api/balance` | Ler capital liquido (USD) |
| `GET /api/ledger` · `POST /api/ledger/reset` | Ver / zerar registos financeiros |
| `POST /api/views/manual` · `POST /api/views/reset` | Introduzir views reais por rede / limpar |
| `POST /api/doc/upload` | Carregar PDF/Word/txt para a Sala de Negocios analisar |
| `POST /api/idea` | Enviar ideia → gera plano em `ideias_negocio/` |
| `GET /api/estacao` | Lista ficheiros das pastas da secretaria |
| `POST /api/open-folder` | Abrir uma pasta no Finder (so Mac local) |
| `POST /api/ad/brief` · `POST /api/ad/approve` | Criar 2 versoes de publicidade / aprovar |
| `POST /api/web/site` · `POST /api/web/guide` | Gerar site HTML + guia de publicacao por rede |
| `POST /api/crm/add` · `POST /api/crm/improve` | Registar interacao/reclamacao + plano de melhoria |
| `POST /api/video/cut` | Corte real de um clip (ffmpeg stream-copy) |
| **`POST /api/video/hype`** | **Processa TODOS os kills → gera cortes de hype (shorts/reels/clips) + copy** |
| `POST /api/ig/sync` · `POST /api/yt/sync` | Sync real de views (precisa de token/key) |
| `GET /analytics` | Pagina de analytics (views por rede) |

## 5. PASTAS (estacao/secretaria/)
```
sala_criacao/      → ideas, cortes, e a subpasta hype/ (os hype videos gerados)
sala_edicao/       → videos melhorados
sala_negocios/     → planos de negocio
sala_financeira/    → registos de capital
sala_publicidade/   → publicidades/ (2 versoes) + aprovacao/
sala_web/           → sites/ + guias/ + contas/
sala_crm/           → interacoes/ + reclamacoes/ + criticas/ + melhorias/
ideias_negocio/     → planos gerados por ideia
videos/clips/cod_main/  → OS TEUS 36 KILLS (origem dos hype)
```

## 6. FLUXO DIARIO DE GESTAO (como alimentar)
1. **Abre** o station (localhost ou tunnel).
2. **Capital real:** painel € → escolhe GANHO/PERCA, valor, origem (YouTube/TikTok/Sponsor), agente → "Registar". Ou `POST /api/entry`.
3. **Documentos:** "Carregar documento" (PDF/Word) → agentes da R2 usam-no nos planos.
4. **Ideias:** "Escrever ideia" → gera plano em `ideias_negocio/`.
5. **Views reais:** so com token IG / key YouTube (ver secao 8). Sem token, o numero fica 0 — nao inventes.
6. **Kills → HYPE:** na **Sala 1**, clica **"⚡ Gerar HYPE de Kills"**. Os agentes processam os 36 clips e geram ~108 cortes (short/reel/clip) + copy com hashtags `#TTEMSPESTT #WarzoneAngola #GhostAngolano`. Tudo vai para `sala_criacao/hype/` e **aguarda a tua aprovacao**.
7. **Publicar:** revê os ficheiros em `hype/`, escolhe os melhores, publica nas redes (manual, por agora). O sistema NAO publica sozinho.

## 7. MANUTENCAO
- **Servidor persistente:** LaunchAgent `com.temspest.station` (arranca no login + auto-recupera).
- **Tunnel persistente:** LaunchAgent `com.temspest.tunnel` (reboot-safe; escreve URL em `tunnel_url.txt`).
- **Menu Bar:** app `station_menu` (icone 💀) → ON/OFF + copiar link.
- **Logs:** `station.err` / `station.log` (servidor), `cloudflared.log` (tunnel).
- **Zerar (se precisares de recomecar limpo):** botoes "ZERAR CAPITAL" e "LIMPAR VIEWS" no simulador.
- **NAO apagues:** `finance.db` (capital real), `estacao/` (trabalho), `videos/` (kills).

## 8. REGRA DE OURO (nunca violar)
- **NAO inventar metricas.** Capital e views SO da backend. Sem backend → mostrar 0 ou "—".
- **NAO inserir dados de teste** no ledger/views. Testes = so leitura.
- **Marca e handles sao sagrados:** TTEMSPESTT / @TEMSPEST999 / @temspest / @TTEMSPESTT. Nunca alterar sem ordem.
- **Publicacao manual:** o sistema prepara, TU aprovas.

## 9. PARA A TUA ESPOSA (futuro)
Quando quiseres que ela opero o sistema, clona este manual:
1. Copia `MANUAL_GESTAO_TEMSPEST.md` → `MANUAL_GESTAO_[NOME].md`.
2. Ajusta a secao 2 (URLs dela) e a secao 8 (o que ela pode/pode nao fazer).
3. Da-lhe o `PROMPT_MESTRE_TEMSPEST.md` — e um prompt auto-contido que qualquer agente entende.
4. Ela so precisa de: abrir o link + carregar documentos/ideias + aprovar hype. O resto e autonomo.

## 10. ESCALAR (plano melhor)
Quando aderires a um plano pago (ex: modelo mais forte / mais ferramentas):
- **Mais agentes por sala:** aumenta `recruitRoom(r, N)` no `index.html`.
- **Tokes reais:** preenche `IG_TOKEN`/`IG_USER_ID` e YouTube API key no `.env` → views automatizadas.
- **Publicacao automatica:** liga `POST /api/ig/sync` + um agendador (cron) depois de aprovar.
- **Mais kills:** adiciona clips a `videos/clips/cod_main/` → o botao HYPE processa-os todos.
- **Backup:** faz copia de `estacao/` + `finance.db` periodicamente (sao o teu patrimonio real).
