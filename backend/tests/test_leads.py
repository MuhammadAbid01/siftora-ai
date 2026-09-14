from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "66666666-6666-6666-6666-666666666666", "email": "lead-owner@example.com"}
USER_B = {"sub": "77777777-7777-7777-7777-777777777777", "email": "not-the-owner@example.com"}


def _run_a_campaign(client: TestClient, *, user: dict[str, str], brief: str) -> dict[str, Any]:
    headers = auth_header(**user)
    created = client.post("/api/campaigns", json={"brief": brief}, headers=headers).json()
    client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/run", headers=headers)
    return client.get(f"/api/campaigns/{created['id']}", headers=headers).json()


class TestLeadsList:
    def test_lists_leads_for_owned_campaign(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )

        response = client.get(
            f"/api/campaigns/{campaign['id']}/leads", headers=auth_header(**USER_A)
        )

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        assert {"status", "score", "company"}.issubset(items[0].keys())

    def test_cross_user_access_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _run_a_campaign(client, user=USER_A, brief="Find design agencies in Dubai, UAE.")

        response = client.get(
            f"/api/campaigns/{campaign['id']}/leads", headers=auth_header(**USER_B)
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "campaign_not_found"


class TestLeadDetail:
    def test_detail_includes_evidence_and_breakdown(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )
        leads = client.get(
            f"/api/campaigns/{campaign['id']}/leads", headers=auth_header(**USER_A)
        ).json()["items"]
        qualified = next(lead for lead in leads if lead["status"] == "qualified")

        response = client.get(f"/api/leads/{qualified['id']}", headers=auth_header(**USER_A))

        assert response.status_code == 200
        body = response.json()
        assert len(body["score_breakdown"]) == 8
        assert any(e["type"] == "fact" for e in body["evidence"])

    def test_cross_user_access_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _run_a_campaign(client, user=USER_A, brief="Find design agencies in Dubai, UAE.")
        leads = client.get(
            f"/api/campaigns/{campaign['id']}/leads", headers=auth_header(**USER_A)
        ).json()["items"]

        response = client.get(f"/api/leads/{leads[0]['id']}", headers=auth_header(**USER_B))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "lead_not_found"


class TestRescore:
    def test_rescore_changes_score_with_new_weights_and_no_provider_call(
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
        original_score = qualified["score"]

        # Push all weight onto a criterion Northbeam scores lower on.
        client.patch(
            f"/api/campaigns/{campaign['id']}",
            json={
                "score_weights": {
                    "industry_fit": 5,
                    "geography_fit": 5,
                    "company_size_fit": 5,
                    "pain_point_evidence": 5,
                    "buying_signal": 5,
                    "contact_relevance": 65,
                    "recency": 5,
                    "evidence_completeness": 5,
                }
            },
            headers=headers,
        )

        response = client.post(f"/api/leads/{qualified['id']}/rescore", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["score"] != original_score
        assert sum(b["points"] for b in body["score_breakdown"]) == pytest.approx(
            body["score"], abs=0.5
        )

    def test_rescore_on_never_scored_lead_is_409(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        campaign = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )
        leads = client.get(f"/api/campaigns/{campaign['id']}/leads", headers=headers).json()[
            "items"
        ]
        extraction_failed = next(
            lead for lead in leads if lead.get("decision_reason") == "extraction_failed"
        )

        response = client.post(f"/api/leads/{extraction_failed['id']}/rescore", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "lead_not_scored"

    def test_rescore_of_other_users_lead_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _run_a_campaign(client, user=USER_A, brief="Find design agencies in Dubai, UAE.")
        leads = client.get(
            f"/api/campaigns/{campaign['id']}/leads", headers=auth_header(**USER_A)
        ).json()["items"]

        response = client.post(
            f"/api/leads/{leads[0]['id']}/rescore", headers=auth_header(**USER_B)
        )

        assert response.status_code == 404
