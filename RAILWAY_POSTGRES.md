# PostgreSQL no Railway — Bússola Inteligente

Guia curto para ativar o banco **no próprio Railway** (sem Supabase). O código já usa `DATABASE_URL` + tabela `public.leads`.

## 1. Criar o Postgres no Railway

1. Abra o **projeto** no Railway.
2. Clique em **+ New** → **Database** → **PostgreSQL** (ou **Add PostgreSQL**).
3. Aguarde o provisionamento. Abra o **card do Postgres**.
4. Vá em **Variables** (ou **Connect**) e copie a **`DATABASE_URL`** (ou `POSTGRES_URL` / `DATABASE_PRIVATE_URL`, conforme o painel mostrar — use a que o Railway indica para apps no mesmo projeto).

## 2. Criar a tabela (automático no deploy)

Com o **`Procfile`** atual, cada deploy roda **`python scripts/ensure_db.py`** antes do Streamlit. Esse script lê **`sql/init_leads.sql`** e cria **`public.leads`** se ainda não existir — **não é obrigatório** colar SQL manualmente no painel do Railway.

**Opcional (manual):** ainda pode executar `sql/init_leads.sql` no Query do Postgres se preferir validar à mão.

## 3. Ligar o app Streamlit

1. Abra o serviço **bussola.inteligente** (ou o nome do seu app).
2. **Variables** → crie/edite **`DATABASE_URL`** com o valor copiado do Postgres.
3. **Deploy** / **Redeploy** do app.

## 4. Teste

1. Abra a URL pública do app.
2. Conclua um diagnóstico até o relatório.
3. Confirme no Postgres (aba Query):  
   `SELECT id, timestamp_iso, empresa FROM public.leads ORDER BY id DESC LIMIT 5;`

## 5. Fallback CSV

Se `DATABASE_URL` estiver ausente ou o insert falhar, o app grava em **`leads.csv`** (comportamento já existente no código).

## Notas

- **Dados de teste:** pode apagar linhas com `TRUNCATE public.leads;` quando quiser zerar.
- **Backup:** configure rotina conforme seu plano Railway (export periódico ou snapshots do provedor).
