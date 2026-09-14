"""The Phase 3 research graph (plan.md §9, adapted — see
specs/phase-3-research.md, Technical Design, "LangGraph usage" for the
documented deviations from the full cross-phase node list).

No checkpointer: a run completes within one `ainvoke()` call inside a
FastAPI BackgroundTask (in-process, plan.md §5/§6) — no cross-process
durability is needed or claimed.
"""

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app import database
from app.providers import (
    LLMOutputError,
    get_extraction_provider,
    get_language_model_provider,
    get_search_provider,
    normalize_domain,
)
from app.schemas import CompanyAnalysis, EvidenceItem, ScoreBreakdownItem, ScoreThresholds
from app.scoring import compute_score, decide_qualification

# Small, fixed, clearly-synthetic per-call costs so the cost-limit code path
# is exercisable without any real provider billing data (see
# specs/phase-3-research.md, Risks — "synthetic cost model").
_SEARCH_CALL_COST = 0.01
_EXTRACT_CALL_COST = 0.01
_ANALYZE_CALL_COST = 0.02


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
    pending_candidates: list[dict[str, Any]]
    seen_domains: list[str]
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
        source_url=candidate["url"],
        status=status,
        score=score,
        decision_reason=decision_reason,
    )
    database.create_lead_evidence(
        lead_id=lead["id"], items=[e.model_dump(exclude_none=True) for e in evidence]
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

    is_operational_failure = decision_reason in ("extraction_failed", "analysis_failed")
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

    new_pending = list(state["pending_candidates"])
    seen = set(state["seen_domains"])
    added = 0
    for r in results:
        domain = normalize_domain(r.domain)
        if domain in seen:
            continue
        new_pending.append(
            {
                "company_name": r.company_name,
                "domain": domain,
                "url": r.url,
                "source_query": query_item["query"],
            }
        )
        seen.add(domain)
        added += 1

    _record_agent_event(
        state["run_id"],
        node="search_companies",
        status="ok",
        summary=(
            f'Query "{query_item["query"]}" found {len(results)} result(s), '
            f"{added} new candidate(s)."
        ),
    )

    return {
        "pending_candidates": new_pending,
        "seen_domains": list(seen),
        "query_cursor": query_cursor + 1,
        "query_retry_count": 0,
        "queries_used": state["queries_used"] + 1,
        "estimated_cost_usd": new_cost,
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
            _record_agent_event(
                state["run_id"],
                node="normalize_and_dedupe",
                status="ok",
                summary=(
                    f"{candidate['company_name']} ({domain}) already has a lead in this "
                    "campaign — merged, not duplicated."
                ),
            )
            return {"pending_candidates": pending, "current_candidate": None}

    return {"pending_candidates": pending, "current_candidate": candidate}


async def analyze_candidate(state: ResearchState) -> dict[str, Any]:
    candidate = state["current_candidate"]
    assert candidate is not None
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

    llm = get_language_model_provider()
    started = time.monotonic()
    try:
        analysis = await llm.analyze_company(
            icp=state["icp"],
            offer=state.get("offer"),
            company_name=candidate["company_name"],
            domain=candidate["domain"],
            url=page.url,
            page_text=page.text,
        )
        analysis_ok, error = True, None
    except LLMOutputError as exc:
        analysis, analysis_ok, error = None, False, str(exc)
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

    has_fact = any(item.type == "fact" for item in analysis.evidence)
    if not has_fact:
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
    elif state["leads_created"] >= state["target_lead_count"]:
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
    if state["leads_created"] >= state["target_lead_count"]:
        return "complete_run"
    if state["estimated_cost_usd"] >= state["limits"]["max_cost_usd"]:
        return "complete_run"
    if state["pending_candidates"]:
        return "normalize_and_dedupe"
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
            "search_companies": "search_companies",
            "complete_run": "complete_run",
        },
    )
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
        pending_candidates=[],
        seen_domains=[],
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
