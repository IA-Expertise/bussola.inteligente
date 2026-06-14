# Instrução técnica para Agente Cursor — Cadastro (CPF/CNPJ), Login e Webhook Asaas

> **Bússola Inteligente (visibilidade digital):** plano por fases e adaptações de negócio em [`APP_MONETIZADO_PLANO_E_GUIA.md`](./APP_MONETIZADO_PLANO_E_GUIA.md). Este arquivo mantém o **detalhe operacional** do webhook e o padrão copiável do CPF Alerta.

**Documento para implantação em outro app** (ex.: CNPJ Alerta, novo produto IA-Expertise).  
**Referência validada em produção:** repositório `https://github.com/IA-Expertise/cpfalerta` (branch `main`, jun/2026).

> **Regra para o agente executor:** copiar **padrões e arquivos listados**, adaptar prefixos/nomes de env (`CNPJALERTA_*`, `cnpjalerta:`), **não** alterar o repositório `cpfalerta` salvo pedido explícito do stakeholder.

---

## 1. Objetivo

Implementar em um app Streamlit + PostgreSQL:

1. **Cadastro rápido** com documento **CPF ou CNPJ** (configurável por produto).
2. **Login de acesso** (e-mail + senha) com sessão persistente após F5.
3. **Cobrança simples Asaas** (checkout hospedado: PIX/boleto) + **webhook** que credita saldo na carteira.

Escopo **mínimo viável** — sem laudo IA, sem Infosimples, sem agendamentos.

---

## 2. Arquitetura (dois serviços Railway)

```text
┌─────────────────────┐     POST /webhook/asaas      ┌──────────────────────────┐
│  Asaas (produção)   │ ───────────────────────────► │  *-webhook (Flask)       │
│  PAYMENT_RECEIVED   │     header: asaas-access-token│  {PRODUTO}_SERVICE=webhook│
└─────────────────────┘                              └────────────┬─────────────┘
                                                                  │ DATABASE_URL
┌─────────────────────┐     POST /v3/payments                  ▼
│  App Streamlit      │ ◄──────────────────────────►   PostgreSQL (tenants,
│  {PRODUTO}_SERVICE  │     criar cobrança / "Já paguei"        pagamentos, users)
│  ≠ webhook          │
└─────────────────────┘
```

| Serviço Railway | Variável | Processo |
|-----------------|----------|----------|
| `meuapp` (Streamlit) | `{PRODUTO}_SERVICE` ausente ou `app` | `streamlit run app.py` |
| `meuapp-webhook` | `{PRODUTO}_SERVICE=webhook` | `gunicorn webhook_asaas:app` |

**Entrypoint:** `scripts/railway_start.py` (mesmo padrão do CPF Alerta).

**Nunca** apontar URL do webhook para o serviço Streamlit (erro **405 Method Not Allowed**).

---

## 3. Arquivos de referência no CPF Alerta (copiar e adaptar)

| Arquivo | Função |
|---------|--------|
| `db_manager.py` | `cadastrar_tenant_e_usuario`, `verificar_login`, `carregar_sessao_por_user_id`, pagamentos Asaas |
| `session_auth.py` | Cookie HMAC assinado (login após F5) |
| `payments_asaas.py` | Cliente API v3, checkout, webhook, fallback "Já paguei" |
| `webhook_asaas.py` | Flask POST `/webhook/asaas`, parse JSON + form-urlencoded |
| `scripts/railway_start.py` | Escolhe Streamlit vs webhook vs worker |
| `migrations/001_initial_schema.sql` | `tenants`, `users` |
| `migrations/003_pagamentos_asaas.sql` | `pagamentos`, `asaas_customer_id` |
| `migrations/005_saldo_centavos.sql` | `tenants.saldo_centavos` |
| `pricing.py` | Pacotes de recarga (opcional simplificado) |
| Trecho paywall em `app.py` | Cadastro, login, gerar link, "Já paguei" |

**Commits Asaas/webhook recomendados no CPF:** `5da0e49` … `2a943cd` + parse `form-urlencoded` (`e84ea7a`).

