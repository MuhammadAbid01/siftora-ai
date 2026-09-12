# Siftora

Agentic Lead Intelligence Platform — see [`plan.md`](./plan.md) for the full
product plan and [`specs/phase-1-foundation.md`](./specs/phase-1-foundation.md)
for what Phase 1 (this codebase, today) actually implements.

Phase 1 ships: a public landing page, Supabase email/password authentication,
a protected dashboard shell, and a FastAPI backend with a typed contract —
with no campaigns, research, scoring, or outreach yet (that's Phase 2+).

## Repository layout

```
frontend/    Next.js 16 (App Router) + TypeScript + Tailwind CSS
backend/     FastAPI + Python 3.12+
supabase/    SQL migrations and seed data
specs/       Phase specifications
docs/        Architecture notes
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- A Supabase project (free tier is fine) — needed for real auth/data; the
  frontend build and most tests run without one using placeholder values.

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local   # fill in your Supabase project URL + anon key
npm run dev                  # http://localhost:3000
```

Frontend quality commands:

```bash
npm run format:check   # Prettier
npm run lint           # ESLint
npm run typecheck      # tsc --noEmit
npm run test           # Vitest unit tests
npm run build          # Next.js production build
npm run test:e2e       # Playwright — see note below
```

**Playwright E2E**: the landing-page and protected-route-redirect specs run
without a live Supabase project. The full sign-up → dashboard → sign-out spec
(`e2e/auth-flow.spec.ts`) exercises real Supabase Auth and is skipped unless
you set `E2E_SUPABASE_LIVE=1` with a real project configured in
`.env.local`.

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate.bat for cmd
pip install -r requirements-dev.txt
cp .env.example .env            # fill in your Supabase project values
uvicorn app.main:app --reload   # http://localhost:8000
```

Backend quality commands:

```bash
ruff format --check .
ruff check .
pytest
```

## Supabase setup

1. Create a Supabase project.
2. Apply `supabase/migrations/0001_init.sql` (via the Supabase SQL editor, the
   Supabase CLI's `supabase db push`, or `supabase db reset` for a local dev
   project) and then `supabase/seed.sql`.
3. Copy the project URL + anon key into `frontend/.env.local`, and the
   project URL + service role key + JWT secret into `backend/.env`. The JWT
   secret is under Project Settings → API → JWT Settings (legacy HS256
   secret).
4. Sign up through the running frontend — a matching `profiles` row is
   created automatically by a database trigger.

See [`docs/architecture.md`](./docs/architecture.md) for how to manually
verify Row Level Security once you have a project.

## What's not implemented yet

Campaigns, ICP planning, research, scoring, outreach drafting, approvals, and
export are out of scope for Phase 1 — see `plan.md` for the full roadmap.
