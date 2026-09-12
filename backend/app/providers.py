"""LanguageModelProvider interface and adapters (plan.md §5).

Routers depend on `get_language_model_provider()`, never on a concrete
adapter, so campaign-planning logic never talks to a vendor SDK directly.
"""

import json
import re
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas import ICP, PlanExtraction, SearchPlanQuery


class LLMOutputError(Exception):
    """Raised when a provider's output can't be parsed or validated."""


class LanguageModelProvider(Protocol):
    async def generate_campaign_plan(
        self, *, brief: str, offer: str | None, target_lead_count: int
    ) -> PlanExtraction: ...


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


class GeminiLanguageModelProvider:
    """Real Gemini-backed adapter. Not exercised live in this environment —
    see specs/phase-2-campaigns.md, Risks and Assumptions.
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
            f"Brief: {brief}\n"
            f"Offer: {offer or '(not specified)'}\n"
            f"Target lead count: {target_lead_count}"
        )

        url = (
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
                response = await client.post(url, json=body)
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


def get_language_model_provider(settings: Settings | None = None) -> LanguageModelProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "gemini":
        assert settings.gemini_api_key  # guaranteed by Settings validation
        return GeminiLanguageModelProvider(
            api_key=settings.gemini_api_key, model=settings.gemini_model
        )
    return FixtureLanguageModelProvider()
