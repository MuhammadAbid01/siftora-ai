from typing import Any

from fastapi.testclient import TestClient

from app import agent, database
from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

ADMIN = {"sub": "e0000000-0000-0000-0000-000000000001", "email": "admin@example.com"}
NON_ADMIN = {"sub": "e0000000-0000-0000-0000-000000000002", "email": "user@example.com"}

_EXPECTED_CATEGORIES = {
    "campaign_parsing",
    "planning",
    "candidate_validation",
    "deduplication",
    "scoring",
    "outreach_grounding",
}


def _make_profile(fake_supabase: FakeSupabaseClient, *, user_id: str, role: str) -> None:
    fake_supabase.table("profiles").insert(
        {"id": user_id, "email": f"{user_id}@example.com", "role": role}
    ).execute()


class TestEvalHarnessEndpoint:
    def test_non_admin_is_forbidden(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        _make_profile(fake_supabase, user_id=NON_ADMIN["sub"], role="user")

        response = client.post("/api/evals/run", headers=auth_header(**NON_ADMIN))

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "admin_required"

    def test_missing_profile_is_forbidden(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        response = client.post("/api/evals/run", headers=auth_header(**NON_ADMIN))

        assert response.status_code == 403

    def test_admin_gets_a_full_report_at_100_percent_against_fixtures(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        _make_profile(fake_supabase, user_id=ADMIN["sub"], role="admin")

        response = client.post("/api/evals/run", headers=auth_header(**ADMIN))

        assert response.status_code == 200
        body = response.json()
        assert {c["category"] for c in body["categories"]} == _EXPECTED_CATEGORIES
        assert body["overall_pass_rate"] == 1.0
        for category in body["categories"]:
            assert category["pass_rate"] == 1.0, category
        assert body["provider_mode"] == {
            "llm": "fixture",
            "search": "fixture",
            "extraction": "fixture",
        }

    def test_category_case_counts_meet_plan_minimums(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        _make_profile(fake_supabase, user_id=ADMIN["sub"], role="admin")
        minimums = {
            "campaign_parsing": 10,
            "planning": 10,
            "candidate_validation": 20,
            "deduplication": 15,
            "scoring": 20,
            "outreach_grounding": 20,
        }

        response = client.post("/api/evals/run", headers=auth_header(**ADMIN))

        by_category = {c["category"]: c for c in response.json()["categories"]}
        for category, minimum in minimums.items():
            assert by_category[category]["total"] >= minimum


# --- Failure/recovery (10 cases) --------------------------------------------
#
# These need the full, database-backed research graph — not exposed through
# POST /api/evals/run (specs/phase-5-hardening.md, Non-goals) — so they run
# here, against the shared fake_supabase fixture, the same way every other
# integration test in this codebase does.

USER_ID = "55555555-5555-5555-5555-555555555599"


def _approved_campaign(*, brief: str, max_cost_usd: float = 5.00) -> dict[str, Any]:
    campaign = database.create_campaign(
        user_id=USER_ID, brief=brief, offer=None, target_lead_count=10
    )
    database.update_campaign(
        user_id=USER_ID, campaign_id=campaign["id"], patch={"limit_max_cost_usd": max_cost_usd}
    )
    campaign = database.get_campaign(user_id=USER_ID, campaign_id=campaign["id"])
    assert campaign is not None
    return campaign


def _run_state(campaign: dict[str, Any], search_plan: list[dict[str, Any]]) -> agent.ResearchState:
    run = database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
    return agent.build_initial_state(
        run_id=run["id"],
        campaign_id=campaign["id"],
        icp={
            "industries": [],
            "locations": [],
            "signals": [],
            "exclusions": [],
            "target_roles": [],
        },
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


class TestFailureRecoveryCases:
    async def test_case_1_extraction_failure_is_a_visible_rejected_lead(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(
            brief="Find design agencies and animation studios in Dubai, UAE."
        )
        plan = [{"query": "design agenc animation dubai", "rationale": "r"}]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        reasons = {lead.get("decision_reason") for lead in leads}
        assert "extraction_failed" in reasons

    async def test_case_2_insufficient_evidence_is_a_visible_rejected_lead(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(brief="Find design agencies in Dubai, UAE.")
        plan = [{"query": "design agenc dubai", "rationale": "r"}]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        reasons = {lead.get("decision_reason") for lead in leads}
        assert "insufficient_evidence" in reasons

    async def test_case_3_weak_query_is_revised_and_recovers(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(brief="Find animation studios in Dubai, UAE.")
        plan = [{"query": "animation studios in Nowhere", "rationale": "r"}]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        run = database.get_campaign_run(run_id=state["run_id"])
        assert run is not None
        assert run["queries_used"] == 1
        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        assert len(leads) >= 1

    async def test_case_4_target_reached_stops_the_run(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(
            brief="Find design agencies and animation studios in Dubai, UAE."
        )
        database.update_campaign(
            user_id=USER_ID, campaign_id=campaign["id"], patch={"target_lead_count": 1}
        )
        campaign = database.get_campaign(user_id=USER_ID, campaign_id=campaign["id"])
        assert campaign is not None
        plan = [{"query": "design agenc animation dubai", "rationale": "r"}]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        run = database.get_campaign_run(run_id=state["run_id"])
        assert run is not None
        assert run["stop_reason"] == "target_reached"

    async def test_case_5_queries_exhausted_stops_the_run(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(brief="Find consulting firms in London, UK.")
        plan = [{"query": "consulting london", "rationale": "r"}]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        run = database.get_campaign_run(run_id=state["run_id"])
        assert run is not None
        assert run["stop_reason"] == "queries_exhausted"

    async def test_case_6_budget_exhausted_stops_the_run(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(
            brief="Find design agencies and animation studios in Dubai, UAE.",
            max_cost_usd=0.01,
        )
        plan = [
            {"query": "design agenc dubai", "rationale": "r1"},
            {"query": "animation dubai", "rationale": "r2"},
        ]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        run = database.get_campaign_run(run_id=state["run_id"])
        assert run is not None
        assert run["stop_reason"] == "budget_exhausted"

    async def test_case_7_pause_requested_stops_the_run_cleanly(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(brief="Find consulting firms in London, UK.")
        plan = [{"query": "consulting london", "rationale": "r"}]
        state = _run_state(campaign, plan)
        database.update_campaign_run(run_id=state["run_id"], patch={"pause_requested": True})

        await agent.run_research(state)

        run = database.get_campaign_run(run_id=state["run_id"])
        assert run is not None
        assert run["status"] == "paused"
        assert run["stop_reason"] == "paused_by_user"

    async def test_case_8_duplicate_candidate_merges_not_duplicates(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(
            brief="Find design agencies and animation studios in Dubai, UAE."
        )
        plan = [
            {"query": "design agenc animation dubai", "rationale": "r1"},
            {"query": "design agenc animation dubai", "rationale": "r2"},
        ]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        domains = [
            database.get_companies_by_ids([lead["company_id"]])[lead["company_id"]]["domain"]
            for lead in leads
        ]
        assert len(domains) == len(set(domains))

    async def test_case_9_needs_review_disposition_is_reachable(
        self, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _approved_campaign(brief="Find design agencies in Dubai, UAE.")
        plan = [{"query": "design agenc dubai", "rationale": "r"}]
        state = _run_state(campaign, plan)

        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        statuses = {lead["status"] for lead in leads}
        assert "needs_review" in statuses

    async def test_case_10_ungroundable_draft_degrades_to_needs_review_not_a_crash(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        """Drives the real `regenerate-outreach` endpoint (not a
        reimplementation of its attempt loop) against the fixture's
        deliberately-ungroundable company (Thinclaim Robotics) — the draft
        is still saved, flagged `needs_review`, never a crash or a silent
        drop (specs/phase-4-outreach.md FR-5/FR-8).
        """
        campaign = _approved_campaign(brief="Find software companies in Berlin, Germany.")
        plan = [{"query": "software berlin", "rationale": "r"}]
        state = _run_state(campaign, plan)
        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        qualified = next(lead for lead in leads if lead["status"] == "qualified")
        headers = auth_header(sub=USER_ID, email="failure-recovery@example.com")

        response = client.post(
            f"/api/leads/{qualified['id']}/regenerate-outreach", json={}, headers=headers
        )

        assert response.status_code == 201
        body = response.json()
        assert body["draft"]["quality_status"] == "needs_review"
        assert body["draft"]["evidence_refs"] == []
