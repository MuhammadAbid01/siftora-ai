from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app import database, outreach
from app.deps import CurrentUser, get_current_user
from app.providers import LanguageModelProvider, get_language_model_provider
from app.schemas import (
    ApprovalResponse,
    CompanySummary,
    EvidenceItem,
    LeadDetailResponse,
    LeadListResponse,
    LeadStatusUpdateRequest,
    LeadSummaryResponse,
    OutreachDraftResponse,
    RegenerateOutreachRequest,
    ScoreBreakdownItem,
    ScoreThresholds,
    ScoreWeights,
)
from app.scoring import compute_score, decide_qualification

router = APIRouter(tags=["leads"])

# One regeneration on quality failure, then accept whatever the second
# attempt produced (specs/phase-4-outreach.md FR-5/FR-8) — never more.
_MAX_DRAFT_ATTEMPTS = 2


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


def _draft_to_response(draft: dict[str, Any]) -> OutreachDraftResponse:
    return OutreachDraftResponse(
        id=draft["id"],
        lead_id=draft["lead_id"],
        channel=draft["channel"],
        subject=draft["subject"],
        body=draft["body"],
        version=draft["version"],
        quality_status=draft["quality_status"],
        evidence_refs=draft.get("evidence_refs") or [],
        created_at=draft["created_at"],
        updated_at=draft["updated_at"],
    )


def approval_to_response(
    approval: dict[str, Any],
    draft: dict[str, Any],
    lead: dict[str, Any],
    company: dict[str, Any],
) -> ApprovalResponse:
    return ApprovalResponse(
        id=approval["id"],
        draft=_draft_to_response(draft),
        lead_id=lead["id"],
        campaign_id=lead["campaign_id"],
        company=_company_summary(company),
        lead_status=lead["status"],
        lead_score=lead["score"],
        status=approval["status"],
        reviewer_id=approval.get("reviewer_id"),
        decided_at=approval.get("decided_at"),
        edited=approval["edited"],
        created_at=approval["created_at"],
        updated_at=approval["updated_at"],
    )


def _lead_approvals(lead: dict[str, Any], company: dict[str, Any]) -> list[ApprovalResponse]:
    drafts = database.list_outreach_drafts_by_lead(lead_id=lead["id"])
    results = []
    for draft in drafts:
        approval = database.get_approval_by_draft(draft_id=draft["id"])
        if approval is not None:
            results.append(approval_to_response(approval, draft, lead, company))
    return results


def _lead_evidence_items(lead_id: str) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            type=item["type"],
            claim=item["claim"],
            excerpt=item.get("excerpt"),
            source_url=item.get("source_url"),
            confidence=(float(item["confidence"]) if item.get("confidence") is not None else None),
        )
        for item in database.list_lead_evidence(lead_id=lead_id)
    ]


def _lead_to_detail(lead: dict[str, Any], company: dict[str, Any]) -> LeadDetailResponse:
    evidence = _lead_evidence_items(lead["id"])
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
        approvals=_lead_approvals(lead, company),
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


@router.patch("/leads/{lead_id}/status", response_model=LeadDetailResponse)
async def update_lead_status(
    lead_id: str,
    body: LeadStatusUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> LeadDetailResponse:
    lead, _campaign = _get_owned_lead_or_404(user_id=current_user.id, lead_id=lead_id)

    database.update_lead(
        lead_id=lead_id,
        patch={"status": body.status, "decision_reason": body.reason or "manual_override"},
    )

    updated_lead = database.get_lead(lead_id=lead_id)
    assert updated_lead is not None
    company = database.get_companies_by_ids([updated_lead["company_id"]])[
        updated_lead["company_id"]
    ]
    return _lead_to_detail(updated_lead, company)


@router.post(
    "/leads/{lead_id}/regenerate-outreach", response_model=ApprovalResponse, status_code=201
)
async def regenerate_outreach(
    lead_id: str,
    body: RegenerateOutreachRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApprovalResponse:
    # Called as a plain function, not via FastAPI Depends: like
    # app/agent.py, get_language_model_provider's own `settings` parameter
    # is a plain Python default, not a Depends() — combining it with a real
    # endpoint body param under FastAPI's dependency injection would make
    # FastAPI treat both as separate body fields requiring an embedded
    # {"body": ..., "settings": ...} envelope instead of a flat JSON body.
    provider: LanguageModelProvider = get_language_model_provider()
    lead, campaign = _get_owned_lead_or_404(user_id=current_user.id, lead_id=lead_id)

    if lead["status"] != "qualified":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "lead_not_qualified",
                "message": "Only qualified leads can receive outreach drafts.",
            },
        )

    company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
    if database.is_domain_suppressed(user_id=current_user.id, domain=company["domain"]):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "domain_suppressed",
                "message": "This company's domain is suppressed and cannot enter approval.",
            },
        )

    icp_row = database.get_icp(campaign_id=campaign["id"]) or {}
    evidence = _lead_evidence_items(lead_id)

    assembled_body = ""
    quality_ok = False
    draft_result = None
    for attempt in range(_MAX_DRAFT_ATTEMPTS):
        draft_result = await provider.draft_outreach(
            icp=icp_row,
            offer=campaign.get("offer"),
            company_name=company["name"],
            domain=company["domain"],
            evidence=evidence,
            channel=body.channel,
            sender_name=campaign.get("sender_name"),
            attempt=attempt,
        )
        assembled_body = outreach.assemble_body(
            company_name=company["name"],
            sender_name=campaign.get("sender_name"),
            observation=draft_result.observation,
            offer_line=draft_result.offer_line,
            cta=draft_result.cta,
        )
        quality_ok, _reasons = outreach.check_quality(
            body=assembled_body, evidence_refs=draft_result.evidence_refs, evidence=evidence
        )
        if quality_ok:
            break

    assert draft_result is not None
    version = database.get_next_draft_version(lead_id=lead_id, channel=body.channel)
    draft = database.create_outreach_draft(
        lead_id=lead_id,
        channel=body.channel,
        subject=draft_result.subject,
        body=assembled_body,
        version=version,
        quality_status="passed" if quality_ok else "needs_review",
        evidence_refs=draft_result.evidence_refs,
    )
    approval = database.create_approval(draft_id=draft["id"])
    return approval_to_response(approval, draft, lead, company)
