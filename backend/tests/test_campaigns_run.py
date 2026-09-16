from typing import Any

from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER = {"sub": "55555555-5555-5555-5555-555555555555", "email": "runner@example.com"}


def _create_approved_campaign(client: TestClient, brief: str) -> dict[str, Any]:
    headers = auth_header(**USER)
    created = client.post("/api/campaigns", json={"brief": brief}, headers=headers).json()
    client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
    confirmed = client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
    assert confirmed.json()["status"] == "plan_approved"
    return confirmed.json()


class TestRunEndpoint:
    def test_run_requires_plan_approval(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        created = client.post(
            "/api/campaigns",
            json={"brief": "Find design agencies to pitch our tool."},
            headers=headers,
        ).json()

        response = client.post(f"/api/campaigns/{created['id']}/run", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "plan_not_approved"

    def test_run_completes_via_background_task_and_produces_leads(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        campaign = _create_approved_campaign(
            client, "Find design agencies and animation studios in Dubai, UAE."
        )

        run_response = client.post(f"/api/campaigns/{campaign['id']}/run", headers=headers)
        assert run_response.status_code == 200
        # Response body reflects state at return time, before the background
        # task (which TestClient still waits for) mutates anything further.
        assert run_response.json()["status"] == "queued"

        finished_campaign = client.get(f"/api/campaigns/{campaign['id']}", headers=headers).json()
        assert finished_campaign["status"] == "completed"

        progress = client.get(f"/api/campaigns/{campaign['id']}/progress", headers=headers).json()
        assert progress["status"] == "completed"
        assert progress["leads_created"] > 0

        leads = client.get(f"/api/campaigns/{campaign['id']}/leads", headers=headers).json()
        assert len(leads["items"]) == progress["leads_created"]

    def test_run_is_idempotent_when_already_active(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")

        # Simulate an in-flight run without letting it complete, by seeding
        # an active campaign_runs row directly (avoids timing races).
        database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "running"}
        )

        response = client.post(f"/api/campaigns/{campaign['id']}/run", headers=headers)

        assert response.status_code == 200
        all_runs = [
            row
            for row in fake_supabase._tables.get("campaign_runs", {}).values()
            if row["campaign_id"] == campaign["id"]
        ]
        assert len(all_runs) == 1  # idempotent — no second run row created


class TestPauseEndpoint:
    def test_pause_without_active_run_is_409(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")

        response = client.post(f"/api/campaigns/{campaign['id']}/pause", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "no_active_run"

    def test_pause_sets_active_run_flag(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        run = database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "running"}
        )

        response = client.post(f"/api/campaigns/{campaign['id']}/pause", headers=headers)

        assert response.status_code == 200
        updated_run = database.get_campaign_run(run_id=run["id"])
        assert updated_run is not None
        assert updated_run["pause_requested"] is True


class TestProgressEndpoint:
    def test_progress_before_any_run_is_404(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")

        response = client.get(f"/api/campaigns/{campaign['id']}/progress", headers=headers)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "no_run_yet"


class TestEditGuard:
    def test_patch_is_blocked_while_a_run_is_active(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "running"}
        )

        response = client.patch(
            f"/api/campaigns/{campaign['id']}", json={"offer": "new offer"}, headers=headers
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "campaign_running"

    def test_plan_regeneration_is_blocked_while_a_run_is_active(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "running"}
        )

        response = client.post(f"/api/campaigns/{campaign['id']}/plan", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "campaign_running"

    def test_confirm_plan_is_blocked_while_a_run_is_active(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "running"}
        )

        response = client.post(f"/api/campaigns/{campaign['id']}/confirm-plan", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "campaign_running"

    def test_delete_is_blocked_while_a_run_is_active(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "running"}
        )

        response = client.delete(f"/api/campaigns/{campaign['id']}", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "campaign_running"

    def test_patch_after_completion_reverts_to_draft(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        campaign = _create_approved_campaign(
            client, "Find design agencies and animation studios in Dubai, UAE."
        )
        client.post(f"/api/campaigns/{campaign['id']}/run", headers=headers)

        finished = client.get(f"/api/campaigns/{campaign['id']}", headers=headers).json()
        assert finished["status"] == "completed"

        edited = client.patch(
            f"/api/campaigns/{campaign['id']}", json={"offer": "changed"}, headers=headers
        )

        assert edited.status_code == 200
        assert edited.json()["status"] == "draft"

    def test_confirm_plan_after_pause_is_not_blocked(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        """A paused run has already stopped for good (no true resume — see
        specs/phase-3-research.md), so unlike `queued`/`running` it must not
        leave the campaign permanently stuck: confirm-plan (and edit/delete)
        need to work again afterward, same as for `completed`/`failed`.
        """
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "paused"}
        )

        response = client.post(f"/api/campaigns/{campaign['id']}/confirm-plan", headers=headers)

        assert response.status_code == 200
        assert response.json()["status"] == "plan_approved"

    def test_patch_after_pause_reverts_to_draft(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        from app import database

        headers = auth_header(**USER)
        campaign = _create_approved_campaign(client, "Find design agencies in Dubai, UAE.")
        database.update_campaign(
            user_id=USER["sub"], campaign_id=campaign["id"], patch={"status": "paused"}
        )

        edited = client.patch(
            f"/api/campaigns/{campaign['id']}", json={"offer": "changed"}, headers=headers
        )

        assert edited.status_code == 200
        assert edited.json()["status"] == "draft"
