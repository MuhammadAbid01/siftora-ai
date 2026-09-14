from typing import Any

from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER_A = {"sub": "88888888-8888-8888-8888-888888888888", "email": "approver@example.com"}
USER_B = {"sub": "99999999-9999-9999-9999-999999999999", "email": "not-the-approver@example.com"}


def _qualified_approval(client: TestClient, *, user: dict[str, str]) -> dict[str, Any]:
    headers = auth_header(**user)
    created = client.post(
        "/api/campaigns",
        json={"brief": "Find design agencies and animation studios in Dubai, UAE."},
        headers=headers,
    ).json()
    client.post(f"/api/campaigns/{created['id']}/plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/confirm-plan", headers=headers)
    client.post(f"/api/campaigns/{created['id']}/run", headers=headers)
    leads = client.get(f"/api/campaigns/{created['id']}/leads", headers=headers).json()["items"]
    qualified = next(lead for lead in leads if lead["status"] == "qualified")
    approval = client.post(
        f"/api/leads/{qualified['id']}/regenerate-outreach", json={}, headers=headers
    ).json()
    return approval


class TestListApprovals:
    def test_lists_pending_across_campaigns(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)

        response = client.get("/api/approvals", headers=auth_header(**USER_A))

        assert response.status_code == 200
        items = response.json()["items"]
        assert any(a["id"] == approval["id"] for a in items)

    def test_status_filter(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        pending = client.get("/api/approvals?status=pending", headers=headers).json()["items"]
        approved = client.get("/api/approvals?status=approved", headers=headers).json()["items"]

        assert all(a["id"] != approval["id"] for a in pending)
        assert any(a["id"] == approval["id"] for a in approved)

    def test_scoped_to_owner(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        _qualified_approval(client, user=USER_A)

        response = client.get("/api/approvals", headers=auth_header(**USER_B))

        assert response.json()["items"] == []


class TestApprove:
    def test_sets_reviewer_and_timestamp(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)

        response = client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["reviewer_id"] == USER_A["sub"]
        assert body["decided_at"] is not None

    def test_blocked_when_domain_suppressed(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.post(
            "/api/suppression",
            json={"domain": approval["company"]["domain"]},
            headers=headers,
        )

        response = client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "domain_suppressed"

    def test_blocked_when_lead_no_longer_qualified(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.patch(
            f"/api/leads/{approval['lead_id']}/status",
            json={"status": "rejected"},
            headers=headers,
        )

        response = client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "lead_not_qualified"

    def test_cross_user_is_404(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        approval = _qualified_approval(client, user=USER_A)

        response = client.post(
            f"/api/approvals/{approval['id']}/approve", headers=auth_header(**USER_B)
        )

        assert response.status_code == 404


class TestReject:
    def test_always_allowed(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)

        response = client.post(
            f"/api/approvals/{approval['id']}/reject",
            json={"reason": "not a fit"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "rejected"


class TestEditDraft:
    def test_edits_in_place_and_invalidates_approval(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        response = client.patch(
            f"/api/approvals/{approval['id']}/draft",
            json={"subject": "New subject line"},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["draft"]["subject"] == "New subject line"
        assert body["draft"]["version"] == 1
        assert body["status"] == "pending"
        assert body["edited"] is True
        assert body["reviewer_id"] is None
        assert body["decided_at"] is None

    def test_editing_a_pending_draft_stays_pending_but_marks_edited(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)

        response = client.patch(
            f"/api/approvals/{approval['id']}/draft",
            json={"body": "A manually corrected body."},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["draft"]["body"] == "A manually corrected body."
        assert body["status"] == "pending"
        assert body["edited"] is True

    def test_editing_a_rejected_draft_also_resets_to_pending(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.post(f"/api/approvals/{approval['id']}/reject", headers=headers)

        response = client.patch(
            f"/api/approvals/{approval['id']}/draft",
            json={"subject": "Reworked subject"},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "pending"
        assert body["reviewer_id"] is None
        assert body["decided_at"] is None

    def test_requires_at_least_one_field(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)

        response = client.patch(f"/api/approvals/{approval['id']}/draft", json={}, headers=headers)

        assert response.status_code == 422

    def test_cross_user_is_404(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        approval = _qualified_approval(client, user=USER_A)

        response = client.patch(
            f"/api/approvals/{approval['id']}/draft",
            json={"subject": "x"},
            headers=auth_header(**USER_B),
        )

        assert response.status_code == 404


class TestSend:
    def test_disabled_by_default(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)
        client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        response = client.post(
            f"/api/approvals/{approval['id']}/send",
            json={"to_email": "contact@example.com"},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "disabled"

    def test_requires_approved(self, client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
        approval = _qualified_approval(client, user=USER_A)
        headers = auth_header(**USER_A)

        response = client.post(
            f"/api/approvals/{approval['id']}/send",
            json={"to_email": "contact@example.com"},
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "approval_not_approved"
