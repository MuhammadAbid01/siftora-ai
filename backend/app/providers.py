"""LanguageModelProvider interface and adapters (plan.md §5).

Routers depend on `get_language_model_provider()`, never on a concrete
adapter, so campaign-planning logic never talks to a vendor SDK directly.
"""

import json
import re
from typing import Literal, Protocol

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas import (
    ICP,
    CompanyAnalysis,
    CriterionSignals,
    DraftOutreachResult,
    EmailSendResult,
    EvidenceItem,
    ExtractedPage,
    PlanExtraction,
    SearchPlanQuery,
    SearchResultItem,
)


class LLMOutputError(Exception):
    """Raised when a provider's output can't be parsed or validated."""


class LanguageModelProvider(Protocol):
    async def generate_campaign_plan(
        self, *, brief: str, offer: str | None, target_lead_count: int
    ) -> PlanExtraction: ...

    async def analyze_company(
        self,
        *,
        icp: dict,
        offer: str | None,
        company_name: str,
        domain: str,
        url: str,
        page_text: str,
    ) -> CompanyAnalysis: ...

    async def draft_outreach(
        self,
        *,
        icp: dict,
        offer: str | None,
        company_name: str,
        domain: str,
        evidence: list[EvidenceItem],
        channel: Literal["email", "linkedin"],
        sender_name: str | None,
        attempt: int = 0,
    ) -> DraftOutreachResult: ...


class SearchProvider(Protocol):
    async def search(
        self, *, query: str, max_results: int, attempt: int = 0
    ) -> list[SearchResultItem]: ...


class WebsiteExtractionProvider(Protocol):
    async def extract(self, *, url: str) -> ExtractedPage | None: ...


class EmailProvider(Protocol):
    async def send(self, *, to_email: str, subject: str, body: str) -> EmailSendResult: ...


def normalize_domain(url_or_domain: str) -> str:
    """Lower-cases and strips scheme/`www.`/path so the same company is
    recognized regardless of how its URL was spelled (plan.md's "normalized
    domain" — see specs/phase-3-research.md FR-7).
    """
    value = url_or_domain.strip().lower()
    value = re.sub(r"^[a-z]+://", "", value)
    value = value.split("/")[0]
    if value.startswith("www."):
        value = value[len("www.") :]
    return value


# --- Fixture adapter (default; zero cost, zero network calls) ----------

_LOCATION_KEYWORDS = {
    "dubai": "Dubai, UAE",
    "uae": "United Arab Emirates",
    "london": "London, UK",
    "united kingdom": "United Kingdom",
    "new york": "New York, USA",
    "san francisco": "San Francisco, USA",
    "united states": "United States",
    "usa": "United States",
    "toronto": "Toronto, Canada",
    "canada": "Canada",
    "singapore": "Singapore",
    "berlin": "Berlin, Germany",
    "remote": "Remote / Global",
}

_INDUSTRY_KEYWORDS = {
    "animation": "Animation studios",
    "design agenc": "Design agencies",
    "agenc": "Agencies",
    "saas": "SaaS companies",
    "software": "Software companies",
    "e-commerce": "Ecommerce companies",
    "ecommerce": "Ecommerce companies",
    "marketing": "Marketing agencies",
    "consulting": "Consulting firms",
    "law firm": "Law firms",
    "clinic": "Healthcare clinics",
    "restaurant": "Restaurants",
    "manufacturing": "Manufacturing companies",
    "retail": "Retail businesses",
}

_SIZE_RANGE_RE = re.compile(r"(\d+)\s*(?:-|to|–)\s*(\d+)\s*employees", re.IGNORECASE)


