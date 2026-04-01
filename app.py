"""
MVP — Diagnóstico de Maturidade Digital (Streamlit + OpenAI GPT-4o-mini)
IAExpertise — leads em leads.csv
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# -----------------------------------------------------------------------------
# Configuração — ajuste o WhatsApp do Arquiteto (DDI + DDD + número, só dígitos)
# -----------------------------------------------------------------------------
WHATSAPP_ARQUITETO = os.getenv("WHATSAPP_ARQUITETO", "5511999999999")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LEADS_CSV = Path(__file__).resolve().parent / "leads.csv"

# AgentMail — remetente (inbox) e destino da notificação (console.agentmail.to)
AGENTMAIL_INBOX = os.getenv("AGENTMAIL_INBOX", "bussola.inteligente@agentmail.to")
AGENTMAIL_NOTIFY_TO = os.getenv("AGENTMAIL_NOTIFY_TO", "contato@iaexpertise.com.br")
AGENTMAIL_INBOX_CLIENT_ID = os.getenv(
    "AGENTMAIL_INBOX_CLIENT_ID", "iaexpertise-bussola-diagnostico"
)

SYSTEM_PROMPT = """Você é um consultor sênior de presença digital para micro e pequenas empresas brasileiras.
Seja crítico, honesto e útil — sem floreio vazio. Use português do Brasil.

TAREFA:
Com base nos dados informados pelo usuário (empresa, segmento, site, redes, dor principal), produza um diagnóstico estruturado.

NOTAS (0 a 10, inteiros) para cada dimensão:
1) presenca_visual — identidade, consistência visual, percepção de profissionalismo no que for dedutível.
2) agilidade_resposta — capacidade aparente de responder rápido (canais informados, presença em WhatsApp, etc.).
3) seo_local — ser encontrado no Google/local (site, Google Meu Negócio, menções, sinais locais).
4) autoridade — conteúdo, prova social, reputação percebida no que for inferível.
5) uso_tecnologia — automação, chatbots, IA, integrações, modernização aparente.

O relatório tem DUAS partes obrigatórias:
A) banho_realidade — fatos duros e diretos sobre lacunas. Inclua pelo menos UMA referência a dado de mercado realista no tom: ex. "Segundo o Sebrae, demorar a responder no WhatsApp pode reduzir drasticamente as chances de conversão" (não invente números precisos se não tiver certeza — use formulações como "estudos indicam" quando necessário).
B) plano_modernizacao — plano acionável mencionando explicitamente a solução Lia (atendimento inteligente no WhatsApp) e produção de vídeos e posts com apoio de IA (IAExpertise).

Para cada dimensão, escreva um parágrafo curto em detalhes[NOME_DA_CHAVE] explicando a nota.

