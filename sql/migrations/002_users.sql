-- Fase 2 — usuários (cadastro / login)
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  senha_hash VARCHAR(255) NOT NULL,
  nome VARCHAR(255) NOT NULL,
  empresa VARCHAR(255),
  cnpj VARCHAR(14),
  asaas_customer_id VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);

COMMENT ON TABLE public.users IS 'Contas de acesso à Bússola Inteligente (relatórios e histórico).';
