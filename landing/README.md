# Landing page — Bússola Inteligente

HTML estático para SEO (Google) e indexação. O app Streamlit fica em outro host.

## Deploy rápido

### Vercel
1. Importe o repositório.
2. **Root Directory:** `landing`
3. Deploy. Aponte `www.seudominio.com.br` ao projeto.

### Cloudflare Pages
1. Conecte o GitHub.
2. **Build output directory:** `landing` (ou copie arquivos para raiz do site).

## Após registrar o domínio

1. Substitua `https://www.bussolainteligente.com.br` em `index.html` (canonical, og:url), `sitemap.xml` e `robots.txt`.
2. Atualize os links **Ver preview grátis** para `https://app.seudominio.com.br/` (ou defina `BUSSOLA_APP_URL` no Railway).
3. No Railway (Streamlit), configure `BUSSOLA_LP_URL` e `BUSSOLA_APP_URL`.

## Arquivos

- `index.html` — página principal
- `robots.txt` / `sitemap.xml` — SEO
