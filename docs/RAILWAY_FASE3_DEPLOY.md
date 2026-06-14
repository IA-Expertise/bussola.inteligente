# Fase 3 — Deploy Railway (app + webhook Asaas)

Dois serviços no **mesmo projeto**, **mesmo repositório**, branch **`migracao-railway`**.

## 1. Serviço Streamlit (já existe)

| Variável | Valor |
|----------|--------|
| `BUSSOLA_SERVICE` | `app` ou **omitir** |
| `DATABASE_URL` | Postgres do projeto |
| `OPENAI_API_KEY` | sua chave |
| `BUSSOLA_AUTH_SECRET` | string aleatória longa |
| `ASAAS_API_KEY` | produção Asaas |
| `ASAAS_SANDBOX` | `0` |
| `ASAAS_BILLING_TYPE` | `PIX` |
| `RELATORIO_PRECO_REAIS` | `19.90` |

**Não** coloque `ASAAS_WEBHOOK_TOKEN` no Streamlit.

**Start:** `Procfile` → `python scripts/railway_start.py` → Streamlit.

---

## 2. Criar serviço webhook (manual no Railway)

1. Projeto → **+ New** → **GitHub Repo** → mesmo repo `bussola.inteligente`.
2. Nome sugerido: **`bussola-webhook`**.
3. Branch: **`migracao-railway`**.
4. **Variables:**

| Variável | Valor |
|----------|--------|
| `BUSSOLA_SERVICE` | **`webhook`** |
| `DATABASE_URL` | **mesma** do Postgres |
| `ASAAS_API_KEY` | **mesma** do app |
| `ASAAS_SANDBOX` | `0` |
| `ASAAS_WEBHOOK_TOKEN` | token do painel Asaas |

5. **Networking** → **Generate Domain** (URL pública).
6. Deploy. Teste: `GET https://SUA-URL/health` → JSON `"service": "webhook"`.

**Não** use a URL do Streamlit no Asaas (dá erro 405).

---

## 3. Painel Asaas

1. **Integrações → Webhooks** → criar/editar.
2. Versão **v3**.
3. URL: `https://SUA-URL-WEBHOOK.up.railway.app/webhook/asaas`
4. Token → copiar para `ASAAS_WEBHOOK_TOKEN` no Railway → **Salvar** no Asaas.
5. Eventos: `PAYMENT_RECEIVED`, `PAYMENT_CONFIRMED`.
6. Webhook **ativo**.

---

## 4. Teste ponta a ponta

1. Preview → desbloquear → login → checkout.
2. **Gerar cobrança Pix** → copiar Pix ou abrir link Asaas.
3. Pagar (sandbox ou valor real).
4. **Já paguei — verificar** ou aguardar webhook.
5. Relatório completo + download HTML.

---

## 5. Troubleshooting

| Problema | Causa provável |
|----------|----------------|
| 405 no webhook | URL aponta para Streamlit |
| 401 webhook | Token Railway ≠ Asaas |
| Pix ok, relatório não abre | `DATABASE_URL` ausente no webhook |
| `GET /health` retorna HTML | `BUSSOLA_SERVICE` não é `webhook` |

Detalhe técnico: `docs/INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md`
