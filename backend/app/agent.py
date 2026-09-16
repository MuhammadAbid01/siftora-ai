"""The Phase 3 research graph (plan.md §9, adapted — see
specs/phase-3-research.md, Technical Design, "LangGraph usage" for the
documented deviations from the full cross-phase node list).

No checkpointer: a run completes within one `ainvoke()` call inside a
FastAPI BackgroundTask (in-process, plan.md §5/§6) — no cross-process
durability is needed or claimed.
"""

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app import database, discovery
from app.providers import (
    LLMOutputError,
    LLMUnavailableError,
    get_extraction_provider,
    get_language_model_provider,
    get_search_provider,
    is_safe_extraction_url,
    normalize_domain,
)
from app.schemas import (
    CompanyAnalysis,
    EvidenceItem,
    ExtractedPage,
    ScoreBreakdownItem,
    ScoreThresholds,
)
from app.scoring import compute_score, decide_qualification

logger = logging.getLogger(__name__)

_LEGAL_SUFFIXES = frozenset(
    {
        "ltd",
        "limited",
        "llc",
        "llp",
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "pvt",
        "private",
        "plc",
        "gmbh",
        "bv",
        "nv",
        "sa",
        "srl",
        "ag",
        "fz",
        "fze",
        "llc_fz",
        "dmcc",
        "the",
    }
)

# Small, fixed, clearly-synthetic per-call costs so the cost-limit code path
# is exercisable without any real provider billing data (see
# specs/phase-3-research.md, Risks — "synthetic cost model").
_SEARCH_CALL_COST = 0.01
_EXTRACT_CALL_COST = 0.01
_ANALYZE_CALL_COST = 0.02
_ENTITY_EXTRACT_COST = 0.02
# Base delay for retrying a provider that reported itself unavailable.
_RETRY_BACKOFF_SECONDS = 2.0


class ResearchState(TypedDict):
    run_id: str
    campaign_id: str
    icp: dict[str, Any]
    offer: str | None
    search_plan: list[dict[str, Any]]
    weights: dict[str, int]
    thresholds: dict[str, int]
    limits: dict[str, Any]
    target_lead_count: int

    query_cursor: int
    query_retry_count: int
    # Search hits awaiting entity extraction. A hit is a *source page*, not
    # a company — `expand_source` turns each into zero or more candidates.
    pending_sources: list[dict[str, Any]]
    pending_candidates: list[dict[str, Any]]
    seen_source_urls: list[str]
    seen_domains: list[str]
    # company_key(name) -> the domain that company was filed under, so a
    # repeat sighting can find the existing candidate/lead to merge into.
    domain_by_company_key: dict[str, str]
    domain_lookups_used: int
    max_domain_lookups: int
    current_candidate: dict[str, Any] | None
    current_analysis: CompanyAnalysis | None
    current_score: int | None
    current_breakdown: list[ScoreBreakdownItem] | None

    queries_used: int
    leads_created: int
    qualified_count: int
    needs_review_count: int
    rejected_count: int
    failed_count: int
    estimated_cost_usd: float
    stop_reason: str | None


def _record_agent_event(
    run_id: str, *, node: str, status: str, summary: str, error: str | None = None
) -> None:
    database.create_agent_event(
        run_id=run_id, node=node, status=status, summary=summary, error=error
    )


def _record_tool_call(
    run_id: str,
    *,
    tool: str,
    provider: str,
    status: str,
    summary: str,
    latency_ms: int,
    cost_usd: float,
    error: str | None = None,
) -> None:
    # tool_calls has no separate error column (only agent_events does) —
    # fold it into the summary instead of widening the schema for one field.
    full_summary = f"{summary} Error: {error}" if error else summary
    database.create_tool_call(
        run_id=run_id,
        tool=tool,
        provider=provider,
        status=status,
        summary=full_summary,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )


def _toggle_scheme(url: str) -> str:
    if url.startswith("https://"):
        return "http://" + url[len("https://") :]
    if url.startswith("http://"):
        return "https://" + url[len("http://") :]
    return f"https://{url}"


def company_key(name: str) -> str:
    """Normalized identity for a company name, for within-run dedup.

    Domain alone is not enough: the same business reached through two
    aggregator front-ends resolved to two different hosts and became two
    leads ("Attock Refinery" via investing.com and uk.investing.com).
    Lower-cases, drops punctuation and strips the legal/style suffixes that
    differ between sources ("Ltd", "LLC", "Pvt", "Co.", "Limited").
    """
    cleaned = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    words = [w for w in cleaned.split() if w not in _LEGAL_SUFFIXES]
    return " ".join(words) or name.strip().lower()


def _provenance_evidence(candidate: dict[str, Any]) -> EvidenceItem | None:
    """Record the page a listing-discovered company was found on.

    When a company is extracted from a roundup, directory or encyclopedia
    article, that page becomes one of the lead's *evidence sources* — it
    never becomes the lead itself. Candidates found directly on their own
    website have no separate provenance to record.
    """
    source_url = candidate.get("evidence_source_url")
    if not source_url:
        return None

    source_title = candidate.get("evidence_source_title") or source_url
    return EvidenceItem(
        type="fact",
        claim=(
            f'{candidate["company_name"]} is named on "{source_title}", '
            "which was found while researching this campaign."
        ),
        excerpt=candidate.get("evidence_source_excerpt") or source_title,
        source_url=source_url,
        confidence=0.5,
    )


def _extra_source_payload(source: dict[str, Any], company_name: str) -> dict[str, Any]:
    """The minimal candidate-shaped dict `_provenance_evidence` needs."""
    return {
        "company_name": company_name,
        "evidence_source_url": source["url"],
        "evidence_source_title": source["title"],
        "evidence_source_excerpt": (source.get("snippet") or source["title"])[:280],
    }


