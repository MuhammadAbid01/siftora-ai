from typing import Any

import pytest

from app import agent, database
from app.schemas import ScoreWeights
from tests.fakes.supabase_fake import FakeSupabaseClient

USER_ID = "44444444-4444-4444-4444-444444444444"

ICP = {
    "industries": ["Design agencies", "Animation studios"],
    "locations": ["Dubai, UAE"],
    "company_size_min": None,
    "company_size_max": None,
    "signals": [],
    "exclusions": [],
    "target_roles": [],
}

FULL_SEARCH_PLAN = [
    {"query": "Design agencies in Dubai, UAE", "rationale": "r1"},
    {"query": "Animation studios in Dubai, UAE", "rationale": "r2"},
    {"query": "Consulting firms in London, UK", "rationale": "r3"},
    {"query": "Design agencies in Faraway City", "rationale": "r4"},
]


def _setup(
    fake_supabase: FakeSupabaseClient,
    *,
    target_lead_count: int = 10,
    max_cost_usd: float = 5.00,
    search_plan: list[dict[str, Any]] | None = None,
    brief: str = "Find design agencies and animation studios in Dubai, UAE.",
) -> tuple[dict, dict]:
    campaign = database.create_campaign(
        user_id=USER_ID, brief=brief, offer=None, target_lead_count=target_lead_count
    )
    database.update_campaign(
        user_id=USER_ID,
        campaign_id=campaign["id"],
        patch={"limit_max_cost_usd": max_cost_usd},
    )
    campaign = database.get_campaign(user_id=USER_ID, campaign_id=campaign["id"])
    assert campaign is not None

    run = database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
    return campaign, run


def _build_state(
    campaign: dict, run: dict, search_plan: list[dict[str, Any]]
) -> agent.ResearchState:
    return agent.build_initial_state(
        run_id=run["id"],
        campaign_id=campaign["id"],
        icp=ICP,
        offer=None,
        search_plan=search_plan,
        weights=campaign["score_weights"],
        thresholds={
            "qualified_min": campaign["score_threshold_qualified"],
            "needs_review_min": campaign["score_threshold_needs_review"],
        },
        limits={
            "max_queries": campaign["limit_max_queries"],
            "max_pages_per_company": campaign["limit_max_pages_per_company"],
            "max_retries": campaign["limit_max_retries"],
            "max_cost_usd": float(campaign["limit_max_cost_usd"]),
        },
        target_lead_count=campaign["target_lead_count"],
    )


