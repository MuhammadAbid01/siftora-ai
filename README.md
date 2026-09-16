# Siftora

**Agentic Lead Intelligence Platform** — researches companies, verifies
evidence, qualifies prospects, drafts personalized outreach, and requires
human approval before any external action. See [`plan.md`](./plan.md) for
the full product plan and `specs/phase-{1..5}-*.md` for what each phase
implements.

All five phases are implemented in this codebase:

1. **Foundation** — landing page, Supabase auth, protected dashboard.
2. **Campaigns** — natural-language brief → ICP → search plan → approval.
3. **Research** — a LangGraph agent searches, extracts, analyzes, scores,
   and deduplicates candidates into evidence-backed leads.
4. **Outreach** — grounded email/LinkedIn drafts, quality checks, a human
   approval queue, suppression, and CSV export.
5. **Hardening** — a deterministic evaluation harness, rate limiting,
   SSRF/prompt-injection defenses, per-campaign analytics, health/readiness
   checks, and a demo-reset action.

Every external provider (LLM, search, extraction, email) defaults to a
deterministic, zero-cost **fixture** adapter — the whole pipeline runs
end-to-end with no API keys and no real Supabase project (see
[`docs/providers.md`](./docs/providers.md)). Real credentials are opt-in.

## Repository layout

```
frontend/    Next.js 16 (App Router) + TypeScript + Tailwind CSS
backend/     FastAPI + Python 3.12+
supabase/    SQL migrations and seed data
specs/       Phase specifications (the source of truth for what's built)
docs/        Architecture, security review, and provider adapter notes
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- A Supabase project (free tier is fine) — needed for real auth/data; the
  frontend build and the entire backend test suite run without one, using
  the fixture providers and an in-memory fake Supabase client.

## Quick start (fixture mode, no external accounts)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; .venv\Scripts\activate.bat for cmd
pip install -r requirements-dev.txt
cp .env.example .env            # defaults are all fixture/disabled — no keys needed to test
pytest                          # the full suite runs against fixtures + a fake Supabase client
uvicorn app.main:app --reload   # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env.local      # fill in your Supabase project URL + anon key to actually sign in
npm run dev                     # http://localhost:3000
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

Backend quality commands:

```bash
ruff format --check .
ruff check .
pytest
```

**Playwright E2E**: the landing-page and protected-route-redirect specs run
without a live Supabase project. `auth-flow`, `campaign-flow`,
`research-flow`, and `outreach-flow` all exercise real Supabase Auth plus
the FastAPI backend's endpoints (fixture providers, so no other credentials
are needed) and are skipped unless you set `E2E_SUPABASE_LIVE=1` with a real
project configured in `.env.local`.

## Supabase setup (for real auth/data)

1. Create a Supabase project.
2. Apply the migrations in order — `0001_init.sql` through
   `0004_outreach.sql` (via the Supabase SQL editor, the Supabase CLI's
   `supabase db push`, or `supabase db reset` for a local dev project) —
   then `supabase/seed.sql`. Phase 5 added no new migration (see
   `docs/architecture.md`, "Why Phase 5 needed no new migration").
3. Copy the project URL + anon key into `frontend/.env.local`, and the
   project URL + service role key + JWT secret into `backend/.env`. The JWT
   secret is under Project Settings → API → JWT Settings (legacy HS256
   secret).
4. Sign up through the running frontend — a matching `profiles` row is
   created automatically by a database trigger, with `role = 'user'`.
5. **Optional — admin access.** `POST /api/evals/run` (the evaluation
   harness) requires an admin account. Promote one via the Supabase SQL
   editor: `update public.profiles set role = 'admin' where id =
   '<user-id>';` — there is no self-service admin sign-up (see
   `docs/security.md`).

See [`docs/architecture.md`](./docs/architecture.md) for the full system
diagram and how to manually verify Row Level Security once you have a
project.

## Enabling real providers (optional)

Every provider defaults to a fixture/disabled adapter. To use real ones, set
in `backend/.env`:

```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free  # optional; this is the default
OPENROUTER_TIMEOUT_SECONDS=180  # optional; free-tier models can take minutes
OPENROUTER_DISABLE_REASONING=true  # optional; default. ~6x faster planning