def _record_repeat_sighting(
    state: ResearchState,
    *,
    pending: list[dict[str, Any]],
    domain: str,
    payload: dict[str, Any],
) -> None:
    """Attach an additional source for a company we've already queued or persisted.

    `seen_domains` stops a company being analyzed twice, but "already seen"
    must not mean "throw the extra evidence away" — finding the same agency
    on three different roundups is exactly the corroboration the evidence
    model is for (plan.md §9). The sighting is attached to the still-pending
    candidate when there is one, and merged into the existing lead when the
    company has already been persisted.
    """
    key = company_key(payload["company_name"])
    for candidate in pending:
        if (domain and candidate["domain"] == domain) or company_key(
            candidate["company_name"]
        ) == key:
            candidate.setdefault("extra_sources", []).append(payload)
            return

    # Not pending any more, so it has already been persisted as a lead.
    # When dedup matched on the name we have no domain in hand; recover the
    # one it was filed under, otherwise the merge silently does nothing.
    domain = domain or state["domain_by_company_key"].get(key, "")
    if not domain:
        return

    company = database.get_company_by_domain(domain=domain)
    if company is None:
        return
    lead = database.get_lead_by_campaign_and_company(
        campaign_id=state["campaign_id"], company_id=company["id"]
    )
    if lead is not None:
        _merge_duplicate_evidence(lead_id=lead["id"], candidate=payload)


def _merge_duplicate_evidence(*, lead_id: str, candidate: dict[str, Any]) -> bool:
    """Attach a repeat discovery to the lead that already exists.

    The same company legitimately turns up on several listicles. Dedup must
    merge those into one lead with multiple evidence entries (plan.md §9,
    "Duplicate -> merge evidence instead of creating another company")
    rather than dropping the later sightings on the floor. Returns True when
    a new evidence row was written.
    """
    provenance = _provenance_evidence(candidate)
    if provenance is None:
        return False

    already = {row.get("source_url") for row in database.list_lead_evidence(lead_id=lead_id)}
    if provenance.source_url in already:
        return False

    database.create_lead_evidence(lead_id=lead_id, items=[provenance.model_dump(exclude_none=True)])
    return True


def _revise_query(query: str) -> str:
    """Broaden a query that returned nothing (FR-6). Dropping the location
    clause is the one concrete strategy implemented; if there's no such
    clause the query is returned unchanged (the fixture's attempt-based
    relaxation still gives it a fresh chance — see providers.py).
    """
    if " in " in query:
        return query.split(" in ")[0].strip()
    return query


def _finalize_candidate(
    state: ResearchState,
    *,
    candidate: dict[str, Any],
    status: str,
    decision_reason: str | None,
    score: int,
    evidence: list[EvidenceItem],
    breakdown: list[ScoreBreakdownItem],
) -> dict[str, Any]:
    """Persist one fully-evaluated candidate (qualified, needs_review, or
    rejected — for any reason) and return the state patch. Every candidate
    the graph looks at ends up here exactly once (FR-8, FR-10: failures are
    visible leads, not silent drops).
    """
    company = database.upsert_company_by_domain(
        domain=candidate["domain"], name=candidate["company_name"]
    )
    lead = database.create_lead(
        campaign_id=state["campaign_id"],
        company_id=company["id"],
        # The company's own page — never the listicle/directory it was
        # found on. That page is recorded below as provenance evidence.
        source_url=candidate["url"],
        status=status,
        score=score,
        decision_reason=decision_reason,
    )

    # Provenance is appended *after* `validate_evidence` has already run on
    # `analysis.evidence`, so a lead can never satisfy the "needs at least
    # one fact" gate on the strength of merely having been listed
    # somewhere (specs/phase-3-research.md FR-10).
    all_evidence = list(evidence)
    seen_sources: set[str] = set()
    for payload in [candidate, *candidate.get("extra_sources", [])]:
        provenance = _provenance_evidence(payload)
        if provenance is not None and provenance.source_url not in seen_sources:
            all_evidence.append(provenance)
            seen_sources.add(provenance.source_url or "")

    database.create_lead_evidence(
        lead_id=lead["id"], items=[e.model_dump(exclude_none=True) for e in all_evidence]
    )
    database.create_score_breakdown(
        lead_id=lead["id"],
        items=[
            {"criterion": b.criterion, "rating": b.rating, "weight": b.weight, "points": b.points}
            for b in breakdown
        ],
    )

    outcome = decision_reason or f"score {score}"
    _record_agent_event(
        state["run_id"],
        node="persist_lead",
        status="ok",
        summary=f"{candidate['company_name']} ({candidate['domain']}) -> {status} ({outcome}).",
    )

    is_operational_failure = decision_reason in (
        "extraction_failed",
        "analysis_failed",
        "unsafe_url",
        "domain_mismatch",
    )
    return {
        "leads_created": state["leads_created"] + 1,
        "qualified_count": state["qualified_count"] + (1 if status == "qualified" else 0),
        "needs_review_count": state["needs_review_count"] + (1 if status == "needs_review" else 0),
        "rejected_count": state["rejected_count"] + (1 if status == "rejected" else 0),
        # A subset of rejected candidates, tracked separately: operational
        # failures (couldn't extract/analyze) vs. a genuine low score.
        "failed_count": state["failed_count"] + (1 if is_operational_failure else 0),
        "current_candidate": None,
        "current_analysis": None,
        "current_score": None,
        "current_breakdown": None,
    }


