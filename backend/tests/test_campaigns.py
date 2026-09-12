from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "11111111-1111-1111-1111-111111111111", "email": "user-a@example.com"}
USER_B = {"sub": "22222222-2222-2222-2222-222222222222", "email": "user-b@example.com"}


def _create_campaign(
    client: TestClient,
    *,
    user: dict[str, str],
    brief: str = "Find design agencies to pitch our new AI tool.",
) -> dict:
    response = client.post(
        "/api/campaigns",
        json={"brief": brief},
        headers=auth_header(sub=user["sub"], email=user["email"]),
    )
    assert response.status_code == 201
    return response.json()


class TestCampaignCrud:
    def test_create_campaign_defaults(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign = _create_campaign(client, user=USER_A)

        assert campaign["status"] == "draft"
        assert campaign["target_lead_count"] == 20
        assert campaign["icp"] is None
        assert campaign["score_weights"]["industry_fit"] == 20
        assert campaign["score_thresholds"] == {"qualified_min": 75, "needs_review_min": 55}

    def test_create_campaign_rejects_short_brief(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        response = client.post(
            "/api/campaigns", json={"brief": "too short"}, headers=auth_header(**USER_A)
        )
        assert response.status_code == 422

    def test_list_campaigns_paginates_with_cursor(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        for _ in range(3):
            _create_campaign(client, user=USER_A)

        first_page = client.get("/api/campaigns?limit=2", headers=auth_header(**USER_A)).json()
        assert len(first_page["items"]) == 2
        assert first_page["next_cursor"] is not None

        second_page = client.get(
            f"/api/campaigns?limit=2&cursor={first_page['next_cursor']}",
            headers=auth_header(**USER_A),
        ).json()
        assert len(second_page["items"]) == 1
        assert second_page["next_cursor"] is None

        seen_ids = {item["id"] for item in first_page["items"]} | {
            item["id"] for item in second_page["items"]
        }
        assert len(seen_ids) == 3

    def test_list_campaigns_only_returns_own(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        _create_campaign(client, user=USER_A)
        _create_campaign(client, user=USER_B)

        response = client.get("/api/campaigns", headers=auth_header(**USER_A))

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1

    def test_get_own_campaign(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        created = _create_campaign(client, user=USER_A)

        response = client.get(f"/api/campaigns/{created['id']}", headers=auth_header(**USER_A))

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_other_users_campaign_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, user=USER_A)

        response = client.get(f"/api/campaigns/{created['id']}", headers=auth_header(**USER_B))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "campaign_not_found"

    def test_patch_other_users_campaign_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, user=USER_A)

        response = client.patch(
            f"/api/campaigns/{created['id']}",
            json={"offer": "hijacked"},
            headers=auth_header(**USER_B),
        )

        assert response.status_code == 404

    def test_delete_other_users_campaign_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, user=USER_A)

        response = client.delete(f"/api/campaigns/{created['id']}", headers=auth_header(**USER_B))

        assert response.status_code == 404

    def test_patch_updates_fields(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, user=USER_A)

        response = client.patch(
            f"/api/campaigns/{created['id']}",
            json={"offer": "New offer", "target_lead_count": 30},
            headers=auth_header(**USER_A),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["offer"] == "New offer"
        assert body["target_lead_count"] == 30

    def test_patch_icp_creates_it(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, user=USER_A)

        response = client.patch(
            f"/api/campaigns/{created['id']}",
            json={"icp": {"industries": ["Design agencies"], "locations": ["Dubai, UAE"]}},
            headers=auth_header(**USER_A),
        )

        assert response.status_code == 200
        assert response.json()["icp"]["industries"] == ["Design agencies"]

    def test_editing_an_approved_campaign_reverts_status_to_draft(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.patch(
            f"/api/campaigns/{created['id']}",
            json={"icp": {"industries": ["Design agencies"], "locations": ["Dubai, UAE"]}},
            headers=headers,
        )
        confirmed = client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
        assert confirmed.json()["status"] == "plan_approved"

        edited = client.patch(
            f"/api/campaigns/{created['id']}", json={"offer": "changed"}, headers=headers
        )

        assert edited.status_code == 200
        assert edited.json()["status"] == "draft"
        assert edited.json()["plan_approved_at"] is None

    def test_delete_campaign(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        created = _create_campaign(client, user=USER_A)
        headers = auth_header(**USER_A)

        response = client.delete(f"/api/campaigns/{created['id']}", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"deleted": True}

        follow_up = client.get(f"/api/campaigns/{created['id']}", headers=headers)
        assert follow_up.status_code == 404

    def test_requires_authentication(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        response = client.get("/api/campaigns")
        assert response.status_code == 401