---

## 4. Banco de dados (mínimo)

### 4.1 Tabelas

```sql
-- tenants: uma empresa/conta por documento
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_empresa    VARCHAR(255) NOT NULL,
    cnpj_cpf        VARCHAR(18)  NOT NULL UNIQUE,  -- só dígitos: 11 (CPF) ou 14 (CNPJ)
    saldo_centavos  INTEGER NOT NULL DEFAULT 0 CHECK (saldo_centavos >= 0),
    asaas_customer_id VARCHAR(64),
    data_criacao    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- users: login por e-mail
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    data_criacao  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pagamentos: uma linha por cobrança Asaas
CREATE TABLE pagamentos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    pacote_id           VARCHAR(32) NOT NULL,
    valor_centavos      INTEGER NOT NULL CHECK (valor_centavos > 0),
    asaas_payment_id    VARCHAR(64) NOT NULL UNIQUE,
    asaas_customer_id   VARCHAR(64),
    status_asaas        VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    creditos_liberados  BOOLEAN NOT NULL DEFAULT FALSE,
    external_reference  VARCHAR(128),
    invoice_url         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paid_at             TIMESTAMPTZ
);
```

### 4.2 Multi-tenant

Toda query de negócio filtra por `tenant_id` da sessão logada.

---

## 5. Cadastro rápido (CPF ou CNPJ)

### 5.1 Regra de documento (escolher por produto)

| Produto | Documento no cadastro | Validação |
|---------|----------------------|-----------|
| **CPF Alerta** (atual) | **CNPJ** (14 dígitos) — PJ | `cnpj_valido()` |
| **CNPJ Alerta** | **CNPJ** (14 dígitos) | idem |
| **App PF** (se permitir) | **CPF** (11 dígitos) | dígitos verificadores CPF |

Implementar **uma** função `validar_documento_cadastro(doc: str) -> tuple[Literal["CPF","CNPJ"], str]` que:

- remove não-dígitos;
- retorna erro claro se tamanho ≠ 11 e ≠ 14;
- valida checksum (CPF ou CNPJ);
- garante `UNIQUE` em `tenants.cnpj_cpf`.

### 5.2 Campos do formulário (Streamlit)

**Cadastro (aba ou expander):**

- Nome / razão social (`nome_empresa`)
- CPF ou CNPJ (`cnpj_cpf`)
- E-mail (`email`)
- Senha (`senha`, mín. 6 caracteres)
- Confirmar senha

**Login:**

- E-mail
- Senha

### 5.3 Fluxo backend (`cadastrar_tenant_e_usuario`)

1. Validar campos.
2. Verificar duplicidade: `email` OU `cnpj_cpf`.
3. `password_hash = PBKDF2-HMAC-SHA256` (padrão do CPF Alerta em `db_manager`).
4. `INSERT tenants` + `INSERT users` em **uma transação**.
5. (Opcional) bônus de cadastro: `creditar_saldo_centavos(tenant_id, bonus)`.
6. Retornar `UserSession` e gravar em `st.session_state.user`.
7. Chamar `persistir_login_cookie(user)` (`session_auth.py`).

### 5.4 Login

1. `verificar_login(email, senha)` → `UserSession` ou `None`.
2. Se OK: `st.session_state.user = sessao`, `persistir_login_cookie(sessao)`.
3. Se falha: mensagem genérica ("E-mail ou senha incorretos") — não revelar qual campo falhou.

### 5.5 Sessão persistente (F5)

Dependências: `extra-streamlit-components`.

1. No início de `app.py`: `if restaurar_sessao_do_cookie(): st.stop()` (cookies ainda carregando).
2. Env **`{PRODUTO}_SESSION_SECRET`**: string aleatória longa em produção (≠ vazio).
3. Cookie assinado HMAC, TTL 30 dias (`session_auth.py`).

**Logout:** limpar `st.session_state.user` + `limpar_login_cookie()`.

---

## 6. Cobrança simples Asaas (app Streamlit)

### 6.1 Variáveis de ambiente (serviço **app**)

