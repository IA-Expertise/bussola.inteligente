"""
Webhook Asaas — serviço Flask (Railway BUSSOLA_SERVICE=webhook).
"""
from __future__ import annotations

import hmac
import json
import logging
import os
from urllib.parse import parse_qs, unquote_plus

from flask import Flask, jsonify, request

from db_manager import buscar_pagamento_por_asaas_id, liquidar_pagamento_por_asaas_id
from payments_asaas import consultar_pagamento_asaas, status_confirmado

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bussola.webhook")

app = Flask(__name__)

EVENTOS_PAGAMENTO = frozenset(
    {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED", "PAYMENT_RECEIVED_IN_CASH"}
)


def _webhook_token() -> str:
    return (os.getenv("ASAAS_WEBHOOK_TOKEN") or "").strip()


def _token_valido() -> bool:
    expected = _webhook_token()
    if not expected:
        return False
    received = (
        request.headers.get("asaas-access-token")
        or request.headers.get("Asaas-Access-Token")
        or ""
    ).strip()
    return hmac.compare_digest(received, expected)


def _parse_webhook_body() -> dict | None:
    raw = request.get_data(cache=True, as_text=True) or ""
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    ct = (request.content_type or "").lower()
    if "application/x-www-form-urlencoded" in ct or raw.strip().startswith("data="):
        form = parse_qs(raw, keep_blank_values=True)
        if "data" in form and form["data"]:
            try:
                return json.loads(unquote_plus(form["data"][0]))
            except json.JSONDecodeError:
                return None
    return None


def _extrair_payment(body: dict) -> tuple[dict | None, str]:
    payment = body.get("payment")
    if isinstance(payment, dict):
        return payment, (body.get("event") or "").strip()
    if body.get("id", "").startswith("pay_"):
        return body, (body.get("event") or "").strip()
    return None, (body.get("event") or "").strip()


def _processar_payment(payment: dict, evento: str) -> tuple[bool, str]:
    pay_id = (payment.get("id") or "").strip()
    if not pay_id or not pay_id.startswith("pay_"):
        return False, "payment.id ausente"

    status = (payment.get("status") or "").upper()
    evento_up = evento.upper()
    pago = status_confirmado(status) or evento_up in EVENTOS_PAGAMENTO

    if not pago and _token_valido():
        try:
            remote = consultar_pagamento_asaas(pay_id)
            status = (remote.get("status") or status).upper()
            pago = status_confirmado(status)
        except Exception as exc:
            log.warning("fallback API falhou pay=%s: %s", pay_id, exc)

    if not pago:
        return False, f"não pago ({status or evento_up})"

    local = buscar_pagamento_por_asaas_id(pay_id)
    if not local:
        log.warning("pagamento local não encontrado: %s", pay_id)
        return False, "pagamento local não encontrado"

    ok = liquidar_pagamento_por_asaas_id(pay_id, status_asaas=status or "RECEIVED")
    return ok, "liberado" if ok else "falha ao liquidar"


@app.get("/health")
def health():
    return jsonify(
        {
            "ok": True,
            "service": "webhook",
            "product": "bussola-inteligente",
        }
    )


@app.post("/webhook/asaas")
@app.post("/webhook")
def webhook_asaas():
    body = _parse_webhook_body()
    if not body:
        return jsonify({"ok": True, "ping": True}), 200

    payment, evento = _extrair_payment(body)
    if not payment or not (payment.get("id") or "").startswith("pay_"):
        return jsonify({"ok": True, "ping": True}), 200

    if not _token_valido():
        pay_id = payment.get("id", "")
        try:
            remote = consultar_pagamento_asaas(pay_id)
            if not status_confirmado(remote.get("status", "")):
                log.warning("webhook sem token válido e pagamento não confirmado: %s", pay_id)
                return jsonify({"ok": False, "error": "unauthorized"}), 401
            log.warning("webhook sem token — fallback API OK pay=%s", pay_id)
        except Exception:
            return jsonify({"ok": False, "error": "unauthorized"}), 401

    liberado, msg = _processar_payment(payment, evento)
    return jsonify(
        {
            "ok": True,
            "accepted": True,
            "liberado": liberado,
            "message": msg,
        }
    ), 200