class FixtureLanguageModelProvider:
    """Deterministic, keyword-driven fixture — no network calls, no cost.

    Returns a complete extraction when the brief names at least one
    recognizable industry and one recognizable location; otherwise returns
    an incomplete extraction (matching whatever it *did* find) so the
    "ask, don't invent" path is deterministically testable.
    """

    async def generate_campaign_plan(
        self, *, brief: str, offer: str | None, target_lead_count: int
    ) -> PlanExtraction:
        lowered = brief.lower()

        industries: list[str] = []
        for keyword, label in _INDUSTRY_KEYWORDS.items():
            if keyword in lowered and label not in industries:
                industries.append(label)

        locations: list[str] = []
        for keyword, label in _LOCATION_KEYWORDS.items():
            if keyword in lowered and label not in locations:
                locations.append(label)

        size_match = _SIZE_RANGE_RE.search(brief)
        company_size_min = int(size_match.group(1)) if size_match else None
        company_size_max = int(size_match.group(2)) if size_match else None

        icp = ICP(
            industries=industries,
            locations=locations,
            company_size_min=company_size_min,
            company_size_max=company_size_max,
            signals=["Active public website"] if industries and locations else [],
            exclusions=[],
            target_roles=["Owner", "Marketing Manager"] if industries and locations else [],
        )

        if not industries or not locations:
            return PlanExtraction(icp=icp, search_plan=[])

        search_plan = [
            SearchPlanQuery(
                query=f"{industry} in {location}",
                rationale="Directly matches the requested industry and location.",
            )
            for industry in industries[:2]
            for location in locations[:2]
        ]

        return PlanExtraction(icp=icp, search_plan=search_plan)

    async def analyze_company(
        self,
        *,
        icp: dict,
        offer: str | None,
        company_name: str,
        domain: str,
        url: str,
        page_text: str,
    ) -> CompanyAnalysis:
        company = _FIXTURE_COMPANIES_BY_DOMAIN.get(domain)
        if company is None or company["thin"]:
            # No usable content — the fixture equivalent of a real page too
            # thin to extract anything from. Zero facts, zero signals: never
            # invented, just genuinely absent (FR-10).
            zero = {field: 0.0 for field in _CRITERIA_FIELDS}
            return CompanyAnalysis(evidence=[], signals=CriterionSignals(**zero))

        evidence = [EvidenceItem(**item) for item in company["evidence"]]
        return CompanyAnalysis(evidence=evidence, signals=CriterionSignals(**company["signals"]))

    async def draft_outreach(
        self,
        *,
        icp: dict,
        offer: str | None,
        company_name: str,
        domain: str,
        evidence: list[EvidenceItem],
        channel: Literal["email", "linkedin"],
        sender_name: str | None,
        attempt: int = 0,
    ) -> DraftOutreachResult:
        fixture_company = _FIXTURE_COMPANIES_BY_DOMAIN.get(domain)
        ungroundable = bool(fixture_company and fixture_company.get("draft_ungroundable"))

        offer_line = (
            f"We help teams like {company_name} with {offer}."
            if offer
            else "We'd love to explore how we could help your team."
        )
        cta = "Would you be open to a quick call next week?"
        subject = f"Quick question for {company_name}"

        if ungroundable:
            # Deterministic "can't ground this" path — always fails
            # regardless of attempt, so the regenerate-once-then-needs_review
            # path (specs/phase-4-outreach.md FR-5/FR-8) is reachable without
            # relying on real model non-determinism.
            return DraftOutreachResult(
                subject=subject,
                observation="We came across your company online.",
                offer_line=offer_line,
                cta=cta,
                evidence_refs=[],
            )

        groundable_index = next(
            (i for i, item in enumerate(evidence) if item.type in ("fact", "inference")),
            None,
        )
        if groundable_index is None:
            return DraftOutreachResult(
                subject=subject,
                observation="We came across your company online.",
                offer_line=offer_line,
                cta=cta,
                evidence_refs=[],
            )

        return DraftOutreachResult(
            subject=subject,
            observation=evidence[groundable_index].claim,
            offer_line=offer_line,
            cta=cta,
            evidence_refs=[groundable_index],
        )


# --- Fixture search + extraction catalog --------------------------------
#
# A small, deterministic, hand-authored set of demo companies. Search
# "attempt" 0 requires ALL of a company's tagged keywords to appear in the
# query text (strict); attempt >= 1 (a revised/broadened query, see
# app/agent.py) requires only ONE (relaxed) — so a query that's too narrow
# on the first try can recover results on retry without needing the agent
# to guess exactly which word to drop. This is a fixture-only abstraction
# for deterministic testing, not a claim about how real search relevance
# works (see specs/phase-3-research.md, Risks).

_CRITERIA_FIELDS = (
    "industry_fit",
    "geography_fit",
    "company_size_fit",
    "pain_point_evidence",
    "buying_signal",
    "contact_relevance",
    "recency",
    "evidence_completeness",
)

