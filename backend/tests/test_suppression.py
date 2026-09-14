from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "aaaaaaaa-1111-1111-1111-111111111111", "email": "suppressor@example.com"}
USER_B = {"sub": "bbbbbbbb-2222-2222-2222-222222222222", "email": "someone-else@example.com"}


class TestCreateAndList:
    def test_creates_and_lists_an_entry(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)

        created = client.post(
            "/api/suppression",
            json={"domain": "Example.com", "reason": "asked to opt out"},
            headers=headers,
        )
        assert created.status_code == 201
        assert created.json()["domain"] == "example.com"  # normalized

        listed = client.get("/api/suppression", headers=headers)
        assert listed.status_code == 200
        assert any(e["domain"] == "example.com" for e in listed.json()["items"])

    def test_creating_the_same_domain_twice_is_idempotent(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)

        first = client.post("/api/suppression", json={"domain": "dupe.example"}, headers=headers)
        second = client.post("/api/suppression", json={"domain": "dupe.example"}, headers=headers)

        assert first.json()["id"] == second.json()["id"]
        items = client.get("/api/suppression", headers=headers).json()["items"]
        assert sum(1 for e in items if e["domain"] == "dupe.example") == 1

    def test_scoped_to_owner(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        client.post(
            "/api/suppression", json={"domain": "onlya.example"}, headers=auth_header(**USER_A)
        )

        listed = client.get("/api/suppression", headers=auth_header(**USER_B))

        assert listed.json()["items"] == []


class TestDelete:
    def test_deletes_an_owned_entry(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        created = client.post(
            "/api/suppression", json={"domain": "gone.example"}, headers=headers
        ).json()

        response = client.delete(f"/api/suppression/{created['id']}", headers=headers)

        assert response.status_code == 200
        assert response.json()["deleted"] is True
        assert client.get("/api/suppression", headers=headers).json()["items"] == []

    def test_cross_user_delete_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = client.post(
            "/api/suppression", json={"domain": "protected.example"}, headers=auth_header(**USER_A)
        ).json()

        response = client.delete(f"/api/suppression/{created['id']}", headers=auth_header(**USER_B))

        assert response.status_code == 404
