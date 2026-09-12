# Phase 1 — Foundation, Landing, Auth, and Database

Status: Implementation
Owner: Primary coding agent (Claude Code)
Parent document: `plan.md`

---

## 1. Goal, Scope, and Non-Goals

### Goal

Stand up the two-application Siftora foundation — a Next.js/TypeScript frontend
and a FastAPI/Python backend — with a public landing page, Supabase-backed
authentication, an initial database schema with RLS, a protected dashboard
shell, typed API contracts, and the tooling (formatting, linting, type
checking, tests, builds, CI) needed to keep later phases safe to build on.

### Scope

- Next.js 14+ (App Router) + TypeScript (strict) frontend, built with `npm`.
- Tailwind CSS for styling; a small set of hand-built, shadcn-style UI
  primitives (button, input, label, card) — no CLI-fetched component registry
  dependency, to keep the build reproducible offline.
- FastAPI + Python 3.12+ backend, `venv` + `pip` + `requirements.txt`.
- Pydantic v2 models as the authoritative API contract (request + response).
- A small typed `fetch` wrapper on the frontend (no generated API client).
- Supabase Auth (email/password) wired into the frontend (browser + server
  clients) and verified on the backend via JWT.
- Supabase Postgres schema: `profiles` table only (the minimum needed to prove
  ownership + RLS in Phase 1). Other tables from `plan.md` §12 arrive in later
  phases.
- Initial migration(s) + seed data (labeled demo data only) + RLS policies.
- Protected dashboard shell (`/dashboard`) that requires a session and shows
  the signed-in user's profile.
- Sign up / sign in / sign out / session restoration.
- Environment variable validation on both frontend and backend (fail fast on
  missing/invalid config).
- Formatting/linting/type-checking/tests/build tooling for both apps.
- Optional GitHub Actions CI running frontend npm checks and backend Ruff +
  pytest checks only.
- Root README documenting setup and the documented run commands.

### Non-goals (Phase 1)

- Campaigns, ICP, planning, LangGraph agent, scoring, research, outreach,
  approvals, export, evaluation, or analytics (Phases 2–5).
- Docker, a distributed job system, workspace/monorepo orchestration
  (Turborepo/Nx), or automatic API-client generation.
- Real search/extraction/LLM/email provider integrations — none are needed in
  Phase 1, so no provider adapters are built yet.
- Admin role UI/permissions beyond the `profiles.role` column existing.
- Password-reset email delivery customization beyond Supabase's default flow.
- Full design system — Phase 1 ships a clean, accessible, honestly-labeled
  landing page and dashboard shell, not final visual polish.

---

## 2. Functional Requirements

### Landing page (`/`)

- FR-1: Sticky navigation with logo, nav links, and Sign in / Start Campaign
  CTAs.
- FR-2: Hero section with product pitch, "Start Campaign" (→ `/sign-up`) and
  "View Demo" (→ demo section anchor) CTAs.
- FR-3: Product mockup section using visibly labeled demo data (e.g. a
  "Demo data" badge) — no fake logos, testimonials, or revenue claims.
- FR-4: Workflow section: define ICP → research → verify/score → approve.
- FR-5: "Why agentic" explanation section.
- FR-6: Features/use-cases section.
- FR-7: Seeded lead example showing evidence + score, labeled as demo data.
- FR-8: Responsible-outreach section describing approval-gating and
  compliance posture.
- FR-9: Technology section listing the real stack from `plan.md` §5.
- FR-10: Footer with GitHub link, Privacy, Terms, and a final CTA.
- FR-11: Mobile navigation menu that opens/closes and exposes the same links.
- FR-12: Page metadata: title, description, Open Graph tags, favicon,
  `sitemap.xml`, `robots.txt`.

### Authentication

- FR-13: `/sign-up` — email + password form (Zod-validated), creates a
  Supabase Auth user, creates a matching `profiles` row, redirects to
  `/dashboard`.
- FR-14: `/sign-in` — email + password form, redirects to `/dashboard` on
  success, shows inline error on failure.