# --- Nodes ----------------------------------------------------------------


async def _call_llm_with_retry(
    state: ResearchState,
    operation: "Callable[[], Awaitable[Any]]",
    *,
    what: str,
):
    """Run one LLM call, retrying transient provider failures.

    A 502/timeout/rate-limit from the provider says nothing about the
    company being analyzed, yet it used to reject the lead outright
    ("Novasecuris -> rejected (analysis_failed)" after a single
    "Upstream error from Nvidia"). Only `LLMUnavailableError` is retried;
    a genuinely unusable response (`LLMOutputError`) has already been
    through the adapter's own repair attempt, so retrying it here would
    just burn time and money.

    Returns (result, error_message). Attempts are bounded by the run's
    configured `max_retries`.
    """
    attempts = max(1, int(state["limits"].get("max_retries", 1)))
    last_error: str | None = None

    for attempt in range(attempts):
        try:
            return await operation(), None
        except LLMUnavailableError as exc:
            last_error = str(exc)
            if attempt + 1 < attempts:
                delay = _RETRY_BACKOFF_SECONDS * (2**attempt)
                _record_agent_event(
                    state["run_id"],
                    node="llm_retry",
                    status="ok",
                    summary=(
                        f"{what}: provider unavailable "
                        f"(attempt {attempt + 1}/{attempts}), retrying in {delay:.0f}s."
                    ),
                    error=last_error,
                )
                await asyncio.sleep(delay)
        except LLMOutputError as exc:
            # Already repaired once inside the adapter; not retried here.
            return None, str(exc)

    return None, last_error


def _usable_leads(state: ResearchState) -> int:
    """Leads the user can actually act on — qualified or needs_review.

    The target must not be satisfied by rejects. `leads_created` counts
    every candidate the graph finalized, including ones rejected for a
    failed extraction or a mismatched domain (they stay visible on purpose,
    FR-8). Counting those toward "find me 6 leads" let a run stop having
    produced two usable companies and four rejections.
    """
    return state["qualified_count"] + state["needs_review_count"]


def _source_priority(source: dict[str, Any]) -> int:
    """Mine the most promising sources first (lower sorts earlier).

    A run is bounded by target/budget, so the *order* sources are mined in
    decides which leads a campaign actually gets. A live "construction
    companies in Karachi" run spent its entire budget on one stock-index
    page — producing six banks, cement and fertilizer companies, all
    correctly rejected — while genuine construction firms further down the
    results were never reached.

    A company's own site yields one high-quality, on-topic lead; a curated
    roundup yields several plausible ones; a directory or index dump is the
    least targeted, so it goes last.
    """
    domain = source["domain"]
    if discovery.is_non_company_domain(domain):
        return 2
    if discovery.looks_like_listing_page(
        title=source["title"], url=source["url"], snippet=source.get("snippet", "")
    ):
        return 1
    return 0


async def search_companies(state: ResearchState) -> dict[str, Any]:
    limits = state["limits"]
    search_plan = state["search_plan"]
    query_cursor = state["query_cursor"]

    if query_cursor >= len(search_plan) or state["queries_used"] >= limits["max_queries"]:
        return {}

    query_item = search_plan[query_cursor]
    provider = get_search_provider()
    started = time.monotonic()
    results = await provider.search(
        query=query_item["query"], max_results=10, attempt=state["query_retry_count"]
    )
    latency_ms = int((time.monotonic() - started) * 1000)

    _record_tool_call(
        state["run_id"],
        tool="search",
        provider=type(provider).__name__,
        status="ok",
        summary=(
            f'Searched "{query_item["query"]}" (attempt {state["query_retry_count"] + 1}) '
            f"-> {len(results)} result(s)."
        ),
        latency_ms=latency_ms,
        cost_usd=_SEARCH_CALL_COST,
    )
    new_cost = round(state["estimated_cost_usd"] + _SEARCH_CALL_COST, 4)

    if not results and state["query_retry_count"] < limits["max_retries"]:
        revised_query = _revise_query(query_item["query"])
        new_plan = list(search_plan)
        new_plan[query_cursor] = {**query_item, "query": revised_query}
        _record_agent_event(
            state["run_id"],
            node="search_companies",
            status="ok",
            summary=(
                f'No results for "{query_item["query"]}"; revising to "{revised_query}" '
                f"(retry {state['query_retry_count'] + 1}/{limits['max_retries']})."
            ),
        )
        return {
            "search_plan": new_plan,
            "query_retry_count": state["query_retry_count"] + 1,
            "estimated_cost_usd": new_cost,
        }

    # A search hit is a page that may *mention* companies — it is not a
    # company. Queue it as a source for `expand_source` to mine; nothing
    # here may name or domain a lead. (Before this, `r.title` was written
    # straight into a lead as `company_name` and `r.domain` as the company
    # domain, which is how listicles and Wikipedia articles became leads.)
    new_sources = list(state["pending_sources"])
    seen_urls = set(state["seen_source_urls"])
    added = 0
    for r in results:
        if r.url in seen_urls:
            continue
        new_sources.append(
            {
                "title": r.title,
                "domain": normalize_domain(r.domain),
                "url": r.url,
                "snippet": r.snippet,
                "source_query": query_item["query"],
            }
        )
        seen_urls.add(r.url)
        added += 1

    # Stable sort: keeps each query's own relevance order within a tier.
    new_sources.sort(key=_source_priority)

    _record_agent_event(
        state["run_id"],
        node="search_companies",
        status="ok",
        summary=(
            f'Query "{query_item["query"]}" found {len(results)} result(s), '
            f"{added} new source page(s) to mine for companies."
        ),
    )

    return {
        "pending_sources": new_sources,
        "seen_source_urls": list(seen_urls),
        "query_cursor": query_cursor + 1,
        "query_retry_count": 0,
        "queries_used": state["queries_used"] + 1,
        "estimated_cost_usd": new_cost,
    }


