# Bússola Inteligente — App monetizado: plano por fases e guia técnico

Documento para **orientar e agilizar** a evolução do produto: LP indexável, app Streamlit, **cadastro/login**, **Pix Asaas + webhook**, histórico e relatório comparativo.

**Referência de implementação já validada (copiar padrões, adaptar nomes):**  
repositório `IA-Expertise/cpfalerta` + arquivo complementar [`INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md`](./INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md).

**Repositório atual (base):** `bussola.inteligente` — Streamlit + Railway Postgres + `database.py` + tabela `public.leads`.

---

## Visão do produto

| Camada | Tecnologia | Função |
|--------|------------|--------|
| **LP** | HTML estático ou Next.js (Vercel/Cloudflare) | SEO, Google, IA; CTA → app |
| **App** | Streamlit no Railway (`app.seudominio.com.br`) | Preview grátis → pagamento → relatório |
| **Webhook** | Flask/Gunicorn no Railway (serviço **separado**) | Asaas confirma Pix → libera relatório |
| **Banco** | PostgreSQL Railway | Usuários, pagamentos, diagnósticos, histórico |

**Preço alvo:** R$ 19,90 por relatório completo (avulso).  
**Recompra:** relatório **comparativo** (mesmo preço ou pacote futuro).

**Sebrae / instituições:** fora do desenho do produto; no máximo divulgação externa.

---

## Plano de ação por fases

### Fase 0 — Preparação (1–2 dias)

- [x] Definir domínio: `www` → LP · `app` → Streamlit · `webhook` → Asaas (subdomínios) — ver `docs/FASE0_DOMINIO_E_ENV.md`
- [ ] Conta Asaas **dedicada** ou produto separado na API (descrição: “Relatório visibilidade digital Bússola”).
- [x] Variáveis de ambiente documentadas (seção 8 + `.env.example`)
- [x] Branch de trabalho: **`feat/monetizacao`**

**Entrega:** infra e contas prontas; app atual continua no ar.

---

### Fase 1 — LP + preview (3–5 dias)

- [x] LP estática em `landing/` (hero, problema, como funciona, preço, FAQ, CTA)
- [x] `meta` / Open Graph / `sitemap.xml` / JSON-LD básico
- [x] CTA LP → app Railway (atualizar domínio ao registrar)
- [x] Streamlit: etapa **preview** (radar + insight + paywall R$ 19,90; relatório completo só com unlock Fase 3 ou `BUSSOLA_DEV_UNLOCK_RELATORIO=1`)
- [x] Formulário mantido (otimizar depois)

**Entrega:** tráfego indexável + funil até preview grátis.

**Estimativa acumulada:** ~1 semana (meio período) ou 3–5 dias focados.

---

### Fase 2 — Cadastro, login e sessão (3–4 dias)

- [x] `db_manager.py` — cadastro e login (e-mail + senha PBKDF2)
- [x] `session_auth.py` — cookie HMAC `bussola_auth` (extra-streamlit-components)
- [x] Tabela `public.users` (`sql/migrations/002_users.sql` + `database.init_db`)
- [x] Fluxo: preview → desbloquear → **auth** → **checkout** (Pix na Fase 3)
- [x] Pré-preenchimento cadastro com dados do formulário

**Entrega:** usuário identificado para histórico e cobrança (Fase 3).

**Railway:** defina `BUSSOLA_AUTH_SECRET` (string aleatória longa) no serviço Streamlit.

---

### Fase 3 — Asaas Pix + webhook (4–6 dias)

- [x] `payments_asaas.py` — criar cobrança Pix, consultar status, “Já paguei”
- [x] `webhook_asaas.py` — Flask POST `/webhook/asaas` + `/health`
- [x] `scripts/railway_start.py` + `Procfile` — app vs webhook via `BUSSOLA_SERVICE`
- [x] Tabela `public.pagamentos` (`sql/migrations/003_pagamentos.sql`)
- [x] Checkout Streamlit: gerar Pix, copia e cola, verificar pagamento, liberar relatório
- [ ] **Você:** 2º serviço Railway + webhook Asaas v3 — ver `docs/RAILWAY_FASE3_DEPLOY.md`

**Entrega:** Pix pago → relatório completo liberado.

---

### Fase 4 — Histórico (2–3 dias)

- [ ] Tabela `diagnosticos` (ou evoluir `leads` com `user_id`, `tipo`, scores JSON).
- [ ] Listar diagnósticos anteriores do usuário logado.
- [ ] Mensagem: “Último diagnóstico em {data} — gerar novo para ver evolução?”.

**Entrega:** base para comparativo e recompra.

**Estimativa acumulada:** +2–3 dias.