RESPONDA APENAS com um JSON válido (sem markdown, sem texto fora do JSON) neste formato exato:
{
  "scores": {
    "presenca_visual": <int 0-10>,
    "agilidade_resposta": <int 0-10>,
    "seo_local": <int 0-10>,
    "autoridade": <int 0-10>,
    "uso_tecnologia": <int 0-10>
  },
  "banho_realidade": "<texto com seções ou parágrafos claros>",
  "plano_modernizacao": "<texto com passos e menção Lia + vídeos/posts por IA>",
  "detalhes": {
    "presenca_visual": "<texto>",
    "agilidade_resposta": "<texto>",
    "seo_local": "<texto>",
    "autoridade": "<texto>",
    "uso_tecnologia": "<texto>"
  }
}
"""


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');
        html, body, [class*="css"] { font-family: 'DM Sans', system-ui, sans-serif; }
        .stApp {
            background: linear-gradient(165deg, #0b1220 0%, #0f172a 45%, #111827 100%);
        }
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdown"] h1) {
            padding-bottom: 0.25rem;
        }
        h1 { letter-spacing: -0.03em; font-weight: 700 !important; color: #f8fafc !important; }
        h2, h3 { color: #e2e8f0 !important; font-weight: 600 !important; }
        .hero-sub {
            color: #94a3b8; font-size: 1.05rem; margin-top: 0.35rem; margin-bottom: 1.25rem;
        }
        .card {
            background: rgba(30, 41, 59, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1rem;
            backdrop-filter: blur(8px);
        }
        .tagline { color: #22d3ee; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; }
        div[data-testid="stExpander"] details {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(71, 85, 105, 0.5);
            border-radius: 10px;
        }
        .stButton > button {
            background: linear-gradient(135deg, #0891b2 0%, #06b6d4 50%, #22d3ee 100%);
            color: #0f172a !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 0.65rem 1.25rem;
            border-radius: 10px;
        }
        .stButton > button:hover { box-shadow: 0 0 24px rgba(34, 211, 238, 0.35); }
        label { color: #cbd5e1 !important; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def call_openai_diagnostico(payload: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. Defina a variável de ambiente ou o secret no Replit."
        )
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.45,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Dados para diagnóstico (JSON ou texto):\n{payload}",
            },
        ],
    )
    raw = completion.choices[0].message.content or "{}"
    return json.loads(raw)


def clamp_score(n: int) -> int:
    return max(0, min(10, int(n)))


def normalize_result(data: dict) -> dict:
    scores = data.get("scores") or {}
    keys = [
        "presenca_visual",
        "agilidade_resposta",
        "seo_local",
        "autoridade",
        "uso_tecnologia",
    ]
    out_scores = {}
    for k in keys:
        v = scores.get(k, 0)
        try:
            out_scores[k] = clamp_score(int(v))
        except (TypeError, ValueError):
            out_scores[k] = 0
    detalhes = data.get("detalhes") or {}
    out_det = {k: str(detalhes.get(k, "")).strip() for k in keys}
    return {
        "scores": out_scores,
        "banho_realidade": str(data.get("banho_realidade", "")).strip(),
        "plano_modernizacao": str(data.get("plano_modernizacao", "")).strip(),
        "detalhes": out_det,
    }


def build_radar_figure(scores: dict) -> go.Figure:
    labels_pt = {
        "presenca_visual": "Presença Visual",
        "agilidade_resposta": "Agilidade de Resposta",
        "seo_local": "SEO Local",
        "autoridade": "Autoridade",
        "uso_tecnologia": "Uso de Tecnologia",
    }
    order = [
        "presenca_visual",
        "agilidade_resposta",
        "seo_local",
        "autoridade",
        "uso_tecnologia",
    ]
    theta = [labels_pt[k] for k in order] + [labels_pt[order[0]]]
    r = [scores[k] for k in order] + [scores[order[0]]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r,
            theta=theta,
            fill="toself",
            fillcolor="rgba(34, 211, 238, 0.28)",
            line=dict(color="#22d3ee", width=2),
            name="Maturidade",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickvals=[0, 2, 4, 6, 8, 10],
                tickfont=dict(color="#94a3b8", size=11),
                gridcolor="rgba(148, 163, 184, 0.25)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#e2e8f0", size=12),
                linecolor="rgba(148, 163, 184, 0.35)",
            ),
            bgcolor="rgba(15, 23, 42, 0.5)",
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=48, b=32, l=48, r=48),
        title=dict(
            text="Mapa de Maturidade Digital (0–10)",
            font=dict(size=18, color="#f1f5f9"),
            x=0.5,
            xanchor="center",
        ),
        height=420,
    )
    return fig


def build_notification_bodies(
    lead: dict,
    scores: dict,
    result: dict,
    ts: str,
) -> tuple[str, str]:
    """Retorna (texto plano, HTML) para o e-mail de notificação."""
    lines = [
        "Novo diagnóstico — Bússola Inteligente / IAExpertise",
        "",
        f"Data/hora: {ts}",
        f"Nome: {lead.get('nome', '')}",
        f"Empresa: {lead.get('empresa', '')}",
        f"Site: {lead.get('site', '')}",
        f"Segmento: {lead.get('segmento', '')}",
        f"Instagram: {lead.get('instagram', '')}",
        f"WhatsApp (lead): {lead.get('whatsapp', '')}",
        f"Maior dor: {lead.get('dor', '')}",
        "",
        "Notas (0–10):",
        f"  Presença visual: {scores.get('presenca_visual', '')}",
        f"  Agilidade de resposta: {scores.get('agilidade_resposta', '')}",
        f"  SEO local: {scores.get('seo_local', '')}",
        f"  Autoridade: {scores.get('autoridade', '')}",
        f"  Uso de tecnologia: {scores.get('uso_tecnologia', '')}",
        "",
        "--- O banho de realidade ---",
        result.get("banho_realidade", ""),
        "",
        "--- Plano de modernização ---",
        result.get("plano_modernizacao", ""),
    ]
    text_body = "\n".join(lines)

    esc = html.escape
    rows_html = "".join(
        f"<tr><td style='padding:6px 12px;border:1px solid #334155;color:#94a3b8'>{esc(k)}</td>"
        f"<td style='padding:6px 12px;border:1px solid #334155;color:#f1f5f9'>{esc(str(v))}</td></tr>"
        for k, v in [
            ("Data/hora", ts),
            ("Nome", lead.get("nome", "")),
            ("Empresa", lead.get("empresa", "")),
            ("Site", lead.get("site", "")),
            ("Segmento", lead.get("segmento", "")),
            ("Instagram", lead.get("instagram", "")),
            ("WhatsApp", lead.get("whatsapp", "")),
            ("Maior dor", lead.get("dor", "")),
        ]
    )
    scores_rows = "".join(
        f"<tr><td style='padding:6px 12px;border:1px solid #334155'>{esc(l)}</td>"
        f"<td style='padding:6px 12px;border:1px solid #334155'><strong>{scores.get(k, '')}</strong>/10</td></tr>"
        for k, l in [
            ("presenca_visual", "Presença visual"),
            ("agilidade_resposta", "Agilidade de resposta"),
            ("seo_local", "SEO local"),
            ("autoridade", "Autoridade"),
            ("uso_tecnologia", "Uso de tecnologia"),
        ]
    )
    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
  <h1 style="color:#22d3ee;font-size:1.25rem;">Novo diagnóstico — Bússola Inteligente</h1>
  <table style="border-collapse:collapse;margin:16px 0;width:100%;max-width:560px;">{rows_html}</table>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Notas</h2>
  <table style="border-collapse:collapse;margin-bottom:24px;width:100%;max-width:560px;">{scores_rows}</table>
  <h2 style="color:#94a3b8;font-size:0.95rem;">O banho de realidade</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:20px;
    white-space:pre-wrap;">{esc(result.get("banho_realidade", ""))}</div>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Plano de modernização</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;white-space:pre-wrap;">
    {esc(result.get("plano_modernizacao", ""))}</div>
</body></html>"""
    return text_body, html_body