| Variável | Exemplo | Obrigatório |
|----------|---------|-------------|
| `DATABASE_URL` | Postgres Railway | Sim |
| `ASAAS_API_KEY` | chave produção | Sim |
| `ASAAS_SANDBOX` | `0` produção | Sim |
| `ASAAS_BILLING_TYPE` | `PIX` | Recomendado |
| `ASAAS_PAYMENT_SUCCESS_URL` | `https://app.seudominio.com.br` | Opcional |

**Não** colocar `ASAAS_WEBHOOK_TOKEN` no Streamlit (só no serviço webhook).

### 6.2 Fluxo "Gerar link de recarga"

1. Usuário logado escolhe pacote (ex.: R$ 50 / R$ 100).
2. Garantir `asaas_customer_id` no tenant (criar customer na API se ausente):

```python
POST https://api.asaas.com/v3/customers
{ "name": "...", "email": "...", "cpfCnpj": "..." }
```

3. Criar cobrança:

```python
POST https://api.asaas.com/v3/payments
{
  "customer": "cus_...",
  "billingType": "PIX",
  "value": 50.00,
  "dueDate": "YYYY-MM-DD",
  "description": "Recarga de saldo",
  "externalReference": "{prefixo}:{tenant_uuid}:{pacote_id}:{sufixo}"
}
```

4. **`externalReference` obrigatório** — amarra webhook ao tenant se o POST chegar antes do registro local.

   - CPF Alerta: `cpfalerta:{tenant_id}:{pacote_id}:{hex}`
   - CNPJ Alerta: `cnpjalerta:{tenant_id}:{pacote_id}:{hex}`

5. `registrar_pagamento_pendente(...)` → INSERT em `pagamentos` com `creditos_liberados=false`.
6. Exibir `invoiceUrl` (link Asaas) + QR se PIX.

### 6.3 Fallback "Já paguei — verificar"

Botão que chama `confirmar_pagamentos_pendentes_tenant(tenant_id)`:

- `GET /v3/payments/{id}` para cada cobrança pendente;
- se status confirmado → `liquidar_pagamento_asaas` (idempotente).

**Manter** mesmo com webhook OK — útil quando fila Asaas atrasa.

---

## 7. Webhook Asaas (serviço Flask separado)

### 7.1 Variáveis (serviço **webhook**)

| Variável | Valor |
|----------|--------|
| `{PRODUTO}_SERVICE` | `webhook` |
| `DATABASE_URL` | **mesma** do app |
| `ASAAS_API_KEY` | **mesma** produção |
| `ASAAS_SANDBOX` | `0` |
| `ASAAS_WEBHOOK_TOKEN` | = token do painel Asaas |

### 7.2 Painel Asaas (configuração precisa)

1. **Integrações → Webhooks →** criar/editar.
2. **Versão: v3** (v2 legado gera penalização falsa — confirmado suporte Asaas jun/2026).
3. **URL:** `https://SEU-WEBHOOK.up.railway.app/webhook/asaas`
4. **Token:** gerar → copiar para Railway → **Salvar** no Asaas (sem Salvar o header não é enviado).
5. **Eventos:** `PAYMENT_RECEIVED`, `PAYMENT_CONFIRMED`.
6. Webhook **ativo** (toggle ON).
7. **Um** webhook por produto/conta — URL dedicada.

### 7.3 Rotas Flask

| Método | Rota | Função |
|--------|------|--------|
| GET | `/health` | JSON diagnóstico (`service: webhook`) |
| POST | `/webhook/asaas` | Processar evento |
| POST | `/webhook` | Alias (opcional) |

### 7.4 Autenticação

- Header oficial: **`asaas-access-token`** (case-insensitive).
- Comparar com `ASAAS_WEBHOOK_TOKEN` via `hmac.compare_digest`.
- **Fallback** (retentativas sem header): consultar `GET /v3/payments/{pay_id}` **antes** de exigir User-Agent.

### 7.5 Parse do body (causa raiz de incidentes)

Ordem em `_parse_webhook_body`:

