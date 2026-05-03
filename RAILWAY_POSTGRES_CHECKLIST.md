# Checklist — PostgreSQL no Railway + Bússola Inteligente

Use este roteiro para verificar se a implantação está completa e correta.  
**Não cole URLs com senha em chats públicos.**

---

## A. Serviço PostgreSQL

- [ ] Existe um serviço **PostgreSQL** no mesmo projeto Railway (ou conectado ao app).
- [ ] O serviço está com status **Deployed / Active** (sem falha permanente).
- [ ] Consegue abrir o painel do Postgres e ver **Variables** ou **Connect**.

---

## B. Schema e tabela

- [ ] Foi executado o SQL completo do arquivo **`sql/init_leads.sql`** (repositório) no editor SQL do Railway Postgres.
- [ ] A tabela **`public.leads`** existe (consulta de teste abaixo sem erro).

**Consulta de verificação:**

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'leads';
```

Esperado: **1 linha** com `public` / `leads`.

---

## C. Serviço do app (Streamlit)

- [ ] Existe o serviço da aplicação (ex.: **bussola.inteligente**).
- [ ] Variável de ambiente **`DATABASE_URL`** está definida **neste serviço** (não só no Postgres).
- [ ] O valor de `DATABASE_URL` aponta para o **mesmo** banco do serviço Postgres (host, porta, database, usuário coerentes).
- [ ] Após alterar variáveis, foi feito **Redeploy** / deploy concluído com sucesso.

---

## D. Rede e URL pública

- [ ] O app tem **domínio público** gerado (não “Unexposed service”).
- [ ] Abrir a URL no navegador carrega a aplicação Streamlit.

---

## E. Teste funcional (ponta a ponta)

- [ ] Percorrer fluxo: landing → formulário → relatório até o fim.
- [ ] Na tela do relatório aparece mensagem de sucesso de persistência (**PostgreSQL**), **ou** mensagem explícita de **fallback CSV** (se for o caso, investigar conexão).
- [ ] No Postgres, após um teste, existe pelo menos **1 linha** em `public.leads`:

```sql
SELECT id, timestamp_iso, empresa
FROM public.leads
ORDER BY id DESC
LIMIT 5;
```

---

## F. Outras variáveis críticas (app)

- [ ] **`OPENAI_API_KEY`** definida (diagnóstico funciona).
- [ ] Se usar e-mail interno: **`AGENTMAIL_API_KEY`**, **`AGENTMAIL_INBOX`**, **`AGENTMAIL_NOTIFY_TO`** definidas (ou aceitar que o e-mail não será enviado).

---

## G. Repositório / deploy

- [ ] O código em produção inclui **`Procfile`**, **`requirements.txt`** com `psycopg2-binary`, e lógica de insert em **`public.leads`** (branch que o Railway faz deploy).

---

## Resultado

| Situação | Ação |
|----------|------|
| Tudo OK até E + linha em `leads` | Implantação Postgres **concluída**. |
| App funciona mas só CSV / erro DB | Revisar `DATABASE_URL`, redeploy, logs do app e permissões do banco. |
| Tabela não existe | Rodar de novo `sql/init_leads.sql`. |

---

*Arquivo alinhado ao guia `RAILWAY_POSTGRES.md`.*
