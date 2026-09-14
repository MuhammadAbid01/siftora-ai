# Phase 2 — Campaigns, ICP, and Planning

Status: Implementation
Owner: Primary coding agent (Claude Code)
Parent document: `plan.md` (§16, with supporting detail from §5, §7, §10, §12, §13, §14, §20–22)
Builds on: `specs/phase-1-foundation.md` (auth, dashboard shell, API contract pattern, provider-interface convention)

---

## 1. Goal, Scope, and Non-Goals

### Goal

Let a signed-in user turn a natural-language campaign brief into a structured,
editable Ideal Customer Profile (ICP) and search plan, configure scoring
weights/thresholds and run limits, and approve the plan — all gated by
strict ownership checks and with no fabricated data when the model can't
determine required fields. No research, scoring computation, or outreach
happens yet; Phase 2 stops at "plan approved, run queued."

### Scope

- Campaign CRUD (create, list, get, update, delete), owned exclusively by
  the creating user.
- A natural-language brief field on the campaign.
- A `LanguageModelProvider` interface (per `plan.md` §5) with two
  implementations: a fixture (deterministic, zero-cost, default) and a real
  Gemini-backed adapter (opt-in via `LLM_PROVIDER=gemini` +
  `GEMINI_API_KEY`), used to turn the brief into a structured ICP plus a
  search plan (list of planned queries with rationale).
- Typed ICP: industries, locations, company size range, buying/pain
  signals, exclusions, offer, target roles.
- Scoring weights (the 8 criteria from `plan.md` §10, must sum to 100) and
  thresholds (qualified / needs-review cutoffs), configurable per campaign.
- Query/page/retry/cost run limits, configurable per campaign.
- Plan review: user can edit any generated ICP field, weights, thresholds,
  or limits before approving.
- Plan approval (`confirm-plan`) — validates the plan is complete and the
  scoring config is internally consistent before allowing it.
- A gated "start run" action (`run`) that only succeeds once the plan is
  approved — it flips `campaigns.status` to `queued` and does nothing else;
  no research, no LangGraph, no actual run execution (that's Phase 3).
- Dashboard UI: campaign list, a creation form, and a combined plan
  review/edit/approve/run page.

### Non-goals (Phase 2)

- Any actual research execution: no search provider, no website extraction,
  no LangGraph graph/state machine, no `campaign_runs` table, no progress
  polling. `POST /api/campaigns/:id/run` only changes `status`.
- Computing a lead score. Phase 2 only lets the user *configure* the
  weights/thresholds that Phase 3 will apply to real leads. No `leads` or
  `score_breakdowns` tables.
- Outreach drafting, approvals, export, or the `outreach_drafts` /
  `approvals` tables (Phase 4).
- Evaluation, analytics, or the `agent_events` / `tool_calls` tables
  (Phase 3 observability, Phase 5 evaluation).
- Admin-role UI or cross-user visibility of any kind.
- Pausing a run or `GET /api/campaigns/:id/progress` (meaningless before a
  run can execute anything — deferred to Phase 3 alongside real execution).
- A live, network-verified Gemini integration. The adapter is implemented
  correctly against the documented API shape but cannot be exercised
  end-to-end in this environment (no API key available) — see Risks.

---

## 2. Functional Requirements

### Campaign CRUD

- FR-1: `POST /api/campaigns` creates a campaign owned by the caller with a
  brief (required, 10–2000 chars), an optional offer description, and a
  target lead count (1–200, default 20). Initial `status = "draft"`.
- FR-2: `GET /api/campaigns` lists only the caller's campaigns, paginated
  (`limit`/`cursor`), newest first.
- FR-3: `GET /api/campaigns/:id` returns one campaign owned by the caller,
  including its ICP (if generated), search plan (if generated), scoring
  config, and limits. Returns 404 (not 403) if the campaign doesn't exist
  or isn't owned by the caller.
- FR-4: `PATCH /api/campaigns/:id` updates the brief, offer, target lead
  count, ICP fields, score weights, thresholds, and/or limits (each
  optional/partial). Rejects writes to campaigns not owned by the caller
  (404). Any successful edit to a campaign whose `status` is
  `plan_approved` or `queued` reverts `status` to `draft` — approval (and
  any queued run) is never silently preserved across an edit, regardless of
  which field changed.
- FR-5: `DELETE /api/campaigns/:id` deletes a campaign (and its ICP via
  cascade) owned by the caller.

### Plan generation

- FR-6: `POST /api/campaigns/:id/plan` sends the campaign's brief (+ offer,
  target count) to the configured `LanguageModelProvider` and requests a
  structured ICP + search plan.
