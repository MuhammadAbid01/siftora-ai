from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app import database
from app.deps import CurrentUser, get_current_user
from app.providers import normalize_domain
from app.schemas import (
    DeleteResponse,
    SuppressionCreateRequest,
    SuppressionEntryResponse,
    SuppressionListResponse,
)

router = APIRouter(prefix="/suppression", tags=["suppression"])


def _to_response(row: dict) -> SuppressionEntryResponse:
    return SuppressionEntryResponse(
        id=row["id"], domain=row["domain"], reason=row.get("reason"), created_at=row["created_at"]
    )


@router.post("", response_model=SuppressionEntryResponse, status_code=201)
async def create_suppression_entry(
    body: SuppressionCreateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> SuppressionEntryResponse:
    row = database.create_suppression_entry(
        user_id=current_user.id, domain=normalize_domain(body.domain), reason=body.reason
    )
    return _to_response(row)


@router.get("", response_model=SuppressionListResponse)
async def list_suppression_entries(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> SuppressionListResponse:
    rows, next_cursor = database.list_suppression_entries(
        user_id=current_user.id, limit=limit, cursor=cursor
    )
    return SuppressionListResponse(items=[_to_response(r) for r in rows], next_cursor=next_cursor)


@router.delete("/{entry_id}", response_model=DeleteResponse)
async def delete_suppression_entry(
    entry_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DeleteResponse:
    existing = database.get_suppression_entry(user_id=current_user.id, entry_id=entry_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "suppression_entry_not_found", "message": "Entry not found."},
        )
    database.delete_suppression_entry(user_id=current_user.id, entry_id=entry_id)
    return DeleteResponse(deleted=True)
