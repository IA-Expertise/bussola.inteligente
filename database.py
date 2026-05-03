"""
database.py — Auto-initialise the public.leads table on startup.

Called once from app.py before any Streamlit rendering so the schema
is guaranteed to exist before the app tries to write leads.
"""

from __future__ import annotations

import os


_DDL = """
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


def init_db() -> None:
    """Create the public.leads table (and its indices) if they do not exist.

    Connects to the PostgreSQL instance identified by the DATABASE_URL
    environment variable.  If the variable is absent or the connection
    fails the function logs a warning and returns without raising, so the
    app can still start and fall back to CSV persistence.
    """
    dsn = (os.getenv("DATABASE_URL") or "").strip()
    if not dsn:
        print("[database] DATABASE_URL not set — skipping schema initialisation.")
        return

    try:
        import psycopg2
    except ImportError:
        print("[database] psycopg2 not available — skipping schema initialisation.")
        return

    conn = None
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cur:
            cur.execute(_DDL)
        conn.commit()
        print("[database] public.leads schema initialised (or already exists).")
    except Exception as exc:
        print(f"[database] Could not initialise schema: {exc}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
