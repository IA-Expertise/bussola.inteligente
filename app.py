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
A análise se baseia nas <strong>5 maiores dores do microempreendedor brasileiro</strong> e em sinais de <strong>presença digital pública</strong>:
<strong>Google</strong> (busca e Maps), <strong>Google Meu Negócio</strong>, <strong>site</strong> e <strong>redes sociais</strong> — o que qualquer pessoa vê sem login.
Nosso diagnóstico é <strong>100% gratuito</strong>, seguro e focado em &quot;ajeitar a sua casa&quot;
para você faturar mais. Não pedimos senhas ou acesso a contas; apenas o que você informa e o que é publicamente observável.
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

SYSTEM_PROMPT = """Você é um consultor sênior de presença digital para microempresas e órgãos no Brasil.
Use português do Brasil. Seja direto, honesto e útil.

ESCOPO DO DIAGNÓSTICO (presença digital pública):
Avalie como o negócio ou instituição aparece em Google (busca orgânica e intenção local), Google Meu Negócio / Google Maps,
site, redes sociais informadas e canais de contato (ex.: WhatsApp). Não invente que acessou contas ou APIs: use apenas o que o usuário descreveu e inferências plausíveis a partir disso.

Contexto Sebrae: quando a "dor" for finanças, contratação etc., trate na "dica de gestor" sem fingir que o gráfico mede fluxo de caixa ou RH.

TAREFA:
Com base nos dados informados (empresa, segmento, site, link Google Maps/GMB, termo de busca, Instagram, outras redes opcionais, WhatsApp, dor Sebrae), produza um diagnóstico em JSON.

NOTAS inteiras de 0 a 10:
- atendimento — clareza e consistência dos canais de contato (WhatsApp, telefone/e-mail se citados), prontidão aparente.
- visual — consistência de nome, logo e comunicação entre site e redes informadas.
- seo_local — encontrabilidade no Google: relevância local, Google Meu Negócio/Maps, coerência NAP (nome/endereço/telefone) quando dedutível; termo de busca informado pelo usuário.
- tecnologia — sinais de modernização (site responsivo, ferramentas, automação) quando dedutível pelos dados; não afirme testes técnicos não feitos.
- autoridade — prova social, avaliações, conteúdo, reputação percebida nos canais citados.

CINCO blocos obrigatórios de texto (além de detalhes por eixo):
1) introducao_analitica — TEXTO INTRODUTÓRIO LONGO (3 a 5 parágrafos). Sintetize o cenário da empresa/órgão: visibilidade no digital, coerência entre canais,
   riscos de invisibilidade ou má impressão ao cidadão/cliente, e oportunidades. Tom profissional, consultivo, sem slogans vazios.
2) caminhos_recomendados — liste de 4 a 6 caminhos PRIORITÁRIOS que a empresa pode traçar (curto/médio prazo). Use linhas começando com número (1. 2. 3.) ou traço (-).
   Cada item deve ser acionável e ligado aos dados informados.
3) raio_x_realista — "raio-X" crítico da presença digital (sem floreio).
4) dica_gestor — conselho prático alinhado à DOR SEBRAE escolhida pelo usuário (Sebrae como referência de contexto; não invente estatísticas exatas).
5) oportunidades_iaexpertise — como Lia (atendimento no WhatsApp) e produção de conteúdo/vídeo com IA ajudam nos pontos citados.

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
  "introducao_analitica": "<texto com vários parágrafos separados por \\n>",
  "caminhos_recomendados": "<texto com lista numerada ou marcadores>",
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
        "introducao_analitica": str(data.get("introducao_analitica", "")).strip(),
        "caminhos_recomendados": str(data.get("caminhos_recomendados", "")).strip(),
        "raio_x_realista": str(data.get("raio_x_realista", "")).strip(),
        "dica_gestor": str(data.get("dica_gestor", "")).strip(),
        "oportunidades_iaexpertise": str(data.get("oportunidades_iaexpertise", "")).strip(),
        "detalhes": out_det,
    }


def build_radar_figure(scores: dict) -> go.Figure:
    labels_pt = {
        "atendimento": "Atendimento",
        "visual": "Visual / marca",
        "seo_local": "Google / Local",
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


def safe_report_filename(empresa: str) -> str:
    raw = re.sub(r"[^\w\s-]", "", (empresa or "").strip(), flags=re.UNICODE)
    raw = re.sub(r"[-\s]+", "_", raw).strip("_") or "relatorio"
    return raw[:60]


def build_html_report(lead: dict, result: dict, fig: go.Figure) -> str:
    """HTML autossuficiente com gráfico Plotly (CDN) e textos do diagnóstico."""
    scores = result["scores"]
    when = datetime.now().strftime("%d/%m/%Y %H:%M")

    try:
        chart_html = fig.to_html(
            full_html=False,
            include_plotlyjs="cdn",
            config={"displayModeBar": True, "responsive": True},
            div_id="radar-bussola-export",
        )
    except Exception:
        chart_html = '<p class="note">Gráfico indisponível na exportação. Veja o relatório no app.</p>'

    def esc_br(s: str) -> str:
        return html.escape(s or "").replace("\n", "<br/>\n")

    sec = (
        ("introducao_analitica", "1. Visão geral e introdução analítica"),
        ("caminhos_recomendados", "2. Caminhos recomendados"),
        ("raio_x_realista", "3. Raio-X realista"),
        ("dica_gestor", "4. Dica de gestor"),
        ("oportunidades_iaexpertise", "5. Oportunidades IAExpertise"),
    )
    blocos = []
    for key, title in sec:
        txt = (result.get(key) or "").strip()
        if txt:
            blocos.append(
                f'<section class="blk"><h2>{html.escape(title)}</h2>'
                f'<div class="body">{esc_br(txt)}</div></section>'
            )

    labels_eixo = {
        "atendimento": "Atendimento",
        "visual": "Visual / marca",
        "seo_local": "Google / Local",
        "tecnologia": "Tecnologia",
        "autoridade": "Autoridade",
    }
    det_parts = []
    for k, lab in labels_eixo.items():
        t = (result.get("detalhes") or {}).get(k, "") or ""
        sc = scores.get(k, 0)
        det_parts.append(
            f'<div class="det"><h3>{html.escape(lab)} — {sc}/10</h3>'
            f'<div class="body">{esc_br(t) if t.strip() else "—"}</div></div>'
        )
    det_html = "\n".join(det_parts)

    esc = html.escape
    emp = esc(lead.get("empresa") or "")
    nom = esc(lead.get("nome") or "")
    seg = esc(lead.get("segmento") or "")
    site = esc(lead.get("site") or "")
    dor = esc(lead.get("dor") or "")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Bússola Inteligente — {emp}</title>
<style>
  :root {{
    --saph: #0F52BA;
    --bg: #0f172a;
    --card: #1e293b;
    --text: #e2e8f0;
    --muted: #94a3b8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2rem 1.25rem 3rem;
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: linear-gradient(165deg, #0a0f1a 0%, var(--bg) 50%, #111827 100%);
    color: var(--text); line-height: 1.55;
  }}
  .wrap {{ max-width: 900px; margin: 0 auto; }}
  header {{
    border-bottom: 1px solid rgba(15, 82, 186, 0.45);
    padding-bottom: 1.25rem; margin-bottom: 1.5rem;
  }}
  .product-row {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }}
  .compass {{ font-size: 1.85rem; line-height: 1; }}
  .product-name {{ font-size: 1.35rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }}
  .brand-sub {{ color: var(--saph); font-weight: 600; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.35rem; }}
  h1 {{ margin: 0.5rem 0 0; font-size: 1.2rem; color: #cbd5e1; font-weight: 600; }}
  .meta {{ color: var(--muted); font-size: 0.9rem; margin-top: 0.75rem; }}
  .meta span {{ display: inline-block; margin-right: 1rem; }}
  .chart-box {{
    background: rgba(30, 41, 59, 0.55);
    border: 1px solid rgba(15, 82, 186, 0.35);
    border-radius: 14px; padding: 1rem; margin: 1.5rem 0;
  }}
  .chart-box h2 {{ margin: 0 0 0.75rem; font-size: 1.05rem; color: var(--muted); font-weight: 600; }}
  .blk {{ margin: 1.35rem 0; }}
  .blk h2 {{ font-size: 1.05rem; color: #cbd5e1; margin: 0 0 0.5rem; border-left: 3px solid var(--saph); padding-left: 0.6rem; }}
  .blk .body, .det .body {{ background: var(--card); border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 10px; padding: 1rem; font-size: 0.95rem; }}
  .det {{ margin: 1rem 0; }}
  .det h3 {{ font-size: 0.95rem; color: #cbd5e1; margin: 0 0 0.4rem; }}
  footer {{ margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid rgba(15, 82, 186, 0.25);
    font-size: 0.8rem; color: var(--muted); text-align: center; }}
  @media print {{
    body {{ background: #fff; color: #111; }}
    .blk .body, .det .body {{ border-color: #ccc; background: #f8fafc; }}
    h1, .product-name {{ color: #111; }}
    .brand-sub {{ color: var(--saph); }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="product-row">
      <span class="compass" title="Bússola Inteligente" aria-hidden="true">🧭</span>
      <div>
        <div class="product-name">Bússola Inteligente</div>
        <div class="brand-sub">IAExpertise</div>
      </div>
    </div>
    <h1>Relatório de maturidade digital</h1>
    <div class="meta">
      <span><strong>Empresa / órgão:</strong> {emp or "—"}</span>
      <span><strong>Contato:</strong> {nom or "—"}</span>
    </div>
    <div class="meta">
      <span><strong>Segmento:</strong> {seg or "—"}</span>
      <span><strong>Site:</strong> {site or "—"}</span>
    </div>
    <div class="meta"><span><strong>Desafio (Sebrae):</strong> {dor or "—"}</span></div>
    <div class="meta"><span><strong>Emitido em:</strong> {esc(when)}</span></div>
  </header>

  <div class="chart-box">
    <h2>Mapa de maturidade (0–10)</h2>
    {chart_html}
  </div>

  {chr(10).join(blocos)}

  <section class="blk">
    <h2>Detalhes por eixo</h2>
    {det_html}
  </section>

  <footer>
    <span aria-hidden="true">🧭</span> Relatório gerado pela <strong>Bússola Inteligente</strong> (IAExpertise). Uso de dados públicos e informações fornecidas pelo solicitante.
    Para salvar em PDF: use Imprimir → Salvar como PDF no navegador.
  </footer>
</div>
</body>
</html>
"""