def send_agentmail_notification(
    lead: dict,
    scores: dict,
    result: dict,
    ts: str,
) -> tuple[bool, str | None]:
    """
    Envia cópia do diagnóstico a partir de AGENTMAIL_INBOX (ex.: bussola.inteligente@agentmail.to)
    para AGENTMAIL_NOTIFY_TO via AgentMail.

    Usa o inbox já existente (ID = endereço completo). Não chama inboxes.create por envio,
    para evitar LimitExceededError no plano gratuito.
    Retorna (ok, mensagem_erro).
    """
    api_key = os.getenv("AGENTMAIL_API_KEY")
    if not api_key:
        return False, "AGENTMAIL_API_KEY ausente"

    try:
        from agentmail import AgentMail
    except ImportError:
        return False, "Pacote 'agentmail' não instalado (pip install agentmail)"

    text_body, html_body = build_notification_bodies(lead, scores, result, ts)
    empresa = (lead.get("empresa") or "Lead").strip()
    subject = f"[Bússola] Novo diagnóstico — {empresa}"
    inbox_id = (AGENTMAIL_INBOX or "").strip()
    if not inbox_id or "@" not in inbox_id:
        return False, "AGENTMAIL_INBOX inválido (ex.: bussola.inteligente@agentmail.to)"

    try:
        client = AgentMail(api_key=api_key)
        client.inboxes.messages.send(
            inbox_id,
            to=AGENTMAIL_NOTIFY_TO,
            subject=subject,
            text=text_body,
            html=html_body,
        )
    except Exception as e:
        return False, str(e)
    return True, None


