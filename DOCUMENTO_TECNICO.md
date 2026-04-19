# Documento técnico — Bússola Inteligente

**Produto:** diagnóstico de maturidade digital para microempresas, agências e contexto de gestão pública (uso declarado).  
**Proprietário / marca:** IAExpertise  
**Repositório:** aplicação monolítica centrada em `app.py` (Streamlit).

---

## 1. Visão geral

A Bússola Inteligente é uma aplicação web que:

1. Apresenta uma **landing** com vídeo institucional e texto de posicionamento.  
2. Coleta **dados de presença digital** (site, Google Maps/GMB, termo de busca, redes, WhatsApp, e-mail, opt-in LGPD, desafio tipo Sebrae).  
3. Chama a **OpenAI API** (modelo configurável, padrão `gpt-4o-mini`) com resposta estruturada em **JSON**.  
4. Exibe **gráfico radar** (Plotly), blocos de texto do diagnóstico, detalhes por eixo e **CTA WhatsApp**.  
5. **Persiste** cada conclusão em `leads.csv` e envia **notificação por e-mail** (AgentMail) para a equipe.  
6. Permite **download** de relatório em **HTML** (com gráfico interativo via CDN Plotly e estilo alinhado ao app; PDF via impressão do navegador).

**Importante:** o motor atual **não executa scraping** nem APIs oficiais do Google em tempo real. A análise é baseada nos **dados informados pelo usuário** e em **inferências plausíveis** instruídas no *system prompt* — o texto deixa isso explícito para não superestimar evidências.

---

## 2. Stack tecnológica

| Componente | Tecnologia | Versão mínima (referência) |
|------------|------------|---------------------------|
| Runtime | Python 3 | 3.8+ (Replit: 3.11) |
| UI | Streamlit | ≥ 1.28 |
| LLM | OpenAI Chat Completions | SDK `openai` ≥ 1.40 |
| Gráficos | Plotly (`graph_objects`) | ≥ 5.18 |
| Config local | `python-dotenv` | ≥ 1.0 |
| E-mail transacional | AgentMail (`agentmail`) | ≥ 0.4 |

Arquivo de dependências: `requirements.txt`.

---

## 3. Estrutura do repositório (relevante)

```
bussola.inteligente/
├── app.py                 # Aplicação principal (único módulo de negócio)
├── requirements.txt
├── DOCUMENTO_TECNICO.md   # Este arquivo
├── .replit                # Comando de execução no Replit
├── .streamlit/
│   └── config.toml        # Tema escuro, cor primária (#0F52BA), porta servidor
├── assets/
│   └── .gitkeep           # Pasta reservada para ativos (ex.: imagens)
└── leads.csv              # Gerado em runtime (não versionar com dados reais)
```

`.gitignore` típico ignora `.env`, `leads.csv`, secrets e ambientes virtuais.

---

## 4. Arquitetura lógica

### 4.1 Fluxo de telas (`st.session_state`)

| Chave | Uso |
|-------|-----|
| `etapa` | `"landing"` \| `"formulario"` \| `"relatorio"` |
| `lead_snap` | Snapshot dos campos do formulário após envio válido |
| `diagnostico_result` | Objeto normalizado retornado pela IA |
| `lead_persistido` | Evita duplicar CSV + e-mail no mesmo relatório (re-run Streamlit) |

Transições usam `st.rerun()` após alterar estado.

### 4.2 Pipeline de dados

```
Landing → Formulário → JSON usuário → OpenAI (JSON mode) → normalize_result
    → UI (radar + textos) → (uma vez) save_lead_csv + AgentMail → download HTML opcional
```

### 4.3 Integrações externas

| Integração | Finalidade | Autenticação |
|------------|------------|--------------|
| OpenAI | Geração do diagnóstico estruturado | `OPENAI_API_KEY` |
| AgentMail | E-mail interno para equipe | `AGENTMAIL_API_KEY`; envio a partir do inbox `AGENTMAIL_INBOX` |
| YouTube (URL) | Vídeo na landing | Opcional `YOUTUBE_VIDEO_URL` |
| WhatsApp (wa.me) | CTA para contato comercial | `WHATSAPP_ARQUITETO` (apenas dígitos E.164 BR) |

---

## 5. Contrato da API OpenAI

### 5.1 Chamada

- **Endpoint:** Chat Completions (SDK `openai`).  
- **Modelo:** `OPENAI_MODEL` (padrão `gpt-4o-mini`).  
- **`response_format`:** `{ "type": "json_object" }` para forçar JSON.  
- **Temperatura:** 0,45 (equilíbrio entre consistência e variação).

### 5.2 Esquema lógico de saída (normalizado em `normalize_result`)

**Scores (0–10, inteiros):**

- `atendimento`  
- `visual`  
- `seo_local` (rótulo de produto: “Google / Local”)  
- `tecnologia`  
- `autoridade`  

**Textos:**

- `introducao_analitica`  
- `caminhos_recomendados`  
- `raio_x_realista`  
- `dica_gestor`  
- `oportunidades_iaexpertise`  

**Detalhes por eixo:** objeto `detalhes` com as mesmas chaves dos scores.

O *system prompt* em `app.py` define o comportamento esperado, limites de escopo (sem fingir acesso a APIs/senhas) e tom de voz.

---

## 6. Entrada do usuário (formulário)

### Campos principais

- Nome do contato, empresa/órgão (obrigatório), segmento, site.  
- **Google Maps / GMB** (URL), termo de busca opcional.  
- Instagram, WhatsApp (normalização de dígitos / máscara BR na exibição).  
- E-mail + **opt-in** (e-mail obrigatório se opt-in marcado).  
- Desafio (lista fixa alinhada a referência Sebrae).

### Opcional (`st.expander`)

