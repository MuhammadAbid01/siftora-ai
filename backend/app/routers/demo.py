from typing import Annotated

from fastapi import APIRouter, Depends

from app import database
from app.deps import CurrentUser, get_current_user
from app.schemas import DemoResetResponse

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", response_model=DemoResetResponse)
async def reset_demo_data(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DemoResetResponse:
    """Deletes every campaign owned by the current user (specs/
    phase-5-hardening.md FR-8) — cascades to ICP/runs/leads/evidence/
    breakdowns/drafts/approvals via existing foreign keys. Never touches
    the global `companies` table (not user data) or another user's rows.
    """
    campaigns, _cursor = database.list_campaigns(user_id=current_user.id, limit=1000, cursor=None)
    deleted = 0
    for campaign in campaigns:
        if database.delete_campaign(user_id=current_user.id, campaign_id=campaign["id"]):
            deleted += 1
    return DemoResetResponse(deleted_campaigns=deleted)
