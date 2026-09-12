import pytest
from pydantic import ValidationError

from app.providers import FixtureLanguageModelProvider
from app.schemas import RunLimits, ScoreThresholds, ScoreWeights


class TestFixtureLanguageModelProvider:
    async def test_complete_brief_produces_full_icp_and_search_plan(self) -> None:
        provider = FixtureLanguageModelProvider()

        result = await provider.generate_campaign_plan(
            brief="Find animation and design agencies in Dubai with 5-50 employees.",
            offer="AI customer support automation",
            target_lead_count=20,
        )

        assert result.icp.industries
        assert result.icp.locations
        assert result.icp.company_size_min == 5
        assert result.icp.company_size_max == 50
        assert result.search_plan

    async def test_vague_brief_returns_incomplete_extraction(self) -> None:
        provider = FixtureLanguageModelProvider()

        result = await provider.generate_campaign_plan(
            brief="Find some good companies that might want our product.",
            offer=None,
            target_lead_count=20,
        )

        assert result.icp.industries == []
        assert result.icp.locations == []
        assert result.search_plan == []

    async def test_never_raises_on_arbitrary_text(self) -> None:
        provider = FixtureLanguageModelProvider()
        result = await provider.generate_campaign_plan(
            brief="asdf qwer", offer=None, target_lead_count=1
        )
        assert result.icp.industries == []


class TestScoreWeights:
    def test_default_weights_sum_to_100(self) -> None:
        ScoreWeights()

    def test_rejects_weights_not_summing_to_100(self) -> None:
        with pytest.raises(ValidationError):
            ScoreWeights(industry_fit=50)

    def test_accepts_a_valid_redistribution(self) -> None:
        weights = ScoreWeights(
            industry_fit=25,
            geography_fit=15,
            company_size_fit=10,
            pain_point_evidence=20,
            buying_signal=10,
            contact_relevance=10,
            recency=5,
            evidence_completeness=5,
        )
        assert weights.industry_fit == 25


class TestScoreThresholds:
    def test_defaults_are_valid(self) -> None:
        ScoreThresholds()

    def test_rejects_needs_review_at_or_above_qualified(self) -> None:
        with pytest.raises(ValidationError):
            ScoreThresholds(qualified_min=60, needs_review_min=60)

    def test_rejects_out_of_range_values(self) -> None:
        with pytest.raises(ValidationError):
            ScoreThresholds(qualified_min=150, needs_review_min=55)


class TestRunLimits:
    def test_defaults_are_valid(self) -> None:
        RunLimits()

    def test_rejects_zero_max_queries(self) -> None:
        with pytest.raises(ValidationError):
            RunLimits(max_queries=0)

    def test_rejects_excessive_cost_limit(self) -> None:
        with pytest.raises(ValidationError):
            RunLimits(max_cost_usd=51)
