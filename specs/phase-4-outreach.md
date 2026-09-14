# Phase 4 — Outreach, Approval, and Export

Status: Implementation
Owner: Primary coding agent (Claude Code)
Parent document: `plan.md` (§18, with supporting detail from §5, §7, §9, §10, §11, §12, §13, §14, §20–22)
Builds on: `specs/phase-1-foundation.md` (auth, provider-interface convention),
`specs/phase-2-campaigns.md` (campaigns/ICP, `LanguageModelProvider` pattern,
`database.py`/`providers.py` structure, fixture-first defaults),
`specs/phase-3-research.md` (leads/evidence/scoring, `companies`/`leads`/
`lead_evidence` tables, LangGraph research run, deterministic-code-enforces-
rules philosophy)

---

## 1. Goal, Scope, and Non-Goals

### Goal

Take a Phase 3 `qualified` lead the rest of the way to a human-approved,
exportable outreach draft: generate a grounded email/LinkedIn draft from the
lead's own stored evidence, run deterministic quality checks (grounding,
length, CTA/offer/observation structure, spam/tone blocklist) that regenerate
once on failure and otherwise flag the draft for review, put every draft in
front of a human reviewer who can edit/approve/reject it, enforce suppression
so a blocked contact can never enter approval, and let approved, non-
suppressed results be exported as CSV. No draft is ever auto-approved and no
email is ever sent without an explicit, disabled-by-default code path.

### Scope

