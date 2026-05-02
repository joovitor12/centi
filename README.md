# Centi - AI Assistant with Newsletter Builder

Centi is an assistant powered by [Parlant](https://parlant.ai/) that manages reminders and now supports an AI newsletter builder.

## Features

- Natural language reminder creation
- Appointment listing, editing, and deletion
- Recurring reminders (daily, weekly, monthly, yearly)
- Newsletter Builder with up to 5 themes
- Theme defaults (videogames, tecnologia, esportes)
- Newsletter generation using Agno
- Newsletter email delivery with Resend
- Scheduled delivery (daily, weekly, every N days)
- Persistence in Supabase

## Requirements

- Python 3.10+
- OpenAI API key
- Supabase project
- Resend API key

## Setup

1. Install dependencies:

```bash
uv sync
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. Configure `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=newsletter@your-domain.com
AGNO_MODEL_ID=gpt-5.4-mini
```

4. Run the chatbot:

```bash
uv run python main.py
```

5. Run API for frontend newsletter management:

```bash
uv run python run_api.py
```

6. Run newsletter scheduler worker:

```bash
uv run python run_newsletter_worker.py

## Deploy no Render

O repositório inclui `render.yaml` com 3 serviços:

- `centi-frontend` (Web Service Next.js)
- `centi-api` (Web Service FastAPI com `run_api.py`)
- `centi-parlant` (Web Service com `run_production.py`)

### Como subir

1. No Render, crie um **Blueprint** apontando para este repositório.
2. O Render vai ler o `render.yaml` e criar os 3 serviços.
3. Configure as variáveis `sync: false` no painel do Render.

### Variáveis principais

- No `centi-api`:
  - `CORS_ALLOW_ORIGINS=https://<frontend>.onrender.com`
  - `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
  - `RESEND_API_KEY`, `RESEND_FROM_EMAIL`
- No `centi-parlant`:
  - `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
  - `AGNO_MODEL_ID` (opcional)
- No `centi-frontend`:
  - `NEXT_PUBLIC_API_BASE_URL=https://<api>.onrender.com`
  - `NEXT_PUBLIC_PARLANT_SERVER_URL=https://<parlant>.onrender.com` (ou URL interna, se aplicável)
  - `NEXT_PUBLIC_PARLANT_AGENT_ID=<agent-id>`
  - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Comandos de runtime usados

- API: `uv run python run_api.py`
- Parlant: `uv run python run_production.py`
```

## Project Structure

```text
centi/
├── main.py
├── run_production.py
├── run_api.py
├── run_newsletter_worker.py
├── app/
│   ├── agent/
│   ├── api/
│   ├── config/
│   ├── services/
│   ├── tools/
│   └── workers/
└── alembic/
```

## Notes

- Newsletter management is available via Parlant tools and HTTP API.
- Apply Alembic migration `create_newsletters_table` before using the feature.
