# Siftora — Lightweight Spec-Driven Development Plan

## 1. Product Overview

**Product name:** Siftora  
**Subtitle:** Agentic Lead Intelligence Platform  
**Portfolio category:** Agentic AI / Full-Stack AI / AI Automation  
**Primary users:** Freelancers, agencies, B2B sales teams, and AI automation providers

### One-line pitch

> Siftora researches companies, verifies evidence, qualifies prospects, drafts personalized outreach, and requires human approval before any external action.

### Example campaign

> Find 20 animation and design agencies in Dubai with 5–50 employees, an active website, and signs that they could benefit from AI customer support or workflow automation. Exclude recruitment agencies and companies without a working website.

Siftora converts this brief into a structured ideal customer profile, creates a search plan, discovers potential companies, analyzes their public websites, rejects irrelevant or duplicate results, calculates an explainable score, prepares evidence-based outreach, and places every draft in a human approval queue.

---

## 2. Goals and MVP Boundary

### Primary goals

1. Demonstrate genuine agentic behavior rather than a single LLM prompt.
2. Solve a commercially understandable lead-generation problem.
3. Show Next.js full-stack frontend, FastAPI/Python AI backend, LangGraph, tool calling, database, and automation skills.
4. Produce leads whose facts and personalization are backed by visible sources.
5. Keep the user in control of outreach through mandatory approval.
6. Provide a polished deployed portfolio experience.

### MVP capabilities

- Email/password authentication
- Campaign creation from natural language
- Structured ideal customer profile (ICP)
- AI-generated research plan with user confirmation
- Web search through a replaceable provider
- Company website extraction and analysis
- Evidence URLs and extracted evidence snippets
- Lead validation, rejection reasons, and deduplication
- Configurable deterministic 0–100 scoring
- Personalized email and LinkedIn-message drafts
- Human approval, edit, reject, and regenerate actions
- CSV export of approved results
- Disabled or sandboxed email delivery
- Campaign progress, tool logs, costs, and agent timeline
- Basic evaluation and analytics
- Production deployment with fixture/demo mode

### Non-goals for MVP

- Fully autonomous bulk emailing
- Unauthorized LinkedIn scraping or automated LinkedIn messaging
- Guessing or purchasing private personal information
- Advanced CRM integrations
- Automated reply handling or follow-up sequences
- Multi-tenant subscriptions and billing
- Mobile app or browser extension
- Custom model training or fine-tuning

---

## 3. Why Siftora Is Agentic

Siftora must not be a fixed n8n sequence or one large prompt. It qualifies as an agentic system because it will:

1. Interpret an open-ended campaign goal.
2. Convert the goal into a structured plan.
3. Decide which research tool to use.
4. Evaluate whether a result is relevant and supported.
5. Revise weak search queries within fixed limits.
6. Use an alternate source when a website fails.
7. Reject irrelevant, duplicate, or unsupported candidates.
8. Maintain state across a long-running workflow.
9. Stop when target, budget, time, or retry limits are reached.
10. Pause before external actions and wait for human approval.
11. Recover safely from tool failures without inventing results.
12. Record an auditable summary of each action and decision.

The LLM may interpret, classify, extract, and recommend. Deterministic application code must enforce scoring math, permissions, limits, suppression rules, approvals, exports, and sending restrictions.

---

## 4. Lightweight SDD Workflow

This project uses practical spec-driven development. It avoids four documents per feature and uses one complete specification per phase.

### Required documents

```text
plan.md                         # Product-level source of truth
specs/
├── phase-1-foundation.md       # Foundation, landing, auth and database
├── phase-2-campaigns.md        # Campaigns, ICP and planning
├── phase-3-research.md         # Discovery, analysis and scoring
├── phase-4-outreach.md         # Drafts, approvals and export
└── phase-5-production.md       # Evaluation, hardening and deployment
```

### Contents of every phase specification

Each phase uses one Markdown file containing:

1. Goal
2. Scope
3. Non-goals
4. Functional requirements
5. Technical design
6. Data, API, and UI changes
7. Ordered implementation checklist
8. Acceptance criteria
9. Testing checklist
10. Risks and assumptions

### One-prompt-per-phase process

For each phase, the primary coding agent must:

