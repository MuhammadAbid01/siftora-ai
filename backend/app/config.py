from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, validated at startup.

    Missing or malformed values raise a pydantic ValidationError immediately,
    so the app fails fast instead of misbehaving at request time.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    supabase_url: AnyHttpUrl
    supabase_service_role_key: str
    supabase_jwt_secret: str
    cors_allowed_origins: str = "http://localhost:3000"

    # Defaults to the zero-cost fixture adapter (plan.md §21) so the product
    # is fully functional without any LLM credentials. Live Gemini is opt-in.
    llm_provider: Literal["fixture", "gemini"] = "fixture"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    plan_generation_max_attempts: int = 2

    # Same zero-cost-by-default pattern as llm_provider (plan.md §21).
    search_provider: Literal["fixture", "tavily"] = "fixture"
    tavily_api_key: str | None = None
    extraction_provider: Literal["fixture", "firecrawl"] = "fixture"
    firecrawl_api_key: str | None = None

    # Real sending is opt-in and disabled by default (plan.md §11/§21).
    email_mode: Literal["disabled", "sandbox", "live"] = "disabled"
    resend_api_key: str | None = None

    @field_validator("supabase_service_role_key", "supabase_jwt_secret")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _require_gemini_key_when_selected(self) -> "Settings":
        if self.llm_provider == "gemini" and not (self.gemini_api_key or "").strip():
            raise ValueError("gemini_api_key is required when llm_provider is 'gemini'")
        return self

    @model_validator(mode="after")
    def _require_search_key_when_selected(self) -> "Settings":
        if self.search_provider == "tavily" and not (self.tavily_api_key or "").strip():
            raise ValueError("tavily_api_key is required when search_provider is 'tavily'")
        return self

    @model_validator(mode="after")
    def _require_extraction_key_when_selected(self) -> "Settings":
        if self.extraction_provider == "firecrawl" and not (self.firecrawl_api_key or "").strip():
            raise ValueError(
                "firecrawl_api_key is required when extraction_provider is 'firecrawl'"
            )
        return self

    @model_validator(mode="after")
    def _require_resend_key_when_selected(self) -> "Settings":
        if self.email_mode == "live" and not (self.resend_api_key or "").strip():
            raise ValueError("resend_api_key is required when email_mode is 'live'")
        return self

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