- `LanguageModelProvider.draft_outreach()` — a new provider method, alongside
  Phase 2/3's `generate_campaign_plan()`/`analyze_company()`, that turns a
  lead's evidence into three separately-generated pieces (`observation`,
  `offer_line`, `cta`, plus a `subject` and `evidence_refs` pointing back at
  the specific evidence items grounding `observation`) — never a single
  freeform email body. `app/outreach.py` (new, pure/deterministic, mirroring
  `scoring.py`'s "LLM proposes, code enforces" split) assembles those pieces
  into the final email body with a fixed template and independently checks
  word count, evidence groundedness, and a spam/urgency-phrase blocklist —
  the "LLM may draft; deterministic code enforces the rules" split from
  `plan.md` §3 applies to outreach exactly as it already does to scoring.
- `POST /api/leads/:id/regenerate-outreach`: generates a new
  `outreach_drafts` version (email or LinkedIn) for a `qualified` lead,
  running the draft→assemble→quality-check cycle up to twice (FR-8) before
  accepting the result either way, and creates a fresh `pending` `approvals`
  row for it. Blocked for a suppressed company's lead (FR-9) — "entering
  approval" happens exactly here, at creation, not only at the approve click.
- `PATCH /api/leads/:id/status`: the manual disposition override Phase 3
  deferred (its own Non-goals section, "without an approval workflow around
  it this doesn't fit cleanly") — now that approvals exist, a user can
  promote a `needs_review` lead to `qualified` (so it becomes draftable) or
  demote a `qualified`/`needs_review` one to `rejected`.
- `outreach_drafts` (append-only version history per lead+channel) and
  `approvals` (one row per draft version; only the latest version per
  lead+channel is actionable) tables, plus `suppression_entries`
  (user-scoped, keyed by normalized domain — the only stable identifier
  available, since contact-email discovery is still deferred, see Phase 3
  Risks and this spec's own Risks).
- Approval queue and editor: `GET /api/approvals` (paginated, optional
  `status` filter, across all of the user's campaigns), `POST
  /api/approvals/:id/approve`, `POST /api/approvals/:id/reject`, `PATCH
  /api/approvals/:id/draft` (in-place subject/body edit — this, not
  regeneration, is what "editing invalidates approval" refers to: it resets
  an `approved`/`rejected` decision back to `pending`).
- `POST /api/campaigns/:id/export`: CSV of every lead whose latest-version
  draft (per channel) has an `approved` approval and whose company domain
  isn't suppressed for this user (checked again at export time, not just at
  approval time — defense in depth against suppression added after
  approval).
- Sender/offer configuration: `sender_name`/`sender_email` added to
  `campaigns` (alongside the existing `offer` from Phase 2), editable through
  the existing `PATCH /api/campaigns/:id`.
- `EmailProvider` interface (`plan.md` §5's fourth required interface,
  the only one not yet built) with `disabled` (default), `sandbox`, and
  `live` (Resend) adapters, plus a minimal, explicitly human-in-the-loop
  `POST /api/approvals/:id/send` (§18's "Optional Resend sandbox" bullet) —
  see Non-goals for why it takes an explicit `to_email` rather than looking
  one up.
- Frontend: lead detail page gains an outreach section (generate/regenerate,
  inline edit, approve/reject); a new `/dashboard/approvals` queue page; the
  campaign detail page gains a sender-info form and an "Export CSV" action.

### Non-goals (Phase 4)

- Contact/email discovery. Still deferred from Phase 3 (its own Risks
  section). `POST /api/approvals/:id/send` therefore takes an explicit,
  human-supplied `to_email` in the request body rather than reading one off
  the lead — the human stays the one who knows (or looks up) the actual
  recipient; inventing or guessing a contact address would be exactly the
  fabricated-looking behavior `plan.md` §4 forbids.
- Automatic outreach drafting as part of the Phase 3 research graph. A
  qualified lead does **not** get a draft the moment `decide_qualification`
  persists it — sender/offer configuration (this phase's own scope item)
  usually doesn't exist yet at research-run time, and Phase 3 explicitly
  scoped `draftOutreach`/`qualityCheckDraft` out of that graph for the same
  reason. Drafting is a separate, explicit, user-triggered action
  (`regenerate-outreach`), matching this phase's own precedent for
  post-run, on-demand actions (`rescore`, Phase 3 FR-18).
- `GET /api/campaigns/:id/analytics`. Listed in `plan.md` §13's API overview
  but scoped to Phase 5 ("funnel, cost, latency, and failure analytics" is a
  Phase 5 bullet, `plan.md` §19) — not implemented here.
- A dedicated suppression-management API surface beyond what's needed to
  make the compliance rule real (`plan.md` §13 lists no suppression routes
  at all). This spec adds a minimal `POST/GET /api/suppression` and `DELETE
  /api/suppression/:id` — a documented, necessary addition in the same
  spirit as Phase 3's own beyond-checklist additions (that spec's Technical
  Design and Testing sections), not a speculative feature.
- Real, durable delivery tracking (a `sent_emails` log, retries, bounce
  handling). `POST /api/approvals/:id/send`'s response *is* the audit
  record for this MVP (disabled/sandboxed/sent, returned synchronously);
  persisting a send history is real product work with no Phase 4 AC
  requiring it.
- Multi-recipient / bulk sending, reply handling, or follow-up sequences —
  explicit MVP non-goals (`plan.md` §2).
- Any change to Phase 1–3 auth, campaign CRUD, plan generation, or research
  behavior beyond adding `sender_name`/`sender_email` to the campaign schema
  and the new `PATCH /api/leads/:id/status` action.

---

## 2. Functional Requirements

### Drafting

- FR-1: `LanguageModelProvider.draft_outreach(icp, offer, company_name,
  domain, evidence, channel, sender_name, attempt)` returns `subject`,
  `observation`, `offer_line`, `cta` (all non-blank strings — enforced by
  Pydantic, so the model literally cannot return an empty piece) and
  `evidence_refs: list[int]`, indices into the **caller-supplied** `evidence`
  list (the lead's actual stored `lead_evidence` rows, in stored order —
  never re-derived or re-fetched from a fixture catalog) that ground
  `observation`. An empty `evidence_refs` is a legal return value (it fails
  the quality check, it doesn't fail validation) — the "nothing invented"
  path from Phase 3 applies here too: an LLM that can't ground its claim
  must say so via an empty list, not fabricate a plausible-looking index.
- FR-2: `app/outreach.py::assemble_body()` builds the final email body
  deterministically from `observation` + `offer_line` (falls back to a
  generic line when `offer` is unset) + `cta`, plus a fixed greeting
  (`"Hi {company_name} team,"`) and signoff (`sender_name` if configured,
  else `"Best regards"`) — the LLM never sees or controls the greeting/
  signoff, so "one observation, one offer, one CTA" (`plan.md` §11) is
  structural, not a hope about model compliance.
- FR-3: `app/outreach.py::check_quality()` is a pure function of
  `(body, evidence_refs, evidence)` returning `(passed: bool, reasons:
  list[str])`. It fails when: the assembled body is 130 words or more
  (`plan.md` §11's "stays below 130 words"); `evidence_refs` is empty, or
  any index is out of range or refers to an `"unknown"`-type evidence item
  (grounding must point at a `fact`/`inference`, never at an item that by
  definition has no excerpt/source — AC "no unsupported personalized
  claims"); or the body contains a blocklisted spam/false-urgency phrase
  (a small fixed list — e.g. "act now", "100% free", "risk-free", "buy now",
  "limited time", "guarantee", "$$$", "no obligation" — case-insensitive
  substring match). This is a deterministic heuristic, not a claim of
  semantic fact-checking; documented as such in Risks.
- FR-4: `POST /api/leads/:id/regenerate-outreach` (body: `{"channel":
  "email" | "linkedin"}`, default `"email"`) requires `lead.status ==
  "qualified"` (409 `lead_not_qualified` otherwise — this is what "low-score
  leads skip outreach" means in force now that drafting actually exists) and
  that the lead's company domain isn't suppressed for the current user (409
  `domain_suppressed` — see FR-9).
- FR-5: Given those checks pass, the endpoint calls `draft_outreach` with
  `attempt=0`, assembles and quality-checks the result; if it fails, calls
  `draft_outreach` again with `attempt=1`, assembles and checks again; the
  **second** attempt's result is kept regardless of outcome. `quality_status
  = "passed"` if the kept attempt passed, else `"needs_review"` — "failed
  quality checks regenerate once, then require review" (`plan.md` §18)
  literally: exactly one regeneration, and a still-failing draft is saved
  (visible for human review), never silently discarded or blocked from being
  saved.
- FR-6: The new draft is inserted as `version = (current max version for
  this lead+channel) + 1` (starts at 1) — `outreach_drafts` rows are
  append-only; nothing is ever updated or deleted by regeneration, so every
  prior version stays queryable ("versions remain accessible").
- FR-7: A new `approvals` row (`status="pending"`, `edited=false`) is
  created for the new draft. Prior approvals for earlier versions of the
  same lead+channel are left untouched (historical) — they were never
  mutated and aren't reachable from any "current" query, but the rows exist.
- FR-8: (see FR-5; stated separately in `plan.md` as its own AC) — this is
  the concrete mechanism behind "failed quality checks regenerate once, then
  require review."
- FR-9: Suppression is enforced primarily at draft-creation time (FR-4) —
  "cannot enter approval" (`plan.md` §11) is read literally: creating the
  `approvals` row *is* entering approval, so the block happens before that
  row can ever exist. It is enforced **again** at `POST
  /api/approvals/:id/approve` (409 `domain_suppressed`) as defense in depth,
  since a domain can be suppressed after a draft/approval already exists.

### Manual status override

- FR-10: `PATCH /api/leads/:id/status` (body: `{"status": "qualified" |
  "needs_review" | "rejected", "reason": str | None}`, owner-only) sets
  `leads.status` and `leads.decision_reason` (to `reason`, or
  `"manual_override"` if omitted). Score and score breakdown are untouched —
  this changes the disposition, not the evaluation. Allowed from any status
  to any other status (a human overriding the agent's call is definitionally
  allowed to go either direction); setting the same status is a no-op 200,
  not an error.

### Approval queue and editing

- FR-11: `GET /api/approvals` (owner-scoped across **all** of the user's
  campaigns, paginated, optional `?status=pending|approved|rejected`)
  returns each approval with its draft, and enough lead/company/campaign
  context (`campaign_id`, company summary, lead status/score) to render a
  queue row without a second round trip.
- FR-12: `POST /api/approvals/:id/approve` requires `status != "approved"`
  is not enforced (re-approving is a harmless no-op, just refreshes
  `decided_at`/`reviewer_id`) but **does** require the parent lead to still
  be `"qualified"` (409 `lead_not_qualified` — closes the gap where a lead
  was manually demoted via FR-10 after a draft was already queued) and the
  company to be unsuppressed (FR-9). Sets `status="approved"`,
  `reviewer_id=current_user.id`, `decided_at=now`.
- FR-13: `POST /api/approvals/:id/reject` (body: `{"reason": str | None}`,
  optional) sets `status="rejected"`, `reviewer_id`, `decided_at`. No
  suppression/qualification gate — rejecting is always allowed.
- FR-14: `PATCH /api/approvals/:id/draft` (body: `{"subject": str | None,
  "body": str | None}`, at least one required) mutates the **current**
  draft's `subject`/`body` in place (no new version — this is a correction,
  not a regeneration) and sets `approvals.edited = true`. If the approval's
  `status` was `"approved"` or `"rejected"`, it resets to `"pending"` and
  clears `reviewer_id`/`decided_at` — "editing an approved draft invalidates
  approval" (`plan.md` §11), and the same logic naturally covers a rejected
  one (there's no reason editing-then-resubmitting should require a status
  no rejection path produces).
- FR-15: AI code (the research graph, the drafting endpoint itself) never
  calls `/approve` or `/reject` — those routes require an authenticated
  human `current_user` exactly like every other owner-scoped route. "AI
  cannot approve drafts" holds structurally: there is no code path from
  `app/agent.py` or `app/outreach.py` to `database.update_approval`.

### Export and sending

- FR-16: `POST /api/campaigns/:id/export` returns `text/csv`. A row is
  included only for a lead+channel whose **latest-version** draft has an
  `approved` approval and whose company domain is not currently suppressed
  for this user (re-checked at export time, not cached from approval time).
  Columns: `lead_id, company_name, domain, source_url, score, status,
  channel, subject, body, approved_at, reviewer_email`. An
  unapproved/rejected/pending draft, or one for a now-suppressed domain,
  never appears — "unapproved drafts cannot be exported/sent as approved."
- FR-17: `POST /api/approvals/:id/send` (body: `{"to_email": EmailStr}`)
  requires `approvals.status == "approved"`, `lead.status == "qualified"`,
  and an unsuppressed domain (same three gates as export, applied to one
  row). Calls `EmailProvider.send(to_email, subject, body)` and returns its
  result verbatim (`status: "disabled" | "sandboxed" | "sent"`). With the
  default `EMAIL_MODE=disabled`, this is a real, exercised code path that
  does nothing — not an unimplemented stub — which is what "real sending is
  disabled by default" means concretely.

### Sender configuration

- FR-18: `CampaignCreateRequest`/`CampaignUpdateRequest`/`CampaignResponse`
  gain optional `sender_name: str | None` and `sender_email: EmailStr |
  None`, stored on `campaigns` and editable through the existing `PATCH
  /api/campaigns/:id` (no new endpoint needed — this is exactly the kind of
  field Phase 2's generic campaign-patch mechanism already handles).
  Editing these fields does **not** trigger the `_REVERT_ON_EDIT_STATUSES`
  draft-to-`draft`-status behavior (`app/routers/campaigns.py`) the way
  `score_weights`/`icp` edits do — sender info doesn't affect plan/research
  validity, only future drafts' signoff line.

---

## 3. Technical Design

### Backend file layout (extends Phase 3's layout)

```text
backend/app/
├── main.py             # + approvals, suppression routers mounted
├── config.py           # + EMAIL_MODE, RESEND_API_KEY
├── schemas.py          # + outreach/approval/suppression models, sender fields on campaign models
├── database.py         # + outreach_drafts/approvals/suppression_entries repositories
├── providers.py        # + LanguageModelProvider.draft_outreach, EmailProvider + adapters
├── outreach.py          # NEW — deterministic assembly + quality checks (mirrors scoring.py)
└── routers/
    ├── campaigns.py      # + POST /:id/export
    ├── leads.py           # + PATCH /:id/status, POST /:id/regenerate-outreach
    ├── approvals.py       # NEW
    └── suppression.py     # NEW
```

### Provider interfaces (extends `app/providers.py`)

```python
class DraftOutreachResult(BaseModel):
    subject: str          # min_length=1
    observation: str       # min_length=1
    offer_line: str         # min_length=1
    cta: str                 # min_length=1
    evidence_refs: list[int]  # may be empty (fails quality, not validation)

# LanguageModelProvider (extended):
    async def draft_outreach(
        self, *, icp: dict, offer: str | None, company_name: str, domain: str,
        evidence: list[EvidenceItem], channel: Literal["email", "linkedin"],
        sender_name: str | None, attempt: int = 0,
    ) -> DraftOutreachResult: ...

class EmailSendResult(BaseModel):
    status: Literal["disabled", "sandboxed", "sent"]
    provider_message_id: str | None = None

class EmailProvider(Protocol):
    async def send(self, *, to_email: str, subject: str, body: str) -> EmailSendResult: ...
```

- `FixtureLanguageModelProvider.draft_outreach` — deterministic: picks the
  first `fact`-or-`inference` item in the **passed-in** `evidence` list as
  `evidence_refs`/`observation` source. One fixture company (new:
  `"Thinclaim Robotics"`, `draft_ungroundable: True`, otherwise a normal
  easily-qualified company — software/Berlin) is special-cased to return
  `evidence_refs=[]` regardless of `attempt`, so the "regenerate once, then
  `needs_review`" path (FR-5/FR-8) is deterministically reachable in tests
  without relying on real model non-determinism — the same pattern as
  Phase 3's `thin`/`broken` flags.
- `GeminiLanguageModelProvider.draft_outreach` — real adapter via `httpx`,
  prompted with the evidence list *indexed* so the model can return
  `evidence_refs` against genuine indices; not live-tested in this
  environment (same posture as `analyze_company` before the user supplied
  real keys — see Phase 2/3 Risks).
- `DisabledEmailProvider` (default) — returns `EmailSendResult(status=
  "disabled")` without any network call.
- `SandboxEmailProvider` — returns `status="sandboxed"`, no network call
  (a clearly-labeled no-op for demoing the "would have sent" path).
- `ResendEmailProvider` — real adapter via `httpx` to the Resend API,
  opt-in, requires `RESEND_API_KEY`; not live-tested in this environment.
- `get_email_provider(settings)` selects by `settings.email_mode`
  (`"disabled"` default → `DisabledEmailProvider`, `"sandbox"` →
  `SandboxEmailProvider`, `"live"` → `ResendEmailProvider`).

### `app/outreach.py`

```python
MAX_WORDS = 130
BLOCKLIST = ("act now", "100% free", "risk-free", "buy now", "limited time",
             "guarantee", "$$$", "no obligation", "click here now", "urgent")

def assemble_body(*, company_name, sender_name, observation, offer_line, cta) -> str: ...
def check_quality(*, body: str, evidence_refs: list[int],
                   evidence: list[EvidenceItem]) -> tuple[bool, list[str]]: ...
```

Both are pure functions — no I/O, no provider calls — so they're unit-tested
directly, the same way `scoring.compute_score` is.

### Data model (new migration `0004_outreach.sql`)

- `campaigns`: `+ sender_name text`, `+ sender_email text`.
- `outreach_drafts`: `id`, `lead_id → leads(id) on delete cascade`,
  `channel check in ('email','linkedin')`, `subject`, `body`,
  `version integer check (version >= 1)`,
  `quality_status check in ('passed','needs_review')`,
  `evidence_refs jsonb not null default '[]'`, `created_at`, `updated_at`,
  `unique(lead_id, channel, version)`. RLS via `lead_id → leads →
  campaigns.user_id` (same join-through pattern as `lead_evidence`).
- `approvals`: `id`, `draft_id → outreach_drafts(id) on delete cascade
  unique` (one approval per draft version), `status check in ('pending',
  'approved','rejected') default 'pending'`, `reviewer_id → auth.users(id)`,
  `decided_at`, `edited boolean not null default false`, `created_at`,
  `updated_at`. RLS via `draft_id → outreach_drafts → leads →
  campaigns.user_id`.
- `suppression_entries`: `id`, `user_id → auth.users(id) on delete cascade`,
  `domain text not null`, `reason text`, `created_at`,
  `unique(user_id, domain)`. RLS: `user_id = auth.uid()` directly (same
  shape as `campaigns`, not join-through).

---

## 4. Routes, Components, and Data/Auth Changes

### Backend routes (new/changed)

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| PATCH | `/api/leads/:id/status` | owner-only | FR-10 |
| POST | `/api/leads/:id/regenerate-outreach` | owner-only | FR-4–FR-9 |
| GET | `/api/approvals` | owner-only (cross-campaign) | FR-11 |
| POST | `/api/approvals/:id/approve` | owner-only | FR-12 |
| POST | `/api/approvals/:id/reject` | owner-only | FR-13 |
| PATCH | `/api/approvals/:id/draft` | owner-only | FR-14 |
| POST | `/api/approvals/:id/send` | owner-only | FR-17 — beyond `plan.md` §13's literal list, see Non-goals |
| POST | `/api/campaigns/:id/export` | owner-only | FR-16 |
| POST | `/api/suppression` | owner-only | addition, see Non-goals |
| GET | `/api/suppression` | owner-only | addition, see Non-goals |
| DELETE | `/api/suppression/:id` | owner-only | addition, see Non-goals |

`PATCH /api/campaigns/:id` gains `sender_name`/`sender_email` (FR-18, no new
route). `GET /api/leads/:id` response gains an `approvals` array (all
versions across both channels, newest first) so the lead detail page can
render/act on drafts without a separate endpoint.

### Frontend routes (new)

| Route | Type | Notes |
| --- | --- | --- |
| `/dashboard/campaigns/:id/leads/:leadId` | page | **extended** — outreach section |
| `/dashboard/campaigns/:id` | page | **extended** — sender form, export button |
| `/dashboard/approvals` | page | NEW — cross-campaign approval queue |

### Data/auth changes

- New migration `supabase/migrations/0004_outreach.sql` (above).
- New env vars (backend, optional with safe defaults): `EMAIL_MODE` (default
  `disabled`), `RESEND_API_KEY`.

---

## 5. Ordered Implementation Checklist

1. [x] Write this specification (`specs/phase-4-outreach.md`).
2. [x] Write migration `supabase/migrations/0004_outreach.sql`.
3. [x] Extend `backend/app/config.py` with `EMAIL_MODE`/`RESEND_API_KEY`.
4. [x] Extend `backend/app/schemas.py` with outreach/approval/suppression
   models and sender fields on campaign models.
5. [x] Write `backend/app/outreach.py` (pure assembly + quality checks).
6. [x] Extend `backend/app/providers.py`: `draft_outreach` (fixture +
   Gemini), `EmailProvider` + three adapters, factory.
7. [x] Extend `backend/app/database.py`: repositories for
   outreach_drafts/approvals/suppression_entries.
8. [x] Extend `backend/tests/fakes/supabase_fake.py` for the three new
   tables.
9. [x] Write `backend/app/routers/leads.py` additions (`/status`,
   `/regenerate-outreach`) and extend `LeadDetailResponse`.
10. [x] Write `backend/app/routers/approvals.py` and
    `backend/app/routers/suppression.py`; mount both in `main.py`.
11. [x] Extend `backend/app/routers/campaigns.py` with `/export`; add
    sender fields to the campaign row mapper.
12. [x] Write backend tests: `outreach.py` purity (assembly, quality-check
    pass/fail cases including each blocklist/length/grounding reason),
    fixture `draft_outreach` determinism (normal + `draft_ungroundable`),
    regenerate-outreach (qualified-only gate, suppressed-domain gate,
    version increment, regenerate-once-then-needs_review), manual status
    override, approvals list/approve/reject/edit-invalidates-approval/
    ownership, export (approved-only, suppressed-excluded, CSV shape),
    send (disabled-by-default), suppression CRUD + ownership.
13. [x] Extend `frontend/src/lib/types/api.ts` with Zod mirrors.
14. [x] Extend `frontend/src/lib/validation/campaigns.ts` with a sender-info
    form schema.
15. [x] Build the outreach section on the lead detail page (generate/
    regenerate, inline edit, approve/reject) as a shared
    `OutreachDraftCard` component.
16. [x] Build `/dashboard/approvals` (queue page, reusing
    `OutreachDraftCard`) and add it to `DashboardNav`.
17. [x] Add the sender-info form and export button to the campaign detail
    page.
18. [x] Write frontend unit tests for new Zod schemas/components.
19. [x] Extend Playwright specs for the outreach flow (gated behind the
    same `E2E_SUPABASE_LIVE` flag as Phases 1–3).
20. [x] Run all frontend and backend quality commands; fix failures.
21. [x] Re-review every Phase 4 acceptance criterion and testing item; fix
    gaps.

---

## 6. Acceptance Criteria

Directly from `plan.md` §18:

- AC-1: Drafts contain no unsupported personalized claims.
- AC-2: Drafts follow configured length and CTA rules.
- AC-3: Failed quality checks regenerate once, then require review.
- AC-4: Versions remain accessible.
- AC-5: AI cannot approve drafts.
- AC-6: Editing invalidates approval.
- AC-7: Suppressed contacts remain blocked.
- AC-8: Unapproved drafts cannot be exported/sent as approved.
- AC-9: Approval records include reviewer, time, and version.
- AC-10: Real sending is disabled by default.

### Verification status (end of Phase 4 implementation)

- **Met and verified (automated):** AC-1 (`check_quality`'s grounding rule —
  `evidence_refs` must reference a `fact`/`inference` —
  `TestCheckQuality::test_fails_when_ref_points_at_an_unknown_item` plus
  `TestRegenerateOutreach::test_ungroundable_fixture_ends_needs_review_after_two_attempts`),
  AC-2 (`check_quality`'s length/blocklist rules, unit-tested directly in
  `test_outreach.py`), AC-3
  (`test_ungroundable_fixture_ends_needs_review_after_two_attempts` — two
  attempts, both fail, `quality_status="needs_review"` is saved, not
  discarded), AC-4 (`test_version_increments_across_repeated_calls` — both
  versions independently fetchable via the lead's `approvals` list), AC-5
  (structural — no code path from `app/agent.py`/`app/outreach.py` to
  `database.create_approval`/`update_approval`; every approve/reject test
  drives the route through an authenticated `current_user`), AC-6
  (`TestEditDraft::test_edits_in_place_and_invalidates_approval` and
  `test_editing_a_rejected_draft_also_resets_to_pending`), AC-7
  (`TestApprove::test_blocked_when_domain_suppressed`,
  `TestRegenerateOutreach::test_blocked_for_a_suppressed_domain`,
  `test_export_excludes_suppressed_domain`), AC-8
  (`test_export_only_includes_approved_latest_version`), AC-9 (schema-level:
  `ApprovalResponse.reviewer_id`/`decided_at` populated on approve, plus
  `draft.version`; asserted in `TestApprove::test_sets_reviewer_and_timestamp`),
  AC-10 (`TestSend::test_disabled_by_default`).
- **Implemented, not end-to-end verified (no live Supabase project in this
  environment):** the real-browser flow (generate a draft, edit it, approve
  it, export CSV, hit send while disabled) through the actual UI. Exercised
  instead by `e2e/outreach-flow.spec.ts`, gated the same way as Phases 1–3's
  live-Supabase specs.

---

## 7. Testing Checklist

### Backend

- [x] `ruff format --check .` passes.
- [x] `ruff check .` passes.
- [x] `pytest` passes (121 tests: 76 carried over from Phases 1–3 + 45 new),
  covering:
  - `outreach.py`: `assemble_body` produces the expected greeting/body/
    signoff shape; `check_quality` fails on each of length/grounding/
    blocklist independently and passes a clean input (AC-1, AC-2).
  - Fixture `draft_outreach`: a normal qualified lead's evidence yields a
    valid, groundable result; the `draft_ungroundable` fixture company
    yields `evidence_refs=[]` on both attempts.
  - `regenerate-outreach`: 409 on a non-`qualified` lead; 409 on a
    suppressed domain (no draft/approval row created); version increments
    across repeated calls for the same lead+channel; the ungroundable
    fixture ends with `quality_status="needs_review"` after exactly two
    attempts, and the draft/approval are still persisted (AC-3, AC-4).
  - `PATCH /leads/:id/status`: updates status/decision_reason, leaves
    score/breakdown untouched, ownership-scoped.
  - Approvals: `GET /approvals` lists across campaigns with optional
    status filter, ownership-scoped; `/approve` sets reviewer/decided_at
    and requires `qualified` + unsuppressed (AC-5, AC-7, AC-9); `/reject`
    always allowed; `PATCH .../draft` edits in place and resets both an
    `approved` and a `rejected` decision back to `pending`, clearing
    reviewer/decided_at (AC-6).
  - Export: only latest-version `approved` drafts appear; a suppressed
    domain's approved draft is excluded even though it was approved before
    suppression; CSV columns match spec (AC-7, AC-8).
  - Send: default `EMAIL_MODE=disabled` returns `status="disabled"` and
    makes no network call; blocked when approval isn't `approved`, lead
    isn't `qualified`, or domain is suppressed (AC-10).
  - Suppression: create/list/delete, ownership-scoped, idempotent create
    (adding the same domain twice doesn't duplicate).

### Frontend

- [x] `npm run format:check` passes.
- [x] `npm run lint` passes.
- [x] `npm run typecheck` passes.
- [x] `npm run test` passes (48 tests: 34 carried over from Phases 1–3 + 14
  new), covering the new Zod schemas (`OutreachDraftResponse`,
  `ApprovalResponse`, `LeadDetailWithApprovalsResponse`), the quality/
  approval status badges, and `OutreachDraftCard`'s approve/reject-button
  visibility by status and edit-mode switch. (Also fixed along the way:
  `vitest.setup.ts` wasn't registering Testing Library's `afterEach`
  cleanup — harmless while every prior test file rendered each status
  value's text at most once across its `it()` blocks, but it surfaced as
  false "multiple elements found" failures once a component test needed
  the same button text in more than one `it()`. Fixed by registering
  `cleanup()` explicitly; unrelated to any Phase 4 behavior.)
- [x] `npm run build` succeeds.
- [x] `npm run test:e2e` — existing non-auth-gated specs still pass; the new
  `outreach-flow.spec.ts` is skipped without a live Supabase project (same
  `E2E_SUPABASE_LIVE` gate as Phases 1–3), not silently claimed passing.

### Manual/documented (not automatable without a live Supabase project)

- [ ] A real signed-in user can generate a draft, edit it, approve it,
  export a CSV, and see a disabled-send result through the actual UI.
  **Not verified** — no live Supabase project in this environment;
  `e2e/outreach-flow.spec.ts` exists and will exercise this the moment
  `E2E_SUPABASE_LIVE=1` is set (fixture providers mean no other credentials
  are needed for this specific flow).
- [ ] `supabase/migrations/0004_outreach.sql` applies cleanly on top of
  `0001`–`0003` via `supabase db reset`. **Not verified** — no Supabase CLI/
  project linked here; reviewed manually for SQL correctness only.

---

## 8. Risks and Assumptions

- **Risk — suppression is domain-scoped, not contact-scoped:** `plan.md`
  §12 describes `suppression_entries` as keyed by "normalized email/domain
  hash," but no contact email exists yet in this system (Phase 3 Risks,
  reaffirmed in this spec's Non-goals). Domain is the only stable identifier
  available, so that's what's enforced. Once contact discovery is built, a
  finer-grained email-level suppression should be added alongside it — this
  is a real, documented gap, not a silent shortcut.
- **Risk — quality checks are deterministic heuristics, not semantic
  fact-checking:** `check_quality`'s grounding rule verifies that a claimed
  evidence index exists and is a `fact`/`inference` — it cannot verify that
  the generated `observation` text actually, semantically matches that
  evidence item's claim. A model could reference a valid index while
  drafting a loosely-related sentence. Closing this fully would need a
  second LLM call (an actual "does this claim match this evidence" judge),
  which this phase doesn't add — consistent with `plan.md` §20's own
  separation of deterministic tests from probabilistic LLM evals (that kind
  of check belongs in Phase 5's evaluation suite, not as a blocking runtime
  gate).
- **Risk — `POST /api/approvals/:id/send` takes a human-supplied
  `to_email`:** this is a deliberate design choice (see Non-goals) to avoid
  fabricating contact data, but it does mean "sending" isn't a one-click
  action yet — the user must know or find the recipient's address
  themselves. Documented here so it isn't mistaken for an oversight when
  contact discovery is eventually built.
- **Risk — `EmailProvider`'s `sandbox`/`live` modes are unverified live in
  this environment:** no `RESEND_API_KEY` was supplied here, so
  `ResendEmailProvider` is reviewed for correctness only, following the
  exact same posture Phase 2/3 used for Gemini/Tavily/Firecrawl before the
  user supplied real keys for those.
- **Assumption:** `EMAIL_MODE` continues the zero-cost-by-default pattern
  (`plan.md` §21) — `disabled` requires no credentials and every Phase 4
  test runs against it; `sandbox`/`live` are opt-in.
- **Non-decision needed:** none of the above affects security, cost, data
  ownership, or architecture beyond what `plan.md` already resolves
  (disabled-by-default sending, fixture-by-default providers, human
  approval before any external action are all `plan.md`'s own mandated
  defaults), so implementation proceeds without pausing for approval.