- FR-7: If the model's structured output fails to parse/validate, the
  request is retried (bounded, default 2 attempts) before returning a clear
  `502 plan_generation_failed` error — the model is never allowed to return
  malformed data silently, and the caller is never left guessing.
- FR-8: If the parsed ICP is missing a required field (industries or
  locations, both empty), the endpoint persists whatever *was* extracted,
  leaves `status = "draft"`, and returns `422 icp_incomplete` naming the
  missing fields — it never invents plausible-sounding industries or
  locations to fill the gap.
- FR-9: On a complete extraction, the endpoint persists the ICP and search
  plan and sets `status = "awaiting_plan_approval"`.
- FR-10: Regenerating a plan (calling `/plan` again) overwrites the
  previous ICP/search plan and resets any prior approval.

### Scoring and limits configuration

- FR-11: Score weights are the 8 criteria from `plan.md` §10
  (`industry_fit`, `geography_fit`, `company_size_fit`,
  `pain_point_evidence`, `buying_signal`, `contact_relevance`, `recency`,
  `evidence_completeness`), defaulting to the table in §10, and must sum to
  exactly 100 whenever written — enforced by Pydantic on every write.
- FR-12: Score thresholds are `qualified_min` (default 75) and
  `needs_review_min` (default 55), with `0 <= needs_review_min <
  qualified_min <= 100` enforced on every write.
- FR-13: Run limits are `max_queries` (default 20, 1–100),
  `max_pages_per_company` (default 5, 1–20), `max_retries` (default 2,
  0–5), and `max_cost_usd` (default 5.00, >0, ≤50) — Phase 3 will enforce
  these; Phase 2 only stores and validates them.

### Plan review and approval

- FR-14: The user can edit any ICP field, weight, threshold, or limit via
  `PATCH` before or after plan generation.
- FR-15: `POST /api/campaigns/:id/confirm-plan` re-validates ICP
  completeness (at least one industry and one location), then sets
  `status = "plan_approved"` and records `plan_approved_at`. Fails with
  `409 plan_incomplete` if the campaign has no ICP yet or the ICP is
  missing industries/locations. It does **not** re-validate the scoring
  config (weights/thresholds/limits) — every write to those fields is
  already validated by the same Pydantic models on `PATCH` (FR-11–13), so
  an invalid scoring config can never reach the database in the first
  place; re-checking it here would be dead code guarding against a state
  that cannot occur.
- FR-16: `POST /api/campaigns/:id/run` succeeds only when
  `status == "plan_approved"`; otherwise it fails with
  `409 plan_not_approved`. On success it sets `status = "queued"` and
  returns the campaign. It performs no other work.

### Frontend

- FR-17: `/dashboard/campaigns` lists the user's campaigns with a status
  badge and a "New campaign" call to action; handles loading, empty, and
  error states.
- FR-18: `/dashboard/campaigns/new` is a short form (brief, offer, target
  count) that creates a draft campaign and navigates to its detail page.
- FR-19: `/dashboard/campaigns/:id` is the combined plan review page:
  brief/offer/target editor, a "Generate plan" action, an editable ICP
  form, a read-only search-plan list, editable weights (with a live,
  client-side "sums to 100" check mirroring the backend) and thresholds,
  editable limits, and "Confirm plan" / "Start run" actions that are
  disabled until their preconditions are met. Handles loading, empty
  (no plan yet), error, and unauthorized (redirect, via the existing
  dashboard auth guard) states.
