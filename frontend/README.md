# Centi Frontend

Centi's frontend rebuilt with **Next.js (App Router)** and **shadcn/ui** to manage newsletters.

## Stack

- Next.js 16 + TypeScript
- Tailwind CSS v4
- shadcn/ui
- Sonner for notifications

## Configuration

1. Copy the example file:

```bash
cp .env.example .env.local
```

2. Update the API URL if needed:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NEXT_PUBLIC_PARLANT_SERVER_URL=http://localhost:8800
NEXT_PUBLIC_PARLANT_AGENT_ID=<centi-agent-id>
```

## Development

```bash
npm install
npm run dev
```

App runs at `http://localhost:3000`.

## Deploy (Render)

Este frontend esta preparado para o servico `centi-frontend` definido no `render.yaml` da raiz.

Variaveis obrigatorias em producao:

```env
NEXT_PUBLIC_API_BASE_URL=https://<api>.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
NEXT_PUBLIC_PARLANT_SERVER_URL=https://<parlant>.onrender.com
NEXT_PUBLIC_PARLANT_AGENT_ID=<centi-agent-id>
```

## Main Screen Features

- List newsletters by `user_id`
- Login/logout with Supabase Auth
- Create newsletters with topics and frequency
- Edit title/email/topics/frequency
- Enable or disable sending
- Generate content with AI
- Send newsletters by email
- Parlant widget (floating chat) with `customerId` from the authenticated Supabase user