async def _lookup_company_domain(state: ResearchState, *, name: str) -> tuple[str | None, float]:
    """Find a company's own website when the page that named it didn't link one.

    Returns (domain, cost_incurred). Bounded by `max_domain_lookups` so
    mining a long listicle can't quietly consume the whole search budget;
    when the budget is gone this returns None and the candidate is dropped
    with a logged reason rather than being given a guessed domain.
    """
    if state["domain_lookups_used"] >= state["max_domain_lookups"]:
        return None, 0.0

    provider = get_search_provider()
    query = f"{name} official website"
    started = time.monotonic()
    try:
        results = await provider.search(query=query, max_results=5)
    except Exception as exc:  # noqa: BLE001 - a lookup failure must not kill the run
        logger.warning("Domain lookup failed for %r: %s", name, exc)
        results = []
    latency_ms = int((time.monotonic() - started) * 1000)

    # "<name> official website" is a noisy query — a live run got website.com,
    # canva.com and flysfo.com (San Francisco airport) back for real Pakistani
    # companies. So prefer a host that visibly resembles the name, and fall
    # back to the best remaining hit only as a candidate: `analyze_candidate`
    # re-checks it against the page it fetches before any lead is created.
    candidates = [
        normalize_domain(r.domain)
        for r in results
        if r.domain and not discovery.is_non_company_domain(normalize_domain(r.domain))
    ]
    matching = [
        normalize_domain(r.domain)
        for r in results
        if r.domain
        and not discovery.is_non_company_domain(normalize_domain(r.domain))
        and discovery.domain_matches_company(name, normalize_domain(r.domain), r.title)
    ]
    resolved = matching[0] if matching else (candidates[0] if candidates else None)

    _record_tool_call(
        state["run_id"],
        tool="resolve_domain",
        provider=type(provider).__name__,
        status="ok" if resolved else "error",
        summary=f'Resolved website for "{name}" -> {resolved or "not found"}.',
        latency_ms=latency_ms,
        cost_usd=_SEARCH_CALL_COST,
        error=None if resolved else "No non-directory domain found",
    )
    return resolved, _SEARCH_CALL_COST


