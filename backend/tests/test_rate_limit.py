import pytest
from fastapi.testclient import TestClient

from app import rate_limit
from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "aa000000-0000-0000-0000-00000000000a", "email": "rl-a@example.com"}
USER_B = {"sub": "aa000000-0000-0000-0000-00000000000b", "email": "rl-b@example.com"}


class TestCheckRateLimit:
    def test_allows_requests_within_the_limit(self) -> None:
        for _ in range(5):
            rate_limit.check_rate_limit(key="user-1", bucket="b", max_requests=5, window_seconds=60)

    def test_raises_once_the_limit_is_exceeded(self) -> None:
        for _ in range(3):
            rate_limit.check_rate_limit(key="user-1", bucket="b", max_requests=3, window_seconds=60)
        with pytest.raises(rate_limit.RateLimitExceeded):
            rate_limit.check_rate_limit(key="user-1", bucket="b", max_requests=3, window_seconds=60)

    def test_buckets_are_independent(self) -> None:
        for _ in range(3):
            rate_limit.check_rate_limit(
                key="user-1", bucket="bucket-a", max_requests=3, window_seconds=60
            )
        # A different bucket for the same key is unaffected.
        rate_limit.check_rate_limit(
            key="user-1", bucket="bucket-b", max_requests=3, window_seconds=60
        )

    def test_keys_are_independent(self) -> None:
        for _ in range(3):
            rate_limit.check_rate_limit(key="user-1", bucket="b", max_requests=3, window_seconds=60)
        # A different key (user) for the same bucket is unaffected.
        rate_limit.check_rate_limit(key="user-2", bucket="b", max_requests=3, window_seconds=60)


class TestPlanEndpointRateLimit:
    def test_11th_plan_call_within_a_minute_is_429(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        created = client.post(
            "/api/campaigns",
            json={"brief": "Find design agencies in Dubai, UAE."},
            headers=headers,
        ).json()

        for _ in range(10):
            response = client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
            assert response.status_code == 200

        response = client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)

        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert "retry_after_seconds" in response.json()["error"]["details"]

    def test_a_different_user_is_not_affected(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers_a = auth_header(**USER_A)
        headers_b = auth_header(**USER_B)
        campaign_a = client.post(
            "/api/campaigns",
            json={"brief": "Find design agencies in Dubai, UAE."},
            headers=headers_a,
        ).json()
        campaign_b = client.post(
            "/api/campaigns",
            json={"brief": "Find law firms in New York."},
            headers=headers_b,
        ).json()

        for _ in range(10):
            assert (
                client.post(
                    f"/api/campaigns/{campaign_a['id']}/plan", headers=headers_a
                ).status_code
                == 200
            )

        # User A is now rate-limited...
        assert (
            client.post(f"/api/campaigns/{campaign_a['id']}/plan", headers=headers_a).status_code
            == 429
        )
        # ...but User B's own budget is untouched.
        assert (
            client.post(f"/api/campaigns/{campaign_b['id']}/plan", headers=headers_b).status_code
            == 200
        )


class TestRunEndpointRateLimit:
    def test_6th_run_call_within_a_minute_is_429(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER_A)
        campaign_ids = []
        for _ in range(6):
            created = client.post(
                "/api/campaigns",
                json={"brief": "Find design agencies in Dubai, UAE."},
                headers=headers,
            ).json()
            client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
            client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
            campaign_ids.append(created["id"])

        for campaign_id in campaign_ids[:5]:
            response = client.post(f"/api/campaigns/{campaign_id}/run", headers=headers)
            assert response.status_code == 200

        response = client.post(f"/api/campaigns/{campaign_ids[5]}/run", headers=headers)

        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
