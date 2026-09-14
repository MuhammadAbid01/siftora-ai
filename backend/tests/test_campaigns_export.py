import csv
import io

from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient
from tests.helpers import auth_header

USER = {"sub": "cccccccc-3333-3333-3333-333333333333", "email": "exporter@example.com"}


def _run_and_qualify(client: TestClient) -> tuple[dict, dict]:
    headers = auth_header(**USER)
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
    return created, qualified


def _parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


class TestExport:
    def test_export_only_includes_approved_latest_version(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        campaign, qualified = _run_and_qualify(client)

        # Unapproved (pending) draft for a second lead should not appear.
        client.post(f"/api/leads/{qualified['id']}/regenerate-outreach", json={}, headers=headers)

        empty_export = client.post(f"/api/campaigns/{campaign['id']}/export", headers=headers)
        assert empty_export.status_code == 200
        assert _parse_csv(empty_export.text) == []

        # Approve version 1, then regenerate to version 2 (still pending) —
        # only the latest version counts, and it's not approved, so export
        # stays empty even though an older version was approved.
        approvals = client.get(f"/api/leads/{qualified['id']}", headers=headers).json()["approvals"]
        v1_approval = next(a for a in approvals if a["draft"]["version"] == 1)
        client.post(f"/api/approvals/{v1_approval['id']}/approve", headers=headers)
        client.post(f"/api/leads/{qualified['id']}/regenerate-outreach", json={}, headers=headers)

        stale_export = client.post(f"/api/campaigns/{campaign['id']}/export", headers=headers)
        assert _parse_csv(stale_export.text) == []

        # Approve the latest (v2) version — now it appears.
        approvals_v2 = client.get(f"/api/leads/{qualified['id']}", headers=headers).json()[
            "approvals"
        ]
        v2_approval = next(a for a in approvals_v2 if a["draft"]["version"] == 2)
        client.post(f"/api/approvals/{v2_approval['id']}/approve", headers=headers)

        final_export = client.post(f"/api/campaigns/{campaign['id']}/export", headers=headers)
        rows = _parse_csv(final_export.text)
        assert len(rows) == 1
        assert rows[0]["lead_id"] == qualified["id"]
        assert rows[0]["channel"] == "email"
        assert rows[0]["reviewer_email"] == USER["email"]

    def test_export_excludes_suppressed_domain(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        headers = auth_header(**USER)
        campaign, qualified = _run_and_qualify(client)
        approval = client.post(
            f"/api/leads/{qualified['id']}/regenerate-outreach", json={}, headers=headers
        ).json()
        client.post(f"/api/approvals/{approval['id']}/approve", headers=headers)

        # Confirm it would otherwise be exported.
        before = _parse_csv(
            client.post(f"/api/campaigns/{campaign['id']}/export", headers=headers).text
        )
        assert len(before) == 1

        client.post(
            "/api/suppression", json={"domain": qualified["company"]["domain"]}, headers=headers
        )

        after = _parse_csv(
            client.post(f"/api/campaigns/{campaign['id']}/export", headers=headers).text
        )
        assert after == []

    def test_export_is_owner_scoped(
        self, client: TestClient, fake_supabase: FakeSupabaseClient
    ) -> None:
        campaign, _qualified = _run_and_qualify(client)

        response = client.post(
            f"/api/campaigns/{campaign['id']}/export",
            headers=auth_header(
                sub="dddddddd-4444-4444-4444-444444444444", email="other@example.com"
            ),
        )

        assert response.status_code == 404