def save_lead_csv(row: dict) -> None:
    fieldnames = [
        "timestamp_iso",
        "nome",
        "empresa",
        "site",
        "segmento",
        "instagram",
        "whatsapp",
        "dor",
        "presenca_visual",
        "agilidade_resposta",
        "seo_local",
        "autoridade",
        "uso_tecnologia",
        "banho_realidade",
        "plano_modernizacao",
        "diagnostico_json",
    ]
    file_exists = LEADS_CSV.is_file()
    with LEADS_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    st.set_page_config(
        page_title="Diagnóstico de Maturidade Digital | IAExpertise",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    st.markdown(
        '<p class="tagline">IAExpertise · Bússola Inteligente</p>',
        unsafe_allow_html=True,
    )
    st.markdown("# Diagnóstico de Maturidade Digital")
    st.markdown(
        '<p class="hero-sub">Análise honesta da sua presença digital — com plano prático e soluções com IA '
        "(Lia, conteúdo e vídeos).</p>",
        unsafe_allow_html=True,
    )

    with st.form("lead_form"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome do contato", placeholder="Maria Silva")
            empresa = st.text_input("Empresa", placeholder="Padaria do Centro Ltda")
            site = st.text_input("Site (URL ou deixe em branco)", placeholder="https://...")
        with c2:
            segmento = st.text_input("Segmento", placeholder="Alimentação, serviços, varejo...")
            instagram = st.text_input("Instagram (@)", placeholder="@suaempresa")
            whatsapp_in = st.text_input("WhatsApp com DDD", placeholder="(11) 99999-9999")

        dor = st.radio(
            "Qual sua maior dor hoje?",
            options=[
                "Atendimento",
                "Criar Conteúdo",
                "Ser encontrado no Google",
            ],
            horizontal=True,
        )
        submitted = st.form_submit_button("Gerar diagnóstico com IA")

    if not submitted:
        st.markdown(
            '<div class="card">Preencha os dados e clique em <strong>Gerar diagnóstico com IA</strong>. '
            "O relatório inclui gráfico de radar, análise crítica e próximos passos com a IAExpertise.</div>",
            unsafe_allow_html=True,
        )
        return

    if not empresa.strip():
        st.error("Informe pelo menos o nome da empresa.")
        return

    user_payload = {
        "nome": nome.strip(),
        "empresa": empresa.strip(),
        "site": site.strip(),
        "segmento": segmento.strip(),
        "instagram": instagram.strip(),
        "whatsapp": whatsapp_in.strip(),
        "dor_principal": dor,
    }

    with st.spinner("Analisando presença digital e montando seu relatório..."):
        try:
            raw = call_openai_diagnostico(json.dumps(user_payload, ensure_ascii=False))
            result = normalize_result(raw)
        except json.JSONDecodeError as e:
            st.error(f"Resposta da IA em formato inválido: {e}")
            return
        except Exception as e:
            st.error(str(e))
            return

    scores = result["scores"]
    fig = build_radar_figure(scores)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("A) O banho de realidade")
    _br = html.escape(result["banho_realidade"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card">{_br}</div>', unsafe_allow_html=True)

    st.subheader("B) Plano de modernização (IAExpertise)")
    _br2 = html.escape(result["plano_modernizacao"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card">{_br2}</div>', unsafe_allow_html=True)

    st.subheader("Detalhes por dimensão")
    label_exp = {
        "presenca_visual": "Presença Visual",
        "agilidade_resposta": "Agilidade de Resposta",
        "seo_local": "SEO Local",
        "autoridade": "Autoridade",
        "uso_tecnologia": "Uso de Tecnologia",
    }
    for key, title in label_exp.items():
        with st.expander(f"{title} — nota {scores[key]}/10"):
            st.write(result["detalhes"].get(key, "Sem detalhe adicional."))

    # Persistência
    ts = datetime.now().isoformat(timespec="seconds")
    diag_json = json.dumps(
        {"scores": scores, **{k: result[k] for k in ("banho_realidade", "plano_modernizacao", "detalhes")}},
        ensure_ascii=False,
    )
    lead_row = {
        "timestamp_iso": ts,
        "nome": nome.strip(),
        "empresa": empresa.strip(),
        "site": site.strip(),
        "segmento": segmento.strip(),
        "instagram": instagram.strip(),
        "whatsapp": whatsapp_in.strip(),
        "dor": dor,
        **{k: scores[k] for k in scores},
        "banho_realidade": result["banho_realidade"],
        "plano_modernizacao": result["plano_modernizacao"],
        "diagnostico_json": diag_json,
    }
    save_lead_csv(lead_row)
    st.success(f"Lead salvo em `{LEADS_CSV.name}` para sua análise posterior.")

    lead_for_mail = {
        "nome": nome.strip(),
        "empresa": empresa.strip(),
        "site": site.strip(),
        "segmento": segmento.strip(),
        "instagram": instagram.strip(),
        "whatsapp": whatsapp_in.strip(),
        "dor": dor,
    }
    ok_mail, err_mail = send_agentmail_notification(lead_for_mail, scores, result, ts)
    if ok_mail:
        st.info(
            f"Notificação enviada de **{AGENTMAIL_INBOX}** para **{AGENTMAIL_NOTIFY_TO}** (AgentMail)."
        )
    else:
        st.warning(
            f"E-mail de notificação não enviado: {err_mail}. "
            "Confira `AGENTMAIL_API_KEY`, o inbox no console AgentMail e variáveis `AGENTMAIL_INBOX` / `AGENTMAIL_NOTIFY_TO`."
        )

    # CTA WhatsApp
    nome_cta = nome.strip() or "Cliente"
    empresa_cta = empresa.strip()
    msg = (
        f"Olá Eduardo! Sou {nome_cta} ({empresa_cta}). "
        f"Quero falar sobre o diagnóstico de maturidade digital e as soluções Lia / IAExpertise."
    )
    phone = only_digits(WHATSAPP_ARQUITETO)
    if len(phone) < 10:
        st.warning("Configure WHATSAPP_ARQUITETO com DDI+DDD+número (só dígitos) para o link funcionar.")
    wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
    st.link_button("Falar com o Arquiteto Eduardo Sona", wa_url, use_container_width=True)


if __name__ == "__main__":
    main()
