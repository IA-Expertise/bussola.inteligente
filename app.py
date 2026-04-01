"""
Bússola Inteligente — Diagnóstico de maturidade digital (Streamlit + GPT-4o-mini)
IAExpertise · leads em leads.csv · AgentMail para notificação interna
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
# Configuração
# -----------------------------------------------------------------------------
WHATSAPP_ARQUITETO = os.getenv("WHATSAPP_ARQUITETO", "5511999999999")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LEADS_CSV = Path(__file__).resolve().parent / "leads.csv"

AGENTMAIL_INBOX = os.getenv("AGENTMAIL_INBOX", "bussola.inteligente@agentmail.to")
AGENTMAIL_NOTIFY_TO = os.getenv("AGENTMAIL_NOTIFY_TO", "contato@iaexpertise.com.br")

LINKEDIN_IAEXPERTISE_URL = os.getenv(
    "LINKEDIN_IAEXPERTISE_URL",
    "https://www.linkedin.com/company/iaexpertise/",
)

# Vídeo da landing — substitua por URL do YouTube (Secret YOUTUBE_VIDEO_URL no Replit)
YOUTUBE_VIDEO_URL = os.getenv(
    "YOUTUBE_VIDEO_URL",
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
)

SAPPHIRE = "#0F52BA"

LANDING_EXPLAIN_HTML = """
<p style="margin:0 0 1rem 0;line-height:1.65;color:#cbd5e1;">
Muitas empresas são excelentes no que fazem, mas invisíveis para quem quer comprar.
A <strong style="color:#f1f5f9;">Bússola Inteligente</strong> utiliza Inteligência Artificial para auditar sua vitrine digital
e identificar exatamente onde você está perdendo clientes.
</p>
<p style="margin:0;line-height:1.65;color:#cbd5e1;">
A análise se baseia nas <strong>5 maiores dores do microempreendedor brasileiro</strong> de acordo com as pesquisas de entidades como
Sebrae, FGV, Google e outras. Nosso diagnóstico é <strong>100% gratuito</strong>, seguro e focado em &quot;ajeitar a sua casa&quot;
para você faturar mais. Não pedimos senhas ou dados sigilosos, apenas analisamos como o mercado enxerga o seu negócio hoje.
</p>
"""

DOR_SEBRAE_OPCOES = [
    "Falta de controle financeiro",
    "Informalidade",
    "Contratação",
    "Captação de clientes",
    "Presença digital mínima",
]

SCORE_KEYS = ["atendimento", "visual", "seo_local", "tecnologia", "autoridade"]

SYSTEM_PROMPT = """Você é um consultor sênior de presença digital e negócios para microempresas brasileiras.
Use português do Brasil. Seja direto, honesto e útil.

Contexto: as cinco maiores dificuldades frequentemente citadas para MEI/pequenos negócios incluem temas como controle financeiro, informalidade, contratação, captação de clientes e presença digital. O diagnóstico a seguir foca presença digital e canais; quando a "dor" do usuário for finanças ou contratação, reconheça isso na "dica de gestor" sem fingir que o gráfico mede fluxo de caixa ou RH.

TAREFA:
Com base nos dados informados (empresa, segmento, site, redes, WhatsApp, dor Sebrae selecionada), produza um diagnóstico em JSON.

NOTAS inteiras de 0 a 10:
- atendimento — agilidade e qualidade aparente de resposta (WhatsApp, canais informados).
- visual — identidade e consistência visual dedutível.
- seo_local — ser encontrado no Google / local / GMB.
- tecnologia — automação, IA, integrações, modernização.
- autoridade — conteúdo, prova social, reputação percebida.

TRÊS textos obrigatórios:
1) raio_x_realista — "raio-X" crítico da presença digital (sem floreio).
2) dica_gestor — conselho prático alinhado à DOR SEBRAE escolhida pelo usuário (Sebrae como referência de contexto; não invente estatísticas exatas).
3) oportunidades_iaexpertise — como Lia (atendimento no WhatsApp) e produção de conteúdo/vídeo com IA ajudam nos pontos citados.

