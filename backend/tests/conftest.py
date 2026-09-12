import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from tests.fakes.supabase_fake import FakeSupabaseClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_supabase(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    """A fresh in-memory Supabase stand-in, wired into app.database for one test."""
    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(database, "get_supabase_admin_client", lambda: fake_client)
    return fake_client
