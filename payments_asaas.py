"""
Cliente Asaas API v3 — cobrança Pix por relatório (Bússola Inteligente).
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

import requests

from db_manager import (
    UserSession,
    atualizar_asaas_customer_id,
    buscar_pagamento_por_id,
    liquidar_pagamento_por_asaas_id,
    obter_asaas_customer_id,
    registrar_pagamento_pendente,
)
from config import RELATORIO_PRECO_REAIS

STATUS_PAGO = frozenset(
    {"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH", "DUNNING_RECEIVED"}
)


@dataclass
class CobrancaPix:
    pagamento_id: str
    asaas_payment_id: str
    invoice_url: str
    pix_payload: str
    pix_encoded_image: str
    status_asaas: str
    valor_reais: float


def _sandbox() -> bool:
    return (os.getenv("ASAAS_SANDBOX") or "0").strip() in ("1", "true", "yes")


def _api_base() -> str:
    if _sandbox():
        return "https://api-sandbox.asaas.com/v3"
    return "https://api.asaas.com/v3"


def _api_key() -> str:
    key = (os.getenv("ASAAS_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("ASAAS_API_KEY não configurada.")
    return key


def _headers() -> dict[str, str]:
    return {
        "access_token": _api_key(),
        "Content-Type": "application/json",
        "User-Agent": "BussolaInteligente/1.0",
    }


def _request(method: str, path: str, *, json_body: dict | None = None) -> dict:
    url = f"{_api_base()}{path}"
    resp = requests.request(method, url, headers=_headers(), json=json_body, timeout=45)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Asaas {resp.status_code}: {detail}")
    if not resp.content:
        return {}
    return resp.json()


def status_confirmado(status: str) -> bool:
    return (status or "").upper() in STATUS_PAGO


def garantir_customer(user: UserSession) -> str:
    existing = obter_asaas_customer_id(user.id)
    if existing:
        return existing

    body: dict = {"name": user.nome or user.email, "email": user.email}
    if user.cnpj and len(user.cnpj) >= 11:
        body["cpfCnpj"] = user.cnpj

    data = _request("POST", "/customers", json_body=body)
    customer_id = (data.get("id") or "").strip()
    if not customer_id:
        raise RuntimeError("Asaas não retornou customer id.")
    atualizar_asaas_customer_id(user.id, customer_id)
    return customer_id


def _external_reference(user_id: str) -> str:
    return f"bussola:report:{user_id}:{uuid.uuid4().hex[:12]}"


def criar_cobranca_relatorio(user: UserSession) -> CobrancaPix:
    customer_id = garantir_customer(user)
    ext_ref = _external_reference(user.id)
    due = (date.today() + timedelta(days=3)).isoformat()
    billing = (os.getenv("ASAAS_BILLING_TYPE") or "PIX").strip().upper()

    pay_body = {
        "customer": customer_id,
        "billingType": billing,
        "value": round(RELATORIO_PRECO_REAIS, 2),
        "dueDate": due,
        "description": "Bússola Inteligente — Relatório completo de visibilidade digital",
        "externalReference": ext_ref,
    }
    payment = _request("POST", "/payments", json_body=pay_body)
    pay_id = (payment.get("id") or "").strip()
    if not pay_id:
        raise RuntimeError("Asaas não retornou payment id.")

    invoice_url = (payment.get("invoiceUrl") or "").strip()
    status = (payment.get("status") or "PENDING").strip()

    pix_payload = ""
    pix_image = ""
    if billing == "PIX":
        try:
            pix = _request("GET", f"/payments/{pay_id}/pixQrCode")
            pix_payload = (pix.get("payload") or "").strip()
            pix_image = (pix.get("encodedImage") or "").strip()
        except Exception:
            pass

    valor_centavos = int(round(RELATORIO_PRECO_REAIS * 100))
    local_id = registrar_pagamento_pendente(
        user_id=user.id,
        asaas_payment_id=pay_id,
        asaas_customer_id=customer_id,
        valor_centavos=valor_centavos,
        external_reference=ext_ref,
        invoice_url=invoice_url,
        pix_payload=pix_payload,
        status_asaas=status,
    )

    return CobrancaPix(
        pagamento_id=local_id,
        asaas_payment_id=pay_id,
        invoice_url=invoice_url,
        pix_payload=pix_payload,
        pix_encoded_image=pix_image,
        status_asaas=status,
        valor_reais=RELATORIO_PRECO_REAIS,
    )


def consultar_pagamento_asaas(asaas_payment_id: str) -> dict:
    return _request("GET", f"/payments/{asaas_payment_id}")


def obter_pix_qrcode(asaas_payment_id: str) -> tuple[str, str]:
    """Retorna (payload, encodedImage base64)."""
    pix = _request("GET", f"/payments/{asaas_payment_id}/pixQrCode")
    return (
        (pix.get("payload") or "").strip(),
        (pix.get("encodedImage") or "").strip(),
    )


def sincronizar_pagamento_local(pagamento_id: str) -> tuple[bool, str | None]:
    """Consulta Asaas e liquida localmente se pago. Retorna (liberado, erro)."""
    row = buscar_pagamento_por_id(pagamento_id)
    if not row:
        return False, "Pagamento não encontrado."
    if row["relatorio_liberado"]:
        return True, None

    try:
        remote = consultar_pagamento_asaas(row["asaas_payment_id"])
    except Exception as exc:
        return False, str(exc)

    status = (remote.get("status") or "").upper()
    if status_confirmado(status):
        liquidar_pagamento_por_asaas_id(
            row["asaas_payment_id"],
            status_asaas=status,
        )
        return True, None
    return False, f"Pagamento ainda não confirmado (status: {status or 'PENDING'})."
