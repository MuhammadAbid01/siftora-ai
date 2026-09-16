"""Regressions from a real run of "construction companies in Karachi".

That single run produced, in one log: two leads for the same company both
domained to a stock-quote site, a startup-database profile page as a lead, a
real company rejected because the provider returned a transient 502, and
another rejected because two evidence rows came back with a null claim.
"""

from typing import Any

import pytest

from app import agent, database, discovery
from app.providers import LLMUnavailableError, _coerce_analysis_payload
from app.schemas import (
    CompanyAnalysis,
    CriterionSignals,
    ExtractedPage,
    PageEntityExtraction,
    SearchResultItem,
)
from tests.fakes.supabase_fake import FakeSupabaseClient

USER_ID = "55555555-5555-5555-5555-555555555555"

CRITERIA = (
    "industry_fit",
    "geography_fit",
    "company_size_fit",
    "pain_point_evidence",
    "buying_signal",
    "contact_relevance",
    "recency",
    "evidence_completeness",
)

FLAT_SIGNALS = CriterionSignals(**dict.fromkeys(CRITERIA, 0.5))

ICP = {
    "industries": ["Construction companies"],
    "locations": ["Karachi, Pakistan"],
    "company_size_min": None,
    "company_size_max": None,
    "signals": [],
    "exclusions": [],
    "target_roles": [],
}


def _signals(value: float) -> dict[str, float]:
    return dict.fromkeys(CRITERIA, value)


def _start(fake: FakeSupabaseClient, plan: list[dict[str, Any]]):
    campaign = database.create_campaign(
        user_id=USER_ID,
        brief="Find construction companies in Karachi.",
        offer=None,
        target_lead_count=10,
    )
    run = database.create_campaign_run(campaign_id=campaign["id"], config_snapshot={})
    state = agent.build_initial_state(
        run_id=run["id"],
        campaign_id=campaign["id"],
        icp=ICP,
        offer=None,
        search_plan=plan,
        weights=campaign["score_weights"],
        thresholds={
            "qualified_min": campaign["score_threshold_qualified"],
            "needs_review_min": campaign["score_threshold_needs_review"],
        },
        limits={
            "max_queries": campaign["limit_max_queries"],
            "max_pages_per_company": campaign["limit_max_pages_per_company"],
            "max_retries": campaign["limit_max_retries"],
            "max_cost_usd": float(campaign["limit_max_cost_usd"]),
        },
        target_lead_count=campaign["target_lead_count"],
    )
    return campaign, state


def _install(monkeypatch: pytest.MonkeyPatch, *, search, extract, llm) -> None:
    monkeypatch.setattr(agent, "get_search_provider", lambda: search)
    monkeypatch.setattr(agent, "get_extraction_provider", lambda: extract)
    monkeypatch.setattr(agent, "get_language_model_provider", lambda: llm)


def _lead_domains(campaign_id: str) -> set[str]:
    leads, _ = database.list_leads(campaign_id=campaign_id, limit=50, cursor=None)
    companies = database.get_companies_by_ids([lead["company_id"] for lead in leads])
    return {companies[lead["company_id"]]["domain"] for lead in leads}


class _AlwaysExtracts:
    def __init__(self, text: str = "page text") -> None:
        self.text = text
        self.fetched: list[str] = []

    async def extract(self, *, url: str) -> ExtractedPage | None:
        self.fetched.append(url)
        return ExtractedPage(url=url, text=self.text)


