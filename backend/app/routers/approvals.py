from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app import database
from app.deps import CurrentUser, get_current_user
from app.providers import EmailProvider, get_email_provider
from app.routers.leads import approval_to_response
from app.schemas import (
    ApprovalDraftEditRequest,
    ApprovalListResponse,
    ApprovalRejectRequest,
    ApprovalResponse,
    ApprovalSendRequest,
    ApprovalStatus,
    EmailSendResult,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404, detail={"code": "approval_not_found", "message": "Approval not found."}
    )


def _get_owned_approval_or_404(
    *, user_id: str, approval_id: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Returns (approval, draft, lead, campaign) after verifying ownership
    through draft -> lead -> campaign, the same join-through-Python pattern
    used everywhere else in this codebase (see database.py's own docstring
    on list_approvals_for_user).
    """
    approval = database.get_approval(approval_id=approval_id)
    if approval is None:
        raise _not_found()
    draft = database.get_outreach_draft(draft_id=approval["draft_id"])
    if draft is None:
        raise _not_found()
    lead = database.get_lead(lead_id=draft["lead_id"])
    if lead is None:
        raise _not_found()
    campaign = database.get_campaign(user_id=user_id, campaign_id=lead["campaign_id"])
    if campaign is None:
        raise _not_found()
    return approval, draft, lead, campaign


def _domain_suppressed(*, user_id: str, lead: dict[str, Any]) -> bool:
    company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
    return database.is_domain_suppressed(user_id=user_id, domain=company["domain"])


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    status: ApprovalStatus | None = None,
) -> ApprovalListResponse:
    rows, next_cursor = database.list_approvals_for_user(
        user_id=current_user.id, limit=limit, cursor=cursor, status=status
    )
    items = []
    for approval in rows:
        draft = database.get_outreach_draft(draft_id=approval["draft_id"])
        assert draft is not None
        lead = database.get_lead(lead_id=draft["lead_id"])
        assert lead is not None
        company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
        items.append(approval_to_response(approval, draft, lead, company))
    return ApprovalListResponse(items=items, next_cursor=next_cursor)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve(
    approval_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApprovalResponse:
    approval, draft, lead, _campaign = _get_owned_approval_or_404(
        user_id=current_user.id, approval_id=approval_id
    )

    if lead["status"] != "qualified":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "lead_not_qualified",
                "message": "This lead is no longer qualified; approval is blocked.",
            },
        )
    if _domain_suppressed(user_id=current_user.id, lead=lead):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "domain_suppressed",
                "message": "This company's domain is suppressed and cannot be approved.",
            },
        )

    updated = database.update_approval(
        approval_id=approval_id,
        patch={
            "status": "approved",
            "reviewer_id": current_user.id,
            "decided_at": database.utcnow_iso(),
        },
    )
    assert updated is not None
    company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
    return approval_to_response(updated, draft, lead, company)


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
async def reject(
    approval_id: str,
    body: ApprovalRejectRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApprovalResponse:
    approval, draft, lead, _campaign = _get_owned_approval_or_404(
        user_id=current_user.id, approval_id=approval_id
    )

    updated = database.update_approval(
        approval_id=approval_id,
        patch={
            "status": "rejected",
            "reviewer_id": current_user.id,
            "decided_at": database.utcnow_iso(),
        },
    )
    assert updated is not None
    company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
    return approval_to_response(updated, draft, lead, company)


@router.patch("/{approval_id}/draft", response_model=ApprovalResponse)
async def edit_draft(
    approval_id: str,
    body: ApprovalDraftEditRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApprovalResponse:
    approval, draft, lead, _campaign = _get_owned_approval_or_404(
        user_id=current_user.id, approval_id=approval_id
    )

    draft_patch: dict[str, Any] = {}
    if body.subject is not None:
        draft_patch["subject"] = body.subject
    if body.body is not None:
        draft_patch["body"] = body.body
    updated_draft = database.update_outreach_draft(draft_id=draft["id"], patch=draft_patch)
    assert updated_draft is not None

    # Editing invalidates whatever decision existed (plan.md §11) — reset to
    # pending regardless of the prior status, including "rejected" (there's
    # no reason an edited-then-resubmitted draft should stay rejected).
    approval_patch = {"edited": True}
    if approval["status"] != "pending":
        approval_patch.update({"status": "pending", "reviewer_id": None, "decided_at": None})
    updated_approval = database.update_approval(approval_id=approval_id, patch=approval_patch)
    assert updated_approval is not None

    company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
    return approval_to_response(updated_approval, updated_draft, lead, company)


@router.post("/{approval_id}/send", response_model=EmailSendResult)
async def send(
    approval_id: str,
    body: ApprovalSendRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> EmailSendResult:
    # Plain function call, not FastAPI Depends — see the identical note in
    # app/routers/leads.py::regenerate_outreach.
    provider: EmailProvider = get_email_provider()
    approval, draft, lead, _campaign = _get_owned_approval_or_404(
        user_id=current_user.id, approval_id=approval_id
    )

    if approval["status"] != "approved":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "approval_not_approved",
                "message": "Only an approved draft can be sent.",
            },
        )
    if lead["status"] != "qualified":
        raise HTTPException(
            status_code=409,
            detail={"code": "lead_not_qualified", "message": "This lead is no longer qualified."},
        )
    if _domain_suppressed(user_id=current_user.id, lead=lead):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "domain_suppressed",
                "message": "This company's domain is suppressed and cannot be sent to.",
            },
        )

    return await provider.send(to_email=body.to_email, subject=draft["subject"], body=draft["body"])
