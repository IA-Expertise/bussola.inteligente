"""
Persistência de usuários — cadastro e login (PostgreSQL).
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class UserSession:
    id: str
    email: str
    nome: str
    empresa: str
    cnpj: str


def _dsn() -> str:
    return (os.getenv("DATABASE_URL") or "").strip()


def _connect():
    import psycopg2

    dsn = _dsn()
    if not dsn:
        raise RuntimeError("DATABASE_URL não configurada.")
    return psycopg2.connect(dsn)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest_hex = stored.split("$", 2)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000)
    return secrets.compare_digest(check.hex(), digest_hex)


def _row_to_session(row: tuple[Any, ...]) -> UserSession:
    return UserSession(
        id=str(row[0]),
        email=row[1],
        nome=row[2],
        empresa=row[3] or "",
        cnpj=row[4] or "",
    )


def carregar_sessao_por_user_id(user_id: str) -> UserSession | None:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return None
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, nome, empresa, cnpj
                FROM public.users WHERE id = %s
                """,
                (str(uid),),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return _row_to_session(row) if row else None


def cadastrar_usuario(
    email: str,
    senha: str,
    nome: str,
    empresa: str = "",
    cnpj: str = "",
) -> tuple[UserSession | None, str | None]:
    email_norm = (email or "").strip().lower()
    nome_norm = (nome or "").strip()
    empresa_norm = (empresa or "").strip()
    cnpj_digits = re.sub(r"\D", "", cnpj or "")

    if not EMAIL_RE.match(email_norm):
        return None, "Informe um e-mail válido."
    if len(senha or "") < 6:
        return None, "A senha deve ter pelo menos 6 caracteres."
    if not nome_norm:
        return None, "Informe seu nome."

    pwd_hash = hash_password(senha)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.users (email, senha_hash, nome, empresa, cnpj)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, nome, empresa, cnpj
                """,
                (
                    email_norm,
                    pwd_hash,
                    nome_norm,
                    empresa_norm or None,
                    cnpj_digits or None,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    except Exception as exc:
        conn.rollback()
        try:
            import psycopg2

            if isinstance(exc, psycopg2.IntegrityError):
                return None, "Este e-mail já está cadastrado. Faça login."
        except ImportError:
            pass
        msg = str(exc).lower()
        if "unique" in msg and "email" in msg:
            return None, "Este e-mail já está cadastrado. Faça login."
        return None, "Não foi possível concluir o cadastro. Tente novamente."
    finally:
        conn.close()

    return _row_to_session(row), None


def verificar_login(email: str, senha: str) -> UserSession | None:
    email_norm = (email or "").strip().lower()
    if not email_norm or not senha:
        return None

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, nome, empresa, cnpj, senha_hash
                FROM public.users WHERE email = %s
                """,
                (email_norm,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row or not verify_password(senha, row[5]):
        return None
    return _row_to_session(row[:5])


def obter_asaas_customer_id(user_id: str) -> str | None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT asaas_customer_id FROM public.users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if row and row[0]:
        return str(row[0]).strip()
    return None


def atualizar_asaas_customer_id(user_id: str, customer_id: str) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET asaas_customer_id = %s WHERE id = %s",
                (customer_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def registrar_pagamento_pendente(
    *,
    user_id: str,
    asaas_payment_id: str,
    asaas_customer_id: str,
    valor_centavos: int,
    external_reference: str,
    invoice_url: str,
    pix_payload: str,
    status_asaas: str,
) -> str:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.pagamentos (
                    user_id, asaas_payment_id, asaas_customer_id, valor_centavos,
                    status_asaas, external_reference, invoice_url, pix_payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    asaas_payment_id,
                    asaas_customer_id,
                    valor_centavos,
                    status_asaas,
                    external_reference,
                    invoice_url or None,
                    pix_payload or None,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return str(row[0])


def buscar_pagamento_por_id(pagamento_id: str) -> dict | None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, asaas_payment_id, status_asaas, relatorio_liberado,
                       invoice_url, pix_payload, external_reference
                FROM public.pagamentos WHERE id = %s
                """,
                (pagamento_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "user_id": str(row[1]),
        "asaas_payment_id": row[2],
        "status_asaas": row[3],
        "relatorio_liberado": row[4],
        "invoice_url": row[5] or "",
        "pix_payload": row[6] or "",
        "external_reference": row[7],
    }


def buscar_pagamento_por_asaas_id(asaas_payment_id: str) -> dict | None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, asaas_payment_id, status_asaas, relatorio_liberado,
                       external_reference
                FROM public.pagamentos WHERE asaas_payment_id = %s
                """,
                (asaas_payment_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "user_id": str(row[1]),
        "asaas_payment_id": row[2],
        "status_asaas": row[3],
        "relatorio_liberado": row[4],
        "external_reference": row[5],
    }


def liquidar_pagamento_por_asaas_id(
    asaas_payment_id: str,
    *,
    status_asaas: str = "RECEIVED",
) -> bool:
    """Marca relatório liberado. Idempotente. Retorna True se liberado (novo ou já estava)."""
    conn = _connect()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, relatorio_liberado FROM public.pagamentos
                WHERE asaas_payment_id = %s FOR UPDATE
                """,
                (asaas_payment_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False
            if row[1]:
                conn.commit()
                return True
            cur.execute(
                """
                UPDATE public.pagamentos
                SET relatorio_liberado = true,
                    status_asaas = %s,
                    paid_at = NOW()
                WHERE asaas_payment_id = %s
                """,
                (status_asaas, asaas_payment_id),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

