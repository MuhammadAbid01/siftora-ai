# Phase 3 — Agentic Research, Evidence, and Scoring

Status: Implementation
Owner: Primary coding agent (Claude Code)
Parent document: `plan.md` (§17, with supporting detail from §5, §7, §9, §10, §11, §12, §13, §14, §20–22)
Builds on: `specs/phase-1-foundation.md` (auth, provider-interface convention),
`specs/phase-2-campaigns.md` (campaigns/ICP, `LanguageModelProvider` pattern,
`database.py`/`providers.py` structure, fixture-first defaults)

---

## 1. Goal, Scope, and Non-Goals

### Goal

Let a user with an approved campaign plan start a real (but bounded,
in-process) research run: a LangGraph agent searches for candidate
companies, extracts and analyzes their public websites, rejects
unsupported or duplicate candidates, computes a deterministic 0–100 score
per lead, and persists everything — evidence, score breakdown, tool calls,
and agent events — so the user can inspect exactly what happened and why.
No outreach is drafted; Phase 3 stops at "qualified/needs-review/rejected
leads with full evidence," which is the hand-off point to Phase 4.

### Scope

- A `campaign_runs` row per run attempt: status, a frozen config snapshot
  (weights/thresholds/limits — "scoring configuration becomes immutable
  for a run", `plan.md` §10), counts, cost estimate, stop reason.
- A LangGraph `StateGraph` (`app/agent.py`) that: consumes the approved
  search plan query-by-query (revising a query up to `max_retries` times
  when it returns nothing), discovers candidate companies, deduplicates
  them (within the run, and globally by domain), extracts each candidate's
  public website, analyzes it into facts/inferences/unknowns plus a
  per-criterion signal, rejects candidates with insufficient evidence,
  scores every remaining candidate deterministically, and persists a
  `leads` row (qualified, needs-review, or rejected — never silently
  dropped) for every candidate it evaluates.
- `SearchProvider` and `WebsiteExtractionProvider` interfaces (`plan.md`
  §5), each with a deterministic fixture adapter (default) and a real
  adapter (Tavily for search, Firecrawl for extraction — both opt-in,
  unverified live in this environment; same posture as Phase 2's Gemini
  adapter).
- `LanguageModelProvider` gains `analyze_company()` (extraction/analysis),
  alongside Phase 2's `generate_campaign_plan()`.
- `app/scoring.py`: a pure, deterministic function from
  (per-criterion signals, weights) to (total score, per-criterion
  breakdown). No LLM call happens at scoring time — only at analysis time,
  and only to produce the signals scoring consumes.
- New tables: `companies` (global, deduplicated by domain — not
  user-owned, so not RLS'd), `leads`, `lead_evidence`, `score_breakdowns`,
  `campaign_runs`, `agent_events`, `tool_calls`.
- `POST /api/campaigns/:id/run` now actually starts research (idempotent —
  a campaign with an already-`running` run returns that run rather than
  starting a second one) instead of Phase 2's placeholder status flip.
  `POST /api/campaigns/:id/pause` and `GET /api/campaigns/:id/progress`
  (both deferred from Phase 2, per that spec's Risks section).
- `GET /api/campaigns/:id/leads`, `GET /api/leads/:id`,
  `POST /api/leads/:id/rescore` (recompute a lead's score against the
  campaign's *current* weights — a deliberate, explicit user action, not a
  run-time mutation, so it doesn't conflict with "immutable for a run").
- `GET /api/runs/:id/events`, `GET /api/runs/:id/tool-calls` — paginated,
  for the tool-log/event-timeline UI.
- Frontend: campaign detail page gains progress + run/pause controls and
  an event/tool-call timeline; new leads list and lead detail pages.

### Non-goals (Phase 3)

- Outreach drafting of any kind (`outreach_drafts`, `approvals` tables,
  `POST /api/leads/:id/regenerate-outreach`) — Phase 4. A qualified lead
  in Phase 3 simply *is* qualified; nothing is drafted for it yet, which
  trivially satisfies `plan.md`'s "low-score leads skip outreach" AC
  (**no** lead, regardless of score, gets outreach in this phase).
- `PATCH /api/leads/:id/status` (a manual disposition override) — without
  an approval workflow around it this doesn't fit cleanly and isn't
  required by any Phase 3 AC; deferred to Phase 4 alongside approvals.
- True checkpointed pause/resume. "Pause" here is cooperative: the run
  checks a flag between candidates and stops cleanly, preserving every
  lead already persisted. "Resume" is calling `/run` again, which starts a
  **new** run from the top of the search plan (already-seen domains are
  still deduplicated globally via `companies`, so it won't re-create
  duplicate leads for companies already captured, but it will re-run
  search queries). A true "continue exactly where it left off" resume is
  out of scope — see Risks.
- Distributed job infrastructure. Runs execute via FastAPI's in-process
  `BackgroundTasks` (`plan.md` §5/§6), exactly like Phase 2's synchronous
  request/response style but async — no Celery, no external queue.
- Real cost tracking against actual provider billing. Fixture-mode cost is
  a small, clearly-labeled synthetic per-call estimate for exercising the
  cost-limit code path, not a real dollar figure.
- Contact discovery (`leads.contact` in `plan.md` §12's one-line sketch).
  Phase 3's own scope bullets don't name a contact-finding tool, and
  fabricating a "sometimes-populated" contact field without a real
  detection heuristic would be exactly the kind of fake behavior the
  project rules forbid. Deferred — see Risks.
- Any change to Phase 1/2 auth, campaign CRUD, or plan-generation
  behavior beyond what's needed to make `/run` do real work and to block
  edits to a campaign while a run is in flight (new in this phase, see
  FR-2).

---

## 2. Functional Requirements

### Run lifecycle

- FR-1: `POST /api/campaigns/:id/run` requires `status == "plan_approved"`
  (unchanged 409 gate from Phase 2). On success it creates a
  `campaign_runs` row (`status="queued"`, a frozen snapshot of the
  campaign's current weights/thresholds/limits/target count), sets
  `campaigns.status = "queued"`, schedules the LangGraph run as a
  `BackgroundTasks` job, and returns immediately with the campaign and run.
  The background job's first action, before any research work, flips both
  to `status="running"` — so `queued` is a real (if often brief) observable
  state, not a placeholder.
- FR-2: While `campaigns.status` is `queued`, `running`, or `paused`,
  `PATCH /api/campaigns/:id` is rejected with `409 campaign_running` — a
  run's config must not change underneath it (`plan.md` §10). Editing a
  `completed` or `failed` campaign is allowed and (as in Phase 2, for
  `plan_approved`) reverts status to `draft`, requiring re-approval before
  running again. **Behavior change from Phase 2:** that spec put `queued`
  in the editable/revert-to-draft set, because at the time it was a
  placeholder end state with no real run behind it (Phase 2 explicitly
  deferred run execution to this phase). Now that `queued` means a run is
  about to execute, it moves into the blocked set alongside `running`/
  `paused` — this is a deliberate, spec'd change, not an unreviewed
  regression.
- FR-3: If a campaign already has a `campaign_runs` row with
  `status in ("queued", "running")`, calling `/run` again returns that
  same run (200) without creating a second one or scheduling a second
  background job — idempotent per `plan.md`'s Phase 3 AC.
- FR-4: `POST /api/campaigns/:id/pause` sets the active run's
  `pause_requested = true`. The graph checks this flag between candidates
  and, once seen, stops cleanly: persists nothing further, sets the run's
  `status = "paused"`, `stop_reason = "paused_by_user"`, and
  `campaigns.status = "paused"`. Returns 409 `no_active_run` if there is no
  `queued`/`running` run.
- FR-5: `GET /api/campaigns/:id/progress` returns the campaign's most
  recent run: status, stop reason, counts (queries used, leads created,
  qualified/needs-review/rejected/failed), estimated cost, timestamps.
  404 if the campaign has never been run.

### Research graph

- FR-6: The graph consumes `search_plan` queries in order, bounded by
  `limits.max_queries`. A query that returns zero results is revised
  (broadened) and retried, up to `limits.max_retries` times, before moving
  to the next query — the agent "revises weak queries only within limits."
- FR-7: Every discovered candidate is normalized (lower-cased, `www.`
  stripped) by domain. A domain already seen in this run (or already
  present in the global `companies` table from a prior run) is merged
  (its `companies` row is reused/refreshed) rather than creating a second
  `leads` row for the same campaign+company pair.
- FR-8: Each remaining candidate's website is extracted
  (`WebsiteExtractionProvider`). If extraction fails, exactly one
  alternate URL form is tried (toggling `http`/`https`); if that also
  fails, the candidate is persisted as a `leads` row with
  `status="rejected"`, `decision_reason="extraction_failed"` — a visible
  failure/fallback result, not a silent drop.
- FR-9: A successfully-extracted page is analyzed
  (`LanguageModelProvider.analyze_company`) into facts, inferences,
  unknowns (each fact/inference carries a source URL and excerpt; unknowns
  carry neither — nothing is invented to fill an unknown), plus one 0–1
  signal per scoring criterion.
- FR-10: A candidate with zero extracted facts is persisted as
  `status="rejected"`, `decision_reason="insufficient_evidence"` rather
  than being scored — "unknown information is not fabricated" applies to
  scoring too: no evidence means no confident score.
- FR-11: `app/scoring.py` computes `points = round(rating * weight, 2)`
  per criterion from the run's frozen weight snapshot, sums to a 0–100
  total, and returns the full breakdown. Given the same signals and
  weights, this always produces the same number (pure function, no I/O).
- FR-12: The total score is compared against the run's frozen thresholds:
  `>= qualified_min` → `qualified`; `>= needs_review_min` → `needs_review`;
  else → `rejected`. No outreach step follows for any status (Phase 4).
- FR-13: The run stops (and persists everything found so far) when any of:
  `leads_created >= target_lead_count` (`stop_reason="target_reached"`),
  `estimated_cost_usd >= limits.max_cost_usd`
  (`"budget_exhausted"`), the search plan and retries are exhausted
  (`"queries_exhausted"`), pause was requested (`"paused_by_user"`), or an
  unrecoverable error occurred (`"error"`) — partial results already
  persisted are never rolled back.
- FR-14: Every graph step that does I/O (search call, extraction call,
  analysis call) writes one `tool_calls` row (tool, provider, status,
  a concise summary, latency, estimated cost). Every node transition
  writes one `agent_events` row with a concise, human-readable summary —
  never a raw chain-of-thought dump (`plan.md` §4 rule).
- FR-15: An exception raised while processing a single candidate is
  caught, logged as a `tool_calls`/`agent_events` error entry, and the run
  continues with the next candidate (recoverable). An exception raised
  outside per-candidate processing (e.g. the database becomes
  unreachable) aborts the whole run: the run and campaign are marked
  `failed` with the error message, and whatever was already persisted is
  kept.

### Leads and runs API

- FR-16: `GET /api/campaigns/:id/leads` lists the campaign's leads
  (paginated, owner-only), each with its score, status, and company
  summary — no evidence payload (kept for the detail endpoint).
- FR-17: `GET /api/leads/:id` (owner-only, via the parent campaign) returns
  the lead plus its company, full evidence list (typed fact/inference/
  unknown), and score breakdown.
- FR-18: `POST /api/leads/:id/rescore` recomputes the lead's score **and**
  status (both, together — a rescore that crosses a threshold must move
  the lead, not just its number) using the campaign's **current**
  `score_weights`/`score_thresholds` (not the run's frozen snapshot)
  against the lead's already-stored per-criterion signals (from its
  existing `score_breakdowns` rows) — no new LLM/search/extraction call.
  If the previous status was `rejected` with a non-score
  `decision_reason` (`extraction_failed`/`insufficient_evidence`),
  rescoring does not apply (409 — there's no score to recompute).
  Returns the updated lead.
- FR-19: `GET /api/runs/:id/events` and `GET /api/runs/:id/tool-calls`
  (owner-only, via the parent campaign) return paginated, newest-first
  lists.

### Frontend

- FR-20: The campaign detail page (`/dashboard/campaigns/:id`) gains a
  progress panel (polls `GET .../progress` every few seconds while a run
  is active), a "Pause" action (visible only while running), and an event/
  tool-call timeline. The existing "Start run" action is unchanged
  (Phase 2); once a run exists, the page shows its live state.
- FR-21: `/dashboard/campaigns/:id/leads` lists leads with status/score,
  linking to a detail page; handles loading/empty/error states.
- FR-22: `/dashboard/campaigns/:id/leads/:leadId` shows the company, its
  evidence (visually distinguishing fact / inference / unknown, each with
  its source link where present), and the score breakdown by criterion;
  includes a "Rescore" action.

---

## 3. Technical Design

### Backend file layout (extends `plan.md` §6 / Phase 2's layout)

```text
backend/app/
├── main.py             # + leads, runs routers mounted
├── config.py           # + SEARCH_PROVIDER, EXTRACTION_PROVIDER, TAVILY_API_KEY, FIRECRAWL_API_KEY
├── schemas.py          # + lead/evidence/score/run/event/tool-call models
├── database.py         # + companies/leads/lead_evidence/score_breakdowns/
│                        #   campaign_runs/agent_events/tool_calls repositories
├── providers.py        # + SearchProvider, WebsiteExtractionProvider,
│                        #   LanguageModelProvider.analyze_company
├── scoring.py           # NEW — deterministic scoring
├── agent.py             # NEW — LangGraph research graph
└── routers/
    ├── campaigns.py      # /run rewritten, + /pause, /progress
    ├── leads.py           # NEW
    └── runs.py            # NEW
```

`EXTRACTION_PROVIDER` is not named in `plan.md` §22's env var list, but a
selector is clearly implied by "Fixture providers" + "Firecrawl provider
adapter" both being required — added by the same pattern as Phase 2's
`LLM_PROVIDER`, defaulting to `fixture`.

### LangGraph usage

`app/agent.py` builds one `StateGraph` (no checkpointer — a run completes
within a single `ainvoke()` call, matching "controlled in-process
background research execution"; no cross-process durability is needed or
claimed). State is a `TypedDict`:

```python
class ResearchState(TypedDict):
    run_id: str
    campaign_id: str
    icp: dict
    search_plan: list[dict]          # [{query, rationale}]
    weights: dict
    thresholds: dict
    limits: dict
    target_lead_count: int

    query_cursor: int
    query_retry_count: int
    pending_candidates: list[dict]
    seen_domains: list[str]
    current_candidate: dict | None
    current_analysis: dict | None

    queries_used: int
    leads_created: int
    qualified_count: int
    needs_review_count: int
    rejected_count: int
    failed_count: int
    estimated_cost_usd: float
    stop_reason: str | None
```

Real graph nodes: `search_companies`, `normalize_and_dedupe`,
`analyze_candidate`, `validate_evidence`, `score_candidate`,
`decide_qualification`, `persist_lead`, `complete_run`. A single reusable
router function (`route_next`) is used as the conditional-edge target
after `search_companies`, `normalize_and_dedupe` (duplicate-skip path),
and `persist_lead`; it re-checks the pause flag and stop conditions (FR-13)
on every call, so those checks happen between every candidate, not just
once.

**Adaptation from `plan.md` §9's full cross-phase node list**, documented
here rather than silently diverging:

- `deduplicateCandidate` is folded into `normalize_and_dedupe` (one node,
  since dedup is a direct consequence of normalization — there is no
  useful intermediate state between them).
- `handleRecoverableFailure` is a plain Python helper
  (`_persist_failed_candidate`) called from each node's own `try/except`,
  not a separate graph node — LangGraph edges represent normal control
  flow, not exception propagation, so routing exceptions *through* a node
  would need a framework-specific mechanism (`add_node(error_handler=...)`)
  that this spec chooses not to depend on for something a plain
  `try/except` already does correctly and more transparently.
- `handleTerminalFailure` wraps the top-level `graph.ainvoke(...)` call in
  the background-task driver (`routers/campaigns.py`), not inside the
  graph — simpler, and the failure mode (DB unreachable, etc.) is by
  definition something the graph's own persistence-dependent nodes can't
  reliably handle themselves.
- `awaitPlanApproval`, `parseCampaignBrief`, `buildSearchPlan`,
  `draftOutreach`, `qualityCheckDraft`, `awaitOutreachApproval` are Phase 2
  (already implemented outside the graph, as plain endpoints) or Phase 4
  (not yet implemented) — not part of this graph.

### Provider interfaces (extends `app/providers.py`)

```python
class SearchResultItem(BaseModel):
    company_name: str
    domain: str
    url: str
    snippet: str

class SearchProvider(Protocol):
    async def search(self, *, query: str, max_results: int) -> list[SearchResultItem]: ...

class ExtractedPage(BaseModel):
    url: str
    text: str

class WebsiteExtractionProvider(Protocol):
    async def extract(self, *, url: str) -> ExtractedPage | None: ...  # None = fetch failed

class EvidenceItem(BaseModel):
    type: Literal["fact", "inference", "unknown"]
    claim: str
    excerpt: str | None = None     # required for fact/inference, absent for unknown
    source_url: str | None = None  # required for fact/inference, absent for unknown
    confidence: float | None = None

class CriterionSignals(BaseModel):
    industry_fit: float; geography_fit: float; company_size_fit: float
    pain_point_evidence: float; buying_signal: float; contact_relevance: float
    recency: float; evidence_completeness: float   # each 0.0–1.0

class CompanyAnalysis(BaseModel):
    evidence: list[EvidenceItem]
    signals: CriterionSignals

# LanguageModelProvider (extended):
    async def analyze_company(
        self, *, icp: dict, offer: str | None, company_name: str, domain: str, page_text: str
    ) -> CompanyAnalysis: ...
```

- `FixtureSearchProvider` — a small in-memory catalog of demo companies
  tagged by industry/location keyword (same keyword-matching convention as
  Phase 2's `FixtureLanguageModelProvider`), returning 0–N matches per
  query so the "revise weak query" path is deterministically exercisable
  (a query with no matching keywords returns zero results).
- `FixtureWebsiteExtractionProvider` — returns canned page text for each
  fixture company's domain; one designated fixture domain always returns
  `None` (simulating an unreachable site) so FR-8's fallback path is
  deterministically testable.
- `FixtureLanguageModelProvider.analyze_company` — derives evidence and
  signals from the fixture page text deterministically (keyword presence
  → signal strength), and returns a shape with zero facts for a
  specifically-designated "thin" fixture company, so FR-10 is
  deterministically testable.
- `TavilySearchProvider` / `FirecrawlExtractionProvider` — real adapters
  via `httpx`, selected by `SEARCH_PROVIDER=tavily` /
  `EXTRACTION_PROVIDER=firecrawl` (+ the matching API key). Not exercised
  live in this environment — see Risks.

### Data model (new migration `0003_research.sql`)

- `campaigns.status` check constraint extended to add `running`,
  `completed`, `failed`, `paused`.
- `companies` (no RLS — global, service-role-write-only, not user data):
  `id`, `domain unique`, `name`, `facts jsonb`, `verified_at`,
  `created_at`, `updated_at`.
- `campaign_runs`: `id`, `campaign_id`, `status
  check in ('queued','running','completed','failed','paused')`,
  `stop_reason`, `pause_requested boolean default false`,
  `config_snapshot jsonb` (frozen weights+thresholds+limits+target count),
  `queries_used`, `leads_created`, `qualified_count`, `needs_review_count`,
  `rejected_count`, `failed_count`, `estimated_cost_usd numeric(10,2)`,
  `error`, `started_at`, `completed_at`, `created_at`, `updated_at`. RLS
  via `campaign_id → campaigns.user_id`.
- `leads`: `id`, `campaign_id`, `company_id`, `source_url`, `status
  check in ('qualified','needs_review','rejected')`, `score
  check between 0 and 100`, `decision_reason`, `created_at`, `updated_at`,
  `unique(campaign_id, company_id)`. RLS via `campaign_id`.
- `lead_evidence`: `id`, `lead_id`, `type
  check in ('fact','inference','unknown')`, `claim`, `excerpt`,
  `source_url`, `confidence numeric(3,2)`, `created_at`. RLS via
  `lead_id → leads → campaigns.user_id`.
- `score_breakdowns`: `id`, `lead_id`, `criterion check in (the 8 names)`,
  `rating numeric(3,2)`, `weight integer`, `points numeric(5,2)`,
  `created_at`, `unique(lead_id, criterion)`. RLS via `lead_id`.
- `agent_events`: `id`, `run_id`, `node`, `status check in ('ok','error')`,
  `summary`, `duration_ms`, `error`, `created_at`. RLS via `run_id`.
- `tool_calls`: `id`, `run_id`, `tool`, `provider`,
  `status check in ('ok','error')`, `summary`, `latency_ms`,
  `cost_usd numeric(10,4)`, `created_at`. RLS via `run_id`.

As in Phases 1–2, the frontend never queries these tables directly; only
the backend's service-role client does, always scoped through the
verified-JWT user id via the owning campaign.

---

## 4. Routes, Components, and Data/Auth Changes

### Backend routes (new/changed)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST | `/api/campaigns/:id/run` | owner-only | **changed** — now runs research (FR-1, FR-3) |
| POST | `/api/campaigns/:id/pause` | owner-only | FR-4 |
| GET | `/api/campaigns/:id/progress` | owner-only | FR-5 |
| GET | `/api/campaigns/:id/leads` | owner-only | FR-16 |
| GET | `/api/leads/:id` | owner-only | FR-17 |
| POST | `/api/leads/:id/rescore` | owner-only | FR-18 |
| GET | `/api/runs/:id/events` | owner-only | FR-19 |
| GET | `/api/runs/:id/tool-calls` | owner-only | FR-19 |

`PATCH /api/campaigns/:id` gains the FR-2 running-campaign guard.

### Frontend routes (new)

| Route | Type | Notes |
| --- | --- | --- |
| `/dashboard/campaigns/:id` | page | **extended** — progress/pause/timeline (FR-20) |
| `/dashboard/campaigns/:id/leads` | page | FR-21 |
| `/dashboard/campaigns/:id/leads/:leadId` | page | FR-22 |

### Data/auth changes

- New migration `supabase/migrations/0003_research.sql` (above).
- New env vars (backend, optional with safe defaults):
  `SEARCH_PROVIDER` (default `fixture`), `TAVILY_API_KEY`,
  `EXTRACTION_PROVIDER` (default `fixture`), `FIRECRAWL_API_KEY`.

---

## 5. Ordered Implementation Checklist

1. [x] Write this specification (`specs/phase-3-research.md`).
2. [x] Write migration `supabase/migrations/0003_research.sql`.
3. [x] Extend `backend/app/config.py` with search/extraction provider settings.
4. [x] Extend `backend/app/schemas.py` with evidence/signal/lead/run/event/tool-call models.
5. [x] Write `backend/app/scoring.py` (pure deterministic scoring).
6. [x] Extend `backend/app/providers.py`: `SearchProvider`, `WebsiteExtractionProvider`, fixture catalog, `analyze_company`, Tavily/Firecrawl adapters, factories.
7. [x] Extend `backend/app/database.py`: repositories for companies/leads/lead_evidence/score_breakdowns/campaign_runs/agent_events/tool_calls.
8. [x] Write `backend/app/agent.py` (LangGraph research graph).
9. [x] Rewrite `POST /campaigns/:id/run`; add `/pause`, `/progress`; add the FR-2 edit guard.
10. [x] Write `backend/app/routers/leads.py` and `backend/app/routers/runs.py`; mount both in `main.py`.
11. [x] Extend the in-memory fake Supabase client for the new tables.
12. [x] Write backend tests: scoring purity/determinism, fixture provider behavior (query-revision, extraction failure, thin-evidence rejection), full graph run via fixtures (target-reached / queries-exhausted / budget-exhausted stop reasons, dedup within a run and across runs), run idempotency, pause, edit-while-running guard, leads/runs endpoints + ownership, rescore.
13. [x] Extend `frontend/src/lib/types/api.ts` with Zod mirrors.
14. [x] Build progress/pause/timeline UI on the campaign detail page.
15. [x] Build `/dashboard/campaigns/:id/leads` and `/leads/:leadId` pages + components.
16. [x] Write frontend unit tests for new Zod schemas/components.
17. [x] Extend Playwright specs for the research flow (gated behind the same live-Supabase flag as Phases 1–2).
18. [x] Run all frontend and backend quality commands; fix failures.
19. [x] Re-review every Phase 3 acceptance criterion and testing item; fix gaps.

---

## 6. Acceptance Criteria

Directly from `plan.md` §17:

- AC-1: Confirmed campaign starts an idempotent run.
- AC-2: Agent revises weak queries only within limits.
- AC-3: Accepted facts include source evidence.
- AC-4: Unknown information is not fabricated.
- AC-5: Broken sites produce failure/fallback results.
- AC-6: Duplicate companies are merged.
- AC-7: Same inputs always produce the same numerical score.
- AC-8: Score breakdown links to evidence.
- AC-9: Low-score leads skip outreach.
- AC-10: Partial results survive failures.
- AC-11: Budget and retry limits are code-enforced.

### Verification status (end of Phase 3 implementation)

- **Met and verified (automated):** every AC above has a direct, passing
  test: AC-1 (`test_run_is_idempotent_when_already_active`), AC-2
  (`test_query_revision_recovers_a_weak_query_within_limits`), AC-3/AC-4
  (`EvidenceItem`'s own structural validator plus
  `test_processes_all_candidates_and_exhausts_queries`'s fact/unknown
  assertions), AC-5/AC-10 (the `brokenlink.example` extraction-failure
  case in the same test — persisted as a lead, run continues), AC-6
  (`TestCrossRunDedup`, both within-run and cross-campaign), AC-7
  (`TestScoringDeterminism`), AC-8 (breakdown-row assertions in the full-run
  test), AC-9 (no outreach code exists anywhere in this diff — see
  Non-goals), AC-11 (`test_target_reached_stops_after_enough_leads`,
  `test_budget_exhausted_stops_the_run`).
- **Implemented, not end-to-end verified (no live Supabase project in this
  environment):** the real-browser flow (run → watch progress → pause →
  inspect leads/evidence through the actual UI) and the migration's
  application via `supabase db reset`. Both are exercised by automated
  tests against fakes/fixtures instead — see §7.

---

## 7. Testing Checklist

### Backend

- [x] `ruff format --check .` passes.
- [x] `ruff check .` passes.
- [x] `pytest` passes (75 tests: 44 carried over from Phases 1–2 + 31 new),
  covering:
  - `scoring.py`: same signals+weights → same score every call (AC-7);
    breakdown rows sum to the total; rating×weight math verified by hand
    for at least one case.
  - Fixture search provider: a query matching the catalog returns results;
    a query matching nothing returns zero (drives query revision).
  - Fixture extraction provider: the designated broken domain returns
    `None`; a good domain returns text.
  - Fixture analysis: a "thin" fixture company yields zero facts; a normal
    one yields evidence with source/excerpt on every fact/inference and
    neither on unknowns (AC-3, AC-4).
  - Full graph run (via fixtures) end to end: produces qualified/
    needs-review/rejected leads with persisted evidence and score
    breakdowns linked to those leads (AC-8); a broken-site candidate
    yields a `rejected`/`extraction_failed` lead, not a crash (AC-5, AC-10);
    a repeated-domain candidate within one run produces exactly one lead,
    not two (AC-6, within-run half of dedup); the same domain reused
    across two different campaigns' runs reuses one `companies` row
    (AC-6, cross-run half); a run stops at `target_reached` once enough
    leads exist and at `queries_exhausted` when the plan runs out
    (AC-2, AC-11); a tiny `max_cost_usd` stops the run at
    `budget_exhausted` (AC-11).
  - `/run` idempotency: a campaign with an existing `running` run returns
    that run on a second call rather than creating another (AC-1).
  - `PATCH` on a `running`/`queued`/`paused` campaign returns
    `409 campaign_running`.
  - `/pause` on an active run sets `paused`/`paused_by_user`; 409 with no
    active run.
  - `/progress` reflects a completed run's counts; 404 with no run yet.
  - Leads/runs endpoints: ownership-scoped (cross-user 404), pagination,
    evidence/breakdown present on lead detail, `/rescore` changes the
    score when given different current weights without re-invoking any
    provider (and 409s on a lead that was never scored).
  - Also added beyond the original checklist: `/plan`, `/confirm-plan`,
    and `DELETE` are all blocked with `409 campaign_running` while a run
    is active (a gap found and closed during implementation — see
    Technical Design's edit-guard note and `TestEditGuard` in
    `tests/test_campaigns_run.py`).

### Frontend

- [x] `npm run format:check` passes.
- [x] `npm run lint` passes.
- [x] `npm run typecheck` passes.
- [x] `npm run test` passes (34 tests: 27 carried over from Phases 1–2 + 7
  new), covering the new Zod schemas (`EvidenceItem`, `CampaignRunResponse`,
  `LeadDetailResponse`, `AgentEventResponse`) and the `LeadStatusBadge`
  component.
- [x] `npm run build` succeeds.
- [x] `npm run test:e2e` — 5 non-auth-gated specs pass locally; the
  sign-up-flow, campaign-flow, and research-flow specs are all skipped
  without a live Supabase project (same `E2E_SUPABASE_LIVE` gate as
  Phases 1–2), not silently claimed passing.

### Manual/documented (not automatable without a live Supabase project)

- [ ] A real signed-in user can run a confirmed campaign, watch progress,
  pause it, and inspect leads/evidence/scores through the actual UI.
  **Not verified** — no live Supabase project in this environment. The
  `e2e/research-flow.spec.ts` spec exists and will exercise this the
  moment `E2E_SUPABASE_LIVE=1` is set against a real project with the
  backend running (fixture providers mean no other credentials are
  needed for this specific flow).
- [ ] `supabase/migrations/0003_research.sql` applies cleanly on top of
  `0001`/`0002` via `supabase db reset`. **Not verified** — no Supabase
  CLI/project linked here; reviewed manually for SQL correctness only.

---

## 8. Risks and Assumptions

- **Update (verified live, September 2026):** the assumption below no
  longer holds — the user supplied real Tavily/Firecrawl/Gemini keys and
  all three were tested directly. `TavilySearchProvider` and
  `FirecrawlExtractionProvider` worked exactly as written on the first
  try against real queries/URLs (no code changes needed). The Gemini
  default model needed updating — see `specs/phase-2-campaigns.md`
  Risks for details, since `generate_campaign_plan`/`analyze_company`
  share the same adapter. All research-graph logic is still covered by
  the fixture-provider test suite for CI/offline determinism; this note
  just records that the real adapters have now also been exercised
  end-to-end, not only reviewed.
- **Assumption:** `LLM_PROVIDER` continues to default to `fixture` (Phase
  2), and `SEARCH_PROVIDER`/`EXTRACTION_PROVIDER` follow the same
  zero-cost-by-default pattern — a full research run costs nothing and
  needs no credentials unless explicitly configured otherwise.
- **Risk — no true resume:** as stated in Non-goals, "pause" is a clean
  stop, not a checkpoint. A future phase wanting real resume-from-exact-
  position would need to persist `query_cursor`/`pending_candidates` on
  the run row and reload them — deliberately not built now since no Phase
  3 AC requires it and it adds real complexity (state serialization,
  staleness of re-loaded candidates) for a capability that isn't tested.
- **Risk — `leads.contact` deferred:** `plan.md` §12 lists `contact` as
  part of the `leads` table, but no Phase 3 scope bullet or AC calls for
  contact discovery, and stubbing a "sometimes populated" field without a
  real detection heuristic would be fabricated-looking behavior. Deferred
  to whichever phase actually builds `findPublicContact`; flagged here so
  it isn't mistaken for an oversight.
- **Risk — synthetic cost model:** fixture-mode `cost_usd`/
  `estimated_cost_usd` values are small fixed constants per tool call
  (e.g. so `max_cost_usd` is reachable in tests), not derived from any
  real provider's pricing. This is sufficient to prove the cost-limit code
  path is enforced (AC-11) but is explicitly not a real budget estimate —
  documented in `docs/providers.md` so it isn't mistaken for one when
  live providers are eventually enabled.
- **Risk — `handleRecoverableFailure`/`handleTerminalFailure` are not
  literal graph nodes:** see Technical Design's adaptation note. The
  observable behavior (partial-result preservation, per-candidate
  isolation, whole-run abort on infrastructure failure) is what the
  acceptance criteria actually test; the exact internal shape is an
  implementation choice.
- **Note — pre-existing gaps found and fixed along the way:** between
  Phase 2 and this phase, the user had manually patched `app/deps.py` to
  support Supabase's newer asymmetric (JWKS) and base64-encoded JWT
  secrets (fixing a real auth bug against their live project) but hadn't
  updated `requirements.txt` to pin the `cryptography` dependency that
  change now requires directly (it happened to work only because
  `supabase`'s own dependency tree pulled it in transitively) — fixed by
  pinning `PyJWT[crypto]` explicitly. Separately, the test fake's
  `_execute_insert` was adding an `updated_at` column to every table,
  including three (`lead_evidence`, `score_breakdowns`, `agent_events`,
  `tool_calls`) that don't have one in the real schema; this masked a
  router bug (`EvidenceItem(**item)` splatting raw DB columns including
  `id`/`lead_id`/`created_at` into a `extra="forbid"` Pydantic model) that
  would have failed against real Postgres. Both are fixed; see
  `app/routers/leads.py::_lead_to_detail` and
  `tests/fakes/supabase_fake.py::_NO_UPDATED_AT_TABLES`.
- **Non-decision needed:** none of the above affects security, cost, data
  ownership, or architecture beyond what `plan.md` already resolves
  (fixture-by-default for every new provider is `plan.md`'s own mandated
  safe default), so implementation proceeds without pausing for approval.