Para cada eixo, detalhes[NOME] explica a nota em um parágrafo curto.

RESPONDA APENAS com JSON válido (sem markdown):
{
  "scores": {
    "atendimento": <int 0-10>,
    "visual": <int 0-10>,
    "seo_local": <int 0-10>,
    "tecnologia": <int 0-10>,
    "autoridade": <int 0-10>
  },
  "raio_x_realista": "<texto>",
  "dica_gestor": "<texto>",
  "oportunidades_iaexpertise": "<texto>",
  "detalhes": {
    "atendimento": "<texto>",
    "visual": "<texto>",
    "seo_local": "<texto>",
    "tecnologia": "<texto>",
    "autoridade": "<texto>"
  }
}
"""


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700&display=swap');
        html, body, [class*="css"] {{ font-family: 'DM Sans', system-ui, sans-serif; }}
        .stApp {{
            background: linear-gradient(165deg, #0a0f1a 0%, #0f172a 40%, #111827 100%);
        }}
        h1 {{ letter-spacing: -0.03em; font-weight: 700 !important; color: #f8fafc !important; }}
        h2, h3 {{ color: #e2e8f0 !important; font-weight: 600 !important; }}
        .tagline-saph {{ color: {SAPPHIRE}; font-size: 0.85rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; }}
        .hero-sub {{ color: #94a3b8; font-size: 1.05rem; margin: 0.5rem 0 1.25rem; }}
        .card-saph {{
            background: rgba(30, 41, 59, 0.55);
            border: 1px solid rgba(15, 82, 186, 0.35);
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1rem;
        }}
        div[data-testid="stExpander"] details {{
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(15, 82, 186, 0.25);
            border-radius: 10px;
        }}
        .stButton > button {{
            background: linear-gradient(135deg, #0a3d8c 0%, {SAPPHIRE} 55%, #3b7ddd 100%) !important;
            color: #f8fafc !important;
            font-weight: 700 !important;
            border: none !important;
            padding: 0.65rem 1.35rem;
            border-radius: 10px !important;
            box-shadow: 0 4px 14px rgba(15, 82, 186, 0.45);
        }}
        .stButton > button:hover {{
            box-shadow: 0 6px 22px rgba(15, 82, 186, 0.55);
            filter: brightness(1.06);
        }}
        label {{ color: #cbd5e1 !important; }}
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        [data-testid="collapsedControl"] {{
            display: none !important;
        }}
        .block-container {{
            padding-top: 2rem !important;
            max-width: 1100px !important;
        }}
        footer {{ visibility: hidden; }}
        .site-footer {{
            margin-top: 3rem;
            padding: 1.75rem 1.25rem 2rem;
            border-top: 1px solid rgba(15, 82, 186, 0.35);
            text-align: center;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.4) 0%, rgba(15, 23, 42, 0.85) 100%);
            border-radius: 14px 14px 0 0;
        }}
        .site-footer .brand {{
            color: {SAPPHIRE};
            font-weight: 700;
            font-size: 1.05rem;
            letter-spacing: 0.04em;
            margin-bottom: 0.35rem;
        }}
        .site-footer .author {{
            color: #e2e8f0;
            font-size: 0.95rem;
            margin: 0.5rem 0;
        }}
        .site-footer a {{
            color: {SAPPHIRE};
            font-weight: 600;
            text-decoration: none;
        }}
        .site-footer a:hover {{ text-decoration: underline; }}
        .lgpd-badge {{
            display: inline-block;
            margin-top: 0.85rem;
            padding: 0.45rem 0.65rem;
            background: rgba(15, 82, 186, 0.15);
            border: 1px solid rgba(15, 82, 186, 0.4);
            border-radius: 8px;
            font-size: 0.8rem;
            color: #94a3b8;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def format_whatsapp_br(raw: str) -> str:
    """Formata para exibição (XX) XXXXX-XXXX / (XX) XXXX-XXXX."""
    d = only_digits(raw)
    if len(d) < 10:
        return raw.strip()
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    return raw.strip()


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
            {"role": "user", "content": f"Dados para diagnóstico:\n{payload}"},
        ],
    )
    raw = completion.choices[0].message.content or "{}"
    return json.loads(raw)


def clamp_score(n: int) -> int:
    return max(0, min(10, int(n)))


def normalize_result(data: dict) -> dict:
    scores = data.get("scores") or {}
    out_scores: dict[str, int] = {}
    for k in SCORE_KEYS:
        v = scores.get(k, 0)
        try:
            out_scores[k] = clamp_score(int(v))
        except (TypeError, ValueError):
            out_scores[k] = 0
    detalhes = data.get("detalhes") or {}
    out_det = {k: str(detalhes.get(k, "")).strip() for k in SCORE_KEYS}
    return {
        "scores": out_scores,
        "raio_x_realista": str(data.get("raio_x_realista", "")).strip(),
        "dica_gestor": str(data.get("dica_gestor", "")).strip(),
        "oportunidades_iaexpertise": str(data.get("oportunidades_iaexpertise", "")).strip(),
        "detalhes": out_det,
    }


def build_radar_figure(scores: dict) -> go.Figure:
    labels_pt = {
        "atendimento": "Atendimento",
        "visual": "Visual",
        "seo_local": "SEO Local",
        "tecnologia": "Tecnologia",
        "autoridade": "Autoridade",
    }
    order = SCORE_KEYS
    theta = [labels_pt[k] for k in order] + [labels_pt[order[0]]]
    r = [scores[k] for k in order] + [scores[order[0]]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=r,
            theta=theta,
            fill="toself",
            fillcolor="rgba(15, 82, 186, 0.35)",
            line=dict(color=SAPPHIRE, width=2),
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
                gridcolor="rgba(15, 82, 186, 0.2)",
            ),
            angularaxis=dict(
                tickfont=dict(color="#e2e8f0", size=12),
                linecolor="rgba(15, 82, 186, 0.35)",
            ),
            bgcolor="rgba(15, 23, 42, 0.5)",
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=48, b=32, l=48, r=48),
        title=dict(
            text="Mapa de maturidade (0–10)",
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
    esc = html.escape
    label_scores = [
        ("atendimento", "Atendimento"),
        ("visual", "Visual"),
        ("seo_local", "SEO local"),
        ("tecnologia", "Tecnologia"),
        ("autoridade", "Autoridade"),
    ]
    lines = [
        "Novo diagnóstico — Bússola Inteligente / IAExpertise",
        "",
        f"Data/hora: {ts}",
        f"Nome: {lead.get('nome', '')}",
        f"Empresa: {lead.get('empresa', '')}",
        f"Site: {lead.get('site', '')}",
        f"Segmento: {lead.get('segmento', '')}",
        f"Instagram: {lead.get('instagram', '')}",
        f"WhatsApp: {lead.get('whatsapp', '')}",
        f"E-mail: {lead.get('email_cliente', '')}",
        f"Opt-in: {lead.get('optin', '')}",
        f"Dor (Sebrae): {lead.get('dor', '')}",
        "",
        "Notas:",
    ]
    for k, lab in label_scores:
        lines.append(f"  {lab}: {scores.get(k, '')}")
    lines.extend(
        [
            "",
            "--- Raio-X realista ---",
            result.get("raio_x_realista", ""),
            "",
            "--- Dica de gestor ---",
            result.get("dica_gestor", ""),
            "",
            "--- Oportunidades IAExpertise ---",
            result.get("oportunidades_iaexpertise", ""),
        ]
    )
    text_body = "\n".join(lines)

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
            ("E-mail", lead.get("email_cliente", "")),
            ("Opt-in", lead.get("optin", "")),
            ("Dor (Sebrae)", lead.get("dor", "")),
        ]
    )
    scores_rows = "".join(
        f"<tr><td style='padding:6px 12px;border:1px solid #334155'>{esc(lab)}</td>"
        f"<td style='padding:6px 12px;border:1px solid #334155'><strong>{scores.get(k, '')}</strong>/10</td></tr>"
        for k, lab in label_scores
    )
    html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px;">
  <h1 style="color:{SAPPHIRE};font-size:1.25rem;">Novo diagnóstico — Bússola Inteligente</h1>
  <table style="border-collapse:collapse;margin:16px 0;width:100%;max-width:560px;">{rows_html}</table>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Notas</h2>
  <table style="border-collapse:collapse;margin-bottom:24px;width:100%;max-width:560px;">{scores_rows}</table>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Raio-X realista</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:16px;white-space:pre-wrap;">{esc(result.get("raio_x_realista", ""))}</div>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Dica de gestor</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:16px;white-space:pre-wrap;">{esc(result.get("dica_gestor", ""))}</div>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Oportunidades IAExpertise</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;white-space:pre-wrap;">{esc(result.get("oportunidades_iaexpertise", ""))}</div>
</body></html>"""
    return text_body, html_body