- FR-20: When plan generation returns `icp_incomplete`, the page shows
  which fields are missing and lets the user fill them in manually via the
  same ICP form, rather than silently blocking or fabricating a plan.

---

## 3. Technical Design

### Backend file layout (extends `plan.md` §6)

```text
backend/app/
├── main.py             # + campaigns router mounted
├── config.py           # + llm_provider, gemini_api_key, gemini_model
├── schemas.py          # + campaign/ICP/plan/scoring/limits models
├── database.py         # NEW — Supabase repository functions (campaigns, campaign_icp)
├── providers.py        # NEW — LanguageModelProvider interface + Fixture/Gemini adapters
├── deps.py             # unchanged
├── supabase_client.py  # unchanged
└── routers/
    ├── health.py, me.py  # unchanged
    └── campaigns.py       # NEW
```

This fills in the `database.py` and `providers.py` files `plan.md` §6
sketches but Phase 1 didn't need yet.

### Provider interface

```python
class ICPExtraction(BaseModel):
    industries: list[str] = []
    locations: list[str] = []
    company_size_min: int | None = None
    company_size_max: int | None = None
    signals: list[str] = []
    exclusions: list[str] = []
    offer: str | None = None
    target_roles: list[str] = []

class SearchPlanQuery(BaseModel):
    query: str
    rationale: str

class PlanExtraction(BaseModel):
    icp: ICPExtraction
    search_plan: list[SearchPlanQuery]

class LanguageModelProvider(Protocol):
    async def generate_campaign_plan(
        self, *, brief: str, offer: str | None, target_lead_count: int
    ) -> PlanExtraction: ...
```

- `FixtureLanguageModelProvider` — deterministic, keyword-driven, zero
  network calls. Returns a complete plan for briefs that mention an
  industry-like term and a location; returns an incomplete extraction
  (empty `industries` or `locations`) for vague briefs, so the
  "ask, don't invent" path is deterministically testable. This is the
  **default** (`LLM_PROVIDER=fixture`), matching `plan.md` §21's
  "zero-cost fixture/demo mode" requirement.
- `GeminiLanguageModelProvider` — calls the Gemini API
  (`generativelanguage.googleapis.com`) with `responseMimeType:
  "application/json"` and a JSON schema matching `PlanExtraction`, via
  `httpx.AsyncClient`. Selected by `LLM_PROVIDER=gemini`, requires
  `GEMINI_API_KEY`. **Not exercised live in this environment** — no API
  key is available here; see Risks.
- `get_language_model_provider()` factory reads `Settings.llm_provider` and
  returns the matching adapter. Routers depend on the factory, never on a
  concrete adapter — same "interfaces, not vendor SDKs" rule as `plan.md`
  §5.

### Retry-then-fail (FR-7) and completeness gate (FR-8)

In `routers/campaigns.py`, `generate_plan()`:

```python
for attempt in range(settings.plan_generation_max_attempts):  # default 2
    try:
        extraction = await provider.generate_campaign_plan(...)
        break
    except (ValidationError, LLMOutputError):
        if attempt == last:
            raise HTTPException(502, {"code": "plan_generation_failed", ...})

if not extraction.icp.industries or not extraction.icp.locations:
    persist_partial(...)  # keeps status == "draft"
    raise HTTPException(422, {"code": "icp_incomplete", "missing_fields": [...]})

persist_full(...)  # status = "awaiting_plan_approval"
```

Retries guard against malformed/unparseable model output (a transport or
schema problem); the completeness gate is a separate, deliberate business
rule that fires even on a perfectly well-formed but under-specified
response.

### Data model (new migration `0002_campaigns.sql`)