---

### Fase 5 — Relatório comparativo (4–6 dias)

- [ ] Na 2ª+ compra: carregar scores do diagnóstico anterior (mesma empresa/CNPJ ou escolha manual).
- [ ] UI: tabela/gráfico **antes × agora** por eixo; texto “melhorou / manteve / piorou”.
- [ ] IA: prompt adicional com contexto do histórico (opcional).
- [ ] Cobrança avulsa R$ 19,90 (`product_type = relatorio_comparativo`).

**Entrega:** produto de acompanhamento; argumento de recompra mensal.

**Estimativa acumulada:** +4–6 dias.

---

### Fase 6 — Polimento e go-live comercial (2–3 dias)

- [ ] Termos de uso, política de privacidade, texto “ferramenta de apoio”.
- [ ] E-mails transacionais (opcional).
- [ ] Monitoramento: logs webhook, taxa preview → pago.
- [ ] `noindex` no app Streamlit; index só na LP.

**Estimativa total (Fases 1–6):** ~**2–3 semanas** tempo focado · ~**4–6 semanas** meio período.

---

## Arquitetura de pagamento (Bússola vs carteira)

No **CPF Alerta**, o webhook **credita saldo** (`saldo_centavos`).  
Na **Bússola**, o modelo natural é **pagamento por relatório**:

```text
Preview grátis → Cobrança Pix (1 pagamento = 1 relatório) → webhook marca PAGO → libera relatório
```

Opcional depois: carteira ou pacote “3 relatósticos” reutilizando a mesma tabela `pagamentos` com `product_type`.

---

## Cadastro e login — regras de negócio

### Cadastro mínimo

| Campo | Obrigatório | Uso |
|-------|-------------|-----|
| E-mail | Sim | Login, histórico, recibo |
| Senha | Sim | Hash bcrypt/argon2 (como cpfalerta) |
| Nome | Sim | Relatório e Asaas customer |
| Empresa / nome fantasia | Sim | Diagnóstico |
| CNPJ | Não (recomendado PJ) | Histórico e comparativo entre meses |
| CPF | Não | Só se quiser NF PF no futuro |

**Validação CPF/CNPJ:** reutilizar validadores do cpfalerta se cadastro unificado; na Bússola pode ser **soft** (formato) no MVP.

### Login

- E-mail + senha → sessão `st.session_state.user`.
- Cookie assinado HMAC (`session_auth.py`) para persistir após F5.
- Logout: limpar session + cookie.

### Quem precisa estar logado?

| Ação | Login |
|------|-------|
| Ver preview | Não |
| Pagar e ver relatório completo | **Sim** (recomendado) |
| Ver histórico / comparativo | **Sim** |

---

## Webhook Asaas — lógica resumida (checklist executor)

1. **URL no painel Asaas:** `https://bussola-webhook….up.railway.app/webhook/asaas` — **versão v3**.
2. **Token** = `ASAAS_WEBHOOK_TOKEN` **só no serviço webhook** (não no Streamlit).
3. **Mesma** `DATABASE_URL` nos dois serviços.
4. **Mesma** `ASAAS_API_KEY` (produção; `ASAAS_SANDBOX=0`).
5. Fluxo:

```text
Asaas POST → validar token → parse body → extrair payment.id + externalReference
  → buscar pagamentos.asaas_payment_id
  → se já creditado/liberado: 200 OK (idempotente)
  → senão: status = RECEIVED/CONFIRMED, relatorio_liberado = true, diagnostic_id associado
  → 200 OK
```

6. **Streamlit** faz polling ou “Já paguei” até `relatorio_liberado` ou consulta status na API.

Detalhes, troubleshooting (401, 405, penalização v2): ver [`INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md`](./INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md) seções 7–9.

---

## Schema PostgreSQL sugerido (evolução)

Além de `public.leads` (legado), migrar para modelo explícito:

