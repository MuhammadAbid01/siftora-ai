from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app import database
from app.deps import CurrentUser, get_current_user
from app.schemas import (
    CompanySummary,
    EvidenceItem,
    LeadDetailResponse,
    LeadListResponse,
    LeadSummaryResponse,
    ScoreBreakdownItem,
    ScoreThresholds,
    ScoreWeights,
)
from app.scoring import compute_score, decide_qualification

router = APIRouter(tags=["leads"])


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def _get_owned_campaign_or_404(*, user_id: str, campaign_id: str) -> dict[str, Any]:
    row = database.get_campaign(user_id=user_id, campaign_id=campaign_id)
    if row is None:
        raise _not_found("campaign_not_found", "Campaign not found.")
    return row


def _get_owned_lead_or_404(*, user_id: str, lead_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    lead = database.get_lead(lead_id=lead_id)
    if lead is None:
        raise _not_found("lead_not_found", "Lead not found.")
    campaign = database.get_campaign(user_id=user_id, campaign_id=lead["campaign_id"])
    if campaign is None:
        raise _not_found("lead_not_found", "Lead not found.")
    return lead, campaign


def _company_summary(row: dict[str, Any]) -> CompanySummary:
    return CompanySummary(id=row["id"], domain=row["domain"], name=row["name"])


def _lead_to_summary(lead: dict[str, Any], company: dict[str, Any]) -> LeadSummaryResponse:
    return LeadSummaryResponse(
        id=lead["id"],
        campaign_id=lead["campaign_id"],
        company=_company_summary(company),
        source_url=lead["source_url"],
        status=lead["status"],
        score=lead["score"],
        decision_reason=lead.get("decision_reason"),
        created_at=lead["created_at"],
        updated_at=lead["updated_at"],
    )


def _lead_to_detail(lead: dict[str, Any], company: dict[str, Any]) -> LeadDetailResponse:
    evidence = [
        EvidenceItem(
            type=item["type"],
            claim=item["claim"],
            excerpt=item.get("excerpt"),
            source_url=item.get("source_url"),
            confidence=(float(item["confidence"]) if item.get("confidence") is not None else None),
        )
        for item in database.list_lead_evidence(lead_id=lead["id"])
    ]
    breakdown = [
        ScoreBreakdownItem(
            criterion=item["criterion"],
            rating=item["rating"],
            weight=item["weight"],
            points=item["points"],
        )
        for item in database.list_score_breakdown(lead_id=lead["id"])
    ]
    return LeadDetailResponse(
        id=lead["id"],
        campaign_id=lead["campaign_id"],
        company=_company_summary(company),
        source_url=lead["source_url"],
        status=lead["status"],
        score=lead["score"],
        decision_reason=lead.get("decision_reason"),
        evidence=evidence,
        score_breakdown=breakdown,
        created_at=lead["created_at"],
        updated_at=lead["updated_at"],
    )


@router.get("/campaigns/{campaign_id}/leads", response_model=LeadListResponse)
async def list_campaign_leads(
    campaign_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> LeadListResponse:
    _get_owned_campaign_or_404(user_id=current_user.id, campaign_id=campaign_id)
    rows, next_cursor = database.list_leads(campaign_id=campaign_id, limit=limit, cursor=cursor)
    companies = database.get_companies_by_ids([row["company_id"] for row in rows])
    items = [_lead_to_summary(row, companies[row["company_id"]]) for row in rows]
    return LeadListResponse(items=items, next_cursor=next_cursor)


@router.get("/leads/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> LeadDetailResponse:
    lead, _campaign = _get_owned_lead_or_404(user_id=current_user.id, lead_id=lead_id)
    company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
    return _lead_to_detail(lead, company)


@router.post("/leads/{lead_id}/rescore", response_model=LeadDetailResponse)
async def rescore_lead(
    lead_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> LeadDetailResponse:
    lead, campaign = _get_owned_lead_or_404(user_id=current_user.id, lead_id=lead_id)

    existing_breakdown = database.list_score_breakdown(lead_id=lead_id)
    if not existing_breakdown:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "lead_not_scored",
                "message": (
                    "This lead was never scored (e.g. extraction or evidence failed), "
                    "so there's nothing to rescore."
                ),
            },
        )

    signals = {item["criterion"]: item["rating"] for item in existing_breakdown}
    weights = ScoreWeights(**campaign["score_weights"]).model_dump()
    thresholds = ScoreThresholds(
        qualified_min=campaign["score_threshold_qualified"],
        needs_review_min=campaign["score_threshold_needs_review"],
    )

    result = compute_score(signals, weights)
    new_status = decide_qualification(result.total, thresholds)

    database.replace_score_breakdown(
        lead_id=lead_id,
        items=[
            {"criterion": b.criterion, "rating": b.rating, "weight": b.weight, "points": b.points}
            for b in result.breakdown
        ],
    )
    database.update_lead(
        lead_id=lead_id,
        patch={"status": new_status, "score": result.total, "decision_reason": None},
    )

    updated_lead = database.get_lead(lead_id=lead_id)
    assert updated_lead is not None
    company = database.get_companies_by_ids([updated_lead["company_id"]])[
        updated_lead["company_id"]
    ]
    return _lead_to_detail(updated_lead, company)