1. Read this plan and inspect the repository.
2. Create or refine the phase specification.
3. Review it internally for contradictions.
4. Implement without waiting unless a decision affects security, cost, data ownership, or fundamental architecture.
5. Work through the checklist in order.
6. Verify tasks before marking them complete.
7. Run the complete phase test suite.
8. Compare results against acceptance criteria.
9. Stop before the next phase and report results.

### Coding-agent rules

- Use one primary coding agent per branch.
- Do not let Codex and Claude Code edit the same branch simultaneously.
- A second agent may perform read-only review.
- Inspect Git status and preserve user changes.
- Do not silently change requirements or architecture.
- Do not add fake behavior and claim it works.
- Mock providers only through explicit adapters and label demo data.
- Never commit secrets or expose server credentials to the browser.
- Use migrations for database changes.
- Store concise decision summaries, never hidden chain-of-thought.
- Do not mark tasks complete while relevant checks fail or are skipped.
- Stop at the active phase boundary.

---

## 5. Technology Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | Next.js + TypeScript | Landing page and dashboard |
| UI | Tailwind CSS + shadcn/ui | Accessible polished interface |
| Backend | FastAPI + Python | API, validation, and business logic |
| API schemas | Pydantic | Authoritative request/response models |
| Frontend validation | Zod | Forms and client-side validation |
| Frontend packages | npm | Standard dependency management |
| Python environment | `venv` + `pip` | Simple isolated backend setup |
| Agent | LangGraph Python | State, routing, retries, and interrupts |
| LLM | Gemini API | Planning, extraction, analysis, and drafting |
| Database | Supabase PostgreSQL | Application data |
| Authentication | Supabase Auth | Accounts and sessions |
| Search | Tavily, Exa, or Serper adapter | Public company discovery |
| Extraction | Firecrawl adapter | Website content and metadata |
| Jobs | FastAPI in-process background tasks | Small bounded MVP research runs |
| Email | Resend adapter | Sandbox/disabled during MVP |
| Observability | Supabase event logs | Basic tool, error, latency, and cost visibility |
| Automation | n8n, optional | Later integrations and follow-ups |
| Deployment | Vercel + Railway/Render + Supabase | Production hosting |

All vendor integrations must use internal interfaces. Agent nodes and business logic must not directly depend on vendor SDKs. Each integration must also have a fixture-backed fake adapter.

Required interfaces:

- `SearchProvider`
- `WebsiteExtractionProvider`
- `LanguageModelProvider`
- `EmailProvider`

---

## 6. Repository Architecture

Use a simple two-application repository: one Next.js frontend and one FastAPI backend. The frontend uses npm. The backend uses Python 3.12+, a local virtual environment, `pip`, `requirements.txt`, Pydantic, Ruff, and pytest. Docker, distributed job infrastructure, workspace orchestration, and generated clients are outside the two-day MVP.

```text
siftora/
├── frontend/                   # Next.js landing page and dashboard
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── package-lock.json
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── agent.py            # LangGraph workflow and state
│   │   ├── tools.py            # Search, extraction, and action tools
│   │   ├── providers.py        # External service adapters and fixtures
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── database.py         # Supabase repositories
│   │   ├── scoring.py          # Deterministic lead scoring
│   │   └── config.py           # Environment settings
│   ├── tests/
│   └── requirements.txt
├── specs/
├── docs/
│   ├── architecture.md
│   ├── security.md
│   └── providers.md
├── supabase/
│   ├── migrations/
│   └── seed.sql
├── .github/workflows/ci.yml    # Optional lightweight checks
├── .env.example
├── .gitignore
├── plan.md
└── README.md
```

FastAPI handles API requests and starts controlled in-process research tasks. Each MVP run is limited to 5–10 companies, stores status and partial results in Supabase, and returns a run ID that the frontend polls. This keeps the demo easy to run locally; the documentation must state that a durable external job system would be needed for production scale.

Pydantic models are the authoritative backend contract. The frontend uses a small typed `fetch` wrapper and Zod for forms. Keep the API surface small enough that automatic client generation is unnecessary.

---

## 7. Roles and Permissions

### User

- Manage personal campaigns
- Confirm research plans
- Run, pause, and inspect research
- View owned leads and evidence
- Configure scoring before a run
- Edit, approve, reject, regenerate, and export drafts