- Facebook, LinkedIn, YouTube, TikTok (URLs ou @).

Payload enviado à IA é um JSON serializado com chaves semânticas (ex.: `google_maps_ou_gmb_url`, `termo_busca_google`, etc.).

---

## 7. Persistência — `leads.csv`

- **Local:** diretório raiz do projeto (`LEADS_CSV`).  
- **Encoding:** UTF-8 com BOM (`utf-8-sig`) para compatibilidade com Excel no Brasil.  
- **Modo:** append; cabeçalho na primeira escrita.

### Colunas (ordem atual)

`timestamp_iso`, `nome`, `empresa`, `site`, `segmento`, `gmb_maps`, `termo_google`, `instagram`, `facebook`, `linkedin`, `youtube`, `tiktok`, `whatsapp`, `email_cliente`, `optin_autorizado`, `dor_sebrae`, cinco notas, cinco blocos textuais longos, `diagnostico_json` (cópia estruturada do resultado).

**Migração de cabeçalho:** se um arquivo antigo existir com colunas diferentes, renomear ou arquivar antes de produção para evitar desalinhamento.

---

## 8. Notificação por e-mail (AgentMail)

- **Remetente:** endereço completo do inbox AgentMail (`AGENTMAIL_INBOX`, ex.: `bussola.inteligente@agentmail.to`).  
- **Destinatário:** `AGENTMAIL_NOTIFY_TO` (padrão `contato@iaexpertise.com.br`).  
- **Implementação:** `client.inboxes.messages.send(inbox_id, ...)` **sem** criar novo inbox a cada envio (evita `LimitExceededError` em planos limitados).  
- Corpo em **texto + HTML** com dados do lead, notas e seções do relatório.

---

## 9. Relatório HTML exportado

- Função `build_html_report(lead, result, fig)` monta documento autossuficiente.  
- Gráfico: `fig.to_html(..., include_plotlyjs="cdn")` — abertura do arquivo requer **acesso à internet** para carregar a biblioteca Plotly.  
- Identidade visual: tema escuro, acento **#0F52BA**, cabeçalho com **Bússola Inteligente** e ícone **🧭**.  
- **PDF:** não gerado no servidor; orientação ao usuário: *Imprimir → Salvar como PDF*.

---

## 10. Interface e UX

- **Tema:** dark mode + safira; parte via `inject_css()` e parte via `.streamlit/config.toml`.  
- **Sidebar Streamlit:** oculta por CSS (conteúdo institucional migrado para **rodapé** na página principal).  
- **Rodapé:** IAExpertise, crédito Eduardo Augusto Sona, link LinkedIn empresa, selo LGPD.  
- **Segurança de exibição:** conteúdo gerado pela IA exibido em HTML passa por `html.escape` onde incorporado em `unsafe_allow_html=True`.

---

## 11. Variáveis de ambiente (referência)

| Variável | Obrigatória? | Descrição |
|----------|--------------|-------------|
| `OPENAI_API_KEY` | Sim (diagnóstico) | Chave OpenAI |
| `OPENAI_MODEL` | Não | Modelo (default `gpt-4o-mini`) |
| `AGENTMAIL_API_KEY` | Não* | Se ausente, e-mail interno não é enviado |
| `AGENTMAIL_INBOX` | Não | Inbox remetente (e-mail completo) |
| `AGENTMAIL_NOTIFY_TO` | Não | Destino da notificação |
| `WHATSAPP_ARQUITETO` | Recomendado | Número CTA `wa.me` (só dígitos) |
| `YOUTUBE_VIDEO_URL` | Não | URL do vídeo da landing |
| `LINKEDIN_IAEXPERTISE_URL` | Não | URL pública LinkedIn IAExpertise |

\* Conforme regra de negócio desejada.

---

## 12. Execução e deploy

### Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opcional: arquivo `.env` na raiz (carregado por `load_dotenv()`).

### Replit

- Arquivo `.replit` define instalação de dependências e `streamlit run` na porta **5000**, host `0.0.0.0`.  
- Secrets do Replit substituem `.env`.  
- Webview associada à porta publicada.

---

## 13. Limitações conhecidas

1. **Não há coleta automática** de Google/Instagram/etc.; qualidade depende do preenchimento e da IA.  
2. **Um único arquivo CSV** — sem multi-tenant, sem autenticação de usuários finais.  
3. **Streamlit** — escalabilidade e UX muito avançadas podem exigir evolução arquitetural (API + front + banco).  
4. **Export HTML** depende de CDN Plotly para o gráfico interativo.  
5. **Custos variáveis:** uso de tokens OpenAI e quotas AgentMail.

---

## 14. Evoluções sugeridas (roadmap técnico)

- Integração **Google Places / Business** (API oficial) para enriquecer dados com consentimento e termos de uso.  
- Backend de **autenticação** e **multi-tenant** (agência / governo) com banco relacional.  
- Histórico mensal e **comparativo de scores**.  
- Geração opcional de **PDF server-side** (biblioteca dedicada).  
- Testes automatizados (`pytest`) para `normalize_result` e sanitização de CSV.

---

## 15. Responsabilidade e conformidade

- O formulário inclui **opt-in** explícito para contato; armazenar e processar dados pessoais deve observar a **LGPD** e políticas internas da IAExpertise.  
- O texto da aplicação reforça **não solicitar senhas** nem acesso a contas privadas; manter consistência em materiais comerciais e contratos.

---

## 16. Contato técnico do documento

Para atualizar este documento junto com o código: manter alinhamento entre `SYSTEM_PROMPT`, colunas de `save_lead_csv` e campos do formulário em `app.py`.

*Documento gerado para apoio a desenvolvimento, operação e propostas comerciais. Última revisão: conforme estado atual do repositório (`app.py` monolítico).*
