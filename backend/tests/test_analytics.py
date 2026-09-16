from typing import Any

from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "f0000000-0000-0000-0000-00000000000a", "email": "analytics-a@example.com"}
USER_B = {"sub": "f0000000-0000-0000-0000-00000000000b", "email": "analytics-b@example.com"}


def _run_a_campaign(client: TestClient, *, user: dict[str, str], brief: str) -> dict[str, Any]:
    headers = auth_header(**user)
    created = client.post("/api/campaigns", json={"brief": brief}, headers=headers).json()
    client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/run", headers=headers)
    return client.get(f"/api/campaigns/{created['id']}", headers=headers).json()


class TestCampaignAnalytics:
    def test_reports_funnel_cost_latency_and_failures(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )

        response = client.get(f"/api/campaigns/{campaign['id']}/analytics", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["campaign_id"] == campaign["id"]
        assert body["runs_count"] == 1
        assert body["qualified_count"] >= 1
        assert body["total_cost_usd"] > 0
        assert body["total_queries_used"] > 0
        # Brokenlink Creative's extraction failure surfaces as a tool-call
        # failure (AC-4: "runs report latency, usage, cost, and failures").
        assert body["tool_call_failures"] >= 1
        assert body["avg_tool_latency_ms"] is not None

    def test_reflects_generated_and_approved_drafts(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )
        leads = client.get(f"/api/campaigns/{campaign['id']}/leads", headers=headers).json()[
            "items"
        ]
        qualified = next(lead for lead in leads if lead["status"] == "qualified")
        approval = client.post(
            f"/api/leads/{qualified['id']}/regenerate-outreach", json={}, headers=headers
        ).json()
        client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        response = client.get(f"/api/campaigns/{campaign['id']}/analytics", headers=headers)

        body = response.json()
        assert body["drafts_generated"] == 1
        assert body["drafts_approved"] == 1
        assert body["drafts_rejected"] == 0

    def test_accumulates_across_multiple_runs(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find consulting firms in London, UK."
        )
        first = client.get(f"/api/campaigns/{campaign['id']}/analytics", headers=headers).json()

        # A campaign whose run is "completed" can be edited (reverts to
        # draft, per Phase 2/3 rules) and run again.
        client.patch(
            f"/api/campaigns/{campaign['id']}", json={"offer": "a new offer"}, headers=headers
        )
        client.post(f"/api/campaigns/{campaign['id']}/plan", headers=headers)
        client.post(f"/api/campaigns/{campaign['id']}/confirm-plan", headers=headers)
        client.post(f"/api/campaigns/{campaign['id']}/run", headers=headers)

        second = client.get(f"/api/campaigns/{campaign['id']}/analytics", headers=headers).json()

        assert second["runs_count"] == 2
        assert second["total_queries_used"] >= first["total_queries_used"]

    def test_404_when_never_run(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        created = client.post(
            "/api/campaigns",
            json={"brief": "Find design agencies in Dubai, UAE."},
            headers=headers,
        ).json()

        response = client.get(f"/api/campaigns/{created['id']}/analytics", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "no_run_yet"

    def test_cross_user_is_404(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find consulting firms in London, UK."
        )

        response = client.get(
            f"/api/campaigns/{campaign['id']}/analytics", headers=auth_header(**USER_B)
        )

        assert response.status_code == 404