SEARCH_PROVIDER=tavily
TAVILY_API_KEY=...

EXTRACTION_PROVIDER=firecrawl
FIRECRAWL_API_KEY=...

EMAIL_MODE=sandbox   # or "live" + RESEND_API_KEY for real delivery
RESEND_API_KEY=...
```

`docs/providers.md` documents exactly what's mocked, sandboxed, or live for
each adapter, and what's actually been verified against real credentials
versus reviewed for correctness only.

## Demo script

A short, honest walkthrough of the whole pipeline in fixture mode (no
credentials needed):

1. Sign up, land on the dashboard.
2. **New campaign** → brief: *"Find design agencies and animation studios
   in Dubai, UAE."* → **Generate plan** → review the ICP and search plan →
   **Confirm plan** → **Start run**.
3. Watch the run progress panel and event timeline update live, then open
   **View leads** — you'll see a mix of `qualified`, `needs_review`, and
   `rejected` leads, each with real evidence (facts/inferences/unknowns,
   each with a source) and a full score breakdown.
4. Open a `qualified` lead → **Generate email draft** → the draft is
   grounded in one of that lead's own evidence items. Edit it, then
   **Approve**.
5. Back on the campaign page, **Export approved (CSV)** downloads the
   approved draft.
6. Visit **Approvals** to see the cross-campaign queue, and **Analytics**
   (on the campaign page) for the funnel/cost/latency/failure summary.
7. **Evaluation** (nav link) requires an admin account (see above) —
   **Run evaluations** exercises the six deterministic categories and
   reports a pass rate per category.
8. **Reset demo data** (dashboard) deletes everything this account owns, for
   a clean slate before the next visitor.

## What's mocked, sandboxed, or live

- **Mocked (default, zero cost):** LLM, search, extraction, and email all
  default to deterministic fixture/disabled adapters. No network calls, no
  credentials required.
- **Sandboxed:** `EMAIL_MODE=sandbox` simulates a send with no network call
  — for demoing the "would have sent" path without a real Resend account.
- **Live (opt-in, real cost/effect):** setting real credentials switches
  each provider to its real adapter. `TavilySearchProvider` and
  `FirecrawlExtractionProvider` have been verified live against real
  credentials; `OpenRouterLanguageModelProvider` (default model is
  free-tier) and `ResendEmailProvider` have been reviewed for correctness
  but not exercised live in this development environment. See
  `docs/providers.md` for the full breakdown.

## Security

See [`docs/security.md`](./docs/security.md) for the full review: RLS +
ownership checks, SSRF/URL validation, prompt-injection defenses, rate
limiting, admin gating, and where secrets live. One real finding from that
review — unrelated to this codebase, in the local git configuration of the
environment this was developed in — is documented there rather than fixed
automatically, per this project's git-safety rules.

## Deployment (not performed here)

The intended production stack is Vercel (frontend) + Railway/Render
(backend) + Supabase (database/auth) — see `plan.md` §5. This repository
ships deployment-ready pieces (health/readiness endpoints, environment-
variable-driven configuration, no hardcoded local URLs) but no deployment
CLI or account is connected in this development environment, so an actual
deployment has not been executed. To deploy:

1. **Supabase**: create a project, apply migrations `0001`–`0004` and the
   seed file, note the project URL/anon key/service role key/JWT secret.
2. **Backend (Railway/Render)**: deploy `backend/` as a Python service
   (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`), set the env vars
   from `backend/.env.example`, and confirm `GET /api/health` and
   `GET /api/health/ready` both return 200 post-deploy.
3. **Frontend (Vercel)**: deploy `frontend/`, set
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and
   `NEXT_PUBLIC_API_BASE_URL` (pointing at the deployed backend), and set
   `CORS_ALLOWED_ORIGINS` on the backend to the deployed frontend's origin.
4. Sign up through the deployed frontend and run through the demo script
   above against production.

## Screenshots

Not included in this repository — producing real ones requires running the
app against a live Supabase project, which wasn't done in this development
environment for this phase (see `specs/phase-5-hardening.md`, Non-goals).
Follow the demo script above against your own project to capture them.
