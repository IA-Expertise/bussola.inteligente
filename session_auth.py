"""
Sessão persistente via cookie assinado (HMAC) — Bússola Inteligente.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone

import streamlit as st

from db_manager import UserSession, carregar_sessao_por_user_id

COOKIE_NAME = "bussola_auth"
TTL_DAYS = 30


def _secret() -> bytes:
    raw = (os.getenv("BUSSOLA_AUTH_SECRET") or "").strip()
    if not raw:
        raw = "dev-insecure-change-me"
    return raw.encode("utf-8")


def issue_session_token(user_id: str) -> str:
    exp = int((datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp())
    payload = f"{user_id}|{exp}".encode("utf-8")
    sig = hmac.new(_secret(), payload, hashlib.sha256).digest()
    blob = base64.urlsafe_b64encode(payload + b"." + sig).decode("ascii")
    return blob


def verify_session_token(token: str) -> str | None:
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        payload, sig = raw.rsplit(b".", 1)
        expected = hmac.new(_secret(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        text = payload.decode("utf-8")
        user_id, exp_str = text.split("|", 1)
        if int(exp_str) < int(time.time()):
            return None
        return user_id
    except Exception:
        return None


def get_cookie_manager():
    """Uma instância por sessão — não usar @st.cache_resource (CookieManager é widget)."""
    if "_cookie_manager" not in st.session_state:
        import extra_streamlit_components as stx

        st.session_state._cookie_manager = stx.CookieManager(key="bussola_cookie_manager")
    return st.session_state._cookie_manager


def persist_login_cookie(user: UserSession) -> None:
    token = issue_session_token(user.id)
    expires = datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)
    get_cookie_manager().set(
        COOKIE_NAME,
        token,
        expires_at=expires,
        key=f"set_{COOKIE_NAME}_{user.id[:8]}",
    )


def clear_login_cookie() -> None:
    get_cookie_manager().delete(COOKIE_NAME, key="del_bussola_auth")


def restaurar_sessao_do_cookie() -> bool:
    """Tenta restaurar st.session_state.user a partir do cookie. Retorna True se restaurou."""
    if st.session_state.get("user"):
        return True

    if st.session_state.get("_auth_cookie_done"):
        return False

    manager = get_cookie_manager()
    token = manager.get(COOKIE_NAME)

    if token is None and not st.session_state.get("_auth_cookie_waited"):
        st.session_state._auth_cookie_waited = True
        return False

    st.session_state._auth_cookie_done = True

    if not token:
        return False

    user_id = verify_session_token(token)
    if not user_id:
        clear_login_cookie()
        return False

    sess = carregar_sessao_por_user_id(user_id)
    if not sess:
        clear_login_cookie()
        return False

    st.session_state.user = sess
    return True


def login_user(user: UserSession) -> None:
    st.session_state.user = user
    persist_login_cookie(user)


def logout_user() -> None:
    st.session_state.user = None
    st.session_state._auth_cookie_done = False
    st.session_state._auth_cookie_waited = False
    clear_login_cookie()
