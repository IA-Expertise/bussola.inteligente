"""
Configuração pública do app monetizado (Fase 0).
Variáveis lidas via os.getenv — sem secrets aqui.
"""
from __future__ import annotations

import os

SAPPHIRE = "#0F52BA"

# URL do app Streamlit (CTA da LP). Atualize ao registrar domínio: https://app.seudominio.com.br
BUSSOLA_APP_URL = (os.getenv("BUSSOLA_APP_URL") or "https://bussolainteligente-production.up.railway.app/").rstrip("/") + "/"

# URL da landing page (opcional no app)
BUSSOLA_LP_URL = (os.getenv("BUSSOLA_LP_URL") or "https://www.bussolainteligente.com.br").rstrip("/")

RELATORIO_PRECO_REAIS = float(os.getenv("RELATORIO_PRECO_REAIS", "19.90"))

# Apenas testes internos: libera relatório completo sem pagamento (Fase 3 remove necessidade)
BUSSOLA_DEV_UNLOCK_RELATORIO = (os.getenv("BUSSOLA_DEV_UNLOCK_RELATORIO") or "").strip() in ("1", "true", "yes")

SCORE_LABELS = {
    "atendimento": "Atendimento",
    "visual": "Visual / marca",
    "seo_local": "Google / Local",
    "tecnologia": "Tecnologia",
    "autoridade": "Autoridade",
}