```sql
-- users
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           VARCHAR(255) NOT NULL UNIQUE,
  senha_hash      VARCHAR(255) NOT NULL,
  nome            VARCHAR(255) NOT NULL,
  empresa         VARCHAR(255),
  cnpj            VARCHAR(14),  -- só dígitos, opcional
  asaas_customer_id VARCHAR(64),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- diagnosticos (substitui/evolui leads)
CREATE TABLE diagnosticos (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  timestamp_iso   TEXT NOT NULL,
  payload_json    JSONB NOT NULL,       -- dados do formulário
  scores_json     JSONB,                -- null até preview/relatório
  diagnostico_json JSONB,               -- null até pago
  tipo            VARCHAR(32) NOT NULL DEFAULT 'standard',  -- standard | comparativo
  parent_id       UUID REFERENCES diagnosticos(id),         -- comparativo → anterior
  preview_only    BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pagamentos (1 Pix = 1 relatório)
CREATE TABLE pagamentos (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES users(id),
  diagnostico_id      UUID REFERENCES diagnosticos(id),
  asaas_payment_id    VARCHAR(64) NOT NULL UNIQUE,
  asaas_customer_id   VARCHAR(64),
  valor_centavos      INTEGER NOT NULL DEFAULT 1990,
  status_asaas        VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  relatorio_liberado  BOOLEAN NOT NULL DEFAULT false,
  product_type        VARCHAR(32) NOT NULL DEFAULT 'relatorio_completo',
  external_reference  VARCHAR(128) NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  paid_at             TIMESTAMPTZ
);

CREATE INDEX idx_diagnosticos_user ON diagnosticos (user_id, created_at DESC);
CREATE INDEX idx_pagamentos_user ON pagamentos (user_id, created_at DESC);
```

Arquivo SQL versionado sugerido: `sql/migrations/002_monetizacao.sql` (criar na Fase 2/3).

---

## Preview vs relatório pago — o que gerar quando

| Momento | OpenAI | Conteúdo |
|---------|--------|----------|
| Preview | Chamada **curta** ou scores parciais | Radar + 1 insight + teaser |
| Após pagamento | Chamada **completa** (atual) | Todos os blocos + export HTML |

Alternativa econômica: gerar relatório completo **uma vez** após pagamento; preview usa heurística local + 1 parágrafo IA.

---

## Variáveis de ambiente

### Serviço Streamlit (`app`)

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | Postgres Railway |
| `OPENAI_API_KEY` | Diagnóstico |
| `OPENAI_MODEL` | Opcional |
| `ASAAS_API_KEY` | API v3 |
| `ASAAS_SANDBOX` | `0` produção |
| `ASAAS_BILLING_TYPE` | `PIX` |
| `BUSSOLA_AUTH_SECRET` | Segredo HMAC cookies (32+ bytes) |
| `BUSSOLA_SERVICE` | `app` ou omitir |
| `RELATORIO_PRECO_CENTAVOS` | `1990` |

**Não** definir `ASAAS_WEBHOOK_TOKEN` no Streamlit.

### Serviço webhook

| Variável | Descrição |
|----------|-----------|
| `BUSSOLA_SERVICE` | `webhook` |
| `DATABASE_URL` | Igual ao app |
| `ASAAS_API_KEY` | Igual |
| `ASAAS_SANDBOX` | `0` |
| `ASAAS_WEBHOOK_TOKEN` | Token do painel Asaas |

---

## Arquivos a criar/adaptar (ordem sugerida para o agente)

1. `sql/migrations/002_monetizacao.sql`
2. `db_manager.py` — users, diagnosticos, pagamentos (copiar cpfalerta)
3. `session_auth.py` — cookie `bussola_auth`
4. `payments_asaas.py` — criar cobrança, “Já paguei”, `externalReference`
5. `webhook_asaas.py` — Flask (copiar cpfalerta)
6. `scripts/railway_start.py` — app vs webhook
7. `Procfile` ou `railway.toml` — start via `railway_start.py`
8. Refatorar `app.py` — preview, paywall, login, pós-pagamento
9. LP em repositório separado ou pasta `landing/` (deploy Vercel)

---

## Testes manuais mínimos (antes de anunciar)

| # | Cenário | Esperado |
|---|---------|----------|
| 1 | LP → app → preview sem login | Radar + CTA pagamento |
| 2 | Cadastro + login | Cookie persiste após F5 |
| 3 | Gerar Pix R$ 19,90 | QR + registro `PENDING` |
| 4 | Pagar Pix real (valor baixo teste) | Webhook 200, `relatorio_liberado` |
| 5 | Relatório completo + HTML | Download ok |
| 6 | “Já paguei” sem webhook | Libera via API |
| 7 | 2º diagnóstico mesmo user | Comparativo (Fase 5) |

---

## O que **não** mexer nesta fase

- Qualidade/prompt da análise IA (já aprovada).
- Integração institucional Sebrae no produto.
- Pré-preenchimento Google/CNPJ (Fase futura).

---

## Referências rápidas

- [`INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md`](./INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md) — detalhe webhook, troubleshooting, checklist Railway.
- [`../RAILWAY_POSTGRES.md`](../RAILWAY_POSTGRES.md) — Postgres no Railway.
- [`../DOCUMENTO_TECNICO.md`](../DOCUMENTO_TECNICO.md) — app atual (pré-monetização).

*Última revisão: plano monetização LP + auth + Asaas + histórico + comparativo.*