### Admin

- Inspect system health, usage, cost, and provider failures
- Manage demo configuration and provider limits

### AI agent

- Interpret goals
- Research public companies
- Analyze and validate evidence
- Recommend qualification
- Draft outreach
- Request approval

The agent cannot approve drafts, override suppression, exceed limits, access another user's data, or send/export without authorization.

---

## 8. End-to-End Workflow

1. User signs in.
2. User creates a campaign from a natural-language goal.
3. User adds filters, exclusions, target count, offer, and limits.
4. Planner produces an ICP and search plan.
5. User reviews and confirms the plan.
6. Background research begins.
7. Search returns candidate companies and sources.
8. Extraction collects public website content.
9. Analyzer extracts facts, inferences, pain points, and unknowns.
10. Validator rejects irrelevant or unsupported candidates.
11. Deduplication merges repeated companies.
12. Deterministic scoring generates a 0–100 result.
13. Qualified leads receive grounded drafts.
14. Quality checks detect unsupported claims.
15. User edits, approves, rejects, or regenerates drafts.
16. Approved results can be exported; sending remains disabled/sandboxed.
17. Dashboard displays funnel, cost, tools, and failures.

---

## 9. Agent Architecture

### Graph state

```ts
type CampaignAgentState = {
  runId: string;
  campaignId: string;
  userId: string;
  status:
    | "planning"
    | "awaiting_plan_approval"
    | "researching"
    | "validating"
    | "scoring"
    | "drafting"
    | "awaiting_outreach_approval"
    | "completed"
    | "failed";
  brief: string;
  icp: IdealCustomerProfile | null;
  searchPlan: SearchPlan | null;
  queries: SearchQuery[];
  candidates: CandidateCompany[];
  acceptedLeadIds: string[];
  rejectedCandidates: RejectedCandidate[];
  currentCandidateIndex: number;
  limits: RunLimits;
  usage: RunUsage;
  errors: AgentError[];
  nextAction: string | null;
};
```

### Nodes

1. `parseCampaignBrief`
2. `validateICP`
3. `buildSearchPlan`
4. `awaitPlanApproval`
5. `searchCompanies`
6. `normalizeCandidates`
7. `analyzeWebsite`
8. `validateEvidence`
9. `deduplicateCandidate`
10. `calculateLeadScore`
11. `decideQualification`
12. `draftOutreach`
13. `qualityCheckDraft`
14. `persistResults`
15. `awaitOutreachApproval`
16. `completeRun`
17. `handleRecoverableFailure`
18. `handleTerminalFailure`

### Conditional behavior

- Missing ICP data → request the missing details.
- Weak results → revise query within limits.
- Website unavailable → try one alternate public source.
- Insufficient evidence → reject or mark `needs_review`.
- Duplicate → merge evidence instead of creating another company.
- Low score → skip outreach generation.
- Unsupported claim → regenerate once, then require review.
- Provider failure → retry with backoff, then pause with partial results.
- Budget exhausted → stop cleanly and retain results.

### Tools and guardrails

| Tool | Purpose | Guardrail |
| --- | --- | --- |
| `searchCompanies` | Discover companies | Query/result budget |
| `extractWebsite` | Extract public pages | URL, timeout, page limits |
| `findPublicContact` | Find public contact evidence | Never guess data |
| `checkDuplicate` | Match company/contact | Deterministic DB check |
| `saveLead` | Persist lead | Evidence required |
| `scoreLead` | Calculate score | Deterministic math |
| `draftOutreach` | Generate draft | Grounded claims only |
| `requestApproval` | Create approval | Mandatory before action |
| `exportApprovedLeads` | Create CSV | Approved/non-suppressed only |
| `sendApprovedEmail` | Deliver email | Disabled by default |

---

## 10. Lead Scoring

| Criterion | Weight |
| --- | ---: |
| Industry fit | 20 |
| Geography fit | 10 |
| Company-size fit | 10 |
| Pain-point evidence | 20 |
| Buying/technology signal | 15 |
| Contact relevance | 10 |
| Website/activity recency | 10 |
| Evidence completeness | 5 |
| **Total** | **100** |

Default thresholds:

- `75–100`: Qualified
- `55–74`: Needs review
- `0–54`: Rejected

