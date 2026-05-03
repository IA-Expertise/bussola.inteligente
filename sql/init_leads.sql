-- Bússola Inteligente — tabela public.leads (PostgreSQL genérico)
-- Use no Railway Postgres: Query / psql / cliente SQL, uma vez por banco.

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