async def expand_source(state: ResearchState) -> dict[str, Any]:
    """Read one source page and turn it into real company candidates.

    This is the node that BUG-2 was missing entirely. Every search hit goes
    through here, and a candidate's identity always comes from an entity
    named in the page's *content*:

    * A reference/directory/social/news host (wikipedia.org, clutch.co,
      quora.com, instagram.com ...) can never become a lead, however the
      model classifies it — it is mined for the companies it names and
      cited as their evidence source.
    * A listing/roundup page yields one candidate per company it names,
      each carrying the listing as provenance.
    * A company's own site yields exactly one candidate, named from the
      page content rather than from its SEO title.
    """
    sources = list(state["pending_sources"])
    source = sources.pop(0)
    patch: dict[str, Any] = {"pending_sources": sources}
    cost = state["estimated_cost_usd"]
    source_domain = source["domain"]

    if not is_safe_extraction_url(source["url"]):
        _record_agent_event(
            state["run_id"],
            node="expand_source",
            status="error",
            summary=f"Skipped source {source['url']}: failed the SSRF/URL-safety check.",
            error="unsafe_url",
        )
        return patch

    if discovery.should_never_fetch(source_domain):
        # Login-walled / non-scrapable host: fetching it is a guaranteed
        # wasted extraction call, so don't spend one to learn that.
        _record_agent_event(
            state["run_id"],
            node="expand_source",
            status="ok",
            summary=(
                f"Skipped {source_domain} without fetching: this host is login-walled "
                "or not scrapable, so it can yield neither a lead nor evidence."
            ),
        )
        return patch

    extraction_provider = get_extraction_provider()
    started = time.monotonic()
    page = await extraction_provider.extract(url=source["url"])
    latency_ms = int((time.monotonic() - started) * 1000)
    _record_tool_call(
        state["run_id"],
        tool="extract",
        provider=type(extraction_provider).__name__,
        status="ok" if page else "error",
        summary=f"Read source {source['url']} -> {'ok' if page else 'failed'}.",
        latency_ms=latency_ms,
        cost_usd=_EXTRACT_CALL_COST,
        error=None if page else "No content extracted",
    )
    cost = round(cost + _EXTRACT_CALL_COST, 4)

    is_non_company = discovery.is_non_company_domain(source_domain)

    if page is None:
        # The page can't be read, so there is nothing to extract entities
        # from. A *reference/directory* host stops here — it could never
        # have been a lead anyway. An ordinary host, though, is most likely
        # a real company whose site is down, and FR-8 requires that to
        # surface as a visible rejected lead rather than vanish. The only
        # name available is the search title, so it must survive
        # `clean_company_name` (which rejects listicle titles, questions and
        # bare domains) — otherwise the candidate is dropped, because a
        # guessed name is worse than no lead.
        fallback_name = None if is_non_company else discovery.clean_company_name(source["title"])
        if fallback_name is None:
            _record_agent_event(
                state["run_id"],
                node="expand_source",
                status="error",
                summary=(
                    f"Could not read source page {source['url']} and could not derive a "
                    f"company name from its title; skipped."
                ),
                error="extraction_failed",
            )
            return {**patch, "estimated_cost_usd": cost}

        _record_agent_event(
            state["run_id"],
            node="expand_source",
            status="error",
            summary=(
                f"Could not read {source['url']}; queuing {fallback_name} "
                f"({source_domain}) so the unreachable site is still reported."
            ),
            error="extraction_failed",
        )
        candidates = list(state["pending_candidates"])
        seen_domains = set(state["seen_domains"])
        keys = dict(state["domain_by_company_key"])
        fallback_key = company_key(fallback_name)
        if source_domain not in seen_domains and fallback_key not in keys:
            candidates.append(
                {
                    "company_name": fallback_name,
                    "domain": source_domain,
                    "url": source["url"],
                    "source_query": source["source_query"],
                    "discovered_via": "direct",
                }
            )
            seen_domains.add(source_domain)
            keys[fallback_key] = source_domain
        return {
            **patch,
            "pending_candidates": candidates,
            "seen_domains": list(seen_domains),
            "domain_by_company_key": keys,
            "estimated_cost_usd": cost,
        }

    listing_hint = discovery.looks_like_listing_page(
        title=source["title"], url=source["url"], snippet=source.get("snippet", "")
    )

    llm = get_language_model_provider()
    started = time.monotonic()
    extraction, error = await _call_llm_with_retry(
        state,
        lambda: llm.extract_companies_from_page(
            icp=state["icp"],
            source_url=page.url,
            source_domain=source_domain,
            page_title=source["title"],
            page_text=page.text,
            looks_like_listing=listing_hint or is_non_company,
        ),
        what=f"Identifying companies on {source_domain}",
    )
    latency_ms = int((time.monotonic() - started) * 1000)
    _record_tool_call(
        state["run_id"],
        tool="extract_companies",
        provider=type(llm).__name__,
        status="ok" if extraction else "error",
        summary=(
            f"Identified companies on {source_domain} -> "
            f"{len(extraction.companies) if extraction else 0} named "
            f"(page_type={extraction.page_type if extraction else 'unknown'})."
        ),
        latency_ms=latency_ms,
        cost_usd=_ENTITY_EXTRACT_COST,
        error=error,
    )
    cost = round(cost + _ENTITY_EXTRACT_COST, 4)

    if extraction is None:
        _record_agent_event(
            state["run_id"],
            node="expand_source",
            status="error",
            summary=f"Could not identify any company on {source['url']}.",
            error=error,
        )
        return {**patch, "estimated_cost_usd": cost}

    # A company's own site is the one case where the source domain IS the
    # company — but never for a denylisted host, where "company_site" just
    # means the article is about one company (a company's Wikipedia page).
    # Those fall through to the listing branch so the page is used purely
    # as an evidence source.
    treat_as_own_site = extraction.page_type == "company_site" and not is_non_company

    new_candidates = list(state["pending_candidates"])
    seen = set(state["seen_domains"])
    domain_by_key = dict(state["domain_by_company_key"])
    lookups_used = state["domain_lookups_used"]
    accepted = 0
    rejected_names: list[str] = []

    if treat_as_own_site:
        named = extraction.companies[0].name if extraction.companies else None
        company_name = named if discovery.is_valid_company_name(named) else None
        if company_name is None:
            # Fall back to recovering a brand from the SEO title. If even
            # that fails validation we drop the candidate — we never
            # persist the raw title as a company name.
            company_name = discovery.clean_company_name(source["title"])

        if company_name is None:
            _record_agent_event(
                state["run_id"],
                node="expand_source",
                status="ok",
                summary=(
                    f"Skipped {source['url']}: could not determine a real company name "
                    f"(page title was {source['title']!r})."
                ),
            )
            return {**patch, "estimated_cost_usd": cost}

        if source_domain not in seen and company_key(company_name) not in domain_by_key:
            domain_by_key[company_key(company_name)] = source_domain
            new_candidates.append(
                {
                    "company_name": company_name,
                    "domain": source_domain,
                    "url": source["url"],
                    "source_query": source["source_query"],
                    "discovered_via": "direct",
                    # Reuse the page we just fetched instead of paying to
                    # scrape the same URL again in `analyze_candidate`.
                    "page_text": page.text,
                    "page_url": page.url,
                }
            )
            seen.add(source_domain)
            accepted += 1
    else:
        reason = (
            "reference/directory domain" if is_non_company else f"page_type={extraction.page_type}"
        )
        for company in extraction.companies:
            if not discovery.is_valid_company_name(company.name):
                rejected_names.append(company.name)
                continue

            name_key = company_key(company.name)
            if name_key in domain_by_key:
                # Same business from another source. Record the extra source
                # and skip — crucially BEFORE spending a domain lookup on it.
                _record_repeat_sighting(
                    state,
                    pending=new_candidates,
                    domain="",
                    payload=_extra_source_payload(source, company.name),
                )
                continue

            domain: str | None = None
            if company.website:
                candidate_domain = normalize_domain(company.website)
                # A company listed on a page can never have that page's own
                # site as its website — such a link is an internal profile
                # page on the aggregator, not the business. Without this the
                # aggregator itself became the lead's domain, and the same
                # company appeared once per country front-end.
                if (
                    candidate_domain
                    and not discovery.is_non_company_domain(candidate_domain)
                    and not discovery.same_site(candidate_domain, source_domain)
                    # A listing that links "Acme Builders" to an unrelated
                    # host is either a mis-read of the page or an ad link;
                    # fall through to a verified lookup instead.
                    and discovery.domain_matches_company(company.name, candidate_domain)
                ):
                    domain = candidate_domain

            if domain is None:
                domain, lookup_cost = await _lookup_company_domain(state, name=company.name)
                if lookup_cost:
                    lookups_used += 1
                    cost = round(cost + lookup_cost, 4)

            if domain is None:
                _record_agent_event(
                    state["run_id"],
                    node="expand_source",
                    status="ok",
                    summary=(
                        f'Could not find a website for "{company.name}" (named on '
                        f"{source_domain}); skipped rather than guessing a domain."
                    ),
                )
                continue

            if domain in seen:
                # Already queued or persisted from another source — keep the
                # corroborating source instead of discarding this sighting.
                _record_repeat_sighting(
                    state,
                    pending=new_candidates,
                    domain=domain,
                    payload=_extra_source_payload(source, company.name),
                )
                continue

            website = (
                company.website
                if company.website and normalize_domain(company.website) == domain
                else f"https://{domain}"
            )
            new_candidates.append(
                {
                    "company_name": company.name,
                    "domain": domain,
                    "url": website,
                    "source_query": source["source_query"],
                    "discovered_via": "listing",
                    "evidence_source_url": source["url"],
                    "evidence_source_title": source["title"],
                    "evidence_source_excerpt": (source.get("snippet") or source["title"])[:280],
                }
            )
            seen.add(domain)
            domain_by_key[name_key] = domain
            accepted += 1

        _record_agent_event(
            state["run_id"],
            node="expand_source",
            status="ok",
            summary=(
                f"{source_domain} treated as a source, not a lead ({reason}): "
                f"{accepted} company candidate(s) extracted from its content."
            ),
        )

    if rejected_names:
        _record_agent_event(
            state["run_id"],
            node="expand_source",
            status="ok",
            summary=(
                f"Rejected {len(rejected_names)} extracted name(s) from {source_domain} that "
                f"did not look like company names: {', '.join(rejected_names[:5])}."
            ),
        )

    return {
        **patch,
        "pending_candidates": new_candidates,
        "seen_domains": list(seen),
        "domain_by_company_key": domain_by_key,
        "domain_lookups_used": lookups_used,
        "estimated_cost_usd": cost,
    }