The LLM may extract facts and criterion ratings. Application code calculates the weighted score. The scoring configuration becomes immutable for a run.

---

## 11. Evidence, Outreach, and Compliance Rules

### Evidence

- Every company requires an accessible source URL.
- Important facts require a source and stored excerpt.
- UI distinguishes facts, inferences, and unknowns.
- Missing information is never invented.
- Search snippets alone should not support important claims when a primary source exists.
- Failed sources remain visible in logs.

### Outreach

- Personalized claims must map to evidence.
- Do not claim false familiarity or product usage.
- Do not create fake urgency, metrics, or deceptive wording.
- Default cold email stays below 130 words.
- Include one relevant observation, one offer, and one clear CTA.
- Rejected or suppressed contacts cannot enter approval.
- Editing an approved draft invalidates approval.

### Responsible use

- Research only permitted public business information.
- Do not bypass authentication, CAPTCHAs, access controls, or rate limits.
- Maintain suppression and opt-out state.
- Real sending remains opt-in, rate-limited, and approval-gated.
- Store source and retrieval timestamp for contact data.
- Allow deletion of user-owned campaign and lead data.

---

## 12. Core Data Model

### Main tables

- `profiles`: user identity and role
- `campaigns`: brief, status, target, thresholds, and limits
- `campaign_icp`: industries, locations, size, signals, exclusions, offer, roles
- `campaign_runs`: state, usage, cost, timestamps, errors, stop reason
- `companies`: normalized domain, business facts, verification timestamp
- `leads`: campaign/company, contact, status, score, decision reason
- `lead_evidence`: claim, excerpt, type, source, timestamp, confidence
- `score_breakdowns`: criterion, rating, weight, points, evidence
- `outreach_drafts`: channel, subject, body, version, quality status
- `approvals`: draft version, decision, reviewer, timestamp, edits
- `agent_events`: node, status, concise summaries, duration, error
- `tool_calls`: tool, provider, status, summaries, latency, cost
- `suppression_entries`: user, normalized email/domain hash, reason

### Database requirements

- Enable RLS on user-owned tables.
- Enforce ownership in API and RLS.
- Keep service credentials server-side.
- Add constraints for statuses, scores, approvals, and uniqueness.
- Store migrations and seed data in version control.
- Seed demo campaigns and companies.

---

## 13. API Overview

### Campaigns

- `POST /api/campaigns`
- `GET /api/campaigns`
- `GET /api/campaigns/:id`
- `PATCH /api/campaigns/:id`
- `DELETE /api/campaigns/:id`
- `POST /api/campaigns/:id/plan`
- `POST /api/campaigns/:id/confirm-plan`
- `POST /api/campaigns/:id/run`
- `POST /api/campaigns/:id/pause`
- `GET /api/campaigns/:id/progress`

### Leads and outreach

- `GET /api/campaigns/:id/leads`
- `GET /api/leads/:id`
- `PATCH /api/leads/:id/status`
- `POST /api/leads/:id/rescore`
- `POST /api/leads/:id/regenerate-outreach`

### Approvals, exports, and runs

- `GET /api/approvals`
- `POST /api/approvals/:id/approve`
- `POST /api/approvals/:id/reject`
- `PATCH /api/approvals/:id/draft`
- `POST /api/campaigns/:id/export`
- `GET /api/runs/:id/events`
- `GET /api/runs/:id/tool-calls`
- `GET /api/campaigns/:id/analytics`

FastAPI validates API payloads using Pydantic models. The frontend uses a small typed `fetch` wrapper and Zod for forms where useful. APIs require authentication, ownership checks, pagination, stable error codes, and idempotency for run/export/send operations.

---

## 14. UI Scope

### Landing page

The landing page is part of Phase 1.

- Sticky navigation
- Hero with `Start Campaign` and `View Demo`
- Product mockup using labeled demo data
- Workflow: define ICP → research → verify/score → approve
- Agentic behavior explanation
- Features and use cases
- Seeded lead example with evidence and score
- Responsible-outreach section
- Technology section
- GitHub, privacy, terms, and final CTA
- Metadata, Open Graph, favicon, sitemap, and robots

No fake logos, testimonials, revenue metrics, or unimplemented claims.

### Application pages

