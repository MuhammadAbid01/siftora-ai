import csv
import io
import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import ValidationError

from app import agent, database
from app.config import Settings, get_settings
from app.deps import CurrentUser, get_current_user
from app.providers import (
    LanguageModelProvider,
    LLMOutputError,
    LLMUnavailableError,
    get_language_model_provider,
)
from app.rate_limit import rate_limiter
from app.schemas import (
    ICP,
    CampaignAnalyticsResponse,
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignRunResponse,
    CampaignUpdateRequest,
    DeleteResponse,
    RunLimits,
    ScoreThresholds,
    ScoreWeights,
    SearchPlanQuery,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# Editing one of these reverts the campaign to `draft` (Phase 2 behavior,
# extended to `completed`/`failed`/`paused` — re-running after a finished
# (or user-paused) run requires re-approval too, same as a first-time run).
_REVERT_ON_EDIT_STATUSES = {"plan_approved", "completed", "failed", "paused"}
# Only while a run is actually queued/in-flight is editing blocked —
# changing config out from under a live run would corrupt it (plan.md §10,
# "immutable for a run"). `paused` is NOT here: by the time a run reaches
# `paused` it has already stopped for good (pause is a clean stop, not a
# checkpoint — specs/phase-3-research.md's "no true resume" risk note), so
# it must be treated like `completed`/`failed` or the campaign would be
# stuck forever with no way to confirm-plan, edit, or run again. See
# specs/phase-3-research.md FR-2 for why this differs from Phase 2, which
# put `queued` in the revert set above instead.
_BLOCKED_FROM_EDIT_STATUSES = {"queued", "running"}


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "campaign_not_found", "message": "Campaign not found."}
    )


def _reject_if_run_active(campaign: dict[str, Any]) -> None:
    """Blocks any mutation (edit, regenerate/confirm plan, delete) while a
    run is queued/running/paused (FR-2) — not just PATCH. Regenerating the
    plan or deleting the campaign out from under an active run would corrupt
    the displayed status or orphan the run's writes.
    """
    if campaign["status"] in _BLOCKED_FROM_EDIT_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "campaign_running",
                "message": (
                    "This campaign has an active run. Pause it (or wait for it to "
                    "finish) before making changes."
                ),
            },
        )