- FR-15: `/reset-password` — request a reset email via Supabase; a
  `/update-password` route to set a new password from the reset link.
- FR-16: Sign-out action clears the session and redirects to `/`.
- FR-17: Session persists across reload (server-verified via cookies) and is
  restored on next visit without re-login.
- FR-18: Unauthenticated access to `/dashboard/**` redirects to `/sign-in`
  with a return-to URL.
- FR-19: A signed-in user only ever sees/affects their own `profiles` row —
  enforced by RLS, not just UI.

### Dashboard shell

- FR-20: `/dashboard` shows the signed-in user's email and profile
  (labeled placeholder for future campaign summary), plus a sign-out control.
- FR-21: Dashboard has a minimal shared layout (nav/sidebar shell) that later
  phases will extend — no campaign-specific UI yet.
- FR-22: Loading, empty, and error states are implemented for the profile
  fetch on the dashboard (per `plan.md` §14 state requirement, scoped to what
  Phase 1 actually fetches).

### Backend API

- FR-23: `GET /api/health` returns service status, no auth required.
- FR-24: `GET /api/me` returns the authenticated user's profile (Pydantic
  response model), 401 if unauthenticated, validated against Supabase JWT.
- FR-25: All backend responses are defined by Pydantic models; validation
  errors return a consistent structured error shape.
- FR-26: Backend fails fast at startup if required environment variables are
  missing or malformed (via a Pydantic Settings model).
- FR-27: CORS restricts allowed origins to the configured frontend URL(s).

### Environment & tooling

- FR-28: Frontend validates required `NEXT_PUBLIC_*` and server-only env vars
  at startup/build via a small typed schema (Zod), failing with a clear error.
- FR-29: `.env.example` lists every variable Phase 1 needs (subset of
  `plan.md` §22) with no real secrets.
- FR-30: Root README documents install, env setup, run, and quality-check
  commands for both apps, run independently, no containers required.

---

## 3. Technical Design

### Repository layout (Phase 1 slice of `plan.md` §6)

```text
siftora/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                 # landing page
│   │   │   ├── sitemap.ts
│   │   │   ├── robots.ts
│   │   │   ├── (auth)/
│   │   │   │   ├── sign-in/page.tsx
│   │   │   │   ├── sign-up/page.tsx
│   │   │   │   ├── reset-password/page.tsx
│   │   │   │   └── update-password/page.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── layout.tsx           # server-side auth guard
│   │   │   │   └── page.tsx
│   │   │   └── auth/callback/route.ts   # Supabase auth code exchange
│   │   ├── components/
│   │   │   ├── ui/                      # button, input, label, card
│   │   │   ├── landing/                 # section components
│   │   │   └── dashboard/
│   │   ├── lib/
│   │   │   ├── env.ts                   # Zod-validated env
│   │   │   ├── api-client.ts            # typed fetch wrapper
│   │   │   ├── supabase/
│   │   │   │   ├── client.ts            # browser client
│   │   │   │   ├── server.ts            # server component/action client
│   │   │   │   └── proxy.ts             # session refresh helper
│   │   │   └── types/api.ts             # types mirroring backend Pydantic
│   │   └── proxy.ts                     # route protection + session refresh
│   │                                    # (Next.js 16 renamed `middleware.ts`
│   │                                    #  to `proxy.ts`; same semantics)
│   ├── e2e/                             # Playwright specs
│   ├── public/
│   ├── .env.example
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── vitest.config.ts
│   ├── playwright.config.ts
│   └── .eslintrc / eslint.config.mjs
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app, CORS, routers
│   │   ├── config.py                    # Pydantic Settings
│   │   ├── schemas.py                   # Pydantic request/response models
│   │   ├── deps.py                      # auth dependency (verify Supabase JWT)
│   │   ├── supabase_client.py           # Supabase client factory
│   │   └── routers/
│   │       ├── health.py
│   │       └── me.py
│   ├── tests/
│   │   ├── test_health.py
│   │   └── test_me.py
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml                   # Ruff + pytest config
│   └── README.md
├── supabase/
│   ├── migrations/
│   │   └── 0001_init.sql                # profiles table + RLS + trigger
│   └── seed.sql                         # labeled demo profile note
├── specs/
│   └── phase-1-foundation.md
├── docs/
│   └── architecture.md
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── plan.md
└── README.md
```