- Sign up, sign in, reset password
- Dashboard overview
- Campaign wizard and plan review
- Campaign progress and activity
- Leads table and evidence-rich lead detail
- Approval queue and draft editor
- Evaluation and analytics

Every data page must support loading, empty, success, partial, recoverable-error, unauthorized, and terminal-failure states.

---

## 15. Phase 1 — Foundation, Landing, Auth, and Database

### Scope

- Simple Next.js/TypeScript frontend and FastAPI/Python backend
- Next.js web application foundation
- FastAPI application foundation
- Pydantic API contracts, typed frontend requests, and environment validation
- npm frontend setup and Python `venv`/`pip` backend setup
- Formatting, linting, tests, builds, and CI
- Responsive Siftora landing page
- Supabase authentication
- Initial migrations and RLS
- Protected dashboard shell
- Seed/demo mode

### Acceptance criteria

- Fresh clone installs and builds through documented commands.
- Root URL shows the public landing page.
- Navigation, mobile menu, and CTAs work.
- Demo mockups are labeled and copy is honest.
- User can sign up, sign in, sign out, and restore a session.
- Protected routes reject unauthenticated access.
- User A cannot access User B's records.
- Database rebuilds from migrations and seed data.
- Documented commands start the frontend and backend separately without containers.
- FastAPI exposes a health endpoint.
- Frontend API calls match the documented Pydantic responses.
- If CI is included, it runs npm frontend checks and backend Ruff/pytest checks only.
- Phase 2 features are not implemented.

**Specification:** `specs/phase-1-foundation.md`

---

## 16. Phase 2 — Campaigns, ICP, and Planning

### Scope

- Campaign CRUD and wizard
- Natural-language brief
- Typed ICP
- Scoring weights and thresholds
- Query, page, retry, and cost limits
- Gemini structured output
- Research-plan generation
- Plan review, edit, and approval

### Acceptance criteria

- User manages only owned campaigns.
- Brief produces schema-valid ICP output.
- Missing required information is requested, not invented.
- User can edit generated fields.
- Weights must total 100.
- Run cannot start without plan approval.
- Invalid model output retries and then fails clearly.
- Phase 3 research is not implemented.

**Specification:** `specs/phase-2-campaigns.md`

---

## 17. Phase 3 — Agentic Research, Evidence, and Scoring

### Scope

- Controlled in-process background research execution
- LangGraph state, nodes, conditional routing, and bounded retries
- Search and Firecrawl provider adapters
- Fixture providers
- Discovery and normalization
- Website analysis
- Facts/inferences/unknowns
- Evidence storage and validation
- Rejection, deduplication, and scoring
- Progress, lead list/detail, tool logs, and event timeline

### Acceptance criteria

- Confirmed campaign starts an idempotent run.
- Agent revises weak queries only within limits.
- Accepted facts include source evidence.
- Unknown information is not fabricated.
- Broken sites produce failure/fallback results.
- Duplicate companies are merged.
- Same inputs always produce the same numerical score.
- Score breakdown links to evidence.
- Low-score leads skip outreach.
- Partial results survive failures.
- Budget and retry limits are code-enforced.

**Specification:** `specs/phase-3-research.md`

---

## 18. Phase 4 — Outreach, Approval, and Export

### Scope

- Email and LinkedIn draft templates
- Sender/offer configuration
- Draft generation
- Unsupported-claim, tone, CTA, length, and spam checks
- Version history
- Approval queue
- Edit, approve, reject, and regenerate
- Suppression checks
- Approved CSV export
- Optional Resend sandbox

### Acceptance criteria

- Drafts contain no unsupported personalized claims.
- Drafts follow configured length and CTA rules.
- Failed quality checks regenerate once, then require review.
- Versions remain accessible.
- AI cannot approve drafts.
- Editing invalidates approval.
- Suppressed contacts remain blocked.
- Unapproved drafts cannot be exported/sent as approved.
- Approval records include reviewer, time, and version.
- Real sending is disabled by default.

**Specification:** `specs/phase-4-outreach.md`

---

## 19. Phase 5 — Evaluation, Hardening, and Deployment

### Scope

- Supabase-backed agent events, tool-call logs, and error logs
- Evaluation dataset and UI
- Routing, tool, evidence, score, and draft evaluations
- Funnel, cost, latency, and failure analytics
- Security review and rate limits
- Health/readiness endpoints and monitoring
- Production deployment
- Demo reset flow
- README, screenshots, architecture diagram, and demo script
- Final landing-page polish