class TestAggregatorInternalLinks:
    """An aggregator's internal profile link must never become a company's domain."""

    async def test_same_site_website_is_rejected_and_the_real_site_is_resolved(
        self, fake_supabase: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The source host here is deliberately NOT on the denylist (a
        # roundup published on an ordinary company's blog), so this test
        # isolates the same-site invariant rather than passing because the
        # denylist happened to catch the host first.
        campaign, state = _start(
            fake_supabase, [{"query": "construction companies in Karachi", "rationale": "r"}]
        )

        class Search:
            async def search(self, *, query: str, max_results: int, attempt: int = 0):
                if "official website" in query:
                    return [
                        SearchResultItem(
                            title="Karachi Builders Ltd",
                            domain="karachibuilders.com.pk",
                            url="https://karachibuilders.com.pk",
                            snippet="Official site",
                        )
                    ]
                return [
                    SearchResultItem(
                        title="Top 10 Construction Companies in Karachi",
                        domain="buildersblog.pk",
                        url="https://buildersblog.pk/top-construction-companies-karachi",
                        snippet="our roundup",
                    )
                ]

        class LLM:
            async def extract_companies_from_page(self, **_kw) -> PageEntityExtraction:
                # Exactly the shape the real model returned on investing.com:
                # the "website" is an internal profile page on the source.
                return PageEntityExtraction(
                    page_type="listing",
                    companies=[
                        {
                            "name": "Karachi Builders",
                            "website": "https://buildersblog.pk/company/karachi-builders",
                        }
                    ],
                )

            async def analyze_company(self, **_kw) -> CompanyAnalysis:
                return CompanyAnalysis(evidence=[], signals=FLAT_SIGNALS)

        _install(monkeypatch, search=Search(), extract=_AlwaysExtracts(), llm=LLM())
        await agent.run_research(state)

        domains = _lead_domains(campaign["id"])
        assert not any(discovery.same_site(d, "buildersblog.pk") for d in domains), (
            f"the source page became the lead's domain: {domains}"
        )
        assert "karachibuilders.com.pk" in domains

    async def test_one_company_via_two_front_ends_is_not_duplicated(
        self, fake_supabase: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        campaign, state = _start(
            fake_supabase,
            [
                {"query": "construction companies in Karachi", "rationale": "r"},
                {"query": "karachi 30 index", "rationale": "r2"},
            ],
        )

        class Search:
            n = 0

            async def search(self, *, query: str, max_results: int, attempt: int = 0):
                if "official website" in query:
                    return [
                        SearchResultItem(
                            title="Attock Refinery Limited",
                            domain="attockrefinery.com.pk",
                            url="https://attockrefinery.com.pk",
                            snippet="Official site",
                        )
                    ]
                Search.n += 1
                host = "investing.com" if Search.n == 1 else "uk.investing.com"
                return [
                    SearchResultItem(
                        title="Karachi 30 Components",
                        domain=host,
                        url=f"https://{host}/indices/karachi-30-components",
                        snippet="index",
                    )
                ]

        class LLM:
            async def extract_companies_from_page(self, **_kw) -> PageEntityExtraction:
                return PageEntityExtraction(
                    page_type="listing",
                    # Same business, spelled slightly differently by each
                    # front-end — name-based dedup has to catch this.
                    companies=[{"name": "Attock Refinery Limited", "website": None}],
                )

            async def analyze_company(self, **_kw) -> CompanyAnalysis:
                return CompanyAnalysis(evidence=[], signals=FLAT_SIGNALS)

        _install(monkeypatch, search=Search(), extract=_AlwaysExtracts(), llm=LLM())
        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        assert len(leads) == 1, f"the same company became {len(leads)} leads"


class TestTransientProviderFailures:
    async def test_a_502_is_retried_rather_than_rejecting_the_lead(
        self, fake_supabase: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        campaign, state = _start(
            fake_supabase, [{"query": "construction companies in Karachi", "rationale": "r"}]
        )
        attempts = {"n": 0}

        class Search:
            async def search(self, *, query: str, max_results: int, attempt: int = 0):
                if "official website" in query:
                    return []
                return [
                    SearchResultItem(
                        title="Dany Tameerat",
                        domain="danytameerat.com",
                        url="https://danytameerat.com",
                        snippet="construction",
                    )
                ]

        class LLM:
            async def extract_companies_from_page(self, **_kw) -> PageEntityExtraction:
                return PageEntityExtraction(
                    page_type="company_site",
                    companies=[{"name": "Dany Tameerat", "website": "https://danytameerat.com"}],
                )

            async def analyze_company(self, **_kw) -> CompanyAnalysis:
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise LLMUnavailableError(
                        "OpenRouter reported an upstream error (code 502): Internal server error"
                    )
                return CompanyAnalysis(
                    evidence=[
                        {
                            "type": "fact",
                            "claim": "Dany Tameerat is a construction company in Karachi.",
                            "excerpt": "Dany Tameerat is a construction company.",
                            "source_url": "https://danytameerat.com",
                        }
                    ],
                    signals=FLAT_SIGNALS,
                )

        monkeypatch.setattr(agent, "_RETRY_BACKOFF_SECONDS", 0.0)
        _install(
            monkeypatch,
            search=Search(),
            extract=_AlwaysExtracts("Dany Tameerat is a construction company."),
            llm=LLM(),
        )
        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        assert attempts["n"] >= 2, "a transient 502 should have been retried"
        assert leads, "a transient provider failure must not cost the company its lead"
        assert leads[0]["decision_reason"] != "analysis_failed"

    async def test_a_persistent_outage_still_fails_the_candidate_visibly(
        self, fake_supabase: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        campaign, state = _start(
            fake_supabase, [{"query": "construction companies in Karachi", "rationale": "r"}]
        )

        class Search:
            async def search(self, *, query: str, max_results: int, attempt: int = 0):
                if "official website" in query:
                    return []
                return [
                    SearchResultItem(
                        title="Dany Tameerat",
                        domain="danytameerat.com",
                        url="https://danytameerat.com",
                        snippet="construction",
                    )
                ]

        class LLM:
            async def extract_companies_from_page(self, **_kw) -> PageEntityExtraction:
                return PageEntityExtraction(
                    page_type="company_site",
                    companies=[{"name": "Dany Tameerat", "website": "https://danytameerat.com"}],
                )

            async def analyze_company(self, **_kw) -> CompanyAnalysis:
                raise LLMUnavailableError("still down")

        monkeypatch.setattr(agent, "_RETRY_BACKOFF_SECONDS", 0.0)
        _install(monkeypatch, search=Search(), extract=_AlwaysExtracts(), llm=LLM())
        await agent.run_research(state)

        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        # Still recorded, never silently dropped (FR-8).
        assert leads and leads[0]["decision_reason"] == "analysis_failed"


class TestAnalysisPayloadCoercion:
    def test_null_claims_are_dropped_instead_of_failing_the_whole_analysis(self) -> None:
        """The live failure: 'evidence.6.claim Input should be a valid string,
        input_value=None' rejected an otherwise-usable company outright.
        """
        payload = {
            "evidence": [
                {
                    "type": "fact",
                    "claim": "Elite Services builds residential projects in Karachi.",
                    "excerpt": "Elite Services builds residential projects.",
                },
                {"type": "fact", "claim": None, "excerpt": "x"},
                {"type": "inference", "claim": None},
            ],
            "signals": _signals(0.5),
        }

        result = CompanyAnalysis.model_validate(
            _coerce_analysis_payload(payload, url="https://eliteservices.pk")
        )

        assert len(result.evidence) == 1
        assert result.evidence[0].source_url == "https://eliteservices.pk"

    def test_a_fact_without_an_excerpt_is_dropped_not_left_unsourced(self) -> None:
        payload = {
            "evidence": [{"type": "fact", "claim": "Claimed with no support."}],
            "signals": _signals(0.0),
        }
        result = CompanyAnalysis.model_validate(
            _coerce_analysis_payload(payload, url="https://x.example")
        )
        assert result.evidence == []

    def test_unknown_evidence_keeps_no_source(self) -> None:
        payload = {
            "evidence": [{"type": "unknown", "claim": "No pricing published."}],
            "signals": _signals(0.0),
        }
        result = CompanyAnalysis.model_validate(
            _coerce_analysis_payload(payload, url="https://x.example")
        )
        assert result.evidence[0].source_url is None

    def test_out_of_range_and_missing_signals_are_clamped(self) -> None:
        payload = {"evidence": [], "signals": {"industry_fit": 5, "geography_fit": -2}}
        result = CompanyAnalysis.model_validate(
            _coerce_analysis_payload(payload, url="https://x.example")
        )
        assert result.signals.industry_fit == 1.0
        assert result.signals.geography_fit == 0.0
        assert result.signals.recency == 0.0


class TestUnfetchableSources:
    async def test_login_walled_sources_are_skipped_without_an_extraction_call(
        self, fake_supabase: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        campaign, state = _start(
            fake_supabase, [{"query": "construction companies in Karachi", "rationale": "r"}]
        )

        class Search:
            async def search(self, *, query: str, max_results: int, attempt: int = 0):
                if "official website" in query:
                    return []
                return [
                    SearchResultItem(
                        title="Construction Companies in Karachi",
                        domain="www.facebook.com",
                        url="https://www.facebook.com/groups/2117121858604974",
                        snippet="group",
                    ),
                    SearchResultItem(
                        title="Construction Companies in Karachi",
                        domain="www.scribd.com",
                        url="https://www.scribd.com/document/487456313/x",
                        snippet="doc",
                    ),
                ]

        class LLM:
            async def extract_companies_from_page(self, **_kw) -> PageEntityExtraction:
                raise AssertionError("should never be reached for an unfetchable host")

            async def analyze_company(self, **_kw) -> CompanyAnalysis:
                raise AssertionError("should never be reached for an unfetchable host")

        extractor = _AlwaysExtracts()
        _install(monkeypatch, search=Search(), extract=extractor, llm=LLM())
        await agent.run_research(state)

        assert extractor.fetched == [], (
            f"paid to fetch hosts that can never yield anything: {extractor.fetched}"
        )
        leads, _ = database.list_leads(campaign_id=campaign["id"], limit=50, cursor=None)
        assert leads == []


class TestTargetCountsUsableLeadsOnly:
    async def test_rejected_candidates_do_not_satisfy_the_target(
        self, fake_supabase: FakeSupabaseClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A run must not stop at "6 leads" when four of them are rejects.

        Observed live: a run reported target_reached with two usable
        companies and four rejections (bad domains, failed extractions).
        """
        campaign, state = _start(
            fake_supabase, [{"query": "construction companies in Karachi", "rationale": "r"}]
        )
        state["target_lead_count"] = 2

        hosts = [f"co{i}.example" for i in range(6)]

        class Search:
            async def search(self, *, query: str, max_results: int, attempt: int = 0):
                if "official website" in query:
                    return []
                return [
                    SearchResultItem(
                        title=f"Company {i}", domain=h, url=f"https://{h}", snippet="builder"
                    )
                    for i, h in enumerate(hosts)
                ]

        class Extract:
            async def extract(self, *, url: str):
                # Every other site is unreachable -> a rejected lead.
                idx = int(url.split("co")[1].split(".")[0])
                if idx % 2 == 0:
                    return None
                return ExtractedPage(url=url, text=f"Company {idx} builds things.")

        class LLM:
            async def extract_companies_from_page(self, *, source_domain, **_kw):
                idx = source_domain.split("co")[1].split(".")[0]
                return PageEntityExtraction(
                    page_type="company_site",
                    companies=[{"name": f"Builder {idx}", "website": f"https://{source_domain}"}],
                )

            async def analyze_company(self, *, url, **_kw):
                return CompanyAnalysis(
                    evidence=[
                        {
                            "type": "fact",
                            "claim": "It builds things.",
                            "excerpt": "builds things",
                            "source_url": url,
                        }
                    ],
                    # 0.7 across the board scores 70, which clears the
                    # default needs_review threshold of 55.
                    signals=CriterionSignals(**dict.fromkeys(CRITERIA, 0.7)),
                )

        _install(monkeypatch, search=Search(), extract=Extract(), llm=LLM())
        await agent.run_research(state)

        run = database.get_campaign_run(run_id=state["run_id"])
        usable = run["qualified_count"] + run["needs_review_count"]
        assert usable >= 2, f"stopped with only {usable} usable lead(s)"
        assert run["rejected_count"] >= 1, "this scenario should also produce rejects"
