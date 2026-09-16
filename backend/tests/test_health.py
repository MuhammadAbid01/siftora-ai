import pytest
from fastapi.testclient import TestClient

from tests.fakes.supabase_fake import FakeSupabaseClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_health_requires_no_auth(client: TestClient) -> None:
    response = client.get("/api/health", headers={})

    assert response.status_code == 200


def test_readiness_returns_ok_when_database_is_reachable(
    client: TestClient, fake_supabase: FakeSupabaseClient
) -> None:
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_readiness_returns_503_when_database_is_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**_kwargs: object) -> None:
        raise RuntimeError("connection refused")

    monkeypatch.setattr("app.routers.health.get_profile", _boom)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}


def test_readiness_requires_no_auth(client: TestClient, fake_supabase: FakeSupabaseClient) -> None:
    response = client.get("/api/health/ready", headers={})

    assert response.status_code == 200
