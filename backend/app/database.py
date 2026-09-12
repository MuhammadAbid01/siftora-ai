"""Supabase repository functions for campaigns + campaign_icp (plan.md §6).

Every function is scoped by `user_id` extracted from the verified JWT —
never a client-supplied id — even though the underlying client uses the
service role key and therefore bypasses RLS. See specs/phase-2-campaigns.md.
"""

from datetime import UTC, datetime
from typing import Any

from app.supabase_client import get_supabase_admin_client

CAMPAIGNS_TABLE = "campaigns"
CAMPAIGN_ICP_TABLE = "campaign_icp"


def create_campaign(
    *, user_id: str, brief: str, offer: str | None, target_lead_count: int
) -> dict[str, Any]:
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGNS_TABLE)
        .insert(
            {
                "user_id": user_id,
                "brief": brief,
                "offer": offer,
                "target_lead_count": target_lead_count,
            }
        )
        .execute()
    )
    return result.data[0]


def list_campaigns(
    *, user_id: str, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    client = get_supabase_admin_client()
    query = (
        client.table(CAMPAIGNS_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)

    rows = query.execute().data or []
    next_cursor = rows[-1]["created_at"] if len(rows) == limit else None
    return rows, next_cursor


def get_campaign(*, user_id: str, campaign_id: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGNS_TABLE)
        .select("*")
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def update_campaign(
    *, user_id: str, campaign_id: str, patch: dict[str, Any]
) -> dict[str, Any] | None:
    if not patch:
        return get_campaign(user_id=user_id, campaign_id=campaign_id)

    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGNS_TABLE)
        .update(patch)
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def delete_campaign(*, user_id: str, campaign_id: str) -> bool:
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGNS_TABLE)
        .delete()
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


def get_icp(*, campaign_id: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGN_ICP_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_icps_for_campaigns(campaign_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not campaign_ids:
        return {}
    client = get_supabase_admin_client()
    result = client.table(CAMPAIGN_ICP_TABLE).select("*").in_("campaign_id", campaign_ids).execute()
    return {row["campaign_id"]: row for row in result.data or []}


def upsert_icp(*, campaign_id: str, data: dict[str, Any]) -> dict[str, Any]:
    client = get_supabase_admin_client()
    existing = get_icp(campaign_id=campaign_id)

    if existing is None:
        result = (
            client.table(CAMPAIGN_ICP_TABLE).insert({"campaign_id": campaign_id, **data}).execute()
        )
    else:
        result = (
            client.table(CAMPAIGN_ICP_TABLE).update(data).eq("campaign_id", campaign_id).execute()
        )
    return result.data[0]


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()
