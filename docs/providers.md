# Provider adapters

Siftora talks to every external service through an interface
(`plan.md` §5), never a vendor SDK directly from business logic. Each
interface has a **fixture** adapter (deterministic, zero network calls,
zero cost) and a **real** adapter (opt-in via env var + API key). Fixture
is always the default.

| Interface | Selector env var | Fixture (default) | Real adapter | Real API key |
| --- | --- | --- | --- | --- |
| `LanguageModelProvider` | `LLM_PROVIDER` | `FixtureLanguageModelProvider` | `GeminiLanguageModelProvider` | `GEMINI_API_KEY` |
| `SearchProvider` | `SEARCH_PROVIDER` | `FixtureSearchProvider` | `TavilySearchProvider` | `TAVILY_API_KEY` |
| `WebsiteExtractionProvider` | `EXTRACTION_PROVIDER` | `FixtureWebsiteExtractionProvider` | `FirecrawlExtractionProvider` | `FIRECRAWL_API_KEY` |
| `EmailProvider` | `EMAIL_MODE` (`disabled`/`sandbox`/`live`) | `DisabledEmailProvider` (`disabled`, default) | `ResendEmailProvider` (`live`) | `RESEND_API_KEY` |

`EmailProvider` has a third, non-fixture no-op mode — `sandbox`
(`SandboxEmailProvider`) — between `disabled` and `live`: it simulates a
send (no network call, no credentials) for demoing the "would have sent"
path, whereas `disabled` doesn't even pretend to.

All factories live in `backend/app/providers.py`
(`get_language_model_provider`, `get_search_provider`,
`get_extraction_provider`, `get_email_provider`). Routers and the research
graph (`backend/app/agent.py`) depend on the factory, never on a concrete
class.

## Fixture behavior (Phases 2–4)

- `FixtureLanguageModelProvider.generate_campaign_plan` — keyword-matches
  the brief against a small industry/location vocabulary; returns an
  incomplete ICP (empty `industries`/`locations`) for a brief that names
  neither, so the "ask, don't invent" path is exercised deterministically.
- `FixtureSearchProvider.search` — matches a small hand-authored company
  catalog against the query text. `attempt=0` requires every one of a
  company's tagged keywords to appear in the query (strict); `attempt>0`
  (a revised/broadened query — see `app/agent.py::_revise_query`) requires
  only one (relaxed). This lets a too-narrow query fail once and then
  recover on retry without the fixture needing to model real search
  relevance.
- `FixtureWebsiteExtractionProvider.extract` — returns canned page text per
  catalog domain; `brokenlink.example` always returns `None`, simulating
  an unreachable site.
- `FixtureLanguageModelProvider.analyze_company` — returns hand-authored
  evidence + per-criterion signals per catalog domain; one catalog company
  is deliberately "thin" (zero facts), so the insufficient-evidence
  rejection path is exercised deterministically.

None of this is meant to model real search relevance or real LLM
reasoning — it exists to make the research graph's control flow (retries,
dedup, rejection, scoring) deterministically testable without any
credentials or network access. See `backend/app/providers.py` for the full
catalog.

- `FixtureLanguageModelProvider.draft_outreach` (Phase 4) — grounds the
  observation in the first `fact`/`inference` item of the **caller-supplied**
  evidence list (never a fixture-only re-derivation); one catalog company
  (`thinclaimrobotics.example`, `draft_ungroundable: True`) always returns
  an empty `evidence_refs` regardless of attempt, so the "regenerate once,
  then require review" quality-check path is deterministically testable.

## Real adapters — not exercised live

`ResendEmailProvider` is implemented against Resend's documented REST API
shape, but **no live call has been made in this development environment** —
no `RESEND_API_KEY` is available here. `GeminiLanguageModelProvider`,
`TavilySearchProvider`, and `FirecrawlExtractionProvider` *have* since been
verified live against real credentials (see `specs/phase-2-campaigns.md`
and `specs/phase-3-research.md`, Risks and Assumptions) — this caveat now
applies only to `ResendEmailProvider`. Anyone running Siftora with a real
Resend key is the first to exercise that specific code path end-to-end; if
Resend's API shape has changed since this was written, expect to need small
adjustments.

## Cost estimates are synthetic

`campaign_runs.estimated_cost_usd` and `tool_calls.cost_usd` in fixture
mode use small, fixed per-call constants (`app/agent.py`:
`_SEARCH_CALL_COST`, `_EXTRACT_CALL_COST`, `_ANALYZE_CALL_COST`) — they
exist so the `max_cost_usd` budget-limit code path is reachable and
testable, not because they reflect real provider pricing. When a real
provider is enabled, these constants still apply (the code doesn't yet
read real per-call billing from any provider's response) — treat the
run's cost figure as a rough, clearly-synthetic estimate, not a bill.