1. `raw = request.get_data(cache=True, as_text=True)`
2. `json.loads(raw)` se JSON direto.
3. Se falhar e `Content-Type` form-urlencoded **ou** body começa com `data=`:
   - `parse_qs` + `json.loads(unquote_plus(form["data"][0]))`
4. Extrair **`payment.id`** (`pay_…`) — **nunca** usar `id` raiz (`evt_…`).

Payload v3 inclui bloco opcional `account` — ignorar; usar `body["payment"]`.

### 7.6 Processamento

```text
POST recebido
  → parse body
  → token OK ou fallback API
  → evento PAYMENT_RECEIVED / PAYMENT_CONFIRMED (ou status pago no payment)
  → processar_pagamento_webhook(payment, evento)
  → liquidar_pagamento_asaas (FOR UPDATE, idempotente)
  → HTTP 200 {"ok": true, "accepted": true, "liberado": true|false}
```

**Ping/teste** Asaas (sem `payment.id`): responder **200** `{"ping": true}` — não creditar.

**Liquidação síncrona** no POST — **não** usar thread daemon (Gunicorn mata thread; Asaas vê 200 sem crédito).

### 7.7 Status considerados pagos

`RECEIVED`, `CONFIRMED`, `RECEIVED_IN_CASH`, `DUNNING_RECEIVED`.

### 7.8 Idempotência

- Chave: `pagamentos.asaas_payment_id` UNIQUE + flag `creditos_liberados`.
- Reenvios do mesmo `evt_…` (comportamento "at least once" Asaas) **não** duplicam saldo.
- (Melhoria futura) registrar `evt_…` em tabela `webhook_eventos` UNIQUE.

---

## 8. UI Streamlit sugerida (capa mínima)

```text
[Se não logado]
  Tabs: Login | Cadastro rápido
  Cadastro: nome, CPF/CNPJ, email, senha
  Login: email, senha

[Se logado]
  Topbar: email, saldo R$, logout
  Seção Recarga: pacotes → Gerar link → Já paguei
  (Resto do produto...)
```

Restaurar cookie **antes** de renderizar forms (`restaurar_sessao_do_cookie`).

---

## 9. Deploy Railway — checklist

### Serviço app

- [ ] `DATABASE_URL` (referência Postgres)
- [ ] `ASAAS_API_KEY`, `ASAAS_SANDBOX=0`
- [ ] `{PRODUTO}_SESSION_SECRET` (produção)
- [ ] Domínio público (ex.: `app.seudominio.com.br`)
- [ ] **Não** definir `{PRODUTO}_SERVICE=webhook`

### Serviço webhook

- [ ] `{PRODUTO}_SERVICE=webhook`
- [ ] `DATABASE_URL` (mesma)
- [ ] `ASAAS_API_KEY`, `ASAAS_SANDBOX=0`
- [ ] `ASAAS_WEBHOOK_TOKEN`
- [ ] Domínio dedicado (ex.: `meuapp-webhook-production.up.railway.app`)
- [ ] `GET /health` → JSON, **não** HTML Streamlit

### Procfile

```text
web: python scripts/railway_start.py
```

---

## 10. Testes de aceitação

| # | Teste | Esperado |
|---|-------|----------|
| 1 | Cadastro CPF ou CNPJ válido | Login automático, tenant criado |
| 2 | Cadastro duplicado | Erro "já cadastrado" |
| 3 | Login errado | Mensagem genérica |
| 4 | F5 após login | Sessão mantida (cookie) |
| 5 | Gerar link recarga | `invoiceUrl`, linha em `pagamentos` PENDING |
| 6 | Pagar no Asaas | Log webhook **200**, `liberado: true`, saldo ↑ |
| 7 | Reenvio mesmo evento | 200, saldo **não** duplica |
| 8 | Já paguei (sem webhook) | Saldo ↑ via API |
| 9 | POST webhook sem token + PIX pago | 200 fallback (log WARN) |
| 10 | `GET /health` webhook | `ok`, `service: webhook` |

### curl (token)

