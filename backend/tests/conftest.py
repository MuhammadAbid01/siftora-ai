import pytest
from fastapi.testclient import TestClient

from app import database, rate_limit
from app.config import get_settings
from app.main import app
from tests.fakes.supabase_fake import FakeSupabaseClient


@pytest.fixture(autouse=True)
def _force_fixture_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never depend on backend/.env's real provider selection.

    A developer's .env needs LLM_PROVIDER=openrouter/SEARCH_PROVIDER=tavily/
    EXTRACTION_PROVIDER=firecrawl to actually *run* the app live — but
    app/agent.py's nodes call get_language_model_provider()/
    get_search_provider()/get_extraction_provider() as plain function
    calls (not FastAPI Depends), so without this override the test suite
    would silently make real, slow, costly network calls and produce
    non-deterministic results. get_settings is a shared lru_cache, so
    clearing it here affects every module that imported the function
    (they all reference the same cached callable).
    """
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    monkeypatch.setenv("SEARCH_PROVIDER", "fixture")
    monkeypatch.setenv("EXTRACTION_PROVIDER", "fixture")
    monkeypatch.setenv("EMAIL_MODE", "disabled")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    """One test's requests must never count against another's rate-limit
    window (app/rate_limit.py's state is module-level/global by design —
    see specs/phase-5-hardening.md FR-9).
    """
    rate_limit.reset()
    yield
    rate_limit.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_supabase(monkeypatch: pytest.MonkeyPatch) -> FakeSupabaseClient:
    """A fresh in-memory Supabase stand-in, wired into app.database for one test."""
    fake_client = FakeSupabaseClient()
    monkeypatch.setattr(database, "get_supabase_admin_client", lambda: fake_client)
    return fake_client
