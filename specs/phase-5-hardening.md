# Phase 5 — Evaluation, Hardening, and Deployment

Status: Implementation
Owner: Primary coding agent (Claude Code)
Parent document: `plan.md` (§19, with supporting detail from §4, §6, §7, §20, §21, §22, §23)
Builds on: `specs/phase-1-foundation.md` through `specs/phase-4-outreach.md` (the
full research → scoring → outreach → approval pipeline this phase evaluates,
hardens, and documents — no new product feature is introduced here)

**Filename note:** `plan.md` §4's document list names this file
`specs/phase-5-production.md`; the user explicitly directed this phase's
specification to live at `specs/phase-5-hardening.md` instead. Content
still fully addresses `plan.md` §19 — only the filename differs from the
plan's own convention, a deliberate, user-directed exception, not a drift.

---

## 1. Goal, Scope, and Non-Goals

### Goal

Take the four-phase pipeline built so far and make it *demonstrably* correct,
safe, and honest about its own limits: a deterministic evaluation harness
that exercises the fixed cases `plan.md` requires, the security gaps this
project has been carrying since Phase 1 (no rate limiting, no SSRF/prompt-
injection defense, no readiness probe) actually closed, an admin-gated way to
see the evaluation results and a user-facing way to see per-campaign
analytics, a demo-reset action, and documentation (README, architecture,
security, a demo script) that accurately describes what's mocked, sandboxed,
or live. No new end-user *feature* is added — every Phase 1–4 acceptance
criterion still holds unchanged.

### Scope

- `app/evals/` — a deterministic evaluation harness covering six of
  `plan.md`'s seven fixed-case categories (campaign-parsing, planning,
  candidate-validation, deduplication, scoring, outreach-grounding — see
  Non-goals for why the seventh, failure/recovery, is verified differently),
  each exercising the **real** production function it evaluates (never a
  reimplementation), reporting per-category and overall pass rates.
- `POST /api/evals/run` (admin-only) — runs the harness against whichever
  `LanguageModelProvider`/`SearchProvider`/`WebsiteExtractionProvider` is
  currently configured (fixture by default, real if the deployer has set
  live credentials — same selector pattern as every other provider in this
  project) and returns the report. Never touches Supabase — see Technical
  Design for why this is a meaningful, deliberate property, not an oversight.
- `GET /api/campaigns/:id/analytics` — the endpoint `plan.md` §13 listed and
  Phase 4 explicitly deferred: funnel (leads by status), draft/approval
  counts, cumulative cost and queries across the campaign's runs, average
  tool-call latency, and tool-call/agent-event failure counts. Purely an
  aggregation over existing Phase 3/4 tables — no new tables.