```powershell
Invoke-RestMethod -Method Post `
  -Uri "https://SEU-WEBHOOK.up.railway.app/webhook/asaas" `
  -Headers @{ "asaas-access-token" = "SEU_TOKEN" } `
  -ContentType "application/json" `
  -Body '{"event":"PAYMENT_RECEIVED","payment":{"id":"pay_test"}}'
```

---

## 11. Armadilhas documentadas (produção CPF Alerta)

| Sintoma | Causa | Correção |
|---------|-------|----------|
| **405** no webhook | URL aponta para Streamlit | `{PRODUTO}_SERVICE=webhook` |
| **401** | Token Railway ≠ Asaas | Alinhar + Salvar webhook + redeploy |
| **200** sem saldo | `DATABASE_URL` ausente no webhook | Env no serviço webhook |
| `sem_payment_id` | Body não parseado | `get_data(cache=True)` + form-urlencoded |
| Penalização v2 | Webhook versão **v2** no painel | Migrar para **v3** |
| Mesmo evento reenviado | Fila Asaas "at least once" | Idempotência; Remover penalização |
| Loop aparente | Evento antigo na fila | Limpar com suporte Asaas |
| Deploy app derruba webhook | Mesmo repo, redeploy conjunto | Aceitável; evitar deploy em horário de PIX |

---

## 12. Adaptação CPF vs CNPJ (checklist do agente)

- [ ] Prefixo `externalReference`: `cpfalerta:` vs `cnpjalerta:` em `montar_external_reference()`.
- [ ] Validação cadastro: CNPJ-only vs CPF+CNPJ conforme produto.
- [ ] Env: `CPFALERTA_*` → `CNPJALERTA_*` (`SESSION_SECRET`, `SERVICE`, etc.).
- [ ] Cookie name: `cpfalerta_auth` → `cnpjalerta_auth` (evitar colisão se mesmo domínio).
- [ ] Textos UI e descrição cobrança Asaas.
- [ ] Conta Asaas **separada** por produto (recomendado).
- [ ] URL webhook Railway **dedicada** por produto.

---

## 13. Ordem de implementação sugerida

1. Migrações SQL (`tenants`, `users`, `pagamentos`, `saldo_centavos`).
2. `db_manager`: cadastro, login, sessão, pagamentos.
3. `session_auth.py` + integração no `app.py`.
4. UI cadastro/login + gate logado.
5. `payments_asaas.py` + paywall mínimo (1–2 pacotes).
6. `webhook_asaas.py` + `railway_start.py`.
7. Segundo serviço Railway (webhook) + variáveis.
8. Config Asaas v3 + teste PIX real.
9. Documentar `.env.example`.

---

## 14. Referências externas

- [Webhooks Asaas](https://docs.asaas.com/docs/about-webhooks)
- [Idempotência webhooks](https://docs.asaas.com/docs/como-implementar-idempotencia-em-webhooks)
- [Penalização de filas](https://docs.asaas.com/docs/penaliza%C3%A7%C3%A3o-de-filas)
- [Reativar fila](https://docs.asaas.com/docs/como-reativar-fila-interrompida)

---

## 15. Prompt sugerido para colar no outro Agente Cursor

```text
Implemente conforme docs/INSTRUCAO_AGENTE_CADASTRO_LOGIN_WEBHOOK_ASAAS.md
e use cpfalerta (GitHub IA-Expertise/cpfalerta) como referência de código.

Produto alvo: [NOME] — cadastro com [CPF|CNPJ|ambos].
Prefixo externalReference: [prefixo]:
Env prefix: [PRODUTO]_

Entregáveis:
- migrations, db_manager (cadastro/login/pagamentos)
- session_auth.py, payments_asaas.py, webhook_asaas.py
- app.py (capa login/cadastro + recarga mínima)
- scripts/railway_start.py, .env.example
- README seção deploy (2 serviços Railway)

Não commitar .env. Não alterar repositório cpfalerta.
Testes: checklist §10.
```

---

*Documento gerado a partir do CPF Alerta em produção (jun/2026). Atualizar se o Asaas ou Railway mudarem comportamento.*
