from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app import database
from app.config import Settings, get_settings
from app.deps import CurrentUser, get_current_user
from app.providers import LanguageModelProvider, LLMOutputError, get_language_model_provider
from app.schemas import (
    ICP,
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdateRequest,
    DeleteResponse,
    RunLimits,
    ScoreThresholds,
    ScoreWeights,
    SearchPlanQuery,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_APPROVED_STATUSES = {"plan_approved", "queued"}


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "campaign_not_found", "message": "Campaign not found."}
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

    campaign_patch: dict[str, Any] = {}
    if body.brief is not None:
        campaign_patch["brief"] = body.brief
    if body.offer is not None:
        campaign_patch["offer"] = body.offer
    if body.target_lead_count is not None:
        campaign_patch["target_lead_count"] = body.target_lead_count
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

    made_any_change = bool(campaign_patch) or bool(icp_patch)
    if made_any_change and existing["status"] in _APPROVED_STATUSES:
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
    _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    database.delete_campaign(user_id=current_user.id, campaign_id=campaign_id)
    return DeleteResponse(deleted=True)


@router.post("/{campaign_id}/plan", response_model=CampaignResponse)
async def generate_plan(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    provider: Annotated[LanguageModelProvider, Depends(get_language_model_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CampaignResponse:
    campaign = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)

    extraction = None
    last_error: Exception | None = None
    for _attempt in range(settings.plan_generation_max_attempts):
        try:
            extraction = await provider.generate_campaign_plan(
                brief=campaign["brief"],
                offer=campaign.get("offer"),
                target_lead_count=campaign["target_lead_count"],
            )
            break
        except (LLMOutputError, ValidationError) as exc:
            last_error = exc

    if extraction is None:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "plan_generation_failed",
                "message": f"The language model did not return a usable plan after "
                f"{settings.plan_generation_max_attempts} attempt(s): {last_error}",
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

    database.update_campaign(
        user_id=current_user.id,
        campaign_id=campaign_id,
        patch={
            "status": "awaiting_plan_approval",
            "plan_approved_at": None,
            "search_plan": [q.model_dump() for q in extraction.search_plan],
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
    _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    icp_row = database.get_icp(campaign_id=campaign_id)

    if not icp_row or not icp_row.get("industries") or not icp_row.get("locations"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "plan_incomplete",
                "message": (
                    "Generate a complete plan (with at least one industry and one "
                    "location) before approving it."
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


@router.post("/{campaign_id}/run", response_model=CampaignResponse)
async def run_campaign(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CampaignResponse:
    campaign = _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)

    if campaign["status"] != "plan_approved":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "plan_not_approved",
                "message": "Approve the plan with /confirm-plan before starting a run.",
            },
        )

    database.update_campaign(
        user_id=current_user.id, campaign_id=campaign_id, patch={"status": "queued"}
    )

    updated_row = database.get_campaign(user_id=current_user.id, campaign_id=campaign_id)
    assert updated_row is not None
    icp_row = database.get_icp(campaign_id=campaign_id)
    return _row_to_response(updated_row, icp_row)
