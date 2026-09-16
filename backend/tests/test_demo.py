from typing import Any

from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "d0000000-0000-0000-0000-00000000000a", "email": "demo-a@example.com"}
USER_B = {"sub": "d0000000-0000-0000-0000-00000000000b", "email": "demo-b@example.com"}


def _create_campaign(client: TestClient, *, user: dict[str, str], brief: str) -> dict[str, Any]:
    return client.post("/api/campaigns", json={"brief": brief}, headers=auth_header(**user)).json()


class TestDemoReset:
    def test_deletes_only_the_callers_own_campaigns(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        _create_campaign(client, user=USER_A, brief="Find design agencies in Dubai, UAE.")
        _create_campaign(client, user=USER_A, brief="Find consulting firms in London, UK.")
        _create_campaign(client, user=USER_B, brief="Find law firms in New York.")

        response = client.post("/api/demo/reset", headers=auth_header(**USER_A))

        assert response.status_code == 200
        assert response.json() == {"deleted_campaigns": 2}

        a_campaigns = client.get("/api/campaigns", headers=auth_header(**USER_A)).json()["items"]
        b_campaigns = client.get("/api/campaigns", headers=auth_header(**USER_B)).json()["items"]
        assert a_campaigns == []
        assert len(b_campaigns) == 1

    def test_cascades_to_leads_and_evidence(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        created = client.post(
            "/api/campaigns",
            json={"brief": "Find design agencies and animation studios in Dubai, UAE."},
            headers=headers,
        ).json()
        client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
        client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
        client.post(f"/api/campaigns/{created['id']}/run", headers=headers)
        leads_before = client.get(f"/api/campaigns/{created['id']}/leads", headers=headers).json()[
            "items"
        ]
        assert len(leads_before) > 0

        client.post("/api/demo/reset", headers=headers)

        response = client.get(f"/api/campaigns/{created['id']}/leads", headers=headers)
        assert response.status_code == 404  # the campaign itself is gone

    def test_returns_zero_when_no_campaigns_exist(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        response = client.post(
            "/api/demo/reset",
            headers=auth_header(
                sub="d0000000-0000-0000-0000-0000000000ff", email="new@example.com"
            ),
        )

        assert response.status_code == 200
        assert response.json() == {"deleted_campaigns": 0}
