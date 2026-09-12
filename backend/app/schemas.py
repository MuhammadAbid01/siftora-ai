from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    version: str


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: EmailStr
    role: Literal["user", "admin"]
    created_at: datetime
    updated_at: datetime


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, object] | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


# --- Campaigns (Phase 2) -----------------------------------------------

CampaignStatus = Literal["draft", "awaiting_plan_approval", "plan_approved", "queued"]


class ScoreWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry_fit: int = 20
    geography_fit: int = 10
    company_size_fit: int = 10
    pain_point_evidence: int = 20
    buying_signal: int = 15
    contact_relevance: int = 10
    recency: int = 10
    evidence_completeness: int = 5

    @model_validator(mode="after")
    def _weights_sum_to_100(self) -> "ScoreWeights":
        total = (
            self.industry_fit
            + self.geography_fit
            + self.company_size_fit
            + self.pain_point_evidence
            + self.buying_signal
            + self.contact_relevance
            + self.recency
            + self.evidence_completeness
        )
        if total != 100:
            raise ValueError(f"score weights must sum to 100, got {total}")
        return self


class ScoreThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qualified_min: int = 75
    needs_review_min: int = 55

    @model_validator(mode="after")
    def _thresholds_ordered(self) -> "ScoreThresholds":
        if not (0 <= self.needs_review_min < self.qualified_min <= 100):
            raise ValueError("thresholds must satisfy 0 <= needs_review_min < qualified_min <= 100")
        return self


class RunLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_queries: int = 20
    max_pages_per_company: int = 5
    max_retries: int = 2
    max_cost_usd: float = 5.00

    @model_validator(mode="after")
    def _limits_in_range(self) -> "RunLimits":
        if not (1 <= self.max_queries <= 100):
            raise ValueError("max_queries must be between 1 and 100")
        if not (1 <= self.max_pages_per_company <= 20):
            raise ValueError("max_pages_per_company must be between 1 and 20")
        if not (0 <= self.max_retries <= 5):
            raise ValueError("max_retries must be between 0 and 5")
        if not (0 < self.max_cost_usd <= 50):
            raise ValueError("max_cost_usd must be > 0 and <= 50")
        return self


class ICP(BaseModel):
    """Structured Ideal Customer Profile — both the LLM extraction shape and
    the API response shape (see specs/phase-2-campaigns.md, Technical design).
    """

    model_config = ConfigDict(extra="forbid")

    industries: list[str] = []
    locations: list[str] = []
    company_size_min: int | None = None
    company_size_max: int | None = None
    signals: list[str] = []
    exclusions: list[str] = []
    target_roles: list[str] = []

    @model_validator(mode="after")
    def _company_size_range_valid(self) -> "ICP":
        if (
            self.company_size_min is not None
            and self.company_size_max is not None
            and self.company_size_min > self.company_size_max
        ):
            raise ValueError("company_size_min must be <= company_size_max")
        return self


class ICPUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industries: list[str] | None = None
    locations: list[str] | None = None
    company_size_min: int | None = None
    company_size_max: int | None = None
    signals: list[str] | None = None
    exclusions: list[str] | None = None
    target_roles: list[str] | None = None

    @model_validator(mode="after")
    def _company_size_range_valid(self) -> "ICPUpdate":
        if (
            self.company_size_min is not None
            and self.company_size_max is not None
            and self.company_size_min > self.company_size_max
        ):
            raise ValueError("company_size_min must be <= company_size_max")
        return self


class SearchPlanQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    rationale: str


class PlanExtraction(BaseModel):
    """The structured output requested from a LanguageModelProvider."""

    model_config = ConfigDict(extra="forbid")

    icp: ICP
    search_plan: list[SearchPlanQuery] = []


class CampaignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str
    offer: str | None = None
    target_lead_count: int = 20

    @model_validator(mode="after")
    def _validate(self) -> "CampaignCreateRequest":
        if not (10 <= len(self.brief.strip()) <= 2000):
            raise ValueError("brief must be between 10 and 2000 characters")
        if not (1 <= self.target_lead_count <= 200):
            raise ValueError("target_lead_count must be between 1 and 200")
        return self


class CampaignUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str | None = None
    offer: str | None = None
    target_lead_count: int | None = None
    icp: ICPUpdate | None = None
    score_weights: ScoreWeights | None = None
    score_thresholds: ScoreThresholds | None = None
    limits: RunLimits | None = None

    @model_validator(mode="after")
    def _validate(self) -> "CampaignUpdateRequest":
        if self.brief is not None and not (10 <= len(self.brief.strip()) <= 2000):
            raise ValueError("brief must be between 10 and 2000 characters")
        if self.target_lead_count is not None and not (1 <= self.target_lead_count <= 200):
            raise ValueError("target_lead_count must be between 1 and 200")
        return self


class CampaignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: CampaignStatus
    brief: str
    offer: str | None
    target_lead_count: int
    icp: ICP | None
    search_plan: list[SearchPlanQuery] | None
    score_weights: ScoreWeights
    score_thresholds: ScoreThresholds
    limits: RunLimits
    plan_approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CampaignResponse]
    next_cursor: str | None = None


class DeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted: Literal[True]