async def normalize_and_dedupe(state: ResearchState) -> dict[str, Any]:
    pending = list(state["pending_candidates"])
    candidate = pending.pop(0)
    domain = candidate["domain"]

    existing_company = database.get_company_by_domain(domain=domain)
    if existing_company is not None:
        existing_lead = database.get_lead_by_campaign_and_company(
            campaign_id=state["campaign_id"], company_id=existing_company["id"]
        )
        if existing_lead is not None:
            # The same company turning up on a second listicle must enrich
            # the existing lead's evidence, not create a duplicate lead and
            # not silently vanish.
            merged = _merge_duplicate_evidence(lead_id=existing_lead["id"], candidate=candidate)
            _record_agent_event(
                state["run_id"],
                node="normalize_and_dedupe",
                status="ok",
                summary=(
                    f"{candidate['company_name']} ({domain}) already has a lead in this "
                    "campaign — merged, not duplicated."
                    + (
                        f" Added {candidate.get('evidence_source_url')} as an extra "
                        "evidence source."
                        if merged
                        else ""
                    )
                ),
            )
            return {"pending_candidates": pending, "current_candidate": None}

    return {"pending_candidates": pending, "current_candidate": candidate}


def has_sufficient_evidence(evidence: list[EvidenceItem]) -> bool:
    """A candidate needs at least one `fact` to be scored (FR-10, Phase 3) —
    extracted as a standalone, pure function (specs/phase-5-hardening.md
    FR-3) so the evaluation harness (app/evals) can exercise the exact same
    logic `validate_evidence` uses, rather than a reimplementation that
    could silently drift out of sync.
    """
    return any(item.type == "fact" for item in evidence)


