from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.providers import LLMOutputError, get_language_model_provider
from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER = {"sub": "33333333-3333-3333-3333-333333333333", "email": "planner@example.com"}


def _create_campaign(client: TestClient, brief: str) -> dict[str, Any]:
    response = client.post("/api/campaigns", json={"brief": brief}, headers=auth_header(**USER))
    assert response.status_code == 201
    return response.json()


class TestPlanGeneration:
    def test_complete_extraction_advances_status(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find design agencies in Dubai with 5-50 employees.")

        response = client.post(f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "awaiting_plan_approval"
        assert body["icp"]["industries"]
        assert body["icp"]["locations"]
        assert body["search_plan"]

    def test_incomplete_extraction_persists_partial_and_returns_422(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find some good companies for our product.")

        response = client.post(f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER))

        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "icp_incomplete"
        assert set(body["error"]["details"]["missing_fields"]) == {"industries", "locations"}

        campaign = client.get(f"/api/campaigns/{created['id']}", headers=auth_header(**USER)).json()
        assert campaign["status"] == "draft"

    def test_retries_then_fails_clearly_on_persistently_invalid_output(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find design agencies in Dubai.")
        attempts = 0

        class AlwaysBrokenProvider:
            async def generate_campaign_plan(self, **_kwargs: Any) -> None:
                nonlocal attempts
                attempts += 1
                raise LLMOutputError("simulated malformed output")

        app.dependency_overrides[get_language_model_provider] = lambda: AlwaysBrokenProvider()
        try:
            response = client.post(
                f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER)
            )
        finally:
            app.dependency_overrides.pop(get_language_model_provider, None)

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "plan_generation_failed"
        assert attempts == 2  # settings.plan_generation_max_attempts default


class TestConfirmPlan:
    def test_fails_without_a_complete_icp(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find design agencies in Dubai.")

        response = client.post(
            f"/api/campaigns/{created['id']}/confirm-plan", headers=auth_header(**USER)
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "plan_incomplete"

    def test_succeeds_after_a_complete_plan(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find design agencies in Dubai with 5-50 employees.")
        client.post(f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER))

        response = client.post(
            f"/api/campaigns/{created['id']}/confirm-plan", headers=auth_header(**USER)
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "plan_approved"
        assert body["plan_approved_at"] is not None


class TestRunGating:
    def test_run_fails_before_approval(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find design agencies in Dubai with 5-50 employees.")

        response = client.post(f"/api/campaigns/{created['id']}/run", headers=auth_header(**USER))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "plan_not_approved"

    def test_run_succeeds_after_approval(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        created = _create_campaign(client, "Find design agencies in Dubai with 5-50 employees.")
        client.post(f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER))
        client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=auth_header(**USER))

        response = client.post(f"/api/campaigns/{created['id']}/run", headers=auth_header(**USER))

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
