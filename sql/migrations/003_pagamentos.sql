-- Fase 3 — cobranças Asaas (1 Pix = 1 relatório)
CREATE TABLE IF NOT EXISTS public.pagamentos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  asaas_payment_id VARCHAR(64) NOT NULL UNIQUE,
  asaas_customer_id VARCHAR(64),
  valor_centavos INTEGER NOT NULL DEFAULT 1990 CHECK (valor_centavos > 0),
  status_asaas VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  relatorio_liberado BOOLEAN NOT NULL DEFAULT false,
  product_type VARCHAR(32) NOT NULL DEFAULT 'relatorio_completo',
  external_reference VARCHAR(128) NOT NULL UNIQUE,
  invoice_url TEXT,
  pix_payload TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  paid_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pagamentos_user ON public.pagamentos (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pagamentos_status ON public.pagamentos (status_asaas);

COMMENT ON TABLE public.pagamentos IS 'Cobranças Asaas — liberação do relatório completo Bússola Inteligente.';
