# Architecture — Phase 1

See `plan.md` for the full product architecture and `specs/phase-1-foundation.md`
for the Phase 1 specification. This document covers what exists today.

## Overview

Two independent applications, no containers:

- **frontend/** — Next.js 16 (App Router) + TypeScript, Tailwind CSS. Talks to
  Supabase Auth directly from the browser/server for sign-up/in/out and
  session management, and to the FastAPI backend for application data.
- **backend/** — FastAPI + Python 3.12+. Verifies the Supabase-issued JWT on
  each request and reads/writes Supabase Postgres using the service role key,
  always scoped to the authenticated user's id.
- **supabase/** — SQL migrations and seed data for the Supabase Postgres
  database used by both apps.

```
Browser ──(Supabase Auth: sign up/in/out, session cookies)──> Supabase Auth
Browser ──(Next.js pages, Server Components)──> Next.js server
Next.js server / browser ──(REST, Bearer JWT)──> FastAPI backend
FastAPI backend ──(service role key, scoped to auth.uid())──> Supabase Postgres
```

## Why a proxy (`src/proxy.ts`) and a layout guard both check auth

Next.js 16 renamed `middleware.ts` to `proxy.ts` (same semantics). The Next.js
docs for Proxy explicitly warn that a matcher change or refactor can silently
remove proxy coverage from a route, so `app/dashboard/layout.tsx` re-checks
the session server-side as defense in depth rather than trusting the proxy
alone.

## Why `GET /api/me` is safe despite using the service role key

The backend's Supabase client is configured with the service role key (which
bypasses Row Level Security), but the `/api/me` handler only ever queries
`profiles` filtered by the user id extracted from the *verified* JWT — never
a client-supplied id. This constraint must be preserved by every future
endpoint that uses the admin client: always scope by the authenticated user,
never trust a path/query parameter for row ownership.

## Verifying RLS manually (requires a live Supabase project)

1. Sign up two users, A and B, through the app.
2. In the Supabase SQL editor, run as each user's JWT (via `set role` /
   `request.jwt.claims`, or through `supabase-js` with each user's session):
   ```sql
   select * from public.profiles where id = '<user-a-id>';
   ```
3. Confirm user B's query for user A's id returns zero rows, and each user's
   query for their own id returns exactly one row.

This cannot be automated without real Supabase credentials — see
`specs/phase-1-foundation.md`, "Risks and Assumptions".