def _row_to_response(row: dict[str, Any], icp_row: dict[str, Any] | None) -> CampaignResponse:
    icp = None
    if icp_row is not None:
        icp = ICP(
            industries=icp_row.get("industries") or [],
            locations=icp_row.get("locations") or [],
            company_size_min=icp_row.get("company_size_min"),
            company_size_max=icp_row.get("company_size_max"),
            signals=icp_row.get("signals") or [],
            exclusions=icp_row.get("exclusions") or [],
            target_roles=icp_row.get("target_roles") or [],
        )

    search_plan = None
    if row.get("search_plan"):
        search_plan = [SearchPlanQuery(**q) for q in row["search_plan"]]

    return CampaignResponse(
        id=row["id"],
        status=row["status"],
        brief=row["brief"],
        offer=row.get("offer"),
        target_lead_count=row["target_lead_count"],
        sender_name=row.get("sender_name"),
        sender_email=row.get("sender_email"),
        icp=icp,
        search_plan=search_plan,
        score_weights=ScoreWeights(**row["score_weights"]),
        score_thresholds=ScoreThresholds(
            qualified_min=row["score_threshold_qualified"],
            needs_review_min=row["score_threshold_needs_review"],
        ),
        limits=RunLimits(
            max_queries=row["limit_max_queries"],
            max_pages_per_company=row["limit_max_pages_per_company"],
            max_retries=row["limit_max_retries"],
            max_cost_usd=float(row["limit_max_cost_usd"]),
        ),
        plan_approved_at=row.get("plan_approved_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _run_row_to_response(row: dict[str, Any]) -> CampaignRunResponse:
    return CampaignRunResponse(
        id=row["id"],
        campaign_id=row["campaign_id"],
        status=row["status"],
        stop_reason=row.get("stop_reason"),
        queries_used=row["queries_used"],
        leads_created=row["leads_created"],
        qualified_count=row["qualified_count"],
        needs_review_count=row["needs_review_count"],
        rejected_count=row["rejected_count"],
        failed_count=row["failed_count"],
        estimated_cost_usd=float(row["estimated_cost_usd"]),
        error=row.get("error"),
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
    )


def _icp_row_to_dict(icp_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "industries": icp_row.get("industries") or [],
        "locations": icp_row.get("locations") or [],
        "company_size_min": icp_row.get("company_size_min"),
        "company_size_max": icp_row.get("company_size_max"),
        "signals": icp_row.get("signals") or [],
        "exclusions": icp_row.get("exclusions") or [],
        "target_roles": icp_row.get("target_roles") or [],
    }


def _get_owned_campaign_or_404(*, user_id: str, campaign_id: str) -> dict[str, Any]:
    row = database.get_campaign(user_id=user_id, campaign_id=campaign_id)
    if row is None:
        raise _not_found()
    return row


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CampaignCreateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignResponse:
    row = database.create_campaign(
        user_id=current_user.id,
        brief=body.brief,
        offer=body.offer,
        target_lead_count=body.target_lead_count,
        sender_name=body.sender_name,
        sender_email=body.sender_email,
    )
    return _row_to_response(row, icp_row=None)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> CampaignListResponse:
    rows, next_cursor = database.list_campaigns(user_id=current_user.id, limit=limit, cursor=cursor)
    icp_by_campaign_id = database.get_icps_for_campaigns([row["id"] for row in rows])
    items = [_row_to_response(row, icp_by_campaign_id.get(row["id"])) for row in rows]
    return CampaignListResponse(items=items, next_cursor=next_cursor)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignResponse:
    row = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    icp_row = database.get_icp(campaign_id=campaign_id)
    return _row_to_response(row, icp_row)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignResponse:
    existing = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    _reject_if_run_active(existing)

    campaign_patch: dict[str, Any] = {}
    if body.brief is not None:
        campaign_patch["brief"] = body.brief
    if body.offer is not None:
        campaign_patch["offer"] = body.offer
    if body.target_lead_count is not None:
        campaign_patch["target_lead_count"] = body.target_lead_count
    if body.sender_name is not None:
        campaign_patch["sender_name"] = body.sender_name
    if body.sender_email is not None:
        campaign_patch["sender_email"] = body.sender_email
    if body.score_weights is not None:
        campaign_patch["score_weights"] = body.score_weights.model_dump()
    if body.score_thresholds is not None:
        campaign_patch["score_threshold_qualified"] = body.score_thresholds.qualified_min
        campaign_patch["score_threshold_needs_review"] = body.score_thresholds.needs_review_min
    if body.limits is not None:
        campaign_patch["limit_max_queries"] = body.limits.max_queries
        campaign_patch["limit_max_pages_per_company"] = body.limits.max_pages_per_company
        campaign_patch["limit_max_retries"] = body.limits.max_retries
        campaign_patch["limit_max_cost_usd"] = body.limits.max_cost_usd

    icp_patch = body.icp.model_dump(exclude_none=True) if body.icp is not None else {}

    # Sender info doesn't affect plan/research validity — only future
    # drafts' signoff line — so it's excluded from the "does this edit
    # require re-approval" check (specs/phase-4-outreach.md FR-18).
    _SENDER_FIELDS = {"sender_name", "sender_email"}
    plan_affecting_patch = {k: v for k, v in campaign_patch.items() if k not in _SENDER_FIELDS}

    made_any_change = bool(plan_affecting_patch) or bool(icp_patch)
    if made_any_change and existing["status"] in _REVERT_ON_EDIT_STATUSES:
        campaign_patch["status"] = "draft"
        campaign_patch["plan_approved_at"] = None

    if campaign_patch:
        database.update_campaign(
            user_id=current_user.id, campaign_id=campaign_id, patch=campaign_patch
        )
    if icp_patch:
        database.upsert_icp(campaign_id=campaign_id, data=icp_patch)

    updated_row = database.get_campaign(user_id=current_user.id, campaign_id=campaign_id)
    assert updated_row is not None
    icp_row = database.get_icp(campaign_id=campaign_id)
    return _row_to_response(updated_row, icp_row)


@router.delete("/{campaign_id}", response_model=DeleteResponse)
async def delete_campaign(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DeleteResponse:
    existing = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    _reject_if_run_active(existing)
    database.delete_campaign(user_id=current_user.id, campaign_id=campaign_id)
    return DeleteResponse(deleted=True)


@router.post(
    "/{campaign_id}/plan",
    response_model=CampaignResponse,
    dependencies=[Depends(rate_limiter("plan", max_requests=10, window_seconds=60))],
)
async def generate_plan(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    provider: Annotated[LanguageModelProvider, Depends(get_language_model_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CampaignResponse:
    campaign = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    _reject_if_run_active(campaign)

    extraction = None
    last_error: Exception | None = None
    provider_unavailable = False
    for attempt in range(settings.plan_generation_max_attempts):
        try:
            extraction = await provider.generate_campaign_plan(
                brief=campaign["brief"],
                offer=campaign.get("offer"),
                target_lead_count=campaign["target_lead_count"],
            )
            break
        except LLMUnavailableError as exc:
            # The provider itself failed (timeout, rate limit, upstream
            # error). There was no output to repair, so this is worth
            # another attempt — and it must not be reported to the user as
            # "your brief couldn't be parsed", which is what the single
            # generic 502 used to do.
            last_error, provider_unavailable = exc, True
            logger.warning(
                "Plan generation attempt %d/%d unavailable for campaign %s: %s",
                attempt + 1,
                settings.plan_generation_max_attempts,
                campaign_id,
                exc,
            )
        except (LLMOutputError, ValidationError) as exc:
            last_error, provider_unavailable = exc, False
            logger.warning(
                "Plan generation attempt %d/%d returned unusable output for campaign %s: %s",
                attempt + 1,
                settings.plan_generation_max_attempts,
                campaign_id,
                exc,
            )

    if extraction is None:
        logger.error(
            "Plan generation failed for campaign %s after %d attempt(s): %s",
            campaign_id,
            settings.plan_generation_max_attempts,
            last_error,
        )
        if provider_unavailable:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "plan_provider_unavailable",
                    "message": (
                        "The planning model is not responding right now. Nothing about "
                        "your campaign has changed — please try again in a moment."
                    ),
                    # The technical cause is reported, not swallowed, but it
                    # is kept out of the headline message shown to the user.
                    "details": {"reason": str(last_error)},
                },
            )
        raise HTTPException(
            status_code=502,
            detail={
                "code": "plan_generation_failed",
                "message": (
                    "We couldn't turn this brief into a plan. Try adding a bit more "
                    "detail — for example the type of company you're targeting and the "
                    "city or country they're in — then generate the plan again."
                ),
                "details": {"reason": str(last_error)},
            },
        )

    database.upsert_icp(campaign_id=campaign_id, data=extraction.icp.model_dump())

    missing_fields = [
        field
        for field, values in (
            ("industries", extraction.icp.industries),
            ("locations", extraction.icp.locations),
        )
        if not values
    ]

    if missing_fields:
        database.update_campaign(
            user_id=current_user.id,
            campaign_id=campaign_id,
            patch={"status": "draft", "plan_approved_at": None, "search_plan": None},
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": "icp_incomplete",
                "message": "The brief didn't specify enough information to build a complete ICP.",
                "details": {"missing_fields": missing_fields},
            },
        )

    # A model can return a complete ICP but forget the search plan. The ICP
    # alone can't be approved (confirm-plan requires both), which would
    # strand the campaign with no way forward, so derive a plain
    # industry × location plan from what was actually extracted. This
    # invents no new targeting information — only phrasings of fields the
    # model already returned.
    search_plan = list(extraction.search_plan)
    if not search_plan:
        search_plan = [
            SearchPlanQuery(
                query=f"{industry} in {location}",
                rationale="Derived from the extracted industry and location.",
            )
            for industry in extraction.icp.industries[:3]
            for location in extraction.icp.locations[:2]
        ]
        logger.info(
            "Model returned no search plan for campaign %s; derived %d quer(ies) from the ICP.",
            campaign_id,
            len(search_plan),
        )

    database.update_campaign(
        user_id=current_user.id,
        campaign_id=campaign_id,
        patch={
            "status": "awaiting_plan_approval",
            "plan_approved_at": None,
            "search_plan": [q.model_dump() for q in search_plan],
        },
    )

    updated_row = database.get_campaign(user_id=current_user.id, campaign_id=campaign_id)
    assert updated_row is not None
    icp_row = database.get_icp(campaign_id=campaign_id)
    return _row_to_response(updated_row, icp_row)


@router.post("/{campaign_id}/confirm-plan", response_model=CampaignResponse)
async def confirm_plan(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignResponse:
    campaign = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    _reject_if_run_active(campaign)
    icp_row = database.get_icp(campaign_id=campaign_id)

    icp_incomplete = not icp_row or not icp_row.get("industries") or not icp_row.get("locations")
    # A campaign can reach a complete ICP without ever regenerating a
    # search_plan — e.g. a user manually fills in the missing ICP fields
    # after an `icp_incomplete` /plan response (FR-20, Phase 2) without
    # calling /plan again. Approving that would let /run start with nothing
    # to search for (queries_used stays 0, zero leads, silently) — so both
    # must be checked, not just the ICP.
    search_plan_missing = not campaign.get("search_plan")

    if icp_incomplete or search_plan_missing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "plan_incomplete",
                "message": (
                    "Generate a complete plan (with at least one industry, one "
                    "location, and a search plan) before approving it."
                ),
            },
        )

    database.update_campaign(
        user_id=current_user.id,
        campaign_id=campaign_id,
        patch={"status": "plan_approved", "plan_approved_at": database.utcnow_iso()},
    )

    updated_row = database.get_campaign(user_id=current_user.id, campaign_id=campaign_id)
    assert updated_row is not None
    return _row_to_response(updated_row, icp_row)


@router.post(
    "/{campaign_id}/run",
    response_model=CampaignResponse,
    dependencies=[Depends(rate_limiter("run", max_requests=5, window_seconds=60))],
)
async def run_campaign(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
) -> CampaignResponse:
    campaign = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)

    # Idempotent (FR-3): a run already queued/running is returned as-is,
    # never duplicated.
    if database.get_active_campaign_run(campaign_id=campaign_id) is not None:
        icp_row = database.get_icp(campaign_id=campaign_id)
        return _row_to_response(campaign, icp_row)

    if campaign["status"] != "plan_approved":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "plan_not_approved",
                "message": "Approve the plan with /confirm-plan before starting a run.",
            },
        )

    icp_row = database.get_icp(campaign_id=campaign_id)
    assert icp_row is not None  # guaranteed complete by confirm-plan (FR-15)

    config_snapshot = {
        "score_weights": campaign["score_weights"],
        "score_threshold_qualified": campaign["score_threshold_qualified"],
        "score_threshold_needs_review": campaign["score_threshold_needs_review"],
        "limit_max_queries": campaign["limit_max_queries"],
        "limit_max_pages_per_company": campaign["limit_max_pages_per_company"],
        "limit_max_retries": campaign["limit_max_retries"],
        "limit_max_cost_usd": float(campaign["limit_max_cost_usd"]),
        "target_lead_count": campaign["target_lead_count"],
    }
    run = database.create_campaign_run(campaign_id=campaign_id, config_snapshot=config_snapshot)
    database.update_campaign(
        user_id=current_user.id, campaign_id=campaign_id, patch={"status": "queued"}
    )

    state = agent.build_initial_state(
        run_id=run["id"],
        campaign_id=campaign_id,
        icp=_icp_row_to_dict(icp_row),
        offer=campaign.get("offer"),
        search_plan=campaign.get("search_plan") or [],
        weights=campaign["score_weights"],
        thresholds={
            "qualified_min": campaign["score_threshold_qualified"],
            "needs_review_min": campaign["score_threshold_needs_review"],
        },
        limits={
            "max_queries": campaign["limit_max_queries"],
            "max_pages_per_company": campaign["limit_max_pages_per_company"],
            "max_retries": campaign["limit_max_retries"],
            "max_cost_usd": float(campaign["limit_max_cost_usd"]),
        },
        target_lead_count=campaign["target_lead_count"],
    )
    background_tasks.add_task(agent.run_research, state)

    updated_row = database.get_campaign(user_id=current_user.id, campaign_id=campaign_id)
    assert updated_row is not None
    return _row_to_response(updated_row, icp_row)


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignResponse:
    campaign = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    active_run = database.get_active_campaign_run(campaign_id=campaign_id)

    if active_run is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "no_active_run", "message": "There is no active run to pause."},
        )

    database.update_campaign_run(run_id=active_run["id"], patch={"pause_requested": True})

    icp_row = database.get_icp(campaign_id=campaign_id)
    return _row_to_response(campaign, icp_row)


