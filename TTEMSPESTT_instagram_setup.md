# TTEMSPESTT — Configuração de Publicação Automática (Meta Graph API)

## Pré-requisitos (já confirmados)
- ✅ Instagram @duna_peps é **Professional/Business**
- ⚠️ Precisa de estar **ligado a uma Facebook Page** (obrigatório para content publishing via Facebook Login)
- ⚠️ Precisa de uma **Meta App** (eu não crio — tu fazes no teu lado, leva 5 min)

## PASSO 1 — Criar Meta App (do teu lado, no browser)
1. Vai a https://developers.facebook.com/apps/creation
2. Caso de uso: **"Other"** → tipo de app: **"Business"**
3. Na app, em **Add Products**, adiciona **"Instagram Graph API"** (configuração com Facebook Login)
4. Em **Roles → Users**, adiciona o teu Facebook como admin

## PASSO 2 — Ligar a Page (obrigatório)
- No Instagram Business, em Settings → Accounts Center → Linked accounts, confirma que está ligado à tua Facebook Page (a mesma que @TTEMSPESTT no Facebook, se existir)
- Se não tiveres Page, cria uma: facebook.com/pages/create (nome: TTEMSPESTT)

## PASSO 3 — Gerar token de acesso (do teu lado)
1. Na Meta App → **Instagram Graph API → API Setup with Facebook Login**
2. Clica em "Add Instagram account" / gera o token
3. Troca por **long-lived token (60 dias)**:
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=APP_ID
     &client_secret=APP_SECRET
     &fb_exchange_token=SHORT_LIVED_TOKEN
   ```
4. **Copia o long-lived token** e envia-me (ou guarda em ficheiro local seguro)

## PASSO 4 — Obter IDs (eu faço com o token)
- `ig_user_id` via: GET /me/accounts?fields=instagram_business_account{id}
- O token + ig_user_id ficam guardados do meu lado (ficheiro local, não partilhado)

## RENOVAÇÃO
- Long-lived token dura **60 dias**. Avisa-me ~50 dias depois para renovar (precisas de refazer Passo 3, ou usar refresh_token se a app tiver权限).

## SEGURANÇA
- O token dá acesso total à tua conta por 60 dias. Nunca o coloques em sítios públicos.
- Eu guardo apenas localmente em ~/.hermes/ (fora do repo).

---
*Gerado por Agent Migs para TTEMSPESTT · 2026*
