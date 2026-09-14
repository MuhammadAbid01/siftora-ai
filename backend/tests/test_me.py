import pytest
from fastapi.testclient import TestClient

from app.routers import me as me_router
from tests.helpers import make_token as _make_token


class _FakeQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def select(self, *_args: str) -> "_FakeQuery":
        return self

    def eq(self, _column: str, _value: str) -> "_FakeQuery":
        return self

    def limit(self, _n: int) -> "_FakeQuery":
        return self

    def execute(self) -> "_FakeResult":
        return _FakeResult(self._rows)


class _FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self.data = rows


class _FakeSupabaseClient:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def table(self, _name: str) -> _FakeQuery:
        return _FakeQuery(self._rows)


def test_me_without_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_with_invalid_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_with_valid_token_returns_profile(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = "11111111-1111-1111-1111-111111111111"
    fake_client = _FakeSupabaseClient(
        [
            {
                "id": user_id,
                "email": "demo.user@example.com",
                "role": "user",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ]
    )
    monkeypatch.setattr(me_router, "get_supabase_admin_client", lambda: fake_client)

    token = _make_token(sub=user_id, email="demo.user@example.com")
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_id
    assert body["email"] == "demo.user@example.com"
    assert body["role"] == "user"


def test_me_with_no_matching_profile_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_client = _FakeSupabaseClient([])
    monkeypatch.setattr(me_router, "get_supabase_admin_client", lambda: fake_client)

    token = _make_token(sub="22222222-2222-2222-2222-222222222222", email="ghost@example.com")
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "profile_not_found"