### Minimum evaluations

- 10 campaign-parsing cases
- 10 planning cases
- 20 candidate-validation cases
- 15 deduplication cases
- 20 scoring cases
- 20 outreach-grounding cases
- 10 failure/recovery cases

### Acceptance criteria

- Deterministic tests pass 100%.
- Structured parsing succeeds in at least 95% of fixed eval runs after retry.
- No quality-approved fixed-set draft contains unsupported personalization.
- Runs report latency, usage, cost, and failures.
- Public fixture demo completes reliably.
- Provider quota/failure states are usable.
- Secrets remain server-side.
- Health checks cover the API and database.
- README supports fresh fixture-mode setup.
- Portfolio docs distinguish mock, sandbox, and live behavior.

**Specification:** `specs/phase-5-production.md`

---

## 20. Testing Strategy

### Unit

- Pydantic models, Zod form schemas, normalization, and deduplication
- Scoring, thresholds, budgets, and suppression
- Provider mapping and outreach quality rules

### Integration

- API/database ownership
- Background research task lifecycle
- LangGraph transitions and bounded retries
- Provider adapters with fixtures
- Approval invalidation and approved-only export

### End-to-end

Use Playwright for landing CTA, authentication, campaign creation, plan confirmation, fixture research, evidence/score review, draft editing, approval/export, pause/resume, failure recovery, and cross-user denial.

### LLM evaluation

- Separate deterministic tests from probabilistic evals.
- Version prompts and validate structured output.
- Use low temperature for extraction/routing.
- Use fixtures in CI and run live-provider evals separately.

### Required quality commands

- Frontend: Prettier, ESLint, TypeScript, Vitest, Playwright, and Next.js production build
- Backend: Ruff format/check and pytest
- Run frontend and backend checks with their documented native commands.

---

## 21. Non-Functional Requirements

### Security

- RLS plus API ownership checks
- URL validation and SSRF defense
- Scraped content treated as untrusted input
- Prompt-injection defenses
- Sanitized rendered content
- Allowlisted tools and validated arguments
- Server-only secrets
- Rate-limited auth, planning, and run start

### Reliability

- Idempotent jobs
- Timeouts and limited retries
- Partial-result preservation
- Pause, resume, and cancellation
- Explicit stop reasons

### Cost control

- Hard query, page, retry, token, and estimated-cost limits
- Pre-run estimate
- Extraction caching
- Cheaper models where appropriate
- Zero-cost fixture/demo mode

### Performance and accessibility

- Database API p95 target below 500 ms
- Planning target below 15 seconds
- Background execution for long work
- Paginated leads/events/tool calls
- Keyboard access, focus states, labels, contrast, and semantic HTML

---

## 22. Environment Variables

```text
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=
GEMINI_API_KEY=
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
EXA_API_KEY=
SERPER_API_KEY=
FIRECRAWL_API_KEY=
RESEND_API_KEY=
EMAIL_MODE=disabled
APP_BASE_URL=
API_BASE_URL=
```

Only variables for the selected providers are mandatory. `EMAIL_MODE` defaults to `disabled` and supports `disabled`, `sandbox`, and `live`.

---

## 23. Definition of MVP Done

- Landing page and dashboard are deployed.
- User creates and confirms a campaign.
- Agent researches through real and fixture providers.
- Companies are normalized and deduplicated.
- Facts display evidence and sources.
- Leads receive deterministic, explainable scores.
- Qualified leads receive grounded drafts.
- User can edit, approve, reject, and export.
- No action bypasses approval or suppression.
- Limits and failures are handled safely.
- Runs expose progress, decisions, errors, usage, and cost.
- Auth, RLS, ownership, unit, integration, and E2E checks pass.
- Public demo honestly labels fixtures and sandbox behavior.

---

## 24. Later Backlog

1. Gmail/Outlook sending
2. Reply classification
3. n8n follow-up sequences
4. HubSpot/Pipedrive sync
5. Team workspaces
6. Campaign templates
7. A/B outreach variants
8. Lead-feedback learning loop
9. Webhooks/public API
10. Slack approvals
11. Natural-language analytics