_FIXTURE_COMPANIES: list[dict] = [
    {
        "company_name": "Northbeam Studio",
        "domain": "northbeamstudio.example",
        "keywords": ["animation", "dubai"],
        "broken": False,
        "thin": False,
        "page_text": (
            "Northbeam Studio is an animation studio based in Dubai, UAE, founded in 2018 "
            "with 22 employees. The team has grown from 8 to 22 people in the last two years "
            "and recently posted three open roles for production coordinators. The site lists "
            "a general contact form but no direct email."
        ),
        "signals": {
            "industry_fit": 1.0,
            "geography_fit": 1.0,
            "company_size_fit": 1.0,
            "pain_point_evidence": 1.0,
            "buying_signal": 0.8,
            "contact_relevance": 0.5,
            "recency": 1.0,
            "evidence_completeness": 1.0,
        },
        "evidence": [
            {
                "type": "fact",
                "claim": "Northbeam Studio has 22 employees and is based in Dubai, UAE.",
                "excerpt": (
                    "Northbeam Studio is an animation studio based in Dubai, UAE, "
                    "founded in 2018 with 22 employees."
                ),
                "source_url": "https://northbeamstudio.example",
                "confidence": 0.9,
            },
            {
                "type": "inference",
                "claim": "Recent hiring for production coordinators suggests capacity constraints.",
                "excerpt": "recently posted three open roles for production coordinators",
                "source_url": "https://northbeamstudio.example",
                "confidence": 0.6,
            },
            {
                "type": "unknown",
                "claim": "No public pricing or direct contact email was found.",
            },
        ],
    },
    {
        "company_name": "Vantage Motion Co.",
        "domain": "vantagemotion.example",
        "keywords": ["design agenc", "dubai"],
        "broken": False,
        "thin": False,
        "page_text": (
            "Vantage Motion Co. is a design agency in Dubai, UAE with a portfolio of 40+ "
            "client projects. The company blog was last updated two months ago describing a "
            "new office opening."
        ),
        "signals": {
            "industry_fit": 0.8,
            "geography_fit": 1.0,
            "company_size_fit": 0.5,
            "pain_point_evidence": 0.5,
            "buying_signal": 0.5,
            "contact_relevance": 0.3,
            "recency": 0.5,
            "evidence_completeness": 0.6,
        },
        "evidence": [
            {
                "type": "fact",
                "claim": "Vantage Motion Co. is a design agency in Dubai, UAE.",
                "excerpt": (
                    "Vantage Motion Co. is a design agency in Dubai, UAE with a "
                    "portfolio of 40+ client projects."
                ),
                "source_url": "https://vantagemotion.example",
                "confidence": 0.85,
            },
            {
                "type": "unknown",
                "claim": "No employee count or hiring signal was found.",
            },
        ],
    },
    {
        "company_name": "Pixel & Pine",
        "domain": "pixelandpine.example",
        "keywords": ["design agenc", "dubai"],
        "broken": False,
        "thin": True,
        "page_text": "Pixel & Pine.",
        "signals": {},
        "evidence": [],
    },
    {
        "company_name": "Brokenlink Creative",
        "domain": "brokenlink.example",
        "keywords": ["design agenc", "animation", "dubai"],
        "broken": True,
        "thin": False,
        "page_text": None,
        "signals": {},
        "evidence": [],
    },
    {
        "company_name": "Thinclaim Robotics",
        "domain": "thinclaimrobotics.example",
        "keywords": ["software", "berlin"],
        "broken": False,
        "thin": False,
        "draft_ungroundable": True,
        "page_text": (
            "Thinclaim Robotics is a software company based in Berlin, Germany, with 30 "
            "employees. The team recently launched a new product line and is actively hiring "
            "engineers."
        ),
        "signals": {
            "industry_fit": 1.0,
            "geography_fit": 1.0,
            "company_size_fit": 0.9,
            "pain_point_evidence": 0.9,
            "buying_signal": 0.8,
            "contact_relevance": 0.6,
            "recency": 0.9,
            "evidence_completeness": 0.9,
        },
        "evidence": [
            {
                "type": "fact",
                "claim": "Thinclaim Robotics has 30 employees and is based in Berlin, Germany.",
                "excerpt": (
                    "Thinclaim Robotics is a software company based in Berlin, Germany, "
                    "with 30 employees."
                ),
                "source_url": "https://thinclaimrobotics.example",
                "confidence": 0.9,
            },
        ],
    },
    {
        "company_name": "Harbor & Co. Consulting",
        "domain": "harborconsulting.example",
        "keywords": ["consulting", "london"],
        "broken": False,
        "thin": False,
        "page_text": (
            "Harbor & Co. Consulting is a management consulting firm headquartered in "
            "London, UK, with 15 consultants. Their site mentions a recent partnership with a "
            "fintech client."
        ),
        "signals": {
            "industry_fit": 0.1,
            "geography_fit": 0.0,
            "company_size_fit": 0.5,
            "pain_point_evidence": 0.2,
            "buying_signal": 0.2,
            "contact_relevance": 0.2,
            "recency": 0.3,
            "evidence_completeness": 0.4,
        },
        "evidence": [
            {
                "type": "fact",
                "claim": "Harbor & Co. Consulting is based in London, UK with 15 consultants.",
                "excerpt": (
                    "Harbor & Co. Consulting is a management consulting firm "
                    "headquartered in London, UK, with 15 consultants."
                ),
                "source_url": "https://harborconsulting.example",
                "confidence": 0.8,
            },
        ],
    },
]

