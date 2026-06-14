# Fase 0 — Domínio e variáveis de ambiente

Checklist enquanto o domínio é registrado e apontado.

## DNS sugerido

| Registro | Destino |
|----------|---------|
| `www.bussolainteligente.com.br` (ou seu domínio) | LP estática (Vercel / Cloudflare Pages) |
| `app.bussolainteligente.com.br` | Serviço Streamlit no Railway |
| `webhook.bussolainteligente.com.br` | Serviço webhook Asaas (Fase 3) |

## Variáveis — serviço Streamlit (app)

| Variável | Exemplo | Fase |
|----------|---------|------|
| `DATABASE_URL` | Postgres Railway | já em uso |
| `OPENAI_API_KEY` | sk-… | já em uso |
| `BUSSOLA_APP_URL` | `https://app.bussolainteligente.com.br/` | 0 |
| `BUSSOLA_LP_URL` | `https://www.bussolainteligente.com.br` | 0 |
| `RELATORIO_PRECO_REAIS` | `19.90` | 1 |
| `BUSSOLA_DEV_UNLOCK_RELATORIO` | `1` só em teste | 1 (dev) |

## Deploy da LP (`landing/`)

1. Pasta `landing/` → Vercel ou Cloudflare Pages (root = `landing`).
2. Edite `landing/sitemap.xml` e meta `og:url` em `index.html` com o domínio final.
3. CTA aponta para `BUSSOLA_APP_URL` (Railway ou `app.` customizado).

## Branch de trabalho

- Desenvolvimento monetização: **`feat/monetizacao`**
- Produção estável até merge: **`migracao-railway`** / **`main`**