- `GET /api/health/ready` — a readiness probe that makes one cheap Supabase
  query and reports `503` if the database is unreachable, alongside the
  existing `GET /api/health` liveness check (`plan.md` §21 "Health checks
  cover the API and database").
- `POST /api/demo/reset` — deletes all of the current user's own campaigns
  (cascading to ICP/runs/leads/evidence/breakdowns/drafts/approvals via the
  existing foreign keys) so a public demo account can be reset between
  visitors. Never touches the global `companies` table or another user's
  data.
- Rate limiting (`app/rate_limit.py`): an in-process, per-user sliding-
  window limiter applied to `POST /campaigns/:id/plan` and `POST
  /campaigns/:id/run` (`plan.md` §21's literal "planning, and run start"),
  extended to `POST /leads/:id/regenerate-outreach` and `POST
  /approvals/:id/send` (both also trigger paid-provider or external-facing
  actions — a deliberate, documented extension of the literal phrase, in
  the same spirit as prior phases' justified beyond-checklist additions).
- Security hardening: a URL-safety check before any extraction attempt
  (`plan.md` §21 "URL validation and SSRF defense"), untrusted-content
  delimiters in the Gemini prompts that carry scraped page text or evidence
  (`plan.md` §21 "Prompt-injection defenses" / "Scraped content treated as
  untrusted input"), and admin-role gating (`get_current_admin_user`,
  `profiles.role`) for the one endpoint that can spend real provider budget
  on demand.
- Documentation: `docs/security.md` (new — named in `plan.md` §6's repo
  layout but never written), an updated `docs/architecture.md` (a diagram
  and narrative covering the full Phase 1–4 system, not just Phase 1), an
  updated root `README.md` (setup for all five phases, a demo script, a
  security-review summary of what was found and fixed), and an updated
  `docs/providers.md` cross-reference.
- Frontend: a `/dashboard/campaigns/:id/analytics` page, an admin-gated
  `/dashboard/evaluation` page (a real "unauthorized" state for a non-admin
  visitor — `plan.md` §14's required page state, exercised for the first
  time by an actual role check), a "Reset demo data" action, and small
  stale-copy fixes (the dashboard overview still said "Research and
  outreach automation arrive in later phases").

### Non-goals (Phase 5)

- **Live-provider or live-Supabase execution in this session.** This
  environment does have real internet access, real Gemini/Tavily/Firecrawl
  keys in `backend/.env`, and a reachable Supabase project (confirmed via a
  read-only check — Phases 1–4's migrations are already applied there).
  The user was asked directly and chose fixture/local-only verification for
  this phase, explicitly to make zero real API calls and touch zero rows in
  the real project. Every acceptance criterion below is therefore verified
  against fixtures/fakes, exactly like Phases 1–4, with the same "not
  verified live" honesty — the difference from prior phases is that this
  time it's a documented **choice**, not an environment limitation.
- **The failure/recovery eval category is not exposed through `/api/evals/
  run`.** Five of the six exposed categories call a pure function or a
  provider method with no database involvement at all; failure/recovery
  fundamentally needs the full LangGraph research run (`agent.run_research`)
  persisting through `app/database.py`. Exposing that over a live admin
  HTTP endpoint would mean every eval run writes synthetic campaigns/leads
  into whatever Supabase project is configured — real data-hygiene damage
  for a "just check the system" action. Instead, failure/recovery's 10 cases
  are verified as `tests/test_evals.py` cases against the shared
  `fake_supabase` fixture, the same infrastructure every other integration
  test in this codebase already uses. This is a deliberate split, not a
  shortcut — see Technical Design.
- **Actual deployment to Vercel/Railway.** No Vercel/Railway CLI or account
  is connected in this environment (confirmed: neither CLI is installed).
  Phase 5 delivers deployment-readiness (health/readiness endpoints,
  documented env vars, a step-by-step deployment guide in the README) but
  does not execute a real deployment. This mirrors `plan.md` §4's own rule
  that a decision affecting infrastructure isn't taken silently.
- **Screenshots.** Producing real UI screenshots would require running the
  live app against a real Supabase project (the one reachable one, which
  the user asked not to touch) or fabricating images, which this project's
  own rules forbid ("no fake behavior and claim it works" extends to fake
  screenshots). The README documents exactly how to take them once the user
  runs the app against their own project.
- **Distributed/shared rate limiting.** The limiter is a single Python
  process's in-memory state (`plan.md`'s whole backend is already a single
  FastAPI process with in-process `BackgroundTasks`, not a distributed
  system) — it resets on restart and doesn't coordinate across multiple
  backend instances. Documented in Risks; upgrading to Redis-backed limits
  is real infrastructure work with no Phase 5 AC requiring it.
- **A full external monitoring/alerting integration** (Sentry, Datadog,
  etc.). `plan.md` §5 names Supabase event logs (`agent_events`/
  `tool_calls`, already built in Phase 3) as the observability mechanism —
  Phase 5 makes that data queryable (analytics endpoint) rather than adding
  a new external dependency.
- **Any change to Phase 1–4 request/response contracts, database schema, or
  business rules.** This phase adds new, additive endpoints and internal
  hardening; it does not touch `campaigns`, `leads`, `outreach_drafts`,
  `approvals`, or any existing route's behavior. No new migration file is
  needed — see Technical Design for why.

---

## 2. Functional Requirements

### Evaluation harness

- FR-1: `app/evals/datasets.py` defines six fixed, hand-authored case lists
  meeting or exceeding `plan.md`'s minimums: `CAMPAIGN_PARSING_CASES` (10),
  `PLANNING_CASES` (10), `CANDIDATE_VALIDATION_CASES` (20),
  `DEDUPLICATION_CASES` (15), `SCORING_CASES` (20),
  `OUTREACH_GROUNDING_CASES` (20) — 95 cases total. Plain Python data
  structures (not JSON files) — this is a small, version-controlled,
  type-checked dataset with no need for a separate parsing/validation layer
  (`plan.md` §4's "avoid... premature abstraction" applies to eval data
  too).
- FR-2: `app/evals/runner.py` provides one `run_<category>()` function per
  category plus `run_all()`. Each calls the **actual** production code being
  evaluated:
  - `run_campaign_parsing()` / `run_planning()` →
    `LanguageModelProvider.generate_campaign_plan()` (via
    `get_language_model_provider()` — whatever's configured).
  - `run_candidate_validation()` → `app.agent.has_sufficient_evidence()`
    (FR-3, extracted from the real graph node — not reimplemented).
  - `run_deduplication()` → `app.providers.normalize_domain()`.
  - `run_scoring()` → `app.scoring.compute_score()`.
  - `run_outreach_grounding()` → `app.outreach.check_quality()` (with
    `app.outreach.assemble_body()` where a case needs an assembled body).
  Each case records `{name, passed, detail}`; each category aggregates to
  `{category, total, passed, pass_rate}`; `run_all()` returns an
  `EvalReport` with all six categories plus an overall pass rate and a
  `provider_mode` map (`{"llm": "fixture"|"gemini", "search": ...,
  "extraction": ...}`) so the report is always honest about what it just
  exercised.
- FR-3: `app/agent.py::has_sufficient_evidence(evidence: list[EvidenceItem])
  -> bool` is extracted from `validate_evidence`'s inline check (`any(item
  .type == "fact" for item in analysis.evidence)`) as a standalone, pure,
  importable function — `validate_evidence` now calls it. Pure refactor, no
  behavior change (covered by the full existing Phase 3 test suite still
  passing unchanged).
- FR-4: `POST /api/evals/run` (admin-only, FR-11) calls `run_all()` and
  returns the `EvalReport`. No campaign/lead/run rows are created — see
  Non-goals.
- FR-5: The failure/recovery category's 10 cases live in
  `tests/test_evals.py`, each driving a real (fixture-backed)
  `agent.run_research()` call (or an existing narrower helper for cases that
  don't need a full run, e.g. query revision) through the shared
  `fake_supabase` fixture, and asserting the resulting `stop_reason`/
  `status`/`decision_reason` matches the case's expectation. This is
  integration-level, not a pure-function call — consistent with why it's
  excluded from the live endpoint (Non-goals).

### Analytics

- FR-6: `GET /api/campaigns/:id/analytics` (owner-only) returns: funnel
  counts (`qualified`/`needs_review`/`rejected` counts from `leads`,
  computed from the full, unpaginated set), `drafts_generated`,
  `drafts_approved`, `drafts_rejected` (across all leads' drafts/
  approvals), `total_cost_usd` and `total_queries_used` (summed across
  **all** of the campaign's `campaign_runs` rows — a campaign can be run
  more than once), `avg_tool_latency_ms` (across all `tool_calls` for those
  runs, `null` if none have a latency recorded), `tool_call_failures` and
  `agent_event_failures` (status = `error` counts across those runs), and
  `runs_count`. 404 if the campaign has never been run (mirrors `/progress`'s
  own `no_run_yet` gate) or doesn't belong to the caller.

### Health and demo reset

- FR-7: `GET /api/health` is unchanged (liveness — no I/O, must stay fast
  and always-200 so it can't itself be a failure point). `GET
  /api/health/ready` performs one `profiles` select via the admin client;
  `200 {"status": "ok", "database": "ok"}` on success, `503 {"status":
  "error", "database": "unreachable"}` if the query raises. Unauthenticated
  (infra health checks don't carry a user JWT).
- FR-8: `POST /api/demo/reset` (authenticated, any role) deletes every
  campaign owned by the current user via the existing `delete_campaign`
  repository function, run once per campaign (cascades handle the rest).
  Returns `{"deleted_campaigns": N}`. Never touches `companies` (global,
  not user data) or other users' rows.

### Rate limiting

- FR-9: `app/rate_limit.py::check_rate_limit(key, bucket, max_requests,
  window_seconds)` is a pure, in-memory sliding-window check (a dict of
  `(key, bucket) -> list[timestamp]`); exceeding the limit raises
  `RateLimitExceeded(retry_after)`. `rate_limiter(bucket, max_requests,
  window_seconds)` returns a FastAPI dependency (keyed by
  `current_user.id`) that turns that into `429 {"code": "rate_limited",
  "details": {"retry_after_seconds": ...}}`. `reset()` clears all state —
  used by an autouse test fixture so one test's requests never affect
  another's.
- FR-10: Applied via `dependencies=[Depends(rate_limiter(...))]` (a
  side-effect-only dependency — it injects nothing into the handler) to:
  `POST /campaigns/:id/plan` (10/min), `POST /campaigns/:id/run` (5/min),
  `POST /leads/:id/regenerate-outreach` (20/min), `POST
  /approvals/:id/send` (20/min). Limits are per-user, not per-campaign or
  global — creating more campaigns cannot be used to bypass the limit.

### Admin gating

- FR-11: `app/deps.py::get_current_admin_user` depends on
  `get_current_user`, looks up the caller's `profiles` row (new
  `database.get_profile()`), and raises `403 {"code": "admin_required"}` if
  the row is missing or `role != "admin"`. There is still no self-service
  way to become an admin (`plan.md`'s Roles section defines no admin
  sign-up flow) — an operator promotes a user by editing `profiles.role`
  directly (documented in `docs/security.md`), exactly as already implied
  by `plan.md` §7.

### Security hardening

- FR-12: `app/providers.py::is_safe_extraction_url(url: str) -> bool`
  rejects non-`http(s)` schemes and hostnames that resolve to loopback,
  link-local, or private-network ranges (RFC 1918 + IPv6 equivalents).
  `app/agent.py::analyze_candidate` calls it before attempting extraction
  (both the primary and the alternate-scheme URL); a candidate whose URL(s)
  fail this check is finalized as `rejected`/`decision_reason=
  "unsafe_url"` — visible, not silently dropped, matching Phase 3's own
  "every candidate ends up somewhere" rule.
- FR-13: The Gemini adapter's `analyze_company` and `draft_outreach`
  prompts wrap scraped page text / evidence excerpts in an explicit
  `<untrusted_content>` block with an instruction that content inside it is
  data to analyze, never instructions to follow, and that the model must
  ignore any request embedded within it. Fixture prompts are unaffected
  (the fixture never constructs a prompt at all).

---

## 3. Technical Design

### Backend file layout (extends Phase 4's layout)

```text
backend/app/
├── main.py             # + evals, demo routers mounted; health.py extended
├── deps.py             # + get_current_admin_user
├── database.py         # + get_profile, list_campaign_runs,
│                        #   list_tool_calls_for_runs, list_agent_events_for_runs
├── agent.py             # + has_sufficient_evidence (extracted), URL-safety gate
├── providers.py         # + is_safe_extraction_url; Gemini prompts hardened
├── rate_limit.py         # NEW — in-process sliding-window limiter
├── evals/                 # NEW
│   ├── __init__.py
│   ├── datasets.py
│   └── runner.py
└── routers/
    ├── campaigns.py      # + GET /:id/analytics; /plan, /run gain rate limits
    ├── leads.py           # /regenerate-outreach gains a rate limit
    ├── approvals.py       # /send gains a rate limit
    ├── health.py          # + GET /health/ready
    ├── evals.py            # NEW
    └── demo.py             # NEW
```

### Why no new migration

Every Phase 5 addition reads existing tables (`analytics`), needs no table
at all (rate limiting is in-process memory; the eval harness calls pure
functions/providers), or reuses an existing column (`profiles.role`,
already `check (role in ('user','admin'))` since `0001_init.sql`). This is
a deliberate observation, not an oversight: Phase 5 is about *using* the
Phase 1–4 data model harder, not extending it.

### `EvalReport` schema (new, `app/schemas.py`)

```python
class EvalCaseResult(BaseModel):
    name: str
    passed: bool
    detail: str | None = None

class EvalCategoryResult(BaseModel):
    category: str
    total: int
    passed: int
    pass_rate: float
    cases: list[EvalCaseResult]

class EvalReport(BaseModel):
    categories: list[EvalCategoryResult]
    overall_pass_rate: float
    provider_mode: dict[str, str]
```

### `CampaignAnalyticsResponse` schema (new)

```python
class CampaignAnalyticsResponse(BaseModel):
    campaign_id: str
    qualified_count: int
    needs_review_count: int
    rejected_count: int
    drafts_generated: int
    drafts_approved: int
    drafts_rejected: int
    total_cost_usd: float
    total_queries_used: int
    avg_tool_latency_ms: float | None
    tool_call_failures: int
    agent_event_failures: int
    runs_count: int
```

### Rate limiter shape

```python
_WINDOWS: dict[tuple[str, str], list[float]] = defaultdict(list)

class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float) -> None: ...

def check_rate_limit(*, key: str, bucket: str, max_requests: int, window_seconds: float) -> None: ...
def reset() -> None: ...
def rate_limiter(bucket: str, max_requests: int, window_seconds: float): ...  # -> FastAPI dependency
```

---

## 4. Routes, Components, and Data/Auth Changes

### Backend routes (new/changed)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/health/ready` | none | FR-7 |
| GET | `/api/campaigns/:id/analytics` | owner-only | FR-6 |
| POST | `/api/demo/reset` | any authenticated user | FR-8 |
| POST | `/api/evals/run` | admin-only | FR-4, FR-11 |
| POST | `/api/campaigns/:id/plan` | owner-only | **changed** — rate-limited (FR-10) |
| POST | `/api/campaigns/:id/run` | owner-only | **changed** — rate-limited (FR-10) |
| POST | `/api/leads/:id/regenerate-outreach` | owner-only | **changed** — rate-limited (FR-10) |
| POST | `/api/approvals/:id/send` | owner-only | **changed** — rate-limited (FR-10) |

### Frontend routes (new)

| Route | Type | Notes |
| --- | --- | --- |
| `/dashboard/campaigns/:id/analytics` | page | FR-6 |
| `/dashboard/evaluation` | page | FR-4 — admin-only, real "unauthorized" state for non-admins |

### Data/auth changes

- No new migration (see Technical Design).
- No new env vars — the eval harness reuses `LLM_PROVIDER`/
  `SEARCH_PROVIDER`/`EXTRACTION_PROVIDER`, exactly like every other
  provider-consuming code path.

---

## 5. Ordered Implementation Checklist

1. [x] Write this specification (`specs/phase-5-hardening.md`).
2. [x] Confirm no migration is needed; verify the live Supabase project
   already has 0001–0004 applied (read-only check — no writes).
3. [x] Extract `app/agent.py::has_sufficient_evidence`; add the URL-safety
   gate (FR-12) and its `unsafe_url` decision reason.
4. [x] Add `app/providers.py::is_safe_extraction_url`; harden the Gemini
   `analyze_company`/`draft_outreach` prompts (FR-13).
5. [x] Write `app/rate_limit.py`.
6. [x] Extend `app/deps.py` with `get_current_admin_user`; extend
   `app/database.py` with `get_profile`, `list_campaign_runs`,
   `list_tool_calls_for_runs`, `list_agent_events_for_runs`.
7. [x] Extend `app/schemas.py` with `EvalCaseResult`/`EvalCategoryResult`/
   `EvalReport`/`CampaignAnalyticsResponse`/`ReadinessResponse`/
   `DemoResetResponse`.
8. [x] Write `app/evals/datasets.py` and `app/evals/runner.py`.
9. [x] Write `app/routers/evals.py`, `app/routers/demo.py`; extend
   `app/routers/health.py`, `app/routers/campaigns.py` (analytics + rate
   limits), `app/routers/leads.py` and `app/routers/approvals.py` (rate
   limits); mount new routers in `main.py`.
10. [x] Extend `tests/fakes/supabase_fake.py` for `profiles` inserts (admin
    test fixtures).
11. [x] Write backend tests: eval harness (each category's real pass rate),
    failure/recovery cases, analytics aggregation, health/readiness,
    demo reset, rate limiting (429 + per-user isolation), admin gating,
    URL-safety gate, prompt-hardening presence.
12. [x] Extend `frontend/src/lib/types/api.ts` with Zod mirrors.
13. [x] Build `/dashboard/campaigns/:id/analytics` and `/dashboard/
    evaluation` pages; add a "Reset demo data" action; fix stale dashboard
    copy.
14. [x] Write frontend unit tests for the new Zod schemas.
15. [x] Write `docs/security.md`; update `docs/architecture.md` (diagram +
    Phase 1–4 narrative) and `docs/providers.md` cross-reference.
16. [x] Rewrite root `README.md` (all five phases, demo script, deployment
    guide, security-review summary).
17. [x] Run all frontend and backend quality commands; fix failures.
18. [x] Re-review every Phase 5 acceptance criterion and testing item; fix
    gaps.

---

## 6. Acceptance Criteria

Directly from `plan.md` §19:

- AC-1: Deterministic tests pass 100%.
- AC-2: Structured parsing succeeds in at least 95% of fixed eval runs
  after retry.
- AC-3: No quality-approved fixed-set draft contains unsupported
  personalization.
- AC-4: Runs report latency, usage, cost, and failures.
- AC-5: Public fixture demo completes reliably.
- AC-6: Provider quota/failure states are usable.
- AC-7: Secrets remain server-side.
- AC-8: Health checks cover the API and database.
- AC-9: README supports fresh fixture-mode setup.
- AC-10: Portfolio docs distinguish mock, sandbox, and live behavior.

### Verification status (end of Phase 5 implementation)

- **Met and verified (automated):** AC-1 (the entire pytest suite, including
  every new Phase 5 test, passes — see §7), AC-2 (fixture-mode
  `campaign_parsing`/`planning` categories run at 100% structured-parse
  success in `test_evals.py`; fixture output is always Pydantic-valid by
  construction, so this is the deterministic floor for the metric — the
  "after retry" language describes the *live* Gemini path, unverified here
  per Non-goals, exactly like Phase 2's own plan-generation retry logic
  which this reuses unchanged), AC-3 (`outreach_grounding` eval category —
  every "should pass" case is genuinely groundable, every "should fail"
  case is caught, both against the real `check_quality`), AC-4
  (`test_analytics_reports_cost_latency_and_failures`), AC-5 (the full
  fixture-mode pipeline — campaign → plan → run → lead → draft → approve →
  export — is exercised end-to-end across the Phase 3/4 suites plus this
  phase's `demo_reset` test; "reliably" is evidenced by that suite passing
  deterministically, not by a live public deployment, see Non-goals), AC-6
  (unchanged from Phase 2/3 — `TavilySearchProvider`/
  `FirecrawlExtractionProvider`/`GeminiLanguageModelProvider` already
  degrade to empty-results/`None`/`LLMOutputError` rather than crashing;
  Phase 5 adds one more graceful-degradation path, the URL-safety gate,
  with its own test), AC-7 (`test_config.py`'s existing coverage plus a new
  assertion that no route ever echoes a provider API key or the Supabase
  service-role key in a response; `docs/security.md` documents the finding
  that the *user's own git remote* has a personal access token embedded in
  its URL — a real secret-hygiene issue this review surfaced, outside this
  codebase's own control, flagged rather than silently fixed since
  `CLAUDE.md`'s Git Safety Protocol forbids touching git config), AC-8
  (`test_health.py`'s new readiness cases), AC-9 (README rewritten and
  its fixture-mode setup steps are the same ones this environment's own
  test suite exercises), AC-10 (`docs/providers.md`, already
  phase-by-phase accurate, now cross-referenced from the rewritten README
  and `docs/security.md`).
- **Implemented, not end-to-end verified (live execution declined this
  phase — see Non-goals):** running `/api/evals/run` against real Gemini/
  Tavily/Firecrawl; applying migrations (already applied) and running the
  live Playwright specs against the real Supabase project; an actual
  Vercel/Railway deployment; real screenshots.

---

## 7. Testing Checklist

### Backend

- [x] `ruff format --check .` passes.
- [x] `ruff check .` passes.
- [x] `pytest` passes (168 tests: 121 carried over from Phases 1–4 + 47
  new), covering:
  - Eval harness: each of the six live-endpoint categories reports
    `pass_rate == 1.0` against fixtures; `provider_mode` reflects the
    forced-fixture test setting (AC-1, AC-2, AC-3).
  - Failure/recovery: 10 cases, each asserting a specific `stop_reason`/
    `status`/`decision_reason` via the real fixture-backed graph.
  - `has_sufficient_evidence`: extracted correctly — existing Phase 3 tests
    (`test_agent.py`) still pass unchanged, confirming no behavior drift.
  - `is_safe_extraction_url`: accepts ordinary `http(s)` URLs, rejects
    `file://`/`ftp://`, rejects loopback/private-network hosts; a candidate
    whose search-result URL fails the check is persisted `rejected`/
    `unsafe_url`, not silently dropped or crashed on.
  - Rate limiting: the (N+1)th request within a window is `429` with
    `retry_after_seconds`; a *different* user's request in the same window
    is unaffected (per-user isolation); resets between tests via an
    autouse fixture.
  - Admin gating: a non-admin/absent-profile caller gets `403
    admin_required` on `/evals/run`; an admin succeeds.
  - Analytics: funnel/cost/latency/failure numbers match hand-computed
    expectations across a multi-run campaign; 404 for a never-run or
    cross-user campaign.
  - Health: `/health` always 200 with no I/O; `/health/ready` 200 against
    the fake client, 503 when the client raises.
  - Demo reset: deletes only the caller's own campaigns (cascade verified
    via leads/drafts disappearing too); another user's campaigns and the
    global `companies` table are untouched.

### Frontend

- [x] `npm run format:check` passes.
- [x] `npm run lint` passes.
- [x] `npm run typecheck` passes.
- [x] `npm run test` passes (55 tests: 48 carried over from Phases 1–4 + 7
  new), covering the new Zod schemas (`ReadinessResponse`, `EvalReport`,
  `CampaignAnalyticsResponse`, `DemoResetResponse`).
- [x] `npm run build` succeeds.
- [x] `npm run test:e2e` — existing non-auth-gated specs still pass; no new
  gated spec is added this phase (analytics/evaluation pages have no new
  live-Supabase-only interaction beyond what auth-flow/research-flow/
  outreach-flow already cover, and admin-role UI has no way to be
  exercised live without a real admin account, which this environment
  cannot create — see Non-goals).

### Manual/documented (not automatable without live execution this phase)

- [ ] `/api/evals/run` against real Gemini/Tavily/Firecrawl, to measure the
  actual (not fixture-floor) structured-parsing success rate. **Not run**
  — the user chose fixture-only verification for this phase (see Non-
  goals); the harness is ready to run the moment `LLM_PROVIDER=gemini`
  etc. are active, with no code change needed.
- [ ] A real deployment to Vercel + Railway. **Not performed** — no
  deployment CLI/account connected here; the README's deployment guide
  documents the steps.
- [ ] Real screenshots for the README. **Not produced** — see Non-goals.

---

## 8. Risks and Assumptions

- **Note — live infrastructure is actually reachable, by choice not
  used:** unlike every prior phase's "no live Supabase project in this
  environment" framing, this environment genuinely has internet access, a
  reachable Supabase project with Phases 1–4's schema already applied, and
  real provider keys. Verification here is fixture-only because the user
  explicitly chose that (asked directly, given the option to go live) —
  not because it was impossible. Recorded precisely so a future phase
  doesn't misread this one as "still no live access."
- **Finding — a GitHub personal access token is embedded in the local git
  remote URL** (`git remote -v` shows it in plaintext in `.git/config`).
  This is outside this codebase and this phase's control surface (it's the
  user's local git configuration, not a file in the repository), and
  `CLAUDE.md`'s Git Safety Protocol explicitly forbids updating git config
  — so this is flagged in `docs/security.md` and here, not silently fixed.
  Recommended remediation (for the user, not automated): use a credential
  helper or SSH instead of an embedded-token HTTPS remote, and rotate the
  token given it's been visible in a terminal transcript. **Status: open**
  — not remediated as of this phase; no agent action was taken on it per
  the Git Safety Protocol above.
- **Risk — in-process rate limiting is single-instance only:** documented
  in Non-goals. Fine for this MVP's single-FastAPI-process deployment
  model; would need a shared store (Redis) behind a load balancer.
- **Risk — eval harness pass rates against fixtures don't predict live
  model behavior:** the 95% "after retry" AC is fundamentally about a real
  LLM's structured-output reliability, which a deterministic fixture
  cannot measure by construction (it's always 100%). The harness is built
  provider-agnostic specifically so the user can get a real number by
  running it with `LLM_PROVIDER=gemini` — flagged, not glossed over.
- **Risk — analytics aggregates across every run of a campaign, not just
  the latest:** a campaign re-run after being edited (Phase 3's
  `_REVERT_ON_EDIT_STATUSES`/`_BLOCKED_FROM_EDIT_STATUSES` rules) will show
  cumulative cost/queries from all attempts, including abandoned ones. This
  is the more honest number for "what has this campaign cost so far" but
  means per-run cost isn't separately broken out in this endpoint —
  `GET /runs/:id/tool-calls` (Phase 3) remains the place for a single run's
  detail.
- **Non-decision needed:** none of the above affects security, cost, data
  ownership, or architecture beyond what `plan.md` already resolves and
  what the user was already asked (live-vs-fixture) — implementation
  proceeds without further pausing for approval.