_FIXTURE_COMPANIES_BY_DOMAIN = {c["domain"]: c for c in _FIXTURE_COMPANIES}


class FixtureSearchProvider:
    """Deterministic, zero-cost, zero-network search fixture."""

    async def search(
        self, *, query: str, max_results: int, attempt: int = 0
    ) -> list[SearchResultItem]:
        lowered = query.lower()
        relaxed = attempt > 0

        def matches(company: dict) -> bool:
            tags = company["keywords"]
            return (
                any(tag in lowered for tag in tags)
                if relaxed
                else all(tag in lowered for tag in tags)
            )

        results = [c for c in _FIXTURE_COMPANIES if matches(c)]
        return [
            SearchResultItem(
                company_name=c["company_name"],
                domain=c["domain"],
                url=f"https://{c['domain']}",
                snippet=(c["page_text"] or f"{c['company_name']} — no preview available.")[:160],
            )
            for c in results[:max_results]
        ]


class FixtureWebsiteExtractionProvider:
    """Deterministic, zero-cost, zero-network extraction fixture.

    `brokenlink.example` always returns None, simulating an unreachable
    site (FR-8) — every other catalog domain returns its canned page text.
    """

    async def extract(self, *, url: str) -> ExtractedPage | None:
        domain = normalize_domain(url)
        company = _FIXTURE_COMPANIES_BY_DOMAIN.get(domain)
        if company is None or company["broken"]:
            return None
        return ExtractedPage(url=url, text=company["page_text"])


# --- Gemini adapter (opt-in; requires GEMINI_API_KEY) -------------------

_GEMINI_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "icp": {
            "type": "object",
            "properties": {
                "industries": {"type": "array", "items": {"type": "string"}},
                "locations": {"type": "array", "items": {"type": "string"}},
                "company_size_min": {"type": "integer", "nullable": True},
                "company_size_max": {"type": "integer", "nullable": True},
                "signals": {"type": "array", "items": {"type": "string"}},
                "exclusions": {"type": "array", "items": {"type": "string"}},
                "target_roles": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["industries", "locations"],
        },
        "search_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["query", "rationale"],
            },
        },
    },
    "required": ["icp", "search_plan"],
}

_GEMINI_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "observation": {"type": "string"},
        "offer_line": {"type": "string"},
        "cta": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["subject", "observation", "offer_line", "cta", "evidence_refs"],
}

_GEMINI_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["fact", "inference", "unknown"]},
                    "claim": {"type": "string"},
                    "excerpt": {"type": "string", "nullable": True},
                    "confidence": {"type": "number", "nullable": True},
                },
                "required": ["type", "claim"],
            },
        },
        "signals": {
            "type": "object",
            "properties": {field: {"type": "number"} for field in _CRITERIA_FIELDS},
            "required": list(_CRITERIA_FIELDS),
        },
    },
    "required": ["evidence", "signals"],
}