def build_notification_bodies(
    lead: dict,
    scores: dict,
    result: dict,
    ts: str,
) -> tuple[str, str]:
    esc = html.escape
    label_scores = [
        ("atendimento", "Atendimento"),
        ("visual", "Visual / marca"),
        ("seo_local", "Google / Local"),
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
        f"Google Maps / GMB: {lead.get('gmb_maps', '')}",
        f"Termo Google (busca): {lead.get('termo_google', '')}",
        f"Instagram: {lead.get('instagram', '')}",
        f"Facebook: {lead.get('facebook', '')}",
        f"LinkedIn: {lead.get('linkedin', '')}",
        f"YouTube: {lead.get('youtube', '')}",
        f"TikTok: {lead.get('tiktok', '')}",
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
            "--- Introdução analítica ---",
            result.get("introducao_analitica", ""),
            "",
            "--- Caminhos recomendados ---",
            result.get("caminhos_recomendados", ""),
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
            ("Google Maps / GMB", lead.get("gmb_maps", "")),
            ("Termo no Google", lead.get("termo_google", "")),
            ("Instagram", lead.get("instagram", "")),
            ("Facebook", lead.get("facebook", "")),
            ("LinkedIn", lead.get("linkedin", "")),
            ("YouTube", lead.get("youtube", "")),
            ("TikTok", lead.get("tiktok", "")),
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
  <h2 style="color:#94a3b8;font-size:0.95rem;">Introdução analítica</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:16px;white-space:pre-wrap;">{esc(result.get("introducao_analitica", ""))}</div>
  <h2 style="color:#94a3b8;font-size:0.95rem;">Caminhos recomendados</h2>
  <div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-bottom:16px;white-space:pre-wrap;">{esc(result.get("caminhos_recomendados", ""))}</div>
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
        "gmb_maps",
        "termo_google",
        "instagram",
        "facebook",
        "linkedin",
        "youtube",
        "tiktok",
        "whatsapp",
        "email_cliente",
        "optin_autorizado",
        "dor_sebrae",
        "atendimento",
        "visual",
        "seo_local",
        "tecnologia",
        "autoridade",
        "introducao_analitica",
        "caminhos_recomendados",
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
    st.caption(
        "Foco em presença digital pública: Google (busca e Maps), Google Meu Negócio, site e redes — sem senhas."
    )

    with st.form("form_diagnostico"):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome do contato", placeholder="Maria Silva")
            empresa = st.text_input("Nome da empresa ou órgão *", placeholder="Sua loja MEI")
            segmento = st.text_input("Segmento", placeholder="Alimentação, serviços…")
        with c2:
            site = st.text_input("Site (URL ou vazio)", placeholder="https://…")
            gmb_maps = st.text_input(
                "Google Maps / Google Meu Negócio",
                placeholder="Cole o link do seu perfil no Maps ou GMB",
                help="Abra o Google Maps, encontre seu negócio e copie o link do navegador.",
            )
            termo_google = st.text_input(
                "Como te encontram no Google? (opcional)",
                placeholder="ex.: padaria centro louveira",
                help="Palavras que o cliente digitaria na busca para achar você.",
            )

        st.markdown("**Redes e contato**")
        c3, c4 = st.columns(2)
        with c3:
            instagram = st.text_input("Instagram", placeholder="@minhaloja")
        with c4:
            whatsapp_in = st.text_input(
                "WhatsApp (com DDD)",
                placeholder="(11) 99999-9999",
                help="Canal oficial de atendimento.",
            )

        with st.expander("Outros canais públicos (opcional)", expanded=False):
            st.caption("Links ou @ — ajudam a cruzar consistência de marca e autoridade.")
            fc1, fc2 = st.columns(2)
            with fc1:
                facebook = st.text_input("Facebook", placeholder="URL da página ou perfil", key="fb")
                linkedin_in = st.text_input("LinkedIn", placeholder="URL da página", key="li")
            with fc2:
                youtube = st.text_input("YouTube", placeholder="URL do canal", key="yt")
                tiktok = st.text_input("TikTok", placeholder="@conta", key="tt")

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
        "google_maps_ou_gmb_url": (gmb_maps or "").strip(),
        "termo_busca_google": (termo_google or "").strip(),
        "instagram": (instagram or "").strip(),
        "facebook": (facebook or "").strip(),
        "linkedin": (linkedin_in or "").strip(),
        "youtube": (youtube or "").strip(),
        "tiktok": (tiktok or "").strip(),
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
        "gmb_maps": (gmb_maps or "").strip(),
        "termo_google": (termo_google or "").strip(),
        "instagram": (instagram or "").strip(),
        "facebook": (facebook or "").strip(),
        "linkedin": (linkedin_in or "").strip(),
        "youtube": (youtube or "").strip(),
        "tiktok": (tiktok or "").strip(),
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

    st.subheader("1) Visão geral e introdução analítica")
    ia_txt = (result.get("introducao_analitica") or "").strip()
    if ia_txt:
        ia_html = html.escape(ia_txt).replace("\n", "<br/>")
        st.markdown(f'<div class="card-saph">{ia_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("—")

    st.subheader("2) Caminhos recomendados")
    cam_txt = (result.get("caminhos_recomendados") or "").strip()
    if cam_txt:
        cam_html = html.escape(cam_txt).replace("\n", "<br/>")
        st.markdown(f'<div class="card-saph">{cam_html}</div>', unsafe_allow_html=True)
    else:
        st.caption("—")

    st.subheader("3) Raio-X realista")
    rx = html.escape(result["raio_x_realista"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card-saph">{rx}</div>', unsafe_allow_html=True)

    st.subheader("4) Dica de gestor")
    dg = html.escape(result["dica_gestor"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card-saph">{dg}</div>', unsafe_allow_html=True)

    st.subheader("5) Oportunidades IAExpertise")
    op = html.escape(result["oportunidades_iaexpertise"]).replace("\n", "<br/>")
    st.markdown(f'<div class="card-saph">{op}</div>', unsafe_allow_html=True)

    labels = {
        "atendimento": "Atendimento",
        "visual": "Visual / marca",
        "seo_local": "Google / Local",
        "tecnologia": "Tecnologia",
        "autoridade": "Autoridade",
    }
    st.subheader("Detalhes por eixo")
    for k, title in labels.items():
        with st.expander(f"{title} — {scores[k]}/10"):
            st.write(result["detalhes"].get(k, "—"))

    report_html = build_html_report(lead, result, fig)
    st.download_button(
        label="Baixar relatório completo (HTML)",
        data=report_html.encode("utf-8"),
        file_name=f"bussola_inteligente_{safe_report_filename(lead.get('empresa', ''))}.html",
        mime="text/html",
        key="download_relatorio_html",
        use_container_width=True,
    )
    st.caption(
        "Abra o arquivo no navegador para visualizar o gráfico interativo. "
        "Para PDF: use Imprimir → Salvar como PDF."
    )

    ts = datetime.now().isoformat(timespec="seconds")

    if not st.session_state.lead_persistido:
        diag_json = json.dumps(
            {
                "scores": scores,
                **{
                    x: result[x]
                    for x in (
                        "introducao_analitica",
                        "caminhos_recomendados",
                        "raio_x_realista",
                        "dica_gestor",
                        "oportunidades_iaexpertise",
                        "detalhes",
                    )
                },
            },
            ensure_ascii=False,
        )
        row = {
            "timestamp_iso": ts,
            "nome": lead.get("nome", ""),
            "empresa": lead.get("empresa", ""),
            "site": lead.get("site", ""),
            "segmento": lead.get("segmento", ""),
            "gmb_maps": lead.get("gmb_maps", ""),
            "termo_google": lead.get("termo_google", ""),
            "instagram": lead.get("instagram", ""),
            "facebook": lead.get("facebook", ""),
            "linkedin": lead.get("linkedin", ""),
            "youtube": lead.get("youtube", ""),
            "tiktok": lead.get("tiktok", ""),
            "whatsapp": lead.get("whatsapp", ""),
            "email_cliente": lead.get("email_cliente", ""),
            "optin_autorizado": lead.get("optin", "nao"),
            "dor_sebrae": lead.get("dor", ""),
            **{k: scores[k] for k in SCORE_KEYS},
            "introducao_analitica": result.get("introducao_analitica", ""),
            "caminhos_recomendados": result.get("caminhos_recomendados", ""),
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
            "gmb_maps": lead.get("gmb_maps", ""),
            "termo_google": lead.get("termo_google", ""),
            "instagram": lead.get("instagram", ""),
            "facebook": lead.get("facebook", ""),
            "linkedin": lead.get("linkedin", ""),
            "youtube": lead.get("youtube", ""),
            "tiktok": lead.get("tiktok", ""),
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
