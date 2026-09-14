from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app import database
from app.deps import CurrentUser, get_current_user
from app.schemas import (
    AgentEventListResponse,
    AgentEventResponse,
    ToolCallListResponse,
    ToolCallResponse,
)

router = APIRouter(prefix="/runs", tags=["runs"])


def _get_owned_run_or_404(*, user_id: str, run_id: str) -> dict[str, Any]:
    run = database.get_campaign_run(run_id=run_id)
    if run is None:
        raise HTTPException(
            status_code=404, detail={"code": "run_not_found", "message": "Run not found."}
        )
    campaign = database.get_campaign(user_id=user_id, campaign_id=run["campaign_id"])
    if campaign is None:
        raise HTTPException(
            status_code=404, detail={"code": "run_not_found", "message": "Run not found."}
        )
    return run


@router.get("/{run_id}/events", response_model=AgentEventListResponse)
async def list_events(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> AgentEventListResponse:
    _get_owned_run_or_404(user_id=current_user.id, run_id=run_id)
    rows, next_cursor = database.list_agent_events(run_id=run_id, limit=limit, cursor=cursor)
    items = [
        AgentEventResponse(
            id=row["id"],
            run_id=row["run_id"],
            node=row["node"],
            status=row["status"],
            summary=row["summary"],
            duration_ms=row.get("duration_ms"),
            error=row.get("error"),
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return AgentEventListResponse(items=items, next_cursor=next_cursor)


@router.get("/{run_id}/tool-calls", response_model=ToolCallListResponse)
async def list_tool_calls(
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> ToolCallListResponse:
    _get_owned_run_or_404(user_id=current_user.id, run_id=run_id)
    rows, next_cursor = database.list_tool_calls(run_id=run_id, limit=limit, cursor=cursor)
    items = [
        ToolCallResponse(
            id=row["id"],
            run_id=row["run_id"],
            tool=row["tool"],
            provider=row["provider"],
            status=row["status"],
            summary=row["summary"],
            latency_ms=row.get("latency_ms"),
            cost_usd=(float(row["cost_usd"]) if row.get("cost_usd") is not None else None),
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return ToolCallListResponse(items=items, next_cursor=next_cursor)