class GeminiLanguageModelProvider:
    """Real Gemini-backed adapter. Verified live against the Gemini API in
    September 2026 — see specs/phase-2-campaigns.md, Risks and Assumptions.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate_campaign_plan(
        self, *, brief: str, offer: str | None, target_lead_count: int
    ) -> PlanExtraction:
        prompt = (
            "Extract a structured ideal customer profile (ICP) and a search plan "
            "from this lead-generation campaign brief. Only include an industry or "
            "location if it is explicitly stated or strongly implied by the brief — "
            "leave the list empty rather than guessing. Never invent company names "
            "or contact details.\n\n"
            "For search_plan queries: these run against a general web search API "
            "(not a specific site's own search), so write plain natural-language "
            "company-discovery queries like '<industry> companies in <location>' or "
            "'<industry> agencies in <location>'. Do not use site: operators (e.g. "
            "site:linkedin.com) or heavily quote-and-operator-laden queries — "
            "general web search engines index LinkedIn and similar gated sites "
            "poorly, so those queries return few or irrelevant results in "
            "practice.\n\n"
            f"Brief: {brief}\n"
            f"Offer: {offer or '(not specified)'}\n"
            f"Target lead count: {target_lead_count}"
        )

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _GEMINI_RESPONSE_SCHEMA,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                payload = response.json()
                text = payload["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return PlanExtraction.model_validate(parsed)
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise LLMOutputError(f"Gemini response could not be parsed: {exc}") from exc

    async def analyze_company(
        self,
        *,
        icp: dict,
        offer: str | None,
        company_name: str,
        domain: str,
        url: str,
        page_text: str,
    ) -> CompanyAnalysis:
        prompt = (
            "Analyze this company's public website text against the ideal customer "
            "profile below. Extract facts (directly stated, with a short verbatim "
            "excerpt) and inferences (reasonable conclusions from the facts, also "
            "with an excerpt) — do not include a source URL for these, it will be "
            "filled in automatically. Also list unknowns (relevant information you "
            "could not find — do not guess a value for these, and do not attach an "
            "excerpt to them). Then rate each of the 8 criteria from 0.0 to 1.0 "
            "based only on the evidence you extracted.\n\n"
            f"ICP: {json.dumps(icp)}\n"
            f"Offer: {offer or '(not specified)'}\n"
            f"Company: {company_name} ({domain})\n"
            f"Website text (from {url}): {page_text}"
        )

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _GEMINI_ANALYSIS_SCHEMA,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                payload = response.json()
                text = payload["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                # Ground every fact/inference's source in the URL we actually
                # fetched — never trust the model to echo it back correctly
                # (plan.md: sources must be genuine, not invented).
                for item in parsed.get("evidence", []):
                    if item.get("type") in ("fact", "inference"):
                        item["source_url"] = url
                return CompanyAnalysis.model_validate(parsed)
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise LLMOutputError(f"Gemini analysis response could not be parsed: {exc}") from exc

    async def draft_outreach(
        self,
        *,
        icp: dict,
        offer: str | None,
        company_name: str,
        domain: str,
        evidence: list[EvidenceItem],
        channel: Literal["email", "linkedin"],
        sender_name: str | None,
        attempt: int = 0,
    ) -> DraftOutreachResult:
        indexed_evidence = "\n".join(
            f"[{i}] ({item.type}) {item.claim}"
            + (f" — excerpt: {item.excerpt}" if item.excerpt else "")
            for i, item in enumerate(evidence)
        )
        prompt = (
            f"Draft a short cold {channel} outreach message to {company_name} ({domain}) "
            "as three separate pieces — do not write a full email, only these pieces:\n"
            "- subject: a short subject line\n"
            "- observation: ONE specific, genuine observation about this company, grounded "
            "in one of the numbered evidence items below — do not state anything not "
            "supported by an evidence item\n"
            "- offer_line: ONE sentence connecting the observation to the sender's offer\n"
            "- cta: ONE clear call to action\n"
            "- evidence_refs: the index number(s) of the evidence item(s) that support "
            "`observation`. If nothing below genuinely supports a specific observation, "
            "return an empty list rather than guessing.\n\n"
            f"Evidence:\n{indexed_evidence or '(none)'}\n\n"
            f"Sender: {sender_name or '(not specified)'}\n"
            f"Offer: {offer or '(not specified)'}\n"
            f"ICP: {json.dumps(icp)}\n"
            f"Attempt: {attempt}"
        )

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _GEMINI_DRAFT_SCHEMA,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                payload = response.json()
                text = payload["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return DraftOutreachResult.model_validate(parsed)
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise LLMOutputError(f"Gemini draft response could not be parsed: {exc}") from exc


def get_language_model_provider(settings: Settings | None = None) -> LanguageModelProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "gemini":
        assert settings.gemini_api_key  # guaranteed by Settings validation
        return GeminiLanguageModelProvider(
            api_key=settings.gemini_api_key, model=settings.gemini_model
        )
    return FixtureLanguageModelProvider()


# --- Tavily search adapter (opt-in; requires TAVILY_API_KEY) ------------


class TavilySearchProvider:
    """Real Tavily-backed adapter. Verified live against the Tavily API in
    September 2026 — see specs/phase-3-research.md, Risks and Assumptions.
    A provider-level failure returns an empty result list rather than
    raising, since the agent already treats "no results" as the trigger
    for query revision.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(
        self, *, query: str, max_results: int, attempt: int = 0
    ) -> list[SearchResultItem]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": self._api_key, "query": query, "max_results": max_results},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            return []

        results = []
        for item in payload.get("results", [])[:max_results]:
            url = item.get("url")
            if not url:
                continue
            results.append(
                SearchResultItem(
                    company_name=item.get("title", url),
                    domain=normalize_domain(url),
                    url=url,
                    snippet=item.get("content", "")[:300],
                )
            )
        return results


