from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.deps import CurrentUser, get_current_user
from app.schemas import ProfileResponse
from app.supabase_client import get_supabase_admin_client

router = APIRouter(tags=["me"])


@router.get("/me", response_model=ProfileResponse)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ProfileResponse:
    supabase = get_supabase_admin_client()

    # Always scoped to the id extracted from the verified JWT — never a
    # client-supplied id — so this admin-client query cannot leak another
    # user's profile even though it bypasses RLS.
    result = supabase.table("profiles").select("*").eq("id", current_user.id).limit(1).execute()

    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=404, detail={"code": "profile_not_found", "message": "Profile not found."}
        )

    return ProfileResponse(**rows[0])
