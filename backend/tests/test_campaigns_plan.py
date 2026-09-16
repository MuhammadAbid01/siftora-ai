from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.providers import LLMOutputError, LLMUnavailableError, get_language_model_provider
from app.schemas import ICP, PlanExtraction, SearchPlanQuery
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
        body = response.json()["error"]
        assert body["code"] == "plan_generation_failed"
        assert attempts == 2  # settings.plan_generation_max_attempts default
        # The user gets actionable guidance, not a raw exception; the
        # technical cause is still reported, just not as the headline.
        assert "simulated malformed output" not in body["message"]
        assert "add" in body["message"].lower()
        assert "simulated malformed output" in body["details"]["reason"]

    def test_provider_outage_is_a_503_not_a_bad_brief(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        """A rate limit or upstream timeout must not be reported to the user
        as "your brief couldn't be parsed" — the brief is fine, the model is
        simply unreachable, and retrying is the right advice.
        """
        created = _create_campaign(client, "Find design agencies in Dubai.")

        class UnavailableProvider:
            async def generate_campaign_plan(self, **_kwargs: Any) -> None:
                raise LLMUnavailableError(
                    "OpenRouter reported an upstream error (code 504): A Timeout Occurred"
                )

        app.dependency_overrides[get_language_model_provider] = lambda: UnavailableProvider()
        try:
            response = client.post(
                f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER)
            )
        finally:
            app.dependency_overrides.pop(get_language_model_provider, None)

        assert response.status_code == 503
        body = response.json()["error"]
        assert body["code"] == "plan_provider_unavailable"
        assert "try again" in body["message"].lower()
        assert "A Timeout Occurred" in body["details"]["reason"]

    def test_a_complete_icp_without_a_search_plan_still_yields_an_approvable_plan(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        """A model can return a usable ICP but forget the search plan. Left
        alone that strands the campaign: confirm-plan requires both, so the
        user could never move forward. The plan is derived from the ICP the
        model did return, inventing no new targeting.
        """
        created = _create_campaign(client, "Find design agencies in Dubai.")

        class NoSearchPlanProvider:
            async def generate_campaign_plan(self, **_kwargs: Any) -> PlanExtraction:
                return PlanExtraction(
                    icp=ICP(industries=["Design agencies"], locations=["Dubai, UAE"]),
                    search_plan=[],
                )

        app.dependency_overrides[get_language_model_provider] = lambda: NoSearchPlanProvider()
        try:
            response = client.post(
                f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER)
            )
        finally:
            app.dependency_overrides.pop(get_language_model_provider, None)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "awaiting_plan_approval"
        assert body["search_plan"]
        assert "Design agencies" in body["search_plan"][0]["query"]
        assert "Dubai, UAE" in body["search_plan"][0]["query"]

        confirm = client.post(
            f"/api/campaigns/{created['id']}/confirm-plan", headers=auth_header(**USER)
        )
        assert confirm.status_code == 200

    def test_every_extracted_icp_field_reaches_the_response(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        """The generated plan must land in every corresponding form field,
        not just industries/locations.
        """
        created = _create_campaign(client, "Find design agencies in Dubai.")

        class RichProvider:
            async def generate_campaign_plan(self, **_kwargs: Any) -> PlanExtraction:
                return PlanExtraction(
                    icp=ICP(
                        industries=["Design agencies"],
                        locations=["Dubai, UAE"],
                        company_size_min=5,
                        company_size_max=50,
                        signals=["Active website"],
                        exclusions=["Recruitment agencies"],
                        target_roles=["Founder"],
                    ),
                    search_plan=[SearchPlanQuery(query="q", rationale="r")],
                )

        app.dependency_overrides[get_language_model_provider] = lambda: RichProvider()
        try:
            response = client.post(
                f"/api/campaigns/{created['id']}/plan", headers=auth_header(**USER)
            )
        finally:
            app.dependency_overrides.pop(get_language_model_provider, None)

        icp = response.json()["icp"]
        assert icp["industries"] == ["Design agencies"]
        assert icp["locations"] == ["Dubai, UAE"]
        assert icp["company_size_min"] == 5
        assert icp["company_size_max"] == 50
        assert icp["signals"] == ["Active website"]
        assert icp["exclusions"] == ["Recruitment agencies"]
        assert icp["target_roles"] == ["Founder"]


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

    def test_fails_when_icp_is_complete_but_no_search_plan_was_ever_generated(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        # Reproduces a real bug: a user can hand-fill ICP fields (after an
        # icp_incomplete /plan response) via PATCH without ever calling
        # /plan again, leaving search_plan null. confirm-plan must catch
        # this — approving it would let /run start with nothing to search
        # for.
        headers = auth_header(**USER)
        created = _create_campaign(client, "Find some good companies for our product.")
        client.post(
            f"/api/campaigns/{created['id']}/plan", headers=headers
        )  # icp_incomplete, search_plan stays null
        client.patch(
            f"/api/campaigns/{created['id']}",
            json={"icp": {"industries": ["Design agencies"], "locations": ["Dubai, UAE"]}},
            headers=headers,
        )

        response = client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "plan_incomplete"


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