def get_search_provider(settings: Settings | None = None) -> SearchProvider:
    settings = settings or get_settings()
    if settings.search_provider == "tavily":
        assert settings.tavily_api_key  # guaranteed by Settings validation
        return TavilySearchProvider(api_key=settings.tavily_api_key)
    return FixtureSearchProvider()


# --- Firecrawl extraction adapter (opt-in; requires FIRECRAWL_API_KEY) --


class FirecrawlExtractionProvider:
    """Real Firecrawl-backed adapter. Verified live against the Firecrawl
    API in September 2026 — see specs/phase-3-research.md, Risks and
    Assumptions. A provider-level failure returns None (the agent's "unreachable site"
    signal) rather than raising.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def extract(self, *, url: str) -> ExtractedPage | None:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"url": url, "formats": ["markdown"]},
                )
                response.raise_for_status()
                payload = response.json()
                text = payload["data"]["markdown"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError):
            return None

        if not text or not text.strip():
            return None
        return ExtractedPage(url=url, text=text)


def get_extraction_provider(settings: Settings | None = None) -> WebsiteExtractionProvider:
    settings = settings or get_settings()
    if settings.extraction_provider == "firecrawl":
        assert settings.firecrawl_api_key  # guaranteed by Settings validation
        return FirecrawlExtractionProvider(api_key=settings.firecrawl_api_key)
    return FixtureWebsiteExtractionProvider()


# --- Email adapters (Phase 4; plan.md §5's fourth required interface) ---
#
# Real sending is opt-in and disabled by default (plan.md §11/§21) — see
# specs/phase-4-outreach.md FR-17. `disabled`/`sandbox` never make a network
# call; only `live` (Resend) does.


class DisabledEmailProvider:
    """Default adapter: makes no network call, sends nothing."""

    async def send(self, *, to_email: str, subject: str, body: str) -> EmailSendResult:
        return EmailSendResult(status="disabled")


class SandboxEmailProvider:
    """Simulates a send with no network call — for demoing the "would have
    sent" path without configuring a real provider.
    """

    async def send(self, *, to_email: str, subject: str, body: str) -> EmailSendResult:
        return EmailSendResult(status="sandboxed")


class ResendEmailProvider:
    """Real Resend-backed adapter. Opt-in; not live-tested in this
    environment — see specs/phase-4-outreach.md, Risks and Assumptions.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def send(self, *, to_email: str, subject: str, body: str) -> EmailSendResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": "onboarding@resend.dev",
                    "to": [to_email],
                    "subject": subject,
                    "text": body,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return EmailSendResult(status="sent", provider_message_id=payload.get("id"))


def get_email_provider(settings: Settings | None = None) -> EmailProvider:
    settings = settings or get_settings()
    if settings.email_mode == "live":
        assert settings.resend_api_key  # guaranteed by Settings validation
        return ResendEmailProvider(api_key=settings.resend_api_key)
    if settings.email_mode == "sandbox":
        return SandboxEmailProvider()
    return DisabledEmailProvider()