@router.get("/{campaign_id}/progress", response_model=CampaignRunResponse)
async def get_progress(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignRunResponse:
    _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    run = database.get_latest_campaign_run(campaign_id=campaign_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "no_run_yet", "message": "This campaign has not been run yet."},
        )

    return _run_row_to_response(run)


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalyticsResponse)
async def get_analytics(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignAnalyticsResponse:
    """Funnel/cost/latency/failure aggregation across every run of this
    campaign (specs/phase-5-hardening.md FR-6) — a campaign run more than
    once shows cumulative numbers, not just the latest run's (see that
    spec's Risks for why).
    """
    _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)

    runs = database.list_campaign_runs(campaign_id=campaign_id)
    if not runs:
        raise HTTPException(
            status_code=404,
            detail={"code": "no_run_yet", "message": "This campaign has not been run yet."},
        )

    leads, _cursor = database.list_leads(campaign_id=campaign_id, limit=1000, cursor=None)
    qualified_count = sum(1 for lead in leads if lead["status"] == "qualified")
    needs_review_count = sum(1 for lead in leads if lead["status"] == "needs_review")
    rejected_count = sum(1 for lead in leads if lead["status"] == "rejected")

    drafts_generated = 0
    drafts_approved = 0
    drafts_rejected = 0
    for lead in leads:
        for draft in database.list_outreach_drafts_by_lead(lead_id=lead["id"]):
            drafts_generated += 1
            approval = database.get_approval_by_draft(draft_id=draft["id"])
            if approval is not None and approval["status"] == "approved":
                drafts_approved += 1
            elif approval is not None and approval["status"] == "rejected":
                drafts_rejected += 1

    total_cost_usd = round(sum(float(r["estimated_cost_usd"]) for r in runs), 2)
    total_queries_used = sum(r["queries_used"] for r in runs)

    run_ids = [r["id"] for r in runs]
    tool_calls = database.list_tool_calls_for_runs(run_ids=run_ids)
    agent_events = database.list_agent_events_for_runs(run_ids=run_ids)

    latencies = [tc["latency_ms"] for tc in tool_calls if tc.get("latency_ms") is not None]
    avg_tool_latency_ms = (sum(latencies) / len(latencies)) if latencies else None

    tool_call_failures = sum(1 for tc in tool_calls if tc["status"] == "error")
    agent_event_failures = sum(1 for ev in agent_events if ev["status"] == "error")

    return CampaignAnalyticsResponse(
        campaign_id=campaign_id,
        qualified_count=qualified_count,
        needs_review_count=needs_review_count,
        rejected_count=rejected_count,
        drafts_generated=drafts_generated,
        drafts_approved=drafts_approved,
        drafts_rejected=drafts_rejected,
        total_cost_usd=total_cost_usd,
        total_queries_used=total_queries_used,
        avg_tool_latency_ms=avg_tool_latency_ms,
        tool_call_failures=tool_call_failures,
        agent_event_failures=agent_event_failures,
        runs_count=len(runs),
    )