### Frontend

- Next.js App Router, TypeScript `strict: true`, no `any` in new code.
- Tailwind CSS for styling. UI primitives in `components/ui/` are hand-written
  (function components + `class-variance-authority`-style variants or plain
  conditional classes) following shadcn/ui conventions, avoiding the shadcn
  CLI's registry fetch so the build has no extra network dependency.
- `lib/env.ts`: a Zod schema parsed once at module load from
  `process.env`, throwing a descriptive error if required vars are missing.
  Exposes a typed `env` object; nothing else in the app reads `process.env`
  directly.
- `lib/api-client.ts`: a small typed `fetch` wrapper:
  - `apiGet<T>(path, schema)`, `apiPost<T>(path, body, schema)` style helpers,
    or a single `apiRequest<T>()` — attaches the Supabase access token as
    `Authorization: Bearer <token>` when present, parses JSON, validates the
    shape against a Zod schema mirroring the backend Pydantic model, and
    throws a typed `ApiError` on non-2xx or schema mismatch.
  - No code generation — response Zod schemas are hand-written next to the
    TypeScript types in `lib/types/api.ts`, matching `backend/app/schemas.py`
    field-for-field. This pairing is documented so future phases keep them in
    sync manually.
- Supabase auth:
  - `lib/supabase/client.ts` — browser client (`createBrowserClient` from
    `@supabase/ssr`) using `NEXT_PUBLIC_SUPABASE_URL` /
    `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
  - `lib/supabase/server.ts` — server client for Server Components/Actions
    using the request's cookies (Next.js 16: `cookies()` is async).
  - `proxy.ts` (Next.js 16's renamed `middleware.ts`; same request/response
    semantics, exported function is `proxy` instead of `middleware`) —
    refreshes the Supabase session cookie on every request and redirects
    unauthenticated requests to `/dashboard/**` to `/sign-in`.
  - `app/dashboard/layout.tsx` additionally re-checks the session
    server-side (defense in depth beyond middleware) before rendering.
- Forms (`sign-up`, `sign-in`, `reset-password`, `update-password`) use
  `react-hook-form` + `zod` for client-side validation.

### Backend

- FastAPI app in `app/main.py`; routers mounted under `/api`.
- `app/config.py`: `Settings(BaseSettings)` (pydantic-settings) reads
  `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`,
  `CORS_ALLOWED_ORIGINS`, `APP_ENV`; validated at import time so the app
  refuses to start with missing/invalid config. `.env` loaded via
  `python-dotenv`/pydantic-settings for local dev only.
- `app/schemas.py`: `HealthResponse`, `ProfileResponse`, `ErrorResponse`
  (Pydantic v2, `model_config = ConfigDict(extra="forbid")` on responses).
- `app/deps.py`: `get_current_user` dependency — decodes/verifies the
  Supabase-issued JWT from the `Authorization` header (using the Supabase JWT
  secret, `python-jose` or `PyJWT`), raises `401` via a typed
  `HTTPException` with a Pydantic-shaped error body on failure.
- `app/supabase_client.py`: a thin factory returning a `supabase-py` client
  configured with the service role key, used server-side only, kept behind a
  small interface (`get_supabase_admin_client()`) so later phases/tests can
  substitute a fake.
- `routers/health.py`: `GET /api/health` → `HealthResponse{status, version}`,
  no auth.
- `routers/me.py`: `GET /api/me` → `ProfileResponse`, requires
  `get_current_user`, reads the `profiles` row by user id via the admin
  client (service role, but scoped to the authenticated user's own id in the
  query — RLS still protects direct DB access from any other path).
- CORS middleware restricts origins to `CORS_ALLOWED_ORIGINS` (parsed list),
  Phase 1 default `http://localhost:3000`.

### Database (Supabase Postgres)

`supabase/migrations/0001_init.sql`:

- `profiles` table: `id uuid primary key references auth.users(id) on delete cascade`,
  `email text not null`, `role text not null default 'user' check (role in ('user','admin'))`,
  `created_at timestamptz not null default now()`, `updated_at timestamptz not null default now()`.
- `updated_at` trigger.
- A trigger on `auth.users` (`handle_new_user`) that inserts a `profiles` row
  automatically on sign-up, so FR-13 doesn't race the client.
- RLS enabled on `profiles`; policies: a user may `select`/`update` only the
  row where `id = auth.uid()`. No `insert`/`delete` policy for regular users
  (handled by the trigger / cascade).
- `supabase/seed.sql`: inserts a note-only comment; Phase 1 does not seed a
  fake auth user (Supabase Auth users can't be created via plain SQL insert
  safely) — demo/day-one seeding of `profiles` beyond the trigger is deferred
  to when campaigns exist. This is called out explicitly in Risks (§8).

### Environment variables (Phase 1 subset of `plan.md` §22)

Frontend (`frontend/.env.example`):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=
```

Backend (`backend/.env.example`):
```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
CORS_ALLOWED_ORIGINS=http://localhost:3000
APP_ENV=development
```

Root `.env.example` aggregates both with comments pointing to each app's env
file. No secrets committed; `.gitignore` excludes `.env`, `.env.local`, and
`.venv/`.

### CI

`.github/workflows/ci.yml` — two jobs, both trigger on push/PR:

- `frontend`: `npm ci`, Prettier check, ESLint, `tsc --noEmit`, Vitest,
  Next.js build. (Playwright E2E excluded from CI in Phase 1 — it needs a
  live Supabase project; documented as a local/manual step.)
- `backend`: create venv, `pip install -r requirements.txt -r requirements-dev.txt`,
  `ruff format --check`, `ruff check`, `pytest`.

No deployment step in Phase 1.

---

## 4. Routes, Components, and Data/Auth Changes

### Frontend routes

| Route | Type | Auth | Notes |
| --- | --- | --- | --- |
| `/` | page | public | Landing page |
| `/sign-up` | page | public | Redirects to `/dashboard` if already signed in |
| `/sign-in` | page | public | Same redirect behavior |
| `/reset-password` | page | public | Request reset email |
| `/update-password` | page | public (requires reset token) | Set new password |
| `/auth/callback` | route handler | public | Exchanges Supabase auth code for a session |
| `/dashboard` | page | protected | Profile summary + sign-out |
| `/sitemap.xml`, `/robots.txt` | generated | public | SEO |

### Key components

- `components/landing/{Nav,Hero,ProductMockup,Workflow,WhyAgentic,Features,SeededLeadExample,ResponsibleOutreach,TechStack,Footer}.tsx`
- `components/ui/{button,input,label,card,badge}.tsx`
- `components/dashboard/{DashboardNav,ProfileCard}.tsx`
- `components/auth/{SignUpForm,SignInForm,ResetPasswordForm,UpdatePasswordForm}.tsx`

### Data/auth changes

- New Supabase project schema: `profiles` table + RLS + `handle_new_user`
  trigger (migration `0001_init.sql`).
- New backend endpoints: `GET /api/health`, `GET /api/me`.
- New frontend auth flows backed by Supabase Auth (email/password provider).
- No changes to any table beyond `profiles` in Phase 1.

---

## 5. Ordered Implementation Checklist

1. [x] Write this specification (`specs/phase-1-foundation.md`).
2. [x] Root scaffolding: `.gitignore`, root `.env.example`, `README.md`, `docs/architecture.md`.
3. [x] Scaffold `frontend/` with Next.js + TypeScript (strict) + Tailwind via `create-next-app`.
4. [x] Add frontend dev tooling: Prettier, ESLint config, Vitest + Testing Library, Playwright.
5. [x] Add `lib/env.ts` (Zod env validation) and `frontend/.env.example`.
6. [x] Add hand-built UI primitives in `components/ui/`.
7. [x] Build landing page sections and compose `app/page.tsx`; add metadata, OG, favicon, sitemap, robots.
8. [x] Add Supabase client helpers (`lib/supabase/{client,server}.ts`) and `@supabase/ssr` dependency.
9. [x] Add `proxy.ts` (Next.js 16 `middleware` replacement) for session refresh + protected-route redirect.
10. [x] Build auth pages (`sign-up`, `sign-in`, `reset-password`, `update-password`) with `react-hook-form` + Zod.
11. [x] Build `app/auth/callback/route.ts`.
12. [x] Build protected `app/dashboard/{layout,page}.tsx` with server-side session check.
13. [x] Add `lib/types/api.ts` + `lib/api-client.ts` typed fetch wrapper.
14. [x] Scaffold `backend/` venv, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` (Ruff + pytest config).
15. [x] Implement `app/config.py` (Pydantic Settings) with fail-fast validation.
16. [x] Implement `app/schemas.py` response/error models.
17. [x] Implement `app/supabase_client.py` and `app/deps.py` (JWT auth dependency).
18. [x] Implement `routers/health.py` and `routers/me.py`; wire into `main.py` with CORS.
19. [x] Write backend tests (`tests/test_health.py`, `tests/test_me.py`) with a fake/mocked Supabase client and a signed test JWT.
20. [x] Write Supabase migration `0001_init.sql` (profiles + RLS + trigger) and `seed.sql`.
21. [x] Write frontend unit tests (Vitest) for `env.ts`, `api-client.ts`, and at least one component.
22. [x] Write Playwright E2E specs: landing CTA navigation, sign-up→dashboard, protected-route redirect, sign-out.
23. [x] Write root `README.md` with install/run/test commands for both apps, and Supabase setup steps.
24. [x] Add `.github/workflows/ci.yml`.
25. [x] Run all frontend and backend quality commands; fix failures.
26. [x] Re-review every acceptance criterion in §6 and testing item in §7; fix gaps.

---

## 6. Acceptance Criteria

Directly from `plan.md` §15, scoped to what Phase 1 builds:

- AC-1: Fresh clone installs and builds through documented commands (no
  undocumented manual steps).
- AC-2: Root URL (`/`) shows the public landing page.
- AC-3: Navigation, mobile menu, and CTAs work (verified via Playwright).
- AC-4: Demo mockups are visibly labeled as demo data; landing copy makes no
  false claims.
- AC-5: A user can sign up, sign in, sign out, and have their session restored
  on reload.
- AC-6: Protected routes (`/dashboard/**`) reject unauthenticated access
  (redirect to `/sign-in`).
- AC-7: User A cannot access User B's `profiles` row (enforced by RLS; not
  just UI-hidden).
- AC-8: The database rebuilds from migrations + seed data
  (`supabase db reset` applies `0001_init.sql` and `seed.sql` cleanly).
- AC-9: Documented commands start the frontend and backend separately,
  without containers.
- AC-10: FastAPI exposes a health endpoint (`GET /api/health`).
- AC-11: Frontend API calls match the documented Pydantic responses (Zod
  schemas mirror `schemas.py` and are exercised by `GET /api/me` on the
  dashboard).
- AC-12: CI (if present) runs only npm frontend checks and backend
  Ruff/pytest checks — no deployment, no Phase 2+ checks.
- AC-13: No Phase 2+ feature (campaigns, ICP, research, scoring, outreach) is
  implemented.

### Verification status (end of Phase 1 implementation)

- **Met and verified:** AC-1 (build succeeds from a clean `npm install` /
  `pip install`), AC-2, AC-3, AC-4, AC-6 (Playwright), AC-9, AC-10, AC-11
  (`/api/me` exercised by both pytest and the dashboard page), AC-12, AC-13.
- **Implemented, not end-to-end verified (no live Supabase project in this
  environment):** AC-5 (sign-up/in/out code paths are complete and unit/E2E
  scaffolding exists, but never run against real Supabase Auth), AC-7 (RLS
  policies are written and reviewed, not exercised against a real database),
  AC-8 (`0001_init.sql`/`seed.sql` reviewed for correctness, not run through
  `supabase db reset`). See §8 Risks for why, and `docs/architecture.md` for
  the manual verification steps a developer with real credentials should run.

---

## 7. Testing Checklist

### Frontend

- [x] `npm run format:check` (Prettier) passes.
- [x] `npm run lint` (ESLint) passes.
- [x] `npm run typecheck` (`tsc --noEmit`) passes.
- [x] `npm run test` (Vitest) passes — 13 tests: env validation (2), api-client success/error paths (4), Nav component (2), auth Zod schemas (5).
- [x] `npm run build` (Next.js production build) succeeds.
- [x] `npm run test:e2e` (Playwright) — 5 of 6 specs pass locally (landing CTAs/mobile menu, protected-route redirect); the live-Supabase sign-up→dashboard→sign-out spec is explicitly skipped (`E2E_SUPABASE_LIVE` unset) rather than claimed passing, since no real Supabase project is available in this environment.

### Backend

- [x] `ruff format --check .` passes.
- [x] `ruff check .` passes.
- [x] `pytest` passes — 9 tests: health endpoint (2), `/api/me` unauthenticated 401 + invalid token 401 + authenticated 200 (mocked Supabase client + signed test JWT) + no-profile 404 (4), settings validation failure/blank-secret/valid-parse cases (3).

### Manual/documented (not automatable without a live Supabase project)

- [ ] Sign up creates a Supabase Auth user and a matching `profiles` row. **Not verified** — no live Supabase project in this environment. Migration/trigger logic is written and reviewed but unexercised end-to-end.
- [ ] RLS verified: querying `profiles` as user B for user A's row returns no rows (documented SQL check in `docs/architecture.md`). **Not verified** for the same reason.
- [ ] `supabase db reset` applies cleanly. **Not verified** — no Supabase CLI/project linked in this environment; SQL was reviewed manually for syntax correctness only.

---

## 8. Risks and Assumptions

- **Assumption:** No Supabase project credentials are available in this
  environment. Phase 1 code is written to be correct against a real Supabase
  project, but end-to-end auth/RLS verification and Playwright E2E runs that
  require a live Supabase instance cannot be executed here. This is reported
  explicitly rather than claimed as passing.
- **Assumption:** "Environment validation" means fail-fast typed parsing
  (Zod/Pydantic Settings), not a live connectivity check against Supabase at
  boot — connectivity is exercised by the actual endpoints.
- **Risk:** Hand-built UI primitives instead of the shadcn CLI means visual
  conventions must be kept consistent manually; acceptable for Phase 1's
  scope (foundation, not final design polish).
- **Risk:** `GET /api/me` uses the Supabase service-role key server-side to
  look up the profile by the JWT-derived user id. This is safe only because
  the query is always scoped to `auth.uid()` extracted from the verified JWT,
  never to a client-supplied id — this constraint must be preserved in later
  phases.
- **Risk:** No fake auth user can be safely created via `seed.sql` alone
  (Supabase Auth users live outside plain SQL); demo-data seeding for
  `profiles` beyond the sign-up trigger is deferred, so AC-8's "seed data"
  is limited to schema/RLS being reproducible, not a pre-populated demo
  account. Flagged here rather than silently narrowing the acceptance
  criterion.
- **Risk:** Playwright E2E and the live-Supabase manual checks cannot run
  without real credentials; CI excludes Playwright for the same reason. This
  is a scope boundary, not a skipped requirement — it is documented in the
  README so a developer with real credentials can run it.
- **Non-decision needed:** None of the choices above affect security, cost,
  data ownership, or fundamental architecture beyond what `plan.md` already
  specifies, so implementation proceeds without pausing for approval.
