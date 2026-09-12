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
    gemini_model: str = "gemini-2.5-flash"
    plan_generation_max_attempts: int = 2

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

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
