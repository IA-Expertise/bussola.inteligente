"""
database.py — Inicialização do schema PostgreSQL para a Bússola Inteligente.
Chamado em app.py logo após load_dotenv() para garantir que public.leads
exista antes de qualquer operação de banco de dados.
"""
from __future__ import annotations

import os
import sys

_SQL = """
CREATE TABLE IF NOT EXISTS public.leads (
  id BIGSERIAL PRIMARY KEY,
  timestamp_iso TEXT NOT NULL,
  nome TEXT,
  empresa TEXT,
  site TEXT,
  segmento TEXT,
  gmb_maps TEXT,
  termo_google TEXT,
  instagram TEXT,
  facebook TEXT,
  linkedin TEXT,
  youtube TEXT,
  tiktok TEXT,
  whatsapp TEXT,
  email_cliente TEXT,
  optin_autorizado TEXT,
  dor_sebrae TEXT,
  atendimento INTEGER,
  visual INTEGER,
  seo_local INTEGER,
  tecnologia INTEGER,
  autoridade INTEGER,
  introducao_analitica TEXT,
  caminhos_recomendados TEXT,
  raio_x_realista TEXT,
  dica_gestor TEXT,
  oportunidades_iaexpertise TEXT,
  diagnostico_json JSONB
);
CREATE INDEX IF NOT EXISTS idx_leads_timestamp_iso ON public.leads (timestamp_iso DESC);
CREATE INDEX IF NOT EXISTS idx_leads_empresa ON public.leads (empresa);
COMMENT ON TABLE public.leads IS 'Leads e diagnósticos exportados da Bússola Inteligente (IAExpertise).';
"""

_initialized = False


def init_db() -> None:
    """Cria a tabela public.leads (e índices) se ainda não existirem.

    Lê DATABASE_URL do ambiente. Retorna silenciosamente se a variável não
    estiver definida. Erros de conexão ou SQL são registrados em stderr mas
    não interrompem a inicialização do app.
    """
    global _initialized
    if _initialized:
        return

    dsn = (os.getenv("DATABASE_URL") or "").strip()
    if not dsn:
        return

    try:
        import psycopg2
    except ImportError:
        print("database.init_db: psycopg2 não instalado — pulando init.", file=sys.stderr)
        return

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        print(f"database.init_db: falha ao conectar ao PostgreSQL: {exc}", file=sys.stderr)
        return

    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            # psycopg2: uma instrução por execute (múltiplos ; no mesmo execute falham)
            for stmt in (s.strip() for s in _SQL.split(";")):
                if stmt:
                    cur.execute(stmt)
        print("database.init_db: schema public.leads verificado/criado com sucesso.")
        _initialized = True
    except Exception as exc:
        print(f"database.init_db: falha ao executar SQL de inicialização: {exc}", file=sys.stderr)
    finally:
        conn.close()