def send_agentmail_notification(
    lead: dict,
    scores: dict,
    result: dict,
    ts: str,
) -> tuple[bool, str | None]:
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
        return False, "AGENTMAIL_INBOX inválido"

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
        "email_cliente",
        "optin_autorizado",
        "dor_sebrae",
        "atendimento",
        "visual",
        "seo_local",
        "tecnologia",
        "autoridade",
        "raio_x_realista",
        "dica_gestor",
        "oportunidades_iaexpertise",
        "diagnostico_json",
    ]
    file_exists = LEADS_CSV.is_file()
    with LEADS_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def init_session() -> None:
    if "etapa" not in st.session_state:
        st.session_state.etapa = "landing"
    if "lead_snap" not in st.session_state:
        st.session_state.lead_snap = {}
    if "diagnostico_result" not in st.session_state:
        st.session_state.diagnostico_result = None
    if "lead_persistido" not in st.session_state:
        st.session_state.lead_persistido = False


def reset_para_landing() -> None:
    st.session_state.etapa = "landing"
    st.session_state.lead_snap = {}
    st.session_state.diagnostico_result = None
    st.session_state.lead_persistido = False


def render_footer() -> None:
    st.markdown(
        f"""
<div class="site-footer">
  <div class="brand">IAExpertise</div>
  <p class="author">Eduardo Augusto Sona — Jornalista e Especialista em IA</p>
  <p><a href="{html.escape(LINKEDIN_IAEXPERTISE_URL)}" target="_blank" rel="noopener">IAExpertise no LinkedIn</a></p>
  <p class="lgpd-badge">🔒 Dados protegidos (LGPD)</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_landing() -> None:
    st.markdown('<p class="tagline-saph">IAExpertise</p>', unsafe_allow_html=True)
    st.markdown("# Bússola Inteligente 🧭")
    st.markdown(
        '<p class="hero-sub">O mapa para tirar sua empresa do invisível e colocar no lucro.</p>',
        unsafe_allow_html=True,
    )

    _, c_mid, _ = st.columns([1, 8, 1])
    with c_mid:
        try:
            st.video(YOUTUBE_VIDEO_URL)
        except Exception:
            st.info("Configure a URL do vídeo em `YOUTUBE_VIDEO_URL` (Secrets).")
            st.markdown(f"[Abrir vídeo no YouTube]({YOUTUBE_VIDEO_URL})")

    st.markdown(
        '<div class="card-saph" style="margin-top:1.25rem;">'
        + LANDING_EXPLAIN_HTML
        + "</div>",
        unsafe_allow_html=True,
    )

    if st.button("Quero analisar meu negócio", type="primary", use_container_width=True):
        st.session_state.etapa = "formulario"
        st.rerun()


def render_formulario() -> None:
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← Início"):
            reset_para_landing()
            st.rerun()
    st.markdown("## Consultoria Gratuita IAExpertise")
    st.caption("Preencha com o que puder — quanto mais contexto, melhor o diagnóstico.")

    with st.form("form_diagnostico"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome do contato", placeholder="Maria Silva")
            empresa = st.text_input("Nome da empresa *", placeholder="Sua loja MEI")
            segmento = st.text_input("Segmento", placeholder="Alimentação, serviços…")
        with c2:
            site = st.text_input("Site (URL ou vazio)", placeholder="https://…")
            instagram = st.text_input("Instagram", placeholder="@minhaloja")
            whatsapp_in = st.text_input(
                "WhatsApp (com DDD)",
                placeholder="(11) 99999-9999",
                help="Apenas números ou com máscara; salvamos o formato brasileiro.",
            )

        email_cliente = st.text_input(
            "E-mail do contato",
            placeholder="nome@empresa.com.br",
            help="Obrigatório se marcar o opt-in abaixo.",
        )
        optin = st.checkbox(
            "Autorizo a IAExpertise a me contatar por e-mail e WhatsApp sobre este diagnóstico e soluções de IA/presença digital. Posso retirar a autorização quando quiser (opt-in).",
            value=False,
        )

        dor = st.selectbox(
            "Qual o maior desafio hoje? (referência Sebrae)",
            options=DOR_SEBRAE_OPCOES,
            index=4,
        )

        submitted = st.form_submit_button("Gerar diagnóstico em 60s")

    if not submitted:
        return

    if not (empresa or "").strip():
        st.error("Informe o nome da empresa.")
        return

    email_stripped = (email_cliente or "").strip()
    if optin and not email_stripped:
        st.error("Para registrar o opt-in, informe seu e-mail.")
        return

    wa_digits = only_digits(whatsapp_in)
    wa_display = format_whatsapp_br(whatsapp_in) if wa_digits else ""

    user_payload = {
        "nome": (nome or "").strip(),
        "empresa": empresa.strip(),
        "site": (site or "").strip(),
        "segmento": (segmento or "").strip(),
        "instagram": (instagram or "").strip(),
        "whatsapp": wa_display or whatsapp_in.strip(),
        "dor_sebrae": dor,
        "email_cliente": email_stripped,
        "optin_contato": optin,
    }

    with st.spinner("Gerando diagnóstico com IA…"):
        try:
            raw = call_openai_diagnostico(json.dumps(user_payload, ensure_ascii=False))
            result = normalize_result(raw)
        except json.JSONDecodeError as e:
            st.error(f"Resposta da IA inválida: {e}")
            return
        except Exception as e:
            st.error(str(e))
            return

    st.session_state.lead_snap = {
        "nome": (nome or "").strip(),
        "empresa": empresa.strip(),
        "site": (site or "").strip(),
        "segmento": (segmento or "").strip(),
        "instagram": (instagram or "").strip(),
        "whatsapp": wa_display or whatsapp_in.strip(),
        "whatsapp_digits": wa_digits,
        "email_cliente": email_stripped,
        "optin": "sim" if optin else "nao",
        "dor": dor,
    }
    st.session_state.diagnostico_result = result
    st.session_state.lead_persistido = False
    st.session_state.etapa = "relatorio"
    st.rerun()


def render_relatorio() -> None:
    result = st.session_state.diagnostico_result
    lead = st.session_state.lead_snap
    if not result or not lead:
        st.warning("Nada para exibir. Volte ao início.")
        if st.button("← Início"):
            reset_para_landing()
            st.rerun()
        return

    r1, _ = st.columns([1, 5])
    with r1:
        if st.button("← Início", key="inicio_rel"):
            reset_para_landing()
            st.rerun()

    scores = result["scores"]
    fig = build_radar_figure(scores)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("1) Raio-X realista")
    rx = html.escape(result["raio_x_realista"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card-saph">{rx}</div>', unsafe_allow_html=True)

    st.subheader("2) Dica de gestor")
    dg = html.escape(result["dica_gestor"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card-saph">{dg}</div>', unsafe_allow_html=True)

    st.subheader("3) Oportunidades IAExpertise")
    op = html.escape(result["oportunidades_iaexpertise"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card-saph">{op}</div>', unsafe_allow_html=True)

    labels = {
        "atendimento": "Atendimento",
        "visual": "Visual",
        "seo_local": "SEO Local",
        "tecnologia": "Tecnologia",
        "autoridade": "Autoridade",
    }
    st.subheader("Detalhes por eixo")
    for k, title in labels.items():
        with st.expander(f"{title} — {scores[k]}/10"):
            st.write(result["detalhes"].get(k, "—"))

    ts = datetime.now().isoformat(timespec="seconds")

    if not st.session_state.lead_persistido:
        diag_json = json.dumps(
            {"scores": scores, **{x: result[x] for x in ("raio_x_realista", "dica_gestor", "oportunidades_iaexpertise", "detalhes")}},
            ensure_ascii=False,
        )
        row = {
            "timestamp_iso": ts,
            "nome": lead.get("nome", ""),
            "empresa": lead.get("empresa", ""),
            "site": lead.get("site", ""),
            "segmento": lead.get("segmento", ""),
            "instagram": lead.get("instagram", ""),
            "whatsapp": lead.get("whatsapp", ""),
            "email_cliente": lead.get("email_cliente", ""),
            "optin_autorizado": lead.get("optin", "nao"),
            "dor_sebrae": lead.get("dor", ""),
            **{k: scores[k] for k in SCORE_KEYS},
            "raio_x_realista": result["raio_x_realista"],
            "dica_gestor": result["dica_gestor"],
            "oportunidades_iaexpertise": result["oportunidades_iaexpertise"],
            "diagnostico_json": diag_json,
        }
        save_lead_csv(row)
        st.session_state.lead_persistido = True
        st.success(f"Lead registrado em `{LEADS_CSV.name}`.")

        lead_mail = {
            "nome": lead.get("nome", ""),
            "empresa": lead.get("empresa", ""),
            "site": lead.get("site", ""),
            "segmento": lead.get("segmento", ""),
            "instagram": lead.get("instagram", ""),
            "whatsapp": lead.get("whatsapp", ""),
            "email_cliente": lead.get("email_cliente", ""),
            "optin": lead.get("optin", "nao"),
            "dor": lead.get("dor", ""),
        }
        ok_mail, err_mail = send_agentmail_notification(lead_mail, scores, result, ts)
        if ok_mail:
            st.info(
                f"Notificação enviada de **{AGENTMAIL_INBOX}** para **{AGENTMAIL_NOTIFY_TO}**."
            )
        else:
            st.warning(f"E-mail interno não enviado: {err_mail}")

    nome_cta = lead.get("nome") or "Cliente"
    empresa_cta = lead.get("empresa") or "minha empresa"
    msg = (
        f"Olá Eduardo! Sou {nome_cta} ({empresa_cta}). "
        f"Quero falar sobre o diagnóstico Bússola Inteligente e as soluções Lia / IAExpertise."
    )
    phone = only_digits(WHATSAPP_ARQUITETO)
    wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
    if len(phone) < 10:
        st.warning("Configure WHATSAPP_ARQUITETO (DDI+DDD+número, só dígitos).")
    st.link_button("Falar com o Arquiteto no WhatsApp", wa_url, use_container_width=True)

    if st.button("Nova análise", use_container_width=True):
        reset_para_landing()
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Bússola Inteligente | IAExpertise",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session()
    inject_css()

    etapa = st.session_state.etapa

    if etapa == "landing":
        render_landing()
    elif etapa == "formulario":
        render_formulario()
    elif etapa == "relatorio":
        render_relatorio()
    else:
        st.session_state.etapa = "landing"
        st.rerun()

    render_footer()


if __name__ == "__main__":
    main()
