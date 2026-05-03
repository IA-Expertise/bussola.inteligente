"""
database.py — Auto-initializes the public.leads schema on startup.
Called from app.py immediately after load_dotenv() so the table exists
before any database operations are attempted.
"""
from __future__ import annotations

import os
import sys


def init_db() -> None:
    """Create public.leads (and its indices) if they don't exist yet.

    Reads DATABASE_URL from the environment.  Returns silently when the
    variable is absent.  All errors are logged to stderr so the app can
    continue running (falling back to CSV) rather than crashing.
    """
    dsn = (os.getenv("DATABASE_URL") or "").strip()
    if not dsn:
        return

    try:
        import psycopg2
    except ImportError:
        print("database.init_db: psycopg2 não instalado — pulando init.", file=sys.stderr)
        return

    sql = """
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

    try:
        conn = psycopg2.connect(dsn)
    except Exception as exc:
        print(f"database.init_db: falha ao conectar ao PostgreSQL: {exc}", file=sys.stderr)
        return

    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        print("database.init_db: tabela public.leads verificada/criada com sucesso.", file=sys.stderr)
    except Exception as exc:
        print(f"database.init_db: falha ao executar SQL de inicialização: {exc}", file=sys.stderr)
    finally:
        conn.close()
