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
COMPANIES_TABLE = "companies"
CAMPAIGN_RUNS_TABLE = "campaign_runs"
LEADS_TABLE = "leads"
LEAD_EVIDENCE_TABLE = "lead_evidence"
SCORE_BREAKDOWNS_TABLE = "score_breakdowns"
AGENT_EVENTS_TABLE = "agent_events"
TOOL_CALLS_TABLE = "tool_calls"


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


def set_campaign_status(*, campaign_id: str, status: str) -> None:
    """Internal, trusted write (no user_id filter) used by the background
    research driver — ownership was already checked once, at `/run` time.
    """
    client = get_supabase_admin_client()
    client.table(CAMPAIGNS_TABLE).update({"status": status}).eq("id", campaign_id).execute()


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


# --- Companies (Phase 3) — global, deduplicated by domain ---------------


def get_company_by_domain(*, domain: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = client.table(COMPANIES_TABLE).select("*").eq("domain", domain).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None


def upsert_company_by_domain(*, domain: str, name: str) -> dict[str, Any]:
    """Get-or-create by domain (FR-6/FR-7 dedup). Refreshes `name` and
    `verified_at` even on an existing row, since being discovered again is
    itself a fresh verification.
    """
    client = get_supabase_admin_client()
    existing = get_company_by_domain(domain=domain)
    patch = {"name": name, "verified_at": utcnow_iso()}

    if existing is None:
        result = client.table(COMPANIES_TABLE).insert({"domain": domain, **patch}).execute()
    else:
        result = client.table(COMPANIES_TABLE).update(patch).eq("domain", domain).execute()
    return result.data[0]


# --- Campaign runs (Phase 3) ---------------------------------------------


def create_campaign_run(*, campaign_id: str, config_snapshot: dict[str, Any]) -> dict[str, Any]:
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGN_RUNS_TABLE)
        .insert({"campaign_id": campaign_id, "config_snapshot": config_snapshot})
        .execute()
    )
    return result.data[0]


def get_campaign_run(*, run_id: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = client.table(CAMPAIGN_RUNS_TABLE).select("*").eq("id", run_id).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None


def get_active_campaign_run(*, campaign_id: str) -> dict[str, Any] | None:
    """The campaign's run currently queued or running, if any (FR-3 idempotency)."""
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGN_RUNS_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .in_("status", ["queued", "running"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_latest_campaign_run(*, campaign_id: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = (
        client.table(CAMPAIGN_RUNS_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def update_campaign_run(*, run_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = client.table(CAMPAIGN_RUNS_TABLE).update(patch).eq("id", run_id).execute()
    rows = result.data or []
    return rows[0] if rows else None


# --- Leads (Phase 3) ------------------------------------------------------


def create_lead(
    *,
    campaign_id: str,
    company_id: str,
    source_url: str,
    status: str,
    score: int,
    decision_reason: str | None,
) -> dict[str, Any]:
    client = get_supabase_admin_client()
    result = (
        client.table(LEADS_TABLE)
        .insert(
            {
                "campaign_id": campaign_id,
                "company_id": company_id,
                "source_url": source_url,
                "status": status,
                "score": score,
                "decision_reason": decision_reason,
            }
        )
        .execute()
    )
    return result.data[0]


def get_lead_by_campaign_and_company(*, campaign_id: str, company_id: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = (
        client.table(LEADS_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("company_id", company_id)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def get_lead(*, lead_id: str) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = client.table(LEADS_TABLE).select("*").eq("id", lead_id).limit(1).execute()
    rows = result.data or []
    return rows[0] if rows else None


def list_leads(
    *, campaign_id: str, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    client = get_supabase_admin_client()
    query = (
        client.table(LEADS_TABLE)
        .select("*")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)

    rows = query.execute().data or []
    next_cursor = rows[-1]["created_at"] if len(rows) == limit else None
    return rows, next_cursor


def update_lead(*, lead_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    client = get_supabase_admin_client()
    result = client.table(LEADS_TABLE).update(patch).eq("id", lead_id).execute()
    rows = result.data or []
    return rows[0] if rows else None


def get_companies_by_ids(company_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not company_ids:
        return {}
    client = get_supabase_admin_client()
    result = client.table(COMPANIES_TABLE).select("*").in_("id", company_ids).execute()
    return {row["id"]: row for row in result.data or []}


# --- Lead evidence + score breakdowns (Phase 3) --------------------------


def create_lead_evidence(*, lead_id: str, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    client = get_supabase_admin_client()
    client.table(LEAD_EVIDENCE_TABLE).insert(
        [{"lead_id": lead_id, **item} for item in items]
    ).execute()


def list_lead_evidence(*, lead_id: str) -> list[dict[str, Any]]:
    client = get_supabase_admin_client()
    result = client.table(LEAD_EVIDENCE_TABLE).select("*").eq("lead_id", lead_id).execute()
    return result.data or []


def create_score_breakdown(*, lead_id: str, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    client = get_supabase_admin_client()
    client.table(SCORE_BREAKDOWNS_TABLE).insert(
        [{"lead_id": lead_id, **item} for item in items]
    ).execute()


def list_score_breakdown(*, lead_id: str) -> list[dict[str, Any]]:
    client = get_supabase_admin_client()
    result = client.table(SCORE_BREAKDOWNS_TABLE).select("*").eq("lead_id", lead_id).execute()
    return result.data or []


def replace_score_breakdown(*, lead_id: str, items: list[dict[str, Any]]) -> None:
    """Used by rescore (FR-18): the lead's signals didn't change, only the
    weights did, so the breakdown rows are fully replaced.
    """
    client = get_supabase_admin_client()
    client.table(SCORE_BREAKDOWNS_TABLE).delete().eq("lead_id", lead_id).execute()
    create_score_breakdown(lead_id=lead_id, items=items)


# --- Agent events + tool calls (Phase 3) ---------------------------------


def create_agent_event(
    *,
    run_id: str,
    node: str,
    status: str,
    summary: str,
    duration_ms: int | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    client = get_supabase_admin_client()
    result = (
        client.table(AGENT_EVENTS_TABLE)
        .insert(
            {
                "run_id": run_id,
                "node": node,
                "status": status,
                "summary": summary,
                "duration_ms": duration_ms,
                "error": error,
            }
        )
        .execute()
    )
    return result.data[0]


def list_agent_events(
    *, run_id: str, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    client = get_supabase_admin_client()
    query = (
        client.table(AGENT_EVENTS_TABLE)
        .select("*")
        .eq("run_id", run_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)
    rows = query.execute().data or []
    next_cursor = rows[-1]["created_at"] if len(rows) == limit else None
    return rows, next_cursor


def create_tool_call(
    *,
    run_id: str,
    tool: str,
    provider: str,
    status: str,
    summary: str,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
) -> dict[str, Any]:
    client = get_supabase_admin_client()
    result = (
        client.table(TOOL_CALLS_TABLE)
        .insert(
            {
                "run_id": run_id,
                "tool": tool,
                "provider": provider,
                "status": status,
                "summary": summary,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
            }
        )
        .execute()
    )
    return result.data[0]


def list_tool_calls(
    *, run_id: str, limit: int, cursor: str | None
) -> tuple[list[dict[str, Any]], str | None]:
    client = get_supabase_admin_client()
    query = (
        client.table(TOOL_CALLS_TABLE)
        .select("*")
        .eq("run_id", run_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if cursor:
        query = query.lt("created_at", cursor)
    rows = query.execute().data or []
    next_cursor = rows[-1]["created_at"] if len(rows) == limit else None
    return rows, next_cursor
