from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    version: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "error"]
    database: Literal["ok", "unreachable"]


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

CampaignStatus = Literal[
    "draft",
    "awaiting_plan_approval",
    "plan_approved",
    "queued",
    "running",
    "completed",
    "failed",
    "paused",
]


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
    sender_name: str | None = None
    sender_email: EmailStr | None = None

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
    sender_name: str | None = None
    sender_email: EmailStr | None = None
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
    sender_name: str | None = None
    sender_email: str | None = None
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


# --- Research (Phase 3) -------------------------------------------------

CRITERIA_FIELDS: tuple[str, ...] = (
    "industry_fit",
    "geography_fit",
    "company_size_fit",
    "pain_point_evidence",
    "buying_signal",
    "contact_relevance",
    "recency",
    "evidence_completeness",
)

Criterion = Literal[
    "industry_fit",
    "geography_fit",
    "company_size_fit",
    "pain_point_evidence",
    "buying_signal",
    "contact_relevance",
    "recency",
    "evidence_completeness",
]

LeadStatus = Literal["qualified", "needs_review", "rejected"]

RunStatus = Literal["queued", "running", "completed", "failed", "paused"]


class CriterionSignals(BaseModel):
    """Per-criterion 0.0-1.0 signal strength, produced by analysis and
    consumed (never re-derived) by the deterministic scorer.
    """

    model_config = ConfigDict(extra="forbid")

    industry_fit: float
    geography_fit: float
    company_size_fit: float
    pain_point_evidence: float
    buying_signal: float
    contact_relevance: float
    recency: float
    evidence_completeness: float

    @model_validator(mode="after")
    def _signals_in_range(self) -> "CriterionSignals":
        for name in CRITERIA_FIELDS:
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        return self


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["fact", "inference", "unknown"]
    claim: str
    excerpt: str | None = None
    source_url: str | None = None
    confidence: float | None = None

    @model_validator(mode="after")
    def _sourcing_matches_type(self) -> "EvidenceItem":
        if self.type in ("fact", "inference"):
            if not self.excerpt or not self.source_url:
                raise ValueError(f"{self.type} evidence requires excerpt and source_url")
        elif self.excerpt is not None or self.source_url is not None:
            raise ValueError(
                "unknown evidence must not carry excerpt/source_url — nothing is invented"
            )
        return self


class CompanyAnalysis(BaseModel):
    """The structured output requested from LanguageModelProvider.analyze_company."""

    model_config = ConfigDict(extra="forbid")

    evidence: list[EvidenceItem] = []
    signals: CriterionSignals


class SearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The *page* title and host of a search hit — a source on which companies
    # may be mentioned, NOT a company identity. Named `title`, not
    # `company_name`, so that using a search hit as a company is a visible
    # mistake rather than a plausible-looking one; `app/discovery.py`
    # explains the bug that naming cost us.
    title: str
    domain: str
    url: str
    snippet: str


class DiscoveredCompany(BaseModel):
    """One real business named in the content of a source page."""

    model_config = ConfigDict(extra="forbid")

    name: str
    website: str | None = None


class PageEntityExtraction(BaseModel):
    """The structured output requested from
    `LanguageModelProvider.extract_companies_from_page`.

    `page_type` distinguishes a company's own site (the page *is* one
    business) from a listing/roundup that merely mentions several, which is
    what decides whether the page's own domain may become a lead.
    """

    model_config = ConfigDict(extra="forbid")

    page_type: Literal["company_site", "listing", "other"]
    companies: list[DiscoveredCompany] = []


class ExtractedPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    text: str


class CompanySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    domain: str
    name: str


class ScoreBreakdownItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion: Criterion
    rating: float
    weight: int
    points: float


class LeadSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    campaign_id: str
    company: CompanySummary
    source_url: str
    status: LeadStatus
    score: int
    decision_reason: str | None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LeadSummaryResponse]
    next_cursor: str | None = None


class LeadDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    campaign_id: str
    company: CompanySummary
    source_url: str
    status: LeadStatus
    score: int
    decision_reason: str | None
    evidence: list[EvidenceItem]
    score_breakdown: list[ScoreBreakdownItem]
    # Every outreach_drafts version's approval, newest first (Phase 4) — a
    # forward reference resolved via LeadDetailResponse.model_rebuild() at
    # the bottom of this module, since ApprovalResponse is defined later.
    approvals: list["ApprovalResponse"] = []
    created_at: datetime
    updated_at: datetime


class CampaignRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    campaign_id: str
    status: RunStatus
    stop_reason: str | None
    queries_used: int
    leads_created: int
    qualified_count: int
    needs_review_count: int
    rejected_count: int
    failed_count: int
    estimated_cost_usd: float
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class AgentEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    node: str
    status: Literal["ok", "error"]
    summary: str
    duration_ms: int | None
    error: str | None
    created_at: datetime


class AgentEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AgentEventResponse]
    next_cursor: str | None = None


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    tool: str
    provider: str
    status: Literal["ok", "error"]
    summary: str
    latency_ms: int | None
    cost_usd: float | None
    created_at: datetime


class ToolCallListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ToolCallResponse]
    next_cursor: str | None = None


# --- Outreach, approval, and export (Phase 4) ----------------------------

OutreachChannel = Literal["email", "linkedin"]
QualityStatus = Literal["passed", "needs_review"]
ApprovalStatus = Literal["pending", "approved", "rejected"]


class DraftOutreachResult(BaseModel):
    """The structured output requested from LanguageModelProvider.draft_outreach.

    Deliberately three separate, individually-required pieces (not one
    freeform body) — deterministic code (app/outreach.py) assembles them and
    enforces length/CTA/grounding rules; the LLM never controls the final
    template (plan.md §3, §11).
    """

    model_config = ConfigDict(extra="forbid")

    subject: str
    observation: str
    offer_line: str
    cta: str
    evidence_refs: list[int] = []

    @model_validator(mode="after")
    def _pieces_not_blank(self) -> "DraftOutreachResult":
        for field in ("subject", "observation", "offer_line", "cta"):
            if not getattr(self, field).strip():
                raise ValueError(f"{field} must not be blank")
        return self


class EmailSendResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["disabled", "sandboxed", "sent"]
    provider_message_id: str | None = None


class RegenerateOutreachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: OutreachChannel = "email"


class OutreachDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    lead_id: str
    channel: OutreachChannel
    subject: str
    body: str
    version: int
    quality_status: QualityStatus
    evidence_refs: list[int]
    created_at: datetime
    updated_at: datetime


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    draft: OutreachDraftResponse
    lead_id: str
    campaign_id: str
    company: CompanySummary
    lead_status: LeadStatus
    lead_score: int
    status: ApprovalStatus
    reviewer_id: str | None
    decided_at: datetime | None
    edited: bool
    created_at: datetime
    updated_at: datetime


class ApprovalListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ApprovalResponse]
    next_cursor: str | None = None


class ApprovalDraftEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str | None = None
    body: str | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "ApprovalDraftEditRequest":
        if self.subject is None and self.body is None:
            raise ValueError("at least one of subject or body must be provided")
        return self


class ApprovalRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class ApprovalSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_email: EmailStr


class LeadStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LeadStatus
    reason: str | None = None


class SuppressionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    reason: str | None = None

    @model_validator(mode="after")
    def _domain_not_blank(self) -> "SuppressionCreateRequest":
        if not self.domain.strip():
            raise ValueError("domain must not be blank")
        return self


class SuppressionEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    domain: str
    reason: str | None
    created_at: datetime


class SuppressionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SuppressionEntryResponse]
    next_cursor: str | None = None


LeadDetailResponse.model_rebuild()


# --- Evaluation harness + analytics (Phase 5) ----------------------------


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    detail: str | None = None


class EvalCategoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    total: int
    passed: int
    pass_rate: float
    cases: list[EvalCaseResult]


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: list[EvalCategoryResult]
    overall_pass_rate: float
    provider_mode: dict[str, str]


class DemoResetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted_campaigns: int


class CampaignAnalyticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    qualified_count: int
    needs_review_count: int
    rejected_count: int
    drafts_generated: int
    drafts_approved: int
    drafts_rejected: int
    total_cost_usd: float
    total_queries_used: int
    avg_tool_latency_ms: float | None
    tool_call_failures: int
    agent_event_failures: int
    runs_count: int
