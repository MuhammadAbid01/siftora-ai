# Architecture

See `plan.md` for the full product architecture and `specs/phase-{1..5}-*.md`
for what each phase actually implements. This document covers the system as
it exists after Phase 5.

## Overview

Two independent applications, no containers:

- **frontend/** — Next.js 16 (App Router) + TypeScript, Tailwind CSS. Talks
  to Supabase Auth directly from the browser/server for sign-up/in/out and
  session management, and to the FastAPI backend for all application data.
- **backend/** — FastAPI + Python 3.12+. Verifies the Supabase-issued JWT on
  each request and reads/writes Supabase Postgres using the service role
  key, always scoped to the authenticated user's id (never a client-supplied
  one — see `docs/security.md`).
- **supabase/** — SQL migrations (`0001` foundation/auth through `0004`
  outreach/approvals — no new migration was needed for Phase 5, see below)
  and seed data.

```
Browser ──(Supabase Auth: sign up/in/out, session cookies)──> Supabase Auth
Browser ──(Next.js pages, Server Components)──> Next.js server
Next.js server / browser ──(REST, Bearer JWT)──> FastAPI backend
FastAPI backend ──(service role key, scoped to auth.uid())──> Supabase Postgres
FastAPI backend ──(LLM/search/extraction/email calls)──> External providers
                     (fixture by default — see docs/providers.md)
```

## The research → outreach pipeline

```
Campaign brief
      │  generate_campaign_plan (LanguageModelProvider)
      ▼
ICP + search plan ──(user confirms)──> plan_approved
      │  POST /campaigns/:id/run — starts a LangGraph research run
      ▼
┌─────────────────────────── app/agent.py's graph ───────────────────────────┐
│ search_companies ──> expand_source ──> normalize_and_dedupe               │
│      (SearchProvider)   (app/discovery.py denylist +                      │
│                          WebsiteExtractionProvider +                      │
│                          LanguageModelProvider                            │
│                          .extract_companies_from_page)                    │
│                              │              (normalize_domain)            │
│                              ▼                     │                      │
│                   a search hit is a SOURCE,        ▼                      │
│                   never a lead — see below   analyze_candidate            │
│                                                 (URL-safety gate ──>      │
│                                                   WebsiteExtractionProvider │
│                                                   ──> LanguageModelProvider │
│                                                       .analyze_company)     │
│                                  │                                          │
│                                  ▼                                          │
│                          validate_evidence (has_sufficient_evidence)        │
│                                  │                                          │
│                                  ▼                                          │
│                 score_candidate (scoring.compute_score, pure)              │
│                                  │                                          │
│                                  ▼                                          │
│                    decide_qualification ──> persist_lead                   │
│                                  │                                          │
│                    (route_next re-checks pause/budget/target/queries       │
│                     between every candidate) ──> complete_run              │
└──────────────────────────────────────────────────────────────────────────┘

### Why `expand_source` exists

A web search result is a *page on which companies may be mentioned*, not a
company. Treating each result as a lead — using its page title as the
company name and its URL's host as the company domain — produced leads
like "Top 15+ Animation Studios In Dubai (2026)" on `edvido.com` and
"What are the top-rated animation studios in the UAE? - Quora", while the
actual agencies listed inside those pages were never captured at all.

`expand_source` is the step that turns sources into companies:

| Source page | Outcome |
| --- | --- |
| Reference/directory/social/news host (`wikipedia.org`, `clutch.co`, `quora.com`, `instagram.com`, ...) | **Never a lead.** Mined for the companies it names; cited as their evidence source. |
| Listicle / roundup / "top N" page | **Never a lead.** Each company named inside becomes its own candidate, with the listicle recorded as provenance evidence. |
| A company's own website | One candidate, named from the page *content* — not from its SEO title. |

Two independent gates decide this, and both must pass before a lead exists:

1. **`app/discovery.py`** (deterministic): a host denylist, a listicle
   heuristic, and `is_valid_company_name`, which rejects page titles,
   questions, bare domains, platform brands and generic navigation labels.
2. **`LanguageModelProvider.extract_companies_from_page`** (probabilistic):
   reads the page and names the businesses on it, classifying the page as
   `company_site`, `listing` or `other`.

Three further invariants hold regardless of any denylist, each added after a
real run violated it:

* **A company's website is never on the source page's own site.** Directory
  and quote pages link to internal profile pages
  (`investing.com/equities/attock-refiner`); taking those at face value made
  the aggregator the lead's domain. `discovery.same_site` also collapses
  country front-ends, so `investing.com` and `uk.investing.com` are one site.
* **Dedup is by company name as well as domain.** The same business reached
  through two front-ends resolved to two hosts and became two leads. The
  name key strips punctuation and legal suffixes (Ltd/LLC/Pvt/Co.), and the
  check runs *before* a domain lookup is spent.
* **Login-walled hosts are never fetched.** Facebook groups, Scribd
  documents and the like return nothing to a scraper, so they are skipped
  before an extraction call is paid for rather than after.

A transient provider failure (502, timeout, rate limit) is retried with
backoff instead of rejecting the candidate — a company must not lose its
lead because the model had a bad minute. Only a genuinely unusable response
falls through to `analysis_failed`, and that is still recorded as a visible
lead rather than dropped.

A lead's identity therefore always comes from an entity named in page
content. A company whose name cannot be established is dropped with a
logged reason rather than being given a guessed one, and a company found
via several sources is merged into one lead carrying each source as
separate evidence.

      │  qualified lead, evidence, score breakdown all persisted
      ▼
POST /leads/:id/regenerate-outreach (user-triggered, not automatic)
      │  LanguageModelProvider.draft_outreach ──> outreach.assemble_body
      │  ──> outreach.check_quality (pure — grounding/length/blocklist)
      ▼
outreach_drafts + approvals (pending) ──(human edits/approves/rejects)──> approved
      │
      ▼
POST /campaigns/:id/export (CSV, approved + unsuppressed only)
```

Every arrow into a `LanguageModelProvider`/`SearchProvider`/
`WebsiteExtractionProvider`/`EmailProvider` box goes through a factory
(`get_language_model_provider()`, etc., all in `app/providers.py`) — nothing
in `app/agent.py`, `app/scoring.py`, or `app/outreach.py` imports a vendor
SDK directly. See `docs/providers.md` for the fixture/real adapter split.

## Why a proxy (`src/proxy.ts`) and a layout guard both check auth

Next.js 16 renamed `middleware.ts` to `proxy.ts` (same semantics). The
Next.js docs for Proxy explicitly warn that a matcher change or refactor can
silently remove proxy coverage from a route, so `app/dashboard/layout.tsx`
re-checks the session server-side as defense in depth rather than trusting
the proxy alone.

## Why `GET /api/me` is safe despite using the service role key

The backend's Supabase client is configured with the service role key
(which bypasses Row Level Security), but every handler that uses it filters
by the user id extracted from the **verified** JWT — never a client-supplied
id. This constraint must be preserved by every future endpoint that uses the
admin client: always scope by the authenticated user, never trust a
path/query parameter for row ownership. See `docs/security.md` for the full
review.

## Observability: `agent_events` and `tool_calls`

Every LangGraph node transition writes a concise `agent_events` row (never a
raw chain-of-thought dump — `plan.md` §4); every I/O call (search, extract,
analyze, draft) writes a `tool_calls` row with latency and a synthetic cost
estimate. `GET /api/runs/:id/events` and `.../tool-calls` (Phase 3) expose
these per-run; `GET /api/campaigns/:id/analytics` (Phase 5) aggregates them
across every run of a campaign into a funnel/cost/latency/failure summary —
see `specs/phase-5-hardening.md`.

## Evaluation harness (`backend/app/evals/`)

Six of `plan.md`'s seven fixed evaluation categories (campaign-parsing,
planning, candidate-validation, deduplication, scoring, outreach-grounding)
run against whichever providers are configured, with zero database
involvement — each calls the real production function it evaluates, never a
reimplementation. `POST /api/evals/run` (admin-only) executes them on demand.
The seventh category, failure/recovery, needs the full database-backed
research graph and is instead verified as backend test cases
(`tests/test_evals.py`) — see `specs/phase-5-hardening.md`'s Non-goals for
why exposing that particular category over a live admin endpoint would mean
every eval run writes synthetic data into whatever Supabase project is
configured.

## Why Phase 5 needed no new migration

Rate limiting is in-process memory (no table). The eval harness calls pure
functions/providers (no table). Analytics reads existing `leads`/
`outreach_drafts`/`approvals`/`campaign_runs`/`tool_calls`/`agent_events`
rows. Admin gating reuses `profiles.role`, already
`check (role in ('user','admin'))` since `0001_init.sql`. Phase 5 is about
using the Phase 1–4 data model harder, not extending it.

## Verifying RLS manually (requires a live Supabase project)

1. Sign up two users, A and B, through the app.
2. In the Supabase SQL editor, run as each user's JWT (via `set role` /
   `request.jwt.claims`, or through `supabase-js` with each user's session):
   ```sql
   select * from public.profiles where id = '<user-a-id>';
   ```
3. Confirm user B's query for user A's id returns zero rows, and each user's
   query for their own id returns exactly one row. Repeat for `campaigns`,
   `leads`, `outreach_drafts`, and `approvals` for full coverage of the
   Phase 3/4 tables.

This cannot be automated without real Supabase credentials — see
`specs/phase-1-foundation.md`, "Risks and Assumptions."