```sql
create table public.campaigns (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  brief text not null,
  offer text,
  target_lead_count integer not null default 20
    check (target_lead_count between 1 and 200),
  status text not null default 'draft'
    check (status in ('draft','awaiting_plan_approval','plan_approved','queued')),
  search_plan jsonb,
  score_weights jsonb not null default '{
    "industry_fit":20,"geography_fit":10,"company_size_fit":10,
    "pain_point_evidence":20,"buying_signal":15,"contact_relevance":10,
    "recency":10,"evidence_completeness":5
  }'::jsonb,
  score_threshold_qualified integer not null default 75
    check (score_threshold_qualified between 0 and 100),
  score_threshold_needs_review integer not null default 55
    check (score_threshold_needs_review between 0 and 100),
  limit_max_queries integer not null default 20 check (limit_max_queries between 1 and 100),
  limit_max_pages_per_company integer not null default 5 check (limit_max_pages_per_company between 1 and 20),
  limit_max_retries integer not null default 2 check (limit_max_retries between 0 and 5),
  limit_max_cost_usd numeric(10,2) not null default 5.00 check (limit_max_cost_usd > 0 and limit_max_cost_usd <= 50),
  plan_approved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (score_threshold_qualified > score_threshold_needs_review)
);

create table public.campaign_icp (
  campaign_id uuid primary key references public.campaigns(id) on delete cascade,
  industries text[] not null default '{}',
  locations text[] not null default '{}',
  company_size_min integer,
  company_size_max integer,
  signals text[] not null default '{}',
  exclusions text[] not null default '{}',
  target_roles text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Both tables get `updated_at` triggers (reusing `public.set_updated_at`
from migration `0001`), RLS enabled, and owner-only policies
(`campaigns.user_id = auth.uid()`; `campaign_icp` via an `exists` subquery
against `campaigns`). As in Phase 1, the frontend never queries these
tables directly — only the FastAPI backend does, using the service-role
client, always scoped to the id extracted from the verified JWT. RLS is
still enabled per `plan.md` §12/§21 as defense-in-depth, not as the primary
enforcement mechanism.

`score_weights` is stored as `jsonb` rather than 8 columns — it's always
read/written as one unit and validated as one unit (sum to 100) by
Pydantic; a `jsonb` column avoids 8 near-duplicate integer columns for a
value that's never queried by individual criterion.

### Backend schemas (additions to `schemas.py`)

`ScoreWeights` (8 int fields, `model_validator` enforcing sum == 100),
`ScoreThresholds` (`qualified_min`, `needs_review_min`, validator enforcing
order), `RunLimits` (4 bounded fields), `ICP`/`ICPUpdate` (the same ICP
shape doubles as the LLM extraction target and the API response shape;
`offer` is deliberately not one of its fields — it's a campaign-level
attribute, not an ICP one, even though `plan.md` §12 groups it under
`campaign_icp` at a high level — see Risks), `SearchPlanQuery`,
`CampaignCreateRequest`, `CampaignUpdateRequest` (all fields optional),
`CampaignResponse` (id, status, brief, offer, target_lead_count, icp,
search_plan, score_weights, score_thresholds, limits, plan_approved_at,
created_at, updated_at), `CampaignListResponse` (items + next_cursor),
`DeleteResponse`.

### Frontend additions

- `lib/types/api.ts` — Zod mirrors of every schema above (same
  hand-maintained-pairing convention as Phase 1).
- `lib/api-client.ts` — add `apiPatch` / `apiDelete` (the generic `request`
  helper already supports the verbs; Phase 1 only exposed `apiGet`/`apiPost`
  wrappers).
- `lib/validation/campaigns.ts` — Zod schemas for the creation form, ICP
  edit form, weights form (`.refine` sum === 100, mirroring the backend
  validator so the user sees the error before submitting), thresholds, and
  limits forms.
- `components/campaigns/` — `campaign-list.tsx`, `status-badge.tsx`,
  `new-campaign-form.tsx`, `icp-form.tsx`, `search-plan-list.tsx`,
  `score-weights-form.tsx`, `score-thresholds-form.tsx`, `run-limits-form.tsx`,
  `plan-actions.tsx` (Generate/Confirm/Run buttons with precondition-based
  disabling).
- Dashboard nav gets a "Campaigns" link; the Phase 1 dashboard's "Coming in
  Phase 2" placeholder is replaced with a real link to `/dashboard/campaigns`.

---

## 4. Routes, Components, and Data/Auth Changes

### Backend routes (new)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST | `/api/campaigns` | required | FR-1 |
| GET | `/api/campaigns` | required | FR-2, paginated |
| GET | `/api/campaigns/:id` | required, owner-only | FR-3 |
| PATCH | `/api/campaigns/:id` | required, owner-only | FR-4 |
| DELETE | `/api/campaigns/:id` | required, owner-only | FR-5 |
| POST | `/api/campaigns/:id/plan` | required, owner-only | FR-6–10 |
| POST | `/api/campaigns/:id/confirm-plan` | required, owner-only | FR-15 |
| POST | `/api/campaigns/:id/run` | required, owner-only | FR-16 |

### Frontend routes (new)

| Route | Type | Auth | Notes |
| --- | --- | --- | --- |
| `/dashboard/campaigns` | page | protected | FR-17 |
| `/dashboard/campaigns/new` | page | protected | FR-18 |
| `/dashboard/campaigns/:id` | page | protected | FR-19–20 |

### Data/auth changes

- New migration `supabase/migrations/0002_campaigns.sql`: `campaigns`,
  `campaign_icp`, RLS policies, triggers.
- New env vars (backend, all optional with safe defaults):
  `LLM_PROVIDER` (default `fixture`), `GEMINI_API_KEY` (required only if
  `LLM_PROVIDER=gemini`), `GEMINI_MODEL` (default `gemini-3.6-flash` —
  updated from the original `gemini-2.5-flash` default after live testing
  in September 2026 showed Google had deprecated that model for new API
  keys; see Risks).
- No changes to `profiles` or Phase 1 auth flows.

---

## 5. Ordered Implementation Checklist

1. [x] Write this specification (`specs/phase-2-campaigns.md`).
2. [x] Write migration `supabase/migrations/0002_campaigns.sql`.
3. [x] Extend `backend/app/config.py` with LLM provider settings + validator.
4. [x] Extend `backend/app/schemas.py` with campaign/ICP/scoring/limits models.
5. [x] Write `backend/app/providers.py` (interface + fixture + Gemini adapters + factory).
6. [x] Write `backend/app/database.py` (campaign/ICP repository functions).
7. [x] Write `backend/app/routers/campaigns.py` (all 8 endpoints) and mount it in `main.py`.
8. [x] Write a reusable in-memory fake Supabase client for tests (`tests/fakes/supabase_fake.py`).
9. [x] Write backend tests: CRUD + ownership, plan generation (complete/incomplete/retry-fail), confirm-plan validation, run gating, scoring/threshold/limits Pydantic validators, config validator.
10. [x] Extend `frontend/src/lib/types/api.ts` with Zod mirrors.
11. [x] Extend `frontend/src/lib/api-client.ts` with `apiPatch`/`apiDelete`.
12. [x] Write `frontend/src/lib/validation/campaigns.ts`.
13. [x] Build campaign components (`components/campaigns/*`).
14. [x] Build `/dashboard/campaigns` (list) with loading/empty/error states.
15. [x] Build `/dashboard/campaigns/new` (creation form).
16. [x] Build `/dashboard/campaigns/:id` (plan review/edit/approve/run) with loading/error states.
17. [x] Wire dashboard nav + Phase 1 dashboard placeholder to link to campaigns.
18. [x] Write frontend unit tests: campaign Zod schemas (incl. weights-sum-100 refine), at least one component.
19. [x] Write/extend Playwright specs for the campaign flow (gated behind the same live-Supabase flag as Phase 1's auth flow, since campaigns require a signed-in user).
20. [x] Run all frontend and backend quality commands; fix failures.
21. [x] Re-review every Phase 2 acceptance criterion and testing item; fix gaps.

---

## 6. Acceptance Criteria

Directly from `plan.md` §16:

- AC-1: User manages only owned campaigns.
- AC-2: Brief produces schema-valid ICP output.
- AC-3: Missing required information is requested, not invented.
- AC-4: User can edit generated fields.
- AC-5: Weights must total 100.
- AC-6: Run cannot start without plan approval.
- AC-7: Invalid model output retries and then fails clearly.
- AC-8: Phase 3 research is not implemented.

### Verification status (end of Phase 2 implementation)

- **Met and verified (automated):** AC-1 (cross-user 404 + own-campaign
  CRUD tests), AC-2 (fixture provider produces a schema-valid `PlanExtraction`
  for a complete brief), AC-3 (fixture provider + `/plan` both tested for
  the incomplete-brief path — persists partial data, returns
  `422 icp_incomplete` naming the missing fields, never fabricates
  industries/locations), AC-4 (`PATCH` tests for campaign fields and ICP
  fields), AC-5 (`ScoreWeights` sum-to-100 validator tested both directions,
  backend and frontend), AC-6 (`/run` 409-before/200-after-approval test),
  AC-7 (retry-then-502 test with a provider that always raises), AC-8 (no
  search/extraction/LangGraph/scoring-computation/outreach code exists in
  this diff).
- **Implemented, not end-to-end verified (no live Supabase project in this
  environment):** the full real-browser flow (sign up → create campaign →
  generate plan → edit → confirm → run) and the migration's actual
  application via `supabase db reset`. Both are exercised by automated
  tests against fakes/fixtures instead — see §7 for the exact gap.

---

## 7. Testing Checklist

### Backend

- [x] `ruff format --check .` passes.
- [x] `ruff check .` passes.
- [x] `pytest` passes (44 tests: 9 carried over from Phase 1 + 35 new),
  covering:
  - Campaign create/list/get/update/delete, all scoped to the owning user;
    cross-user access returns 404 (AC-1). Cursor pagination also verified
    (3 campaigns, limit 2 → 2 items + cursor, then 1 item + no cursor).
  - Fixture provider returns a complete `PlanExtraction` for a
    fully-specified brief (AC-2) and an incomplete one (empty
    industries/locations) for a vague brief (AC-3).
  - `/plan` persists partial ICP + returns `422 icp_incomplete` on an
    incomplete extraction, without ever writing fabricated industries/locations.
  - `/plan` retries on a simulated invalid/unparseable model response and
    returns `502 plan_generation_failed` after exhausting attempts (AC-7).
  - `ScoreWeights` rejects a set of weights that doesn't sum to 100 (AC-5);
    accepts one that does.
  - `ScoreThresholds` rejects `needs_review_min >= qualified_min`.
  - `/confirm-plan` fails `409 plan_incomplete` on a missing/incomplete ICP,
    succeeds and sets `plan_approved_at` on a complete one.
  - Editing a `plan_approved` (or `queued`) campaign via `PATCH` reverts its
    status to `draft` (FR-4).
  - `/run` fails with `409` before approval and succeeds (`status=queued`)
    after (AC-6).
  - `Settings` fails validation when `LLM_PROVIDER=gemini` and
    `GEMINI_API_KEY` is unset (and succeeds when it is set; defaults to
    `fixture` when unspecified).

### Frontend

- [x] `npm run format:check` passes.
- [x] `npm run lint` passes.
- [x] `npm run typecheck` passes.
- [x] `npm run test` passes (27 tests: 13 carried over from Phase 1 + 14
  new), covering the campaign Zod schemas (list-field splitting, blank
  company-size handling, weights-sum-to-100 accept/reject, thresholds
  ordering, limits bounds) and the `StatusBadge` component.
- [x] `npm run build` succeeds.
- [x] `npm run test:e2e` — 5 non-auth-gated specs pass locally; the
  sign-up-flow and campaign-flow specs are both skipped without a live
  Supabase project (same `E2E_SUPABASE_LIVE` gate as Phase 1), not silently
  claimed passing.

### Manual/documented (not automatable without a live Supabase project)

- [ ] A real signed-in user can create a campaign, generate a plan, edit
  it, approve it, and start the run through the actual UI. **Not
  verified** — no live Supabase project (and thus no way to authenticate
  against the running frontend+backend) in this environment. The
  `e2e/campaign-flow.spec.ts` spec exists and will exercise this the
  moment `E2E_SUPABASE_LIVE=1` is set against a real project with the
  backend running.
- [ ] `supabase/migrations/0002_campaigns.sql` applies cleanly on top of
  `0001_init.sql` via `supabase db reset`. **Not verified** — no Supabase
  CLI/project linked here; reviewed manually for SQL correctness only.

---

## 8. Risks and Assumptions

- **Assumption (carried over from Phase 1):** no live Supabase project is
  available in this environment. All campaign persistence logic is tested
  against an in-memory fake Supabase client with realistic filter/ownership
  semantics, not a real database — migration correctness is reviewed
  manually, not executed.
- **Update (verified live, September 2026):** the user supplied a real
  `GEMINI_API_KEY` and the assumption above was tested. `GeminiLanguageModelProvider`'s
  request shape (`generateContent` + `responseMimeType: application/json`
  + `responseSchema`) works correctly as originally written — but the
  original default model, `gemini-2.5-flash`, now returns
  `404 NOT_FOUND` ("no longer available to new users") for this key.
  Google's error response names `gemini-3.6-flash` as the replacement;
  tested directly (both plain and structured-output `generateContent`
  calls) and confirmed working, so `GEMINI_MODEL`'s default was updated
  to `gemini-3.6-flash`. `TavilySearchProvider` and
  `FirecrawlExtractionProvider` (Phase 3) were tested live at the same
  time and both worked exactly as written, no changes needed. `LLM_PROVIDER`/
  `SEARCH_PROVIDER`/`EXTRACTION_PROVIDER` still default to `fixture` so the
  product remains fully functional and demo-able with zero credentials;
  this update only concerns what happens when live mode is deliberately
  enabled.
- **Risk:** storing `score_weights` as `jsonb` instead of individual
  columns trades a small amount of DB-level queryability (you can't filter
  campaigns by a specific weight in SQL) for avoiding 8 rarely-touched
  columns. Acceptable since nothing in Phase 2–3 needs to query by
  individual weight.
- **Risk:** editing ICP/weights/thresholds after `plan_approved` reverts
  status to `draft` (FR-4) rather than silently keeping the campaign
  "approved" against a plan the user just changed. This is a deliberate
  interpretation of `plan.md`'s "editing an approved draft invalidates
  approval" principle (stated for outreach drafts in §11, applied here by
  analogy to plan approval) — flagged in case a future phase wants a
  different reconciliation rule (e.g., re-approval only required for
  ICP/plan edits, not limit tweaks).
- **Risk:** `plan.md` §12 lists `offer` as one of `campaign_icp`'s columns,
  but this spec stores `offer` on `campaigns` instead and does not persist
  it on `campaign_icp` at all (the `ICP`/`ICPUpdate` models have no `offer`
  field). Rationale: `offer` is user-entered at campaign-creation time
  (`plan.md` §8, step 3), before any ICP exists, and is never re-derived by
  the planner — treating it as a campaign-level attribute avoids an awkward
  eager-created, mostly-empty `campaign_icp` row just to hold one field.
  `plan.md` §12 is a one-line high-level sketch, not a column-level DDL
  spec, so this is treated as an implementation-detail interpretation
  rather than a contradiction requiring a pause — flagged here so a later
  phase doesn't assume `offer` lives in `campaign_icp`.
- **Non-decision needed:** none of the above affects security, cost, data
  ownership, or architecture beyond what `plan.md` already resolves
  (fixture-by-default is `plan.md`'s own mandated safe default, not a new
  judgment call), so implementation proceeds without pausing for approval.
