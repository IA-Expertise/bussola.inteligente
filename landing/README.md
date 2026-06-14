# Landing page — Bússola Inteligente

HTML estático (visual claro, vendas) em `index.html`.  
App Streamlit: `https://app.bussolainteligente.com.br/` (Railway).

## Ajustes rápidos

No final de `index.html`, bloco `BUSSOLA_CONFIG`:

- `APP_URL` — URL do app (Streamlit)
- `YOUTUBE_VIDEO_ID` — ID do vídeo YouTube (mesmo de `YOUTUBE_VIDEO_URL` no Railway)

## Deploy no DreamHost

### Opção A — Site na DreamHost (FTP)

1. Painel DreamHost → **Manage Websites** → site `bussolainteligente.com.br`.
2. Abra o diretório **`public_html`** (ou pasta do domínio `www`).
3. Envie **todos** os arquivos de `landing/`:
   - `index.html`
   - `robots.txt`
   - `sitemap.xml`
4. Acesse `https://www.bussolainteligente.com.br/`.

### Opção B — Subdomínio `app` na DreamHost

1. **DNS / Subdomains:** crie `app.bussolainteligente.com.br`.
2. Aponte **CNAME** `app` → URL do Railway (ex.: `bussolainteligente-production.up.railway.app`).
3. No Railway, configure domínio customizado `app.bussolainteligente.com.br`.

### DNS (propagação)

| Registro | Destino |
|----------|---------|
| `www` | Servidor DreamHost (site estático) ou A/CNAME conforme painel |
| `app` | CNAME → Railway (Streamlit) |
| `@` (apex) | Redirecionar para `www` (recomendado) |

## Alternativa: Vercel / Cloudflare Pages

1. Root directory: `landing`
2. CNAME `www` → projeto Vercel/Cloudflare

## SEO

- `robots.txt` e `sitemap.xml` já apontam para `www.bussolainteligente.com.br`
- Após publicar, cadastre o site no [Google Search Console](https://search.google.com/search-console)

## Railway (app)

Variáveis recomendadas:

- `BUSSOLA_LP_URL=https://www.bussolainteligente.com.br`
- `BUSSOLA_APP_URL=https://app.bussolainteligente.com.br/`
- `YOUTUBE_VIDEO_URL=https://www.youtube.com/watch?v=SEU_ID`
