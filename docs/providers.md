# Provider adapters

Siftora talks to every external service through an interface
(`plan.md` §5), never a vendor SDK directly from business logic. Each
interface has a **fixture** adapter (deterministic, zero network calls,
zero cost) and a **real** adapter (opt-in via env var + API key). Fixture
is always the default.

| Interface | Selector env var | Fixture (default) | Real adapter | Real API key |
| --- | --- | --- | --- | --- |
| `LanguageModelProvider` | `LLM_PROVIDER` | `FixtureLanguageModelProvider` | `OpenRouterLanguageModelProvider` | `OPENROUTER_API_KEY` |
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
no `RESEND_API_KEY` is available here. `TavilySearchProvider` and
`FirecrawlExtractionProvider` *have* since been verified live against real
credentials (see `specs/phase-3-research.md`, Risks and Assumptions).
`OpenRouterLanguageModelProvider` replaced the original Gemini adapter and
talks to OpenRouter's OpenAI-compatible chat-completions API, defaulting to
the free-tier `nvidia/nemotron-3.5-lightning:free` model. This adapter
**has** now been verified live (campaign planning and page entity
extraction both round-tripped against real credentials).

Two things about OpenRouter that the adapter has to defend against, learned
the hard way:

* **Upstream failures arrive as HTTP 200.** A rate limit, an unavailable
  model or a provider-side timeout comes back as a normal `200` whose body
  is `{"error": {...}}` with **no `choices` key**. `raise_for_status()`
  does not catch this. The adapter inspects the body explicitly and raises
  `LLMUnavailableError`, which callers can distinguish from "the model
  answered but the output was unusable" (`LLMOutputError`).
* **Reasoning tokens, not the network, dominate latency.** Every call this
  app makes is structured extraction against a fixed shape, which
  chain-of-thought does not improve. On a measured planning call the model
  spent **3,613 of 3,634 completion tokens on reasoning** and took ~105s;
  the same call with `reasoning: {"enabled": false}` returned the same
  shape in ~17s. The adapter therefore disables reasoning by default
  (`OPENROUTER_DISABLE_REASONING=true`). End-to-end planning went from
  ~167s to ~5-14s.
* **Disabling reasoning changes how the model reads the prompt.** With
  reasoning off, the model stopped producing an *instance* of the JSON
  Schema it was shown and started echoing the schema's own shape, nesting
  its (correct) extraction under a `properties` key -- which validated as a
  completely empty ICP, so the user was told their brief lacked detail. The
  prompts now show a **value skeleton** (`{"icp": {"industries": [], ...}}`)
  rather than a JSON Schema, and `_unwrap_json_schema_envelope` recovers the
  instance if a model does it anyway.
* **Free-tier reasoning models are slow, and may return a null `content`.**
  The previous default, `nvidia/nemotron-3-ultra-550b-a55b:free`, exceeded
  OpenRouter's own ~300s upstream limit on a full planning prompt and
  therefore *always* produced a 504 error envelope — campaign planning
  could never succeed with it. Even the current default takes 1-3 minutes
  under load, so `OPENROUTER_TIMEOUT_SECONDS` defaults to 180. For
  anything latency-sensitive (plan.md targets planning under 15s), use a
  paid model and lower the timeout.

## Evaluating providers on demand (Phase 5)

`POST /api/evals/run` (admin-only) runs the deterministic evaluation
harness (`backend/app/evals/`) against whichever providers are currently
configured — the same fixture-by-default, real-if-configured factories as
everywhere else in this file. Against fixtures it always reports 100% (the
fixture output is Pydantic-valid by construction); pointing it at real
credentials (`LLM_PROVIDER=openrouter`, etc.) is how to get a genuine
structured-parsing-success-rate number for `plan.md` §19's "at least 95%
after retry" acceptance criterion. See `docs/security.md` for the admin-role
gate and `specs/phase-5-hardening.md` for why this endpoint never touches
Supabase (so running it can't pollute real user data with synthetic
campaigns/leads).

## Cost estimates are synthetic

`campaign_runs.estimated_cost_usd` and `tool_calls.cost_usd` in fixture
mode use small, fixed per-call constants (`app/agent.py`:
`_SEARCH_CALL_COST`, `_EXTRACT_CALL_COST`, `_ANALYZE_CALL_COST`) — they
exist so the `max_cost_usd` budget-limit code path is reachable and
testable, not because they reflect real provider pricing. When a real
provider is enabled, these constants still apply (the code doesn't yet
read real per-call billing from any provider's response) — treat the
run's cost figure as a rough, clearly-synthetic estimate, not a bill.