class TestFullRun:
    async def test_processes_all_candidates_and_exhausts_queries(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign, run = _setup(fake_supabase, target_lead_count=10, search_plan=FULL_SEARCH_PLAN)
        state = _build_state(campaign, run, FULL_SEARCH_PLAN)

        await agent.run_research(state)

        finished_run = database.get_campaign_run(run_id=run["id"])
        assert finished_run is not None
        assert finished_run["status"] == "completed"
        assert finished_run["stop_reason"] == "queries_exhausted"

        finished_campaign = database.get_campaign(user_id=USER_ID, campaign_id=campaign["id"])
        assert finished_campaign is not None
        assert finished_campaign["status"] == "completed"

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        by_domain = {}
        for lead in leads:
            company = database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]
            by_domain[company["domain"]] = lead

        assert set(by_domain) == {
            "northbeamstudio.example",
            "vantagemotion.example",
            "pixelandpine.example",
            "harborconsulting.example",
            "brokenlink.example",
        }
        assert by_domain["northbeamstudio.example"]["status"] == "qualified"
        assert by_domain["northbeamstudio.example"]["score"] == 92
        assert by_domain["vantagemotion.example"]["status"] == "needs_review"
        assert by_domain["pixelandpine.example"]["status"] == "rejected"
        assert by_domain["pixelandpine.example"]["decision_reason"] == "insufficient_evidence"
        assert by_domain["brokenlink.example"]["status"] == "rejected"
        assert by_domain["brokenlink.example"]["decision_reason"] == "extraction_failed"
        assert by_domain["harborconsulting.example"]["status"] == "rejected"
        assert by_domain["harborconsulting.example"]["decision_reason"] is None

        # AC-8: score breakdown links to evidence — every scored lead (not
        # rejected-by-failure) has both a full breakdown and stored evidence.
        northbeam_lead = by_domain["northbeamstudio.example"]
        breakdown = database.list_score_breakdown(lead_id=northbeam_lead["id"])
        evidence = database.list_lead_evidence(lead_id=northbeam_lead["id"])
        assert len(breakdown) == 8
        assert sum(b["points"] for b in breakdown) == pytest.approx(92, abs=0.5)
        assert any(e["type"] == "fact" for e in evidence)
        assert any(e["type"] == "unknown" and e["source_url"] is None for e in evidence)

        # extraction_failed / insufficient_evidence leads never invented a score.
        broken_lead = by_domain["brokenlink.example"]
        assert database.list_score_breakdown(lead_id=broken_lead["id"]) == []

        events, _ = database.list_agent_events(run_id=run["id"], limit=100, cursor=None)
        tool_calls, _ = database.list_tool_calls(run_id=run["id"], limit=100, cursor=None)
        assert len(events) > 0
        assert len(tool_calls) > 0

    async def test_target_reached_stops_after_enough_leads(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign, run = _setup(fake_supabase, target_lead_count=1, search_plan=FULL_SEARCH_PLAN)
        state = _build_state(campaign, run, FULL_SEARCH_PLAN)

        await agent.run_research(state)

        finished_run = database.get_campaign_run(run_id=run["id"])
        assert finished_run is not None
        assert finished_run["stop_reason"] == "target_reached"
        assert finished_run["leads_created"] == 1

    async def test_budget_exhausted_stops_the_run(self, fake_supabase: FakeSupabaseClient) -> None:
        campaign, run = _setup(
            fake_supabase, target_lead_count=100, max_cost_usd=0.03, search_plan=FULL_SEARCH_PLAN
        )
        state = _build_state(campaign, run, FULL_SEARCH_PLAN)

        await agent.run_research(state)

        finished_run = database.get_campaign_run(run_id=run["id"])
        assert finished_run is not None
        assert finished_run["stop_reason"] == "budget_exhausted"
        assert finished_run["leads_created"] == 1

    async def test_pause_requested_stops_before_processing_anything(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign, run = _setup(fake_supabase, target_lead_count=10, search_plan=FULL_SEARCH_PLAN)
        database.update_campaign_run(run_id=run["id"], patch={"pause_requested": True})
        state = _build_state(campaign, run, FULL_SEARCH_PLAN)

        await agent.run_research(state)

        finished_run = database.get_campaign_run(run_id=run["id"])
        assert finished_run is not None
        assert finished_run["status"] == "paused"
        assert finished_run["stop_reason"] == "paused_by_user"
        assert finished_run["leads_created"] == 0

    async def test_query_revision_recovers_a_weak_query_within_limits(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        # Query 4 alone: fails strict match, succeeds on the first revision.
        campaign, run = _setup(
            fake_supabase, target_lead_count=10, search_plan=[FULL_SEARCH_PLAN[3]]
        )
        state = _build_state(campaign, run, [FULL_SEARCH_PLAN[3]])

        await agent.run_research(state)

        events, _ = database.list_agent_events(run_id=run["id"], limit=100, cursor=None)
        revision_events = [e for e in events if "revising" in e["summary"]]
        assert len(revision_events) == 1

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        # Relaxed (any-tag) matching on retry finds every "design agenc"-tagged
        # fixture company, not just the one this test originally targeted.
        assert len(leads) == 3


class TestCrossRunDedup:
    async def test_same_company_across_two_campaigns_shares_one_company_row(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        query = [FULL_SEARCH_PLAN[1]]  # "Animation studios in Dubai, UAE" -> Northbeam only

        campaign_a, run_a = _setup(
            fake_supabase,
            search_plan=query,
            brief="Find animation studios in Dubai, UAE first time.",
        )
        await agent.run_research(_build_state(campaign_a, run_a, query))

        campaign_b, run_b = _setup(
            fake_supabase,
            search_plan=query,
            brief="Find animation studios in Dubai, UAE second time.",
        )
        await agent.run_research(_build_state(campaign_b, run_b, query))

        company = database.get_company_by_domain(domain="northbeamstudio.example")
        assert company is not None

        leads_a, _ = database.list_leads(campaign_id=campaign_a["id"], limit=10, cursor=None)
        leads_b, _ = database.list_leads(campaign_id=campaign_b["id"], limit=10, cursor=None)
        assert len(leads_a) == 1
        assert len(leads_b) == 1
        assert leads_a[0]["company_id"] == company["id"]
        assert leads_b[0]["company_id"] == company["id"]
        assert leads_a[0]["id"] != leads_b[0]["id"]

    async def test_rerunning_the_same_campaign_does_not_duplicate_the_lead(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        query = [FULL_SEARCH_PLAN[1]]
        campaign, run_1 = _setup(fake_supabase, search_plan=query)
        await agent.run_research(_build_state(campaign, run_1, query))

        run_2 = database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        await agent.run_research(_build_state(campaign, run_2, query))

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=10, cursor=None)
        assert len(leads) == 1  # merged, not duplicated (AC-6)


class TestScoringDeterminism:
    def test_same_signals_and_weights_always_score_the_same(self) -> None:
        from app.scoring import compute_score

        weights = ScoreWeights().model_dump()
        signals = {
            "industry_fit": 0.7,
            "geography_fit": 0.6,
            "company_size_fit": 0.5,
            "pain_point_evidence": 0.8,
            "buying_signal": 0.4,
            "contact_relevance": 0.3,
            "recency": 0.9,
            "evidence_completeness": 0.6,
        }
        results = [compute_score(signals, weights).total for _ in range(5)]
        assert len(set(results)) == 1
