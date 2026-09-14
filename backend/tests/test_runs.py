from typing import Any

from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "88888888-8888-8888-8888-888888888888", "email": "run-owner@example.com"}
USER_B = {"sub": "99999999-9999-9999-9999-999999999999", "email": "not-the-owner@example.com"}


def _run_a_campaign(client: TestClient, *, user: dict[str, str], brief: str) -> dict[str, Any]:
    headers = auth_header(**user)
    created = client.post("/api/campaigns", json={"brief": brief}, headers=headers).json()
    client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/run", headers=headers)
    progress = client.get(f"/api/campaigns/{created['id']}/progress", headers=headers).json()
    return progress


class TestEvents:
    def test_lists_events_for_owned_run(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        run = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )

        response = client.get(f"/api/runs/{run['id']}/events", headers=auth_header(**USER_A))

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        assert any(e["node"] == "complete_run" for e in items)

    def test_cross_user_access_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        run = _run_a_campaign(client, user=USER_A, brief="Find design agencies in Dubai, UAE.")

        response = client.get(f"/api/runs/{run['id']}/events", headers=auth_header(**USER_B))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "run_not_found"


class TestToolCalls:
    def test_lists_tool_calls_for_owned_run(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        run = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )

        response = client.get(f"/api/runs/{run['id']}/tool-calls", headers=auth_header(**USER_A))

        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) > 0
        assert {"tool", "provider", "status"}.issubset(items[0].keys())

    def test_pagination_respects_limit(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        run = _run_a_campaign(
            client, user=USER_A, brief="Find design agencies and animation studios in Dubai, UAE."
        )

        response = client.get(
            f"/api/runs/{run['id']}/tool-calls?limit=1", headers=auth_header(**USER_A)
        )

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    def test_cross_user_access_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        run = _run_a_campaign(client, user=USER_A, brief="Find design agencies in Dubai, UAE.")

        response = client.get(f"/api/runs/{run['id']}/tool-calls", headers=auth_header(**USER_B))

        assert response.status_code == 404