async def analyze_candidate(state: ResearchState) -> dict[str, Any]:
    candidate = state["current_candidate"]
    assert candidate is not None

    if not is_safe_extraction_url(candidate["url"]):
        _record_agent_event(
            state["run_id"],
            node="analyze_candidate",
            status="error",
            summary=(
                f"{candidate['company_name']} ({candidate['domain']}) rejected: "
                "URL failed the SSRF/URL-safety check."
            ),
            error="unsafe_url",
        )
        return _finalize_candidate(
            state,
            candidate=candidate,
            status="rejected",
            decision_reason="unsafe_url",
            score=0,
            evidence=[],
            breakdown=[],
        )

    extraction_provider = get_extraction_provider()

    async def try_extract(url: str) -> Any:
        started = time.monotonic()
        page = await extraction_provider.extract(url=url)
        latency_ms = int((time.monotonic() - started) * 1000)
        _record_tool_call(
            state["run_id"],
            tool="extract",
            provider=type(extraction_provider).__name__,
            status="ok" if page else "error",
            summary=f"Extracted {url} -> {'ok' if page else 'failed'}.",
            latency_ms=latency_ms,
            cost_usd=_EXTRACT_CALL_COST,
            error=None if page else "No content extracted",
        )
        return page

    # `expand_source` already fetched this exact page when the candidate is
    # its own site — reuse it rather than paying to scrape the same URL a
    # second time.
    reused = candidate.get("page_text")
    if reused:
        page = ExtractedPage(url=candidate.get("page_url") or candidate["url"], text=reused)
        cost_after_extract = state["estimated_cost_usd"]
    else:
        page = await try_extract(candidate["url"])
        cost_after_extract = round(state["estimated_cost_usd"] + _EXTRACT_CALL_COST, 4)

        if page is None:
            alternate_url = _toggle_scheme(candidate["url"])
            page = await try_extract(alternate_url)
            cost_after_extract = round(cost_after_extract + _EXTRACT_CALL_COST, 4)

    if page is None:
        patch = _finalize_candidate(
            state,
            candidate=candidate,
            status="rejected",
            decision_reason="extraction_failed",
            score=0,
            evidence=[],
            breakdown=[],
        )
        return {**patch, "estimated_cost_usd": cost_after_extract}

    # The decisive check that this domain really is this company's. A
    # resolved domain is only ever a best guess from a noisy "<name> official
    # website" search — live runs produced website.com, canva.com and
    # flysfo.com for real Pakistani companies. The page we just fetched
    # settles it: a company's own site says its own name. Rejecting here
    # costs one extraction and no analysis, and prevents the worst outcome,
    # a lead pointing at a stranger's website.
    if candidate.get("discovered_via") == "listing" and not discovery.page_mentions_company(
        candidate["company_name"], page.text
    ):
        _record_agent_event(
            state["run_id"],
            node="analyze_candidate",
            status="error",
            summary=(
                f"{candidate['company_name']} rejected: {page.url} never mentions the "
                "company, so the resolved website is not theirs."
            ),
            error="domain_mismatch",
        )
        patch = _finalize_candidate(
            state,
            candidate=candidate,
            status="rejected",
            decision_reason="domain_mismatch",
            score=0,
            evidence=[],
            breakdown=[],
        )
        return {**patch, "estimated_cost_usd": cost_after_extract}

    llm = get_language_model_provider()
    started = time.monotonic()
    analysis, error = await _call_llm_with_retry(
        state,
        lambda: llm.analyze_company(
            icp=state["icp"],
            offer=state.get("offer"),
            company_name=candidate["company_name"],
            domain=candidate["domain"],
            url=page.url,
            page_text=page.text,
        ),
        what=f"Analyzing {candidate['domain']}",
    )
    analysis_ok = analysis is not None
    latency_ms = int((time.monotonic() - started) * 1000)

    _record_tool_call(
        state["run_id"],
        tool="analyze",
        provider=type(llm).__name__,
        status="ok" if analysis_ok else "error",
        summary=f"Analyzed {candidate['domain']} -> {'ok' if analysis_ok else 'failed'}.",
        latency_ms=latency_ms,
        cost_usd=_ANALYZE_CALL_COST,
        error=error,
    )
    new_cost = round(cost_after_extract + _ANALYZE_CALL_COST, 4)

    if not analysis_ok or analysis is None:
        patch = _finalize_candidate(
            state,
            candidate=candidate,
            status="rejected",
            decision_reason="analysis_failed",
            score=0,
            evidence=[],
            breakdown=[],
        )
        return {**patch, "estimated_cost_usd": new_cost}

    return {"current_analysis": analysis, "estimated_cost_usd": new_cost}


async def validate_evidence(state: ResearchState) -> dict[str, Any]:
    analysis = state["current_analysis"]
    assert analysis is not None
    candidate = state["current_candidate"]
    assert candidate is not None

    if not has_sufficient_evidence(analysis.evidence):
        patch = _finalize_candidate(
            state,
            candidate=candidate,
            status="rejected",
            decision_reason="insufficient_evidence",
            score=0,
            evidence=analysis.evidence,
            breakdown=[],
        )
        return patch

    return {}


async def score_candidate(state: ResearchState) -> dict[str, Any]:
    analysis = state["current_analysis"]
    assert analysis is not None
    result = compute_score(analysis.signals.model_dump(), state["weights"])
    return {"current_score": result.total, "current_breakdown": result.breakdown}


async def decide_qualification_node(state: ResearchState) -> dict[str, Any]:
    assert state["current_score"] is not None
    status = decide_qualification(state["current_score"], ScoreThresholds(**state["thresholds"]))
    candidate = state["current_candidate"]
    analysis = state["current_analysis"]
    assert candidate is not None and analysis is not None
    patch = _finalize_candidate(
        state,
        candidate=candidate,
        status=status,
        decision_reason=None,
        score=state["current_score"],
        evidence=analysis.evidence,
        breakdown=state["current_breakdown"] or [],
    )
    return patch


async def complete_run(state: ResearchState) -> dict[str, Any]:
    run = database.get_campaign_run(run_id=state["run_id"])
    paused = bool(run and run.get("pause_requested"))

    if paused:
        stop_reason = "paused_by_user"
    elif _usable_leads(state) >= state["target_lead_count"]:
        stop_reason = "target_reached"
    elif state["estimated_cost_usd"] >= state["limits"]["max_cost_usd"]:
        stop_reason = "budget_exhausted"
    else:
        stop_reason = "queries_exhausted"

    final_status = "paused" if paused else "completed"
    database.update_campaign_run(
        run_id=state["run_id"],
        patch={
            "status": final_status,
            "stop_reason": stop_reason,
            "queries_used": state["queries_used"],
            "leads_created": state["leads_created"],
            "qualified_count": state["qualified_count"],
            "needs_review_count": state["needs_review_count"],
            "rejected_count": state["rejected_count"],
            "failed_count": state["failed_count"],
            "estimated_cost_usd": state["estimated_cost_usd"],
            "completed_at": database.utcnow_iso(),
        },
    )
    database.set_campaign_status(campaign_id=state["campaign_id"], status=final_status)
    _record_agent_event(
        state["run_id"],
        node="complete_run",
        status="ok",
        summary=f"Run finished: {stop_reason}. {state['leads_created']} lead(s) evaluated.",
    )
    return {"stop_reason": stop_reason}


# --- Routing ----------------------------------------------------------