_EXPORT_FIELDNAMES = [
    "lead_id",
    "company_name",
    "domain",
    "source_url",
    "score",
    "status",
    "channel",
    "subject",
    "body",
    "approved_at",
    "reviewer_email",
]


def _latest_drafts_by_channel(lead_id: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for draft in database.list_outreach_drafts_by_lead(lead_id=lead_id):
        channel = draft["channel"]
        if channel not in latest or draft["version"] > latest[channel]["version"]:
            latest[channel] = draft
    return latest


@router.post("/{campaign_id}/export")
async def export_campaign_leads(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    """CSV of every lead+channel whose latest-version draft is approved and
    whose company domain isn't suppressed — re-checked here, not cached from
    approval time (specs/phase-4-outreach.md FR-16).
    """
    _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)

    leads, _cursor = database.list_leads(campaign_id=campaign_id, limit=1000, cursor=None)
    companies = database.get_companies_by_ids([lead["company_id"] for lead in leads])

    rows: list[dict[str, Any]] = []
    for lead in leads:
        company = companies[lead["company_id"]]
        if database.is_domain_suppressed(user_id=current_user.id, domain=company["domain"]):
            continue
        for channel, draft in _latest_drafts_by_channel(lead["id"]).items():
            approval = database.get_approval_by_draft(draft_id=draft["id"])
            if approval is None or approval["status"] != "approved":
                continue
            rows.append(
                {
                    "lead_id": lead["id"],
                    "company_name": company["name"],
                    "domain": company["domain"],
                    "source_url": lead["source_url"],
                    "score": lead["score"],
                    "status": lead["status"],
                    "channel": channel,
                    "subject": draft["subject"],
                    "body": draft["body"],
                    "approved_at": approval.get("decided_at") or "",
                    # Only the campaign owner can ever reach this route (or
                    # approve a draft in the first place), so the reviewer
                    # is always the current requester in this MVP's
                    # single-reviewer-per-campaign model.
                    "reviewer_email": current_user.email,
                }
            )

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_EXPORT_FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="campaign-{campaign_id}-export.csv"'
        },
    )