async def route_next(state: ResearchState) -> str:
    """Central dispatcher, re-evaluated between every candidate (FR-13):
    checks the pause flag and every stop condition before deciding whether
    to keep processing pending candidates, fetch more via search, or stop.
    """
    run = database.get_campaign_run(run_id=state["run_id"])
    if run and run.get("pause_requested"):
        return "complete_run"
    if _usable_leads(state) >= state["target_lead_count"]:
        return "complete_run"
    if state["estimated_cost_usd"] >= state["limits"]["max_cost_usd"]:
        return "complete_run"
    if state["pending_candidates"]:
        return "normalize_and_dedupe"
    # Mine already-fetched sources before spending another query.
    if state["pending_sources"]:
        return "expand_source"
    if (
        state["query_cursor"] < len(state["search_plan"])
        and state["queries_used"] < state["limits"]["max_queries"]
    ):
        return "search_companies"
    return "complete_run"


async def route_after_normalize(state: ResearchState) -> str:
    return "analyze_candidate" if state["current_candidate"] is not None else "route_next"


async def route_after_analyze(state: ResearchState) -> str:
    return "validate_evidence" if state["current_analysis"] is not None else "route_next"


async def route_after_validate(state: ResearchState) -> str:
    return "score_candidate" if state["current_analysis"] is not None else "route_next"


def build_graph() -> Any:
    graph = StateGraph(ResearchState)

    graph.add_node("search_companies", search_companies)
    graph.add_node("expand_source", expand_source)
    graph.add_node("normalize_and_dedupe", normalize_and_dedupe)
    graph.add_node("analyze_candidate", analyze_candidate)
    graph.add_node("validate_evidence", validate_evidence)
    graph.add_node("score_candidate", score_candidate)
    graph.add_node("decide_qualification", decide_qualification_node)
    graph.add_node("complete_run", complete_run)
    # `route_next` isn't a real processing node, but conditional edges need a
    # named source; it's registered as a passthrough so multiple nodes can
    # route through the same dispatcher function.
    graph.add_node("route_next", lambda state: {})

    graph.add_edge(START, "search_companies")
    graph.add_edge("search_companies", "route_next")
    graph.add_conditional_edges(
        "route_next",
        route_next,
        {
            "normalize_and_dedupe": "normalize_and_dedupe",
            "expand_source": "expand_source",
            "search_companies": "search_companies",
            "complete_run": "complete_run",
        },
    )
    graph.add_edge("expand_source", "route_next")
    graph.add_conditional_edges(
        "normalize_and_dedupe",
        route_after_normalize,
        {"analyze_candidate": "analyze_candidate", "route_next": "route_next"},
    )
    graph.add_conditional_edges(
        "analyze_candidate",
        route_after_analyze,
        {"validate_evidence": "validate_evidence", "route_next": "route_next"},
    )
    graph.add_conditional_edges(
        "validate_evidence",
        route_after_validate,
        {"score_candidate": "score_candidate", "route_next": "route_next"},
    )
    graph.add_edge("score_candidate", "decide_qualification")
    graph.add_edge("decide_qualification", "route_next")
    graph.add_edge("complete_run", END)

    return graph.compile()


_GRAPH = build_graph()


def build_initial_state(
    *,
    run_id: str,
    campaign_id: str,
    icp: dict[str, Any],
    offer: str | None,
    search_plan: list[dict[str, Any]],
    weights: dict[str, int],
    thresholds: dict[str, int],
    limits: dict[str, Any],
    target_lead_count: int,
) -> ResearchState:
    return ResearchState(
        run_id=run_id,
        campaign_id=campaign_id,
        icp=icp,
        offer=offer,
        search_plan=search_plan,
        weights=weights,
        thresholds=thresholds,
        limits=limits,
        target_lead_count=target_lead_count,
        query_cursor=0,
        query_retry_count=0,
        pending_sources=[],
        pending_candidates=[],
        seen_source_urls=[],
        seen_domains=[],
        domain_by_company_key={},
        domain_lookups_used=0,
        # Domain lookups share the search budget but must never starve the
        # planned queries, so they may only use what the plan won't.
        max_domain_lookups=max(0, limits["max_queries"] - len(search_plan)),
        current_candidate=None,
        current_analysis=None,
        current_score=None,
        current_breakdown=None,
        queries_used=0,
        leads_created=0,
        qualified_count=0,
        needs_review_count=0,
        rejected_count=0,
        failed_count=0,
        estimated_cost_usd=0.0,
        stop_reason=None,
    )


async def run_research(state: ResearchState) -> None:
    """The background-task entry point (FR-1). Flips the run/campaign to
    `running` first, then drives the graph. An exception escaping the graph
    is a terminal failure (`handleTerminalFailure`, plan.md §9 — implemented
    here rather than as a graph node; see specs/phase-3-research.md,
    Technical Design) — whatever was already persisted is kept.
    """
    database.update_campaign_run(run_id=state["run_id"], patch={"status": "running"})
    database.set_campaign_status(campaign_id=state["campaign_id"], status="running")
    _record_agent_event(state["run_id"], node="run_research", status="ok", summary="Run started.")

    try:
        await _GRAPH.ainvoke(state)
    except Exception as exc:  # noqa: BLE001 - deliberate: any escaping error is a terminal failure
        database.update_campaign_run(
            run_id=state["run_id"],
            patch={
                "status": "failed",
                "stop_reason": "error",
                "error": str(exc),
                "completed_at": database.utcnow_iso(),
            },
        )
        database.set_campaign_status(campaign_id=state["campaign_id"], status="failed")
        _record_agent_event(
            state["run_id"],
            node="run_research",
            status="error",
            summary="Run failed.",
            error=str(exc),
        )